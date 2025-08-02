# Metadata Extractors

High-performance Python tools for extracting metadata from various data platforms.

## Components

### BigQuery Metadata Counter

A tool that efficiently counts BigQuery resources across your Google Cloud project.

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

---

### Redash Metadata Extractor

A tool that efficiently extracts metadata from Redash instances.

#### What It Does

Provides **three key counts**:
- **Dashboards**: Total number of dashboards
- **Widgets**: Number of widgets with associated queries (excludes text-only widgets)
- **Saved Queries**: Total number of saved queries in the Redash instance

#### Quick Start

1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Set Up Environment**: Add your Redash credentials to `.env`:
   ```bash
   REDASH_API_URL=https://your.redash.instance
   REDASH_API_KEY=your_redash_api_key
   ```
3. **Run**: `python redash/main.py`

#### Sample Output

```
🔧 Redash Metadata Extractor
========================================
🌐 Redash URL: https://your.redash.instance
🔑 API Key: ************5678

🔄 Extracting metadata...
✅ Extraction completed in 4.35 seconds!

📊 Results:
   - Dashboards: 15
   - Widgets: 42
   - Saved Queries: 128
```

#### Features

- ⚡ **Fast**: Concurrent processing for optimal performance
- 🔄 **Robust**: Automatic retry logic with exponential backoff
- 🎯 **Smart filtering**: Only counts widgets that have associated queries
- 🌐 **Version-aware**: Automatically detects Redash version for compatibility

For detailed documentation, see [redash/README.md](redash/README.md).

---

### Bitbucket Connector

A high-performance tool that extracts aggregate counts from Bitbucket workspaces using concurrent processing.

#### What It Does

Provides **four key counts**:
- **Repositories**: Total number of repositories in the workspace
- **Files**: Number of text files (<100MB, excludes Git metadata)
- **Pull Requests**: Total number of pull requests (open and closed)
- **Commits**: Total number of commits across all repositories

#### Key Features

- ⚡ **Ultra-fast**: Concurrent processing with configurable parallelism (default: 20 parallel requests)
- 📁 **Smart filtering**: Only counts text files, excludes binaries and Git metadata
- 🔄 **Robust**: Automatic token refresh and retry logic with exponential backoff
- 📊 **Comprehensive**: Processes up to 1000 repositories per workspace
- 🎯 **Count-focused**: Returns clean aggregate numbers instead of detailed metadata

#### Performance Optimizations

**PR Counting**: Uses `aiohttp` with field filtering (`pagelen=100`, `fields=` query params) and concurrent page fetching to dramatically reduce processing time from ~100 seconds to ~2 seconds for large repositories.

**Fast Path Alternative** *(not implemented, for future reference)*: For repositories where you trust all PRs have valid fields, a single API call can get the total count:
```python
# Single call to get total PR count (no validation)
params = {"state": "ALL", "pagelen": 1, "fields": "size"}
response = await session.get(url, params=params)
total_count = (await response.json()).get("size", 0)
# Rounds-trips: 1, Payload: ~200 bytes
```

#### Quick Start

1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Set Up Environment**: Add your Bitbucket credentials to `.env`:
   ```bash
   BITBUCKET_CLIENT_ID=your_bitbucket_client_id
   BITBUCKET_CLIENT_SECRET=your_bitbucket_client_secret
   BITBUCKET_ACCESS_TOKEN=your_bitbucket_access_token
   BITBUCKET_REFRESH_TOKEN=your_bitbucket_refresh_token
   ```
3. **Run**: `python bitbucket/main.py`

#### Sample Output

```
🔧 Bitbucket Repository Metrics
========================================
🌐 Workspace: your-workspace-name
🔑 Processing first workspace found

🔄 Fetching repository metrics...
✅ Bitbucket metrics collection completed in 15.32 seconds!

--- Bitbucket Workspace Metrics ---
Workspace: your-workspace-name
----------------------------------
Global Counts:
  Total Repositories: 42
  Total Files (text, <100MB): 15,847
  Total Pull Requests: 1,203
  Total Commits: 8,956
----------------------------------

Repository-Level Breakdown:
  Repo: project-alpha
    Files: 156
    PRs: 23
    Commits: 245
  Repo: project-beta
    Files: 89
    PRs: 12
    Commits: 167
  ...
```

#### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BITBUCKET_CLIENT_ID` | OAuth client ID | Required |
| `BITBUCKET_CLIENT_SECRET` | OAuth client secret | Required |
| `BITBUCKET_ACCESS_TOKEN` | OAuth access token | Required |
| `BITBUCKET_REFRESH_TOKEN` | OAuth refresh token | Required |
| `BITBUCKET_MAX_PARALLEL` | Max parallel API requests | 20 |
| `LOCAL_REPO_DIR` | Directory for cloned repos | `./cloned_repos` |

#### Performance & Constraints

- **Repository Limit**: Processes up to 1000 repositories per workspace
- **File Constraints**: 
  - Maximum file size: 100MB
  - Text files only (MIME type + content analysis)
  - Excludes `.git/` directories and metadata
- **Workspace Processing**: Processes only the first workspace found
- **Concurrency**: Configurable parallel processing for optimal performance

#### Authentication

Uses Bitbucket OAuth 2.0 flow:
1. Create OAuth app in Bitbucket to get client ID and secret
2. Obtain access and refresh tokens through Bitbucket's OAuth flow
3. Tokens are automatically refreshed using client credentials when expired

#### Testing

Run the integration test:
```bash
python bitbucket/test_bitbucket.py
``` 