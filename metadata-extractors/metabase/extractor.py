from __future__ import annotations

import json
import os
from pathlib import Path

import requests

BASE_URL = os.environ["METABASE_URL"]
API_KEY = os.environ["METABASE_API_KEY"]
DUMP_DIR = Path(__file__).parent / "_metabase_dump"

# How many items per artifact to sample (2..5)
try:
    _n = int(os.environ.get("SAMPLE_LIMIT", "5"))
except ValueError:
    _n = 5
SAMPLE_LIMIT = max(2, min(_n, 5))

# How many result rows to keep per executed card
try:
    ROW_SAMPLE_LIMIT = int(os.environ.get("ROW_SAMPLE_LIMIT", "10"))
except ValueError:
    ROW_SAMPLE_LIMIT = 10

HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


class MetabaseExtractor:
    def __init__(self, base_url: str = BASE_URL, headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.h = headers if headers is not None else HEADERS
        DUMP_DIR.mkdir(parents=True, exist_ok=True)

    # ---- low-level HTTP ----
    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        r = requests.get(url, headers=self.h, timeout=30)
        if r.status_code != 200:
            raise SystemExit(f"GET {path} -> {r.status_code} {r.text[:300]}")
        return r.json()

    def _post(self, path: str, json_body: dict):
        url = f"{self.base_url}{path}"
        r = requests.post(url, headers=self.h, json=json_body, timeout=60)
        if r.status_code not in (200, 202):
            raise RuntimeError(f"POST {path} -> {r.status_code} {r.text[:300]}")
        return r.json()

    # ---- dump helpers ----
    def _open_dump(self, name: str):
        fpath = DUMP_DIR / f"{name}.jsonl"
        return fpath.open("w", encoding="utf-8")  # truncate each run

    def _write_line(
        self, fp, artifact: str, kind: str, data: dict, obj_id: int | None = None
    ):
        line = {"artifact": artifact, "kind": kind, "data": data}
        if obj_id is not None:
            line["id"] = obj_id
        fp.write(json.dumps(line, ensure_ascii=False) + "\n")

    # ---- result sampling for cards ----
    def _sample_result_for_card(
        self, card_id: int, row_cap: int = ROW_SAMPLE_LIMIT
    ) -> dict:
        """Execute a card's query and return first N rows as structured data."""
        try:
            result = self._post(f"/api/card/{card_id}/query", {"parameters": []})
        except Exception as e:
            return {"data_error": str(e)[:200]}

        data = result.get("data") or {}
        cols = data.get("cols") or []
        rows = data.get("rows") or []
        names = [c.get("display_name") or c.get("name") for c in cols]

        obj_rows = []
        for r in rows[:row_cap]:
            if isinstance(r, list):
                obj_rows.append(
                    {n: (r[i] if i < len(r) else None) for i, n in enumerate(names)}
                )
            elif isinstance(r, dict):
                obj_rows.append(r)
            else:
                obj_rows.append({"_value": r})

        return {
            "columns": names,
            "rows": obj_rows,
            "row_count_sampled": min(len(rows), row_cap),
        }

    # ---- artifact fetchers ----
    def fetch_collections(self) -> int:
        items = self._get("/api/collection")
        with self._open_dump("collections") as fp:
            for obj in items[:SAMPLE_LIMIT]:
                self._write_line(fp, "collections", "list", obj, obj.get("id"))
        return len(items)

    def fetch_dashboards(self) -> int:
        items = self._get("/api/dashboard")
        with self._open_dump("dashboards") as fp:
            for obj in items[:SAMPLE_LIMIT]:
                did = obj.get("id")
                # Write list sample
                self._write_line(fp, "dashboards", "list", obj, did)
                # Write detail sample with ordered_cards, parameters, etc.
                detail = self._get(f"/api/dashboard/{did}")
                self._write_line(fp, "dashboards", "detail", detail, did)
        return len(items)

    def fetch_cards_and_counts(self) -> tuple[int, int, int, int]:
        # returns (total_cards, questions, models, metrics)
        items = self._get("/api/card")
        q_count = m_count = me_count = 0
        q_written = m_written = me_written = 0

        with (
            self._open_dump("cards") as fp_q,
            self._open_dump("models") as fp_m,
            self._open_dump("metrics") as fp_me,
        ):
            for obj in items:
                cid = obj.get("id")
                ctype = (obj.get("type") or "").lower()

                if ctype == "model":
                    m_count += 1
                    if m_written < SAMPLE_LIMIT:
                        # Write list sample
                        self._write_line(fp_m, "models", "list", obj, cid)
                        # Write detail sample
                        detail = self._get(f"/api/card/{cid}")
                        self._write_line(fp_m, "models", "detail", detail, cid)
                        # Write result sample (first 10 rows)
                        sample = self._sample_result_for_card(cid)
                        self._write_line(fp_m, "models", "result", sample, cid)
                        m_written += 1
                elif ctype == "metric":
                    me_count += 1
                    if me_written < SAMPLE_LIMIT:
                        self._write_line(fp_me, "metrics", "list", obj, cid)
                        detail = self._get(f"/api/card/{cid}")
                        self._write_line(fp_me, "metrics", "detail", detail, cid)
                        sample = self._sample_result_for_card(cid)
                        self._write_line(fp_me, "metrics", "result", sample, cid)
                        me_written += 1
                else:
                    q_count += 1
                    if q_written < SAMPLE_LIMIT:
                        self._write_line(fp_q, "cards", "list", obj, cid)
                        detail = self._get(f"/api/card/{cid}")
                        self._write_line(fp_q, "cards", "detail", detail, cid)
                        sample = self._sample_result_for_card(cid)
                        self._write_line(fp_q, "cards", "result", sample, cid)
                        q_written += 1

        total_cards = len(items)
        return total_cards, q_count, m_count, me_count

    def fetch_segments(self) -> int:
        items = self._get("/api/segment")
        with self._open_dump("segments") as fp:
            for obj in items[:SAMPLE_LIMIT]:
                self._write_line(fp, "segments", "list", obj, obj.get("id"))
        return len(items)

    def fetch_snippets(self) -> int:
        items = self._get("/api/native-query-snippet")
        with self._open_dump("snippets") as fp:
            for obj in items[:SAMPLE_LIMIT]:
                self._write_line(fp, "snippets", "list", obj, obj.get("id"))
        return len(items)
