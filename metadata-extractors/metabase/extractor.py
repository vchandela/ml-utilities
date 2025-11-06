from __future__ import annotations

import json
import os
from pathlib import Path

import requests

BASE_URL = os.environ["METABASE_URL"]
API_KEY = os.environ["METABASE_API_KEY"]
DUMP_DIR = Path(__file__).parent / "_metabase_dump"
SAMPLE_MAX = 5  # keep files tiny; change to 2-5 as you like

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

    # ---- artifact fetchers ----
    def fetch_collections(self) -> int:
        items = self._get("/api/collection")
        with self._open_dump("collections") as fp:
            for obj in items[:SAMPLE_MAX]:
                self._write_line(fp, "collections", "list", obj, obj.get("id"))
        return len(items)

    def fetch_dashboards(self) -> int:
        items = self._get("/api/dashboard")
        with self._open_dump("dashboards") as fp:
            for obj in items[:SAMPLE_MAX]:
                did = obj.get("id")
                detail = self._get(f"/api/dashboard/{did}")
                self._write_line(fp, "dashboards", "detail", detail, did)
        return len(items)

    def fetch_cards_and_counts(self) -> tuple[int, int, int, int]:
        # returns (total_cards, questions, models, metrics)
        items = self._get("/api/card")
        q_count = m_count = me_count = 0
        q_written = m_written = me_written = 0

        with self._open_dump("cards") as fp_q, self._open_dump(
            "models"
        ) as fp_m, self._open_dump("metrics") as fp_me:
            for obj in items:
                cid = obj.get("id")
                ctype = (obj.get("type") or "").lower()

                if ctype == "model":
                    m_count += 1
                    if m_written < SAMPLE_MAX:
                        detail = self._get(f"/api/card/{cid}")
                        self._write_line(fp_m, "models", "detail", detail, cid)
                        m_written += 1
                elif ctype == "metric":
                    me_count += 1
                    if me_written < SAMPLE_MAX:
                        detail = self._get(f"/api/card/{cid}")
                        self._write_line(fp_me, "metrics", "detail", detail, cid)
                        me_written += 1
                else:
                    q_count += 1
                    if q_written < SAMPLE_MAX:
                        detail = self._get(f"/api/card/{cid}")
                        self._write_line(fp_q, "cards", "detail", detail, cid)
                        q_written += 1

        total_cards = len(items)
        return total_cards, q_count, m_count, me_count

    def fetch_segments(self) -> int:
        items = self._get("/api/segment")
        with self._open_dump("segments") as fp:
            for obj in items[:SAMPLE_MAX]:
                self._write_line(fp, "segments", "list", obj, obj.get("id"))
        return len(items)

    def fetch_snippets(self) -> int:
        items = self._get("/api/native-query-snippet")
        with self._open_dump("snippets") as fp:
            for obj in items[:SAMPLE_MAX]:
                self._write_line(fp, "snippets", "list", obj, obj.get("id"))
        return len(items)
