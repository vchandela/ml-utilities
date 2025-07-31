# BigQuery Metadata Counter

A high-performance Python tool that efficiently counts BigQuery resources across your Google Cloud project.

## What It Does

Provides **three key counts**:
- **Datasets**: Total number of datasets
- **Logical Tables**: Physical tables collapsed by date-sharding (e.g., `events_20240101`, `events_20240102` → counted as 1)  
- **Unique Queries**: Distinct queries executed in the last 800 days (configurable)

## Key Features

- ⚡ **Ultra-fast**: Counts 7,000+ tables in ~9 seconds using concurrent processing
- 🌍 **Multi-region aware**: Automatically detects and queries all BigQuery regions
- 📊 **Smart consolidation**: Handles date-sharded tables intelligently
- 🔒 **Secure**: Uses Google Cloud service account authentication
- 🎯 **Focused output**: Clean summary instead of overwhelming JSON dumps

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Copy `.env.example` to `.env` and fill in your credentials:
```bash
BIGQUERY_SA_CREDS_JSON={"type":"service_account",...}
BIGQUERY_PROJECT_ID="your-project-id"  
BIGQUERY_CLIENT_EMAIL="your-service-account@project.iam.gserviceaccount.com"
QUERY_DAYS_BACK=800
```

### 3. Run
```bash
python bigquery/main.py
```

## Sample Output

```
🔧 BigQuery Metadata Counter
========================================
📁 Project: your-project-id
👤 Service Account: service-account@project.iam.gserviceaccount.com  
🗓️ Query History: Last 800 days

🔄 Counting resources...
✅ Counting completed in 9.20 seconds!

📊 Results:
   - Datasets: 36
   - Logical Tables: 988
   - Unique Queries (last 800 days): 410862
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BIGQUERY_SA_CREDS_JSON` | Service account credentials JSON | Required |
| `BIGQUERY_PROJECT_ID` | Your GCP project ID | Required |
| `BIGQUERY_CLIENT_EMAIL` | Service account email | Required |
| `QUERY_DAYS_BACK` | Days to look back for query history | 800 |

## Performance

- **Concurrent processing**: Runs all operations in parallel
- **Region optimization**: Automatically queries correct BigQuery regions
- **Smart caching**: Shares region discovery across operations
- **Efficient queries**: Uses database-level aggregation instead of client-side processing

## Requirements

- Python 3.8+
- Google Cloud BigQuery access
- Service account with BigQuery Data Viewer permissions

## Architecture

Built for production use with:
- Async/await concurrency patterns
- Automatic retry logic for API calls  
- Clean error handling and logging
- Modular, testable code structure 