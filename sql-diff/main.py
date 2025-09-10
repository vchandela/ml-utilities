#!/usr/bin/env python3
import argparse, json, re
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Set, List, Dict
from collections import Counter

from sqlglot import parse_one, expressions as exp
from sqlglot.diff import diff as sg_diff
from sqlglot.optimizer import optimize
from sqlglot.errors import OptimizeError

def read_text(p): 
    with open(p, "r", encoding="utf-8") as f: 
        return f.read()

def load_schema(p: Optional[str]) -> Optional[Dict]:
    if not p: return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def canonical_sql(sql: str, dialect: str, schema: Optional[Dict], allow_unresolved: bool) -> str:
    try:
        expr = optimize(sql, dialect=dialect, schema=schema,
                        validate_qualify_columns=not allow_unresolved)
    except OptimizeError:
        if not allow_unresolved: raise
        expr = optimize(sql, dialect=dialect, schema=schema,
                        validate_qualify_columns=False)
    return expr.sql(dialect=dialect)

def ast_edit_script(sql_a: str, sql_b: str, dialect: str):
    a = parse_one(sql_a, read=dialect)
    b = parse_one(sql_b, read=dialect)
    return sg_diff(a, b, dialect=dialect, delta_only=True)

@dataclass(frozen=True)
class QuerySignature:
    leaf_tables: Tuple[str, ...]
    join_edges: Tuple[Tuple[str, str, str], ...]   # (left, right, join_type)
    agg_funcs: Tuple[Tuple[str, bool], ...]        # (func_name, is_distinct)
    set_ops: Tuple[str, ...]
    has_limit: bool
    has_order_by: bool
    date_window: Optional[Tuple[str, str]]

# --- NEW: collect CTE names (aliases defined in WITH clause) ---
def _collect_cte_names(root: exp.Expression) -> set[str]:
    ctes = set()
    for cte in root.find_all(exp.CTE):
        alias = cte.args.get("alias")
        if alias and alias.this:
            ctes.add(str(alias.this).lower())
    return ctes

def _normalize_table(t: exp.Table, keep_catalog: bool) -> str:
    cat = (t.catalog or "").strip()
    db  = (t.db or "").strip()
    nm  = (t.name or "").strip()
    parts = ([cat] if keep_catalog and cat else []) + [db, nm]
    parts = [p for p in parts if p]
    return ".".join(p.lower() for p in parts)

# Base-table heuristic: require db (dataset/schema) to be present.
def _is_base_table(t: exp.Table) -> bool:
    return bool(t.db)  # keeps `seekho.users_userprofile`, drops bare CTE names like `paid`, `duf`, etc.

def _rel_name(node: exp.Expression | None, keep_catalog: bool) -> str:
    if node is None:
        return ""
    if isinstance(node, exp.Table):
        return _normalize_table(node, keep_catalog)
    if isinstance(node, exp.Subquery):
        alias = node.args.get("alias")
        if alias and alias.this:
            return str(alias.this).lower()
    # try first table under this node
    for t in node.find_all(exp.Table):
        return _normalize_table(t, keep_catalog)
    return ""  # empty means "unknown/derived"

def _collect_leaf_tables(root: exp.Expression, keep_catalog: bool, cte_names: set[str]) -> list[str]:
    tables = []
    for t in root.find_all(exp.Table):
        name = _normalize_table(t, keep_catalog)
        # skip CTE references and non-qualified names
        if (t.name or "").lower() in cte_names:
            continue
        if not _is_base_table(t):
            continue
        tables.append(name)
    # sort deterministically
    return sorted(set(tables))

def _collect_join_edges(root: exp.Expression, keep_catalog: bool, cte_names: set[str]) -> list[tuple[str,str,str]]:
    """
    Record only edges where BOTH endpoints resolve to base warehouse tables
    (exclude CTEs and unknown/derived sides). Endpoints are unordered per edge.
    """
    edges = set()
    for j in root.find_all(exp.Join):
        join_type = (j.kind or "inner").lower()

        # left side name
        left_name = _rel_name(j.this, keep_catalog)
        # right side: explicit expression or infer by subtracting left subtree tables
        right_name = _rel_name(j.args.get("expression"), keep_catalog)
        if not right_name:
            left_tables = {_normalize_table(t, keep_catalog) for t in (j.this.find_all(exp.Table) if j.this else [])}
            inferred = None
            for t in j.find_all(exp.Table):
                n = _normalize_table(t, keep_catalog)
                if n not in left_tables:
                    inferred = n; break
            right_name = inferred or ""

        # filter out empties and CTEs
        if not left_name or not right_name:
            continue
        # if a side is a naked CTE (no db), drop
        if left_name.split(".")[0] in cte_names or right_name.split(".")[0] in cte_names:
            continue
        # require they look like db.table at least
        if left_name.count(".") < 1 or right_name.count(".") < 1:
            continue

        a, b = sorted([left_name, right_name])
        edges.add((a, b, join_type))

    # sort deterministically
    return sorted(edges)

AGG_NAMES = {"count", "sum", "avg", "min", "max", "approx_count_distinct"}

def _collect_agg_funcs(root: exp.Expression) -> Set[Tuple[str, bool]]:
    aggs = set()
    for f in root.find_all(exp.Func):
        name = (f.name or "").lower()
        if name in AGG_NAMES:
            is_distinct = bool(getattr(f, "distinct", False))
            aggs.add((name, is_distinct))
    return aggs

def _collect_set_ops(root: exp.Expression) -> List[str]:
    ops = []
    for node in root.find_all(exp.Union):
        ops.append("UNION ALL" if node.args.get("distinct") is False else "UNION")
    for node in root.find_all(exp.Intersect):
        ops.append("INTERSECT ALL" if node.args.get("distinct") is False else "INTERSECT")
    for node in root.find_all(exp.Except):
        ops.append("EXCEPT ALL" if node.args.get("distinct") is False else "EXCEPT")
    return ops

def _has_limit(root: exp.Expression) -> bool:
    return any(True for _ in root.find_all(exp.Limit))

def _has_order_by(root: exp.Expression) -> bool:
    return any(True for _ in root.find_all(exp.Order))

_DATE_LIT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _literal_date_text(node: exp.Expression) -> Optional[str]:
    # DATE 'YYYY-MM-DD' often becomes a Literal under SQLGlot's BigQuery dialect.
    if isinstance(node, exp.Literal):
        s = node.name.strip("'\"")
        return s if _DATE_LIT_RE.match(s) else None
    # CAST('YYYY-MM-DD' AS DATE) → check inner literal
    inner = node.args.get("this") if hasattr(node, "args") else None
    if isinstance(inner, exp.Literal):
        s = inner.name.strip("'\"")
        return s if _DATE_LIT_RE.match(s) else None
    return None

def _window_from_where(where_expr: exp.Expression) -> Optional[Tuple[str, str]]:
    """
    Extract a (low, high) from a single WHERE: supports BETWEEN and >= / <= pairs.
    Returns None if we can't find a clean literal pair.
    """
    lows, highs = [], []
    # BETWEEN low AND high
    for b in where_expr.find_all(exp.Between):
        low = _literal_date_text(b.args.get("this"))
        high = _literal_date_text(b.args.get("expression"))
        if low and high:
            lows.append(low); highs.append(high)
    # >= low, <= high
    for ge in where_expr.find_all(exp.GTE):
        s = _literal_date_text(ge.right)
        if s: lows.append(s)
    for le in where_expr.find_all(exp.LTE):
        s = _literal_date_text(le.right)
        if s: highs.append(s)
    if lows and highs:
        return (min(lows), max(highs))
    return None

def _final_selects(root: exp.Expression) -> List[exp.Select]:
    """
    Return the top-level SELECT leaves that directly feed the query result.
    Ignore CTE bodies. Unwrap ORDER at the top if present.
    Handle UNION/UNION ALL trees by gathering both branches' SELECTs.
    """
    # Unwrap WITH: the "this" under With is the actual query producing output
    node = root.this if isinstance(root, exp.With) else root
    # Unwrap top-level ORDER BY envelope if present
    if isinstance(node, exp.Order):
        node = node.this

    selects: List[exp.Select] = []

    def descend(n: exp.Expression):
        nonlocal selects
        # strip ORDER at branch level too
        if isinstance(n, exp.Order):
            return descend(n.this)
        if isinstance(n, exp.Union):
            descend(n.this)
            descend(n.expression)
        elif isinstance(n, exp.Select):
            selects.append(n)
        else:
            # In case dialect wraps in another node, collect direct Select children but
            # DON'T walk into CTEs again (we already unwrapped With at top level).
            for s in n.find_all(exp.Select):
                selects.append(s)

    descend(node)
    return selects

def _extract_final_date_window(root: exp.Expression) -> Optional[Tuple[str, str]]:
    """
    Effective output window = intersection of per-branch windows at the top level.
    For UNION/UNION ALL:
      low  = max(low_i)
      high = min(high_i)
    If a branch has no literal window, we can't assert a final window → return None.
    """
    # Only consider top-level SELECTs feeding the result set
    sels = _final_selects(root)
    branch_windows: List[Tuple[str, str]] = []
    for s in sels:
        w = s.args.get("where")
        if not w:
            return None  # a branch without WHERE → we don't know the final window
        wh = _window_from_where(w.this)
        if not wh:
            return None  # can't find clean literal bounds in this branch
        branch_windows.append(wh)

    if not branch_windows:
        return None

    # Intersection across branches
    lows  = [lo for lo, _ in branch_windows]
    highs = [hi for _, hi in branch_windows]
    low_final  = max(lows)
    high_final = min(highs)
    return (low_final, high_final) if low_final <= high_final else None

def build_signature(sql: str, dialect: str, schema: dict | None, allow_unresolved: bool, keep_catalog: bool) -> QuerySignature:
    try:
        root = optimize(sql, dialect=dialect, schema=schema, validate_qualify_columns=not allow_unresolved)
    except OptimizeError:
        root = optimize(sql, dialect=dialect, schema=schema, validate_qualify_columns=False)

    cte_names = _collect_cte_names(root)

    return QuerySignature(
        leaf_tables=tuple(_collect_leaf_tables(root, keep_catalog, cte_names)),
        join_edges=tuple(_collect_join_edges(root, keep_catalog, cte_names)),
        agg_funcs=tuple(sorted(_collect_agg_funcs(root))),
        set_ops=tuple(sorted(_collect_set_ops(root))),
        has_limit=_has_limit(root),
        has_order_by=_has_order_by(root),
        date_window=_extract_final_date_window(root),
    )

def compare_signatures(a: QuerySignature, b: QuerySignature):
    same = a == b
    delta = {}
    for k in asdict(a):
        if getattr(a, k) != getattr(b, k):
            delta[k] = {"golden": getattr(a, k), "intern": getattr(b, k)}
    return same, delta

def main():
    ap = argparse.ArgumentParser(description="SQL equivalence with SQLGlot (optimizer, AST diff, signature).")
    ap.add_argument("--sql1", required=True)
    ap.add_argument("--sql2", required=True)
    ap.add_argument("--schema")
    ap.add_argument("--dialect", default="bigquery")
    ap.add_argument("--allow-unresolved", action="store_true")
    ap.add_argument("--keep-catalog", action="store_true")
    args = ap.parse_args()

    sql_a = read_text(args.sql1)
    sql_b = read_text(args.sql2)
    schema = load_schema(args.schema)

    canon_a = canonical_sql(sql_a, args.dialect, schema, args.allow_unresolved)
    canon_b = canonical_sql(sql_b, args.dialect, schema, args.allow_unresolved)
    print("\n=== CANONICAL OPTIMIZED SQL — golden ===\n", canon_a)
    print("\n=== CANONICAL OPTIMIZED SQL — intern ===\n", canon_b)
    print("\nCanonical-optimized equality:", canon_a.strip() == canon_b.strip())

    edits = ast_edit_script(sql_a, sql_b, args.dialect)
    counts = Counter(type(e).__name__ for e in edits)
    print("\n=== AST DIFF (golden → intern) ===")
    print("Edit counts:", counts)
    for e in edits[:20]:
        print(" ", e)
    if len(edits) > 20:
        print(f"  ... ({len(edits) - 20} more edits)")

    sig_a = build_signature(sql_a, args.dialect, schema, args.allow_unresolved, args.keep_catalog)
    sig_b = build_signature(sql_b, args.dialect, schema, args.allow_unresolved, args.keep_catalog)

    same, delta = compare_signatures(sig_a, sig_b)
    print("\n=== SIGNATURE — golden ===")
    print(json.dumps(asdict(sig_a), indent=2))
    print("\n=== SIGNATURE — intern ===")
    print(json.dumps(asdict(sig_b), indent=2))
    print("\nSame intent (signature equal)?", same)
    if not same:
        print("\nDifferences by feature:")
        for k, v in delta.items():
            print(f" - {k}:")
            print("    golden:", v["golden"])
            print("    intern:", v["intern"])

if __name__ == "__main__":
    main()
