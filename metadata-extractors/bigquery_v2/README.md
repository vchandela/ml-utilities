# BigQuery Golden Query Feature Extractor v2

A comprehensive tool for identifying and analyzing the most valuable BigQuery queries in your organization through detailed feature extraction.

## Overview

The Golden Query Feature Extractor implements a 5-phase workflow to identify the top 50 most frequently executed query patterns from the last 180 days and extracts rich features for analysis and ranking.

### Workflow Phases

1. **Phase 0: Setup & Connection** - Establishes BigQuery connection using service account credentials
2. **Phase 1: Raw Job History Ingestion** - Fetches complete query history across all regions concurrently
3. **Phase 2: Candidate Identification** - Identifies top 50 most frequent raw SQL queries
4. **Phase 3: SQL Normalization & Grouping** - Creates canonical query "shapes" and groups executions
5. **Phase 4: Feature Extraction** - Extracts comprehensive features across 4 categories
6. **Phase 5: Output Generation** - Writes results to both JSON and CSV formats

## Prerequisites

### Environment Setup

Create a `.env` file in the project root with:

```bash
BIGQUERY_SA_CREDS_JSON='{"type": "service_account", "project_id": "your-project", ...}'
BIGQUERY_PROJECT_ID='your-gcp-project-id'
BIGQUERY_CLIENT_EMAIL='your-sa-email@your-project.iam.gserviceaccount.com'
```

### Dependencies

All dependencies are listed in `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `pandas>=2.0.0` - Data manipulation and CSV export
- `sqlglot>=18.5.1` - SQL parsing and normalization
- `google-cloud-bigquery>=3.0.0` - BigQuery API client
- `python-dotenv>=1.0.0` - Environment variable loading

## Usage

### Command Line Execution

From the project root directory:

```bash
# Run the feature extractor directly
python -m bigquery_v2.query_feature_extractor

# Or run via the main entry point
python -m bigquery_v2.main
```

### Programmatic Usage

```python
import asyncio
from bigquery_v2.query_feature_extractor import main

# Run the complete extraction process
asyncio.run(main())
```

## Output Files

The extractor generates two output files in the project root:

### 1. JSON Output: `golden_queries_poc_output.json`

Complete feature data in JSON format for programmatic analysis:

```json
[
  {
    "query_shape_id": "abc123...",
    "normalized_sql": "SELECT name, age FROM users WHERE id = ?",
    "total_execution_count": 47,
    "distinct_user_count": 8,
    "list_of_distinct_users": ["user1@company.com", ...],
    "execution_regularity_stdev": 3600.5,
    "creator_first_seen_user": "user1@company.com",
    "primary_user_most_frequent_executor": "user2@company.com",
    "source_tables": ["project.dataset.users"],
    "destination_table": null,
    "is_temporary_write": false,
    "join_count": 0,
    "cte_count": 1,
    "window_function_count": 0,
    "aggregation_presence": true,
    "subquery_count": 0,
    "statement_type": "SELECT"
  }
]
```

### 2. CSV Output: `golden_queries_poc_output.csv`

Tabular data optimized for spreadsheet analysis with logical column ordering:

| query_shape_id | statement_type | total_execution_count | distinct_user_count | ... |
|----------------|----------------|----------------------|-------------------- |-----|
| abc123...      | SELECT         | 47                   | 8                   | ... |

## Feature Categories

### 🔄 Execution & Usage Features
- `total_execution_count`: Number of executions of this query shape
- `distinct_user_count`: Number of unique users who executed this query
- `list_of_distinct_users`: Complete list of user emails
- `full_execution_history`: Complete timeline of executions
- `last_execution_timestamp`: Most recent execution
- `execution_regularity_stdev`: Statistical measure of execution frequency consistency

### 👥 Authorship & Ownership Features
- `creator_first_seen_user`: User who first executed this query shape
- `primary_user_most_frequent_executor`: User who executes this query most often

### 🔗 Lineage & Asset Interaction Features
- `source_tables`: All tables/datasets this query reads from
- `destination_table`: Where the query writes output (if any)
- `is_temporary_write`: Boolean flag for temporary table detection
- Placeholder fields for future golden score calculations

### 🏗️ Structural Complexity Features
- `join_count`: Number of JOIN operations
- `cte_count`: Number of Common Table Expressions (WITH clauses)
- `window_function_count`: Number of analytical window functions
- `aggregation_presence`: Boolean indicating GROUP BY presence
- `subquery_count`: Number of nested SELECT statements
- `statement_type`: Type of SQL operation (SELECT, CREATE, etc.)

## Technical Architecture

### SQL Normalization Process

The extractor uses advanced SQL normalization to group queries by structure rather than literal values:

1. **Parsing**: Uses sqlglot with BigQuery dialect for accurate parsing
2. **Literal Replacement**: Replaces all literal values (strings, numbers, dates) with `?` placeholders
3. **Standardized Formatting**: Applies consistent formatting and casing
4. **Stable Hashing**: Generates SHA256 hash as unique query shape ID

Example transformation:
```sql
-- Input
SELECT name, age FROM users WHERE id = 123 AND created_date = '2024-01-01'

-- Normalized Output
SELECT
  name,
  age
FROM users
WHERE
  id = ? AND created_date = ?
```

### Performance Optimizations

- **Concurrent Processing**: All region queries execute in parallel using asyncio
- **Memory Efficiency**: Uses pandas for efficient data manipulation
- **Early Filtering**: Identifies top candidates before expensive parsing operations
- **Robust Error Handling**: Continues processing even if individual regions fail

## Troubleshooting

### Common Issues

1. **Connection Errors**: Verify service account credentials and project permissions
2. **No Data Found**: Check date range and ensure query history exists
3. **Memory Issues**: For very large datasets, consider reducing the lookback period
4. **Permission Errors**: Ensure service account has BigQuery Job User and Data Viewer roles

### Logging

The extractor provides detailed logging at INFO level showing progress through each phase:

```
2024-01-01 10:00:00 - INFO - Phase 1: Starting raw job history ingestion...
2024-01-01 10:00:05 - INFO - Phase 1 complete: Ingested a total of 15,847 jobs.
2024-01-01 10:00:05 - INFO - ✅ Phase 1 complete: Raw job history ingestion finished
...
```

## License

This project is part of the ML Utilities metadata extractors collection.
