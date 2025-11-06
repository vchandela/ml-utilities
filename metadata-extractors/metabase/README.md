# Metabase Metadata Extractor

Extracts Metabase metadata as JSONL samples with **executed query results** (first 10 rows) for Questions, Models, and Metrics.

## Quick Start

**Prerequisites:** Python 3.10+, Metabase API key

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure (required)
export METABASE_API_KEY=mb_XXXXXXXXXXXXXXXX
export METABASE_URL=http://localhost:3000

# Run
python main.py
```

**Output:** JSONL files in `_metabase_dump/` + one-line summary with counts

## Configuration

### Required
- `METABASE_API_KEY` - API key with read permissions
- `METABASE_URL` - Metabase instance URL

### Optional
- `SAMPLE_LIMIT=5` - Samples per artifact (2-5, default: 5)
- `ROW_SAMPLE_LIMIT=10` - Query result rows (default: 10)

## Output Files

All files written to `_metabase_dump/` (truncated fresh each run):

| File | Artifact | Content |
|------|----------|---------|
| `collections.jsonl` | Collections | List samples (2-5) |
| `dashboards.jsonl` | Dashboards | List + detail samples (2-5) |
| `cards.jsonl` | Questions | List + detail + **10-row results** (2-5) |
| `models.jsonl` | Models | List + detail + **10-row results** (2-5) |
| `metrics.jsonl` | Metrics | List + detail + **10-row results** (2-5) |
| `segments.jsonl` | Segments | List samples (2-5) |
| `snippets.jsonl` | SQL Snippets | List samples (2-5) |

## JSONL Schema

Each line is a JSON object with this structure:

```json
{
  "artifact": "cards|models|metrics|dashboards|collections|segments|snippets",
  "kind": "list|detail|result",
  "id": 123,
  "data": { ... }
}
```

### Kind Types
- **`list`** - Basic metadata from list endpoint
- **`detail`** - Full definition from detail endpoint (dashboards, cards/models/metrics)
- **`result`** - Executed query results with columns and rows (cards/models/metrics only)

### Result Data Structure
For `kind=result` on Cards/Models/Metrics:
```json
{
  "data": {
    "columns": ["col1", "col2", "col3"],
    "rows": [
      {"col1": "value", "col2": 42, "col3": "2025-11-06"},
      ...
    ],
    "row_count_sampled": 10
  }
}
```

If query execution fails: `{"data": {"data_error": "error message"}}`

## What Gets Extracted

### 7 Artifact Types
1. **Collections** - Organizational structure and hierarchy
2. **Dashboards** - Dashboard configs with `ordered_cards` and parameter mappings
3. **Questions (Cards)** - Standard questions with queries and **actual result data**
4. **Models** - Data models with queries and **actual result data**
5. **Metrics** - Metric definitions with queries and **actual result data**
6. **Segments** - Named filters with MBQL definitions
7. **SQL Snippets** - Reusable SQL fragments and templates

### Summary Output
Prints one-line summary: `Collections: N | Dashboards: N | Questions: N | Models: N | Metrics: N | Segments: N | Snippets: N`

Counts reflect **all** items (not just samples).

## Notes
- Files are truncated fresh on each run
- Query execution uses empty parameters (`{"parameters": []}`)
- HTTP 200 and 202 status codes are both accepted for query execution
- Timeout: 30s for GET, 60s for POST (query execution)
