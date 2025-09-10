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

def _normalize_table(t: exp.Table, keep_catalog: bool) -> str:
    cat = (t.catalog or "").strip()
    db  = (t.db or "").strip()
    nm  = (t.name or "").strip()
    parts = ([cat] if keep_catalog and cat else []) + [db, nm]
    parts = [p for p in parts if p]
    return ".".join(p.lower() for p in parts)

def _rel_name(node: Optional[exp.Expression], keep_catalog: bool) -> str:
    """Stable name for any relational node (Table/Subquery/Join/None)."""
    if node is None:
        return "<unknown>"
    if isinstance(node, exp.Table):
        return _normalize_table(node, keep_catalog)
    if isinstance(node, exp.Subquery):
        # Prefer alias if present; else try first table inside; else generic
        alias = node.args.get("alias")
        if alias and alias.this:
            return str(alias.this).lower()
        for t in node.find_all(exp.Table):
            return _normalize_table(t, keep_catalog)
        return "<subquery>"
    # Fallback: first table inside this subtree
    for t in node.find_all(exp.Table):
        return _normalize_table(t, keep_catalog)
    # Last resort: trimmed text (kept short & lowercased)
    s = node.sql(dialect="") if hasattr(node, "sql") else str(node)
    return re.sub(r"\s+", " ", s).strip()[:80].lower() or "<expr>"

def _collect_leaf_tables(root: exp.Expression, keep_catalog: bool) -> Set[str]:
    return {_normalize_table(t, keep_catalog) for t in root.find_all(exp.Table)}

def _collect_join_edges(root: exp.Expression, keep_catalog: bool) -> Set[Tuple[str, str, str]]:
    """
    Robust join edge extractor:
    - If right side is missing/derived, infer it by scanning tables in the join
      that are not in the left subtree.
    - Endpoints are unordered (we sort the pair) so different join orders compare equal.
    """
    edges: Set[Tuple[str, str, str]] = set()
    for j in root.find_all(exp.Join):
        join_type = (j.kind or "inner").lower()
        left_name  = _rel_name(j.this, keep_catalog)
        # try the explicit right arm
        right_name = _rel_name(j.args.get("expression"), keep_catalog)

        # if the right is unknown, infer from difference of tables inside the join
        if right_name in ("<unknown>", "<expr>"):
            left_tables = {
                _normalize_table(t, keep_catalog) for t in (j.this.find_all(exp.Table) if j.this else [])
            }
            inferred = None
            for t in j.find_all(exp.Table):
                name = _normalize_table(t, keep_catalog)
                if name not in left_tables:
                    inferred = name
                    break
            right_name = inferred or right_name

        a, b = sorted([left_name, right_name])
        edges.add((a, b, join_type))
    return edges

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
    if isinstance(node, exp.Literal):
        s = node.name.strip("'\"")
        return s if _DATE_LIT_RE.match(s) else None
    inner = node.args.get("this") if hasattr(node, "args") else None
    if isinstance(inner, exp.Literal):
        s = inner.name.strip("'\"")
        return s if _DATE_LIT_RE.match(s) else None
    return None

def _extract_date_window(root: exp.Expression) -> Optional[Tuple[str, str]]:
    lows, highs = [], []
    for where in root.find_all(exp.Where):
        w = where.this
        for b in w.find_all(exp.Between):
            low = _literal_date_text(b.args.get("this"))
            high = _literal_date_text(b.args.get("expression"))
            if low and high:
                lows.append(low); highs.append(high)
        for ge in w.find_all(exp.GTE):
            s = _literal_date_text(ge.right);  
            if s: lows.append(s)
        for le in w.find_all(exp.LTE):
            s = _literal_date_text(le.right);  
            if s: highs.append(s)
    if lows and highs:
        return (min(lows), max(highs))
    return None

def build_signature(sql: str, dialect: str, schema: Optional[Dict], allow_unresolved: bool, keep_catalog: bool) -> QuerySignature:
    try:
        root = optimize(sql, dialect=dialect, schema=schema,
                        validate_qualify_columns=not allow_unresolved)
    except OptimizeError:
        root = optimize(sql, dialect=dialect, schema=schema,
                        validate_qualify_columns=False)
    return QuerySignature(
        leaf_tables=tuple(sorted(_collect_leaf_tables(root, keep_catalog))),
        join_edges=tuple(sorted(_collect_join_edges(root, keep_catalog))),
        agg_funcs=tuple(sorted(_collect_agg_funcs(root))),
        set_ops=tuple(sorted(_collect_set_ops(root))),
        has_limit=_has_limit(root),
        has_order_by=_has_order_by(root),
        date_window=_extract_date_window(root),
    )

def compare_signatures(a: QuerySignature, b: QuerySignature):
    same = a == b
    delta = {}
    for k in asdict(a):
        if getattr(a, k) != getattr(b, k):
            delta[k] = {"A": getattr(a, k), "B": getattr(b, k)}
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
    print("\n=== CANONICAL OPTIMIZED SQL — A ===\n", canon_a)
    print("\n=== CANONICAL OPTIMIZED SQL — B ===\n", canon_b)
    print("\nCanonical-optimized equality:", canon_a.strip() == canon_b.strip())

    edits = ast_edit_script(sql_a, sql_b, args.dialect)
    counts = Counter(type(e).__name__ for e in edits)
    print("\n=== AST DIFF (A → B) ===")
    print("Edit counts:", counts)
    for e in edits[:20]:
        print(" ", e)
    if len(edits) > 20:
        print(f"  ... ({len(edits) - 20} more edits)")

    sig_a = build_signature(sql_a, args.dialect, schema, args.allow_unresolved, args.keep_catalog)
    sig_b = build_signature(sql_b, args.dialect, schema, args.allow_unresolved, args.keep_catalog)

    same, delta = compare_signatures(sig_a, sig_b)
    print("\n=== SIGNATURE — A ===")
    print(json.dumps(asdict(sig_a), indent=2))
    print("\n=== SIGNATURE — B ===")
    print(json.dumps(asdict(sig_b), indent=2))
    print("\nSame intent (signature equal)?", same)
    if not same:
        print("\nDifferences by feature:")
        for k, v in delta.items():
            print(f" - {k}:")
            print("    A:", v["A"])
            print("    B:", v["B"])

if __name__ == "__main__":
    main()
