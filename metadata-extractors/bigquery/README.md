# BigQuery Metadata Extractor

This connector extracts comprehensive metadata from Google BigQuery including datasets, tables, views, and query history.

## Features

- **Dataset Metadata**: Extracts dataset information including descriptions, labels, creation dates, and table counts
- **Table Metadata**: Detailed table information including schema, partitioning, clustering, row counts, and size
- **Query History**: Recent query execution history with complexity scoring
- **Document Counts**: Categorized counts of different BigQuery object types
- **Connection Testing**: Validates credentials and connectivity

## Requirements

Install the required dependencies from the root directory:

```bash
pip install -r ../requirements.txt
```

## Authentication

This connector requires Google Cloud service account credentials with BigQuery access. You need:

1. A service account with BigQuery permissions
2. The service account JSON key file
3. Project ID where BigQuery datasets reside

### Required Permissions

The service account needs these IAM roles:
- `BigQuery Data Viewer` - to read data and metadata
- `BigQuery Job User` - to execute queries for metadata extraction

## Usage

### Basic Usage

```python
import asyncio
import json
from metadata import extract_metadata

# Prepare credentials
credentials = {
    "sa_creds_json": {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        "client_email": "service-account@your-project.iam.gserviceaccount.com",
        "client_id": "client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    },
    "project_id": "your-project-id",
    "client_email": "service-account@your-project.iam.gserviceaccount.com"
}

# Extract metadata
async def main():
    try:
        metadata = await extract_metadata(credentials)
        print(json.dumps(metadata, indent=2, default=str))
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

### Environment Variables

You can also use environment variables:

```bash
export BIGQUERY_SA_CREDS_JSON='{"type":"service_account",...}'
export BIGQUERY_PROJECT_ID="your-project-id"
export BIGQUERY_CLIENT_EMAIL="service-account@your-project.iam.gserviceaccount.com"
```

Then run:

```bash
python main.py
```



### Selective Extraction

Control what metadata to extract:

```python
metadata = await extract_metadata(
    credentials,
    include_datasets=True,
    include_tables=True,
    include_queries=True,
    query_days_back=30  # Get 30 days of query history
)
```

## Output Structure

The extractor returns a dictionary with the following structure:

```json
{
  "connection_test": {
    "success": true,
    "message": "Connection successful. Found 5 datasets."
  },
  "document_counts": {
    "datasets": 5,
    "tables": 23,
    "views": 8,
    "external_tables": 2,
    "materialized_views": 1
  },
  "datasets": [
    {
      "dataset_id": "my_dataset",
      "description": "Dataset description",
      "owner": null,
      "created_at": "2023-01-01T00:00:00",
      "default_table_expiration": null,
      "labels": {"env": "prod"},
      "table_count": 15
    }
  ],
  "tables": [
    {
      "table_name": "users",
      "dataset_name": "my_dataset",
      "project_id": "my-project",
      "description": "User data table",
      "owner": null,
      "created_at": "2023-01-01T00:00:00",
      "modified_at": "2023-12-01T00:00:00",
      "row_count": 1000000,
      "size_bytes": 50000000,
      "partition_info": {
        "type": "DAY",
        "field": "created_date",
        "expiration_ms": null
      },
      "clustering_keys": ["user_id"],
      "columns": [
        {
          "name": "user_id",
          "type": "STRING",
          "mode": "REQUIRED",
          "description": "Unique user identifier"
        }
      ]
    }
  ],
  "queries": [
    {
      "query_id": "job_123456",
      "query_text": "SELECT COUNT(*) FROM my_dataset.users",
      "user_email": "user@example.com",
      "start_time": "2023-12-01T10:00:00",
      "end_time": "2023-12-01T10:00:05",
      "duration_ms": 5000,
      "bytes_scanned": 1000000,
      "cached": false,
      "status": "DONE",
      "referenced_tables": ["my_dataset.users"],
      "importance_score": 1.5
    }
  ]
}
```

## Error Handling

The connector includes comprehensive error handling:

- **Connection Errors**: Validates credentials and tests connectivity
- **Permission Errors**: Handles insufficient permissions gracefully
- **API Errors**: Manages BigQuery API limits and quotas
- **Data Errors**: Handles missing or malformed metadata

## Logging

The connector uses Python's logging module. Set the log level via:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Limitations

- Query history is limited to the last 1000 queries
- Large datasets may take time to process completely
- Some metadata (like owner information) is not available through BigQuery APIs
- Region must be specified correctly for INFORMATION_SCHEMA queries 