# Metabase Metadata Extractor (minimal JSONL)

## Prereqs
- Python 3.10+
- Metabase running at http://localhost:3000
- API key with read permissions (we default to your provided key)

## Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configure (optional)
```bash
# Override the default key if needed
export METABASE_API_KEY=mb_XXXXXXXXXXXXXXXX
# Override base URL if your port/host differs
export METABASE_URL=http://localhost:3000
```

## Run
```bash
python -m main
```

Or from the parent directory:
```bash
python -m metabase.main
```

## Output
- JSONL files in `metabase/_metabase_dump/` (truncated freshly each run)
- Each artifact file contains **up to 5 example payloads** (change `SAMPLE_MAX` in code to 2–5 if you prefer fewer)
- One summary line with counts

## Output Files
```
metabase/_metabase_dump/collections.jsonl
metabase/_metabase_dump/dashboards.jsonl
metabase/_metabase_dump/cards.jsonl         # sample QUESTION cards (detail only; up to 5)
metabase/_metabase_dump/models.jsonl        # sample MODEL cards (detail only; up to 5)
metabase/_metabase_dump/metrics.jsonl       # sample METRIC cards (detail only; up to 5)
metabase/_metabase_dump/segments.jsonl
metabase/_metabase_dump/snippets.jsonl
```

## Artifacts Extracted
1. **Collections** - organizational structure
2. **Dashboards** - dashboard definitions with ordered_cards
3. **Questions/Cards** - standard questions
4. **Models** - data models (special card type)
5. **Metrics** - metric definitions (special card type)
6. **Segments** - named filters with MBQL
7. **SQL Snippets** - reusable SQL fragments

