# Redash Metadata Extractor

A high-performance Python tool that efficiently extracts metadata from Redash instances.

## What It Does

Provides **three key counts**:
- **Dashboards**: Total number of dashboards
- **Widgets**: Number of widgets with associated queries (excludes text-only widgets)
- **Saved Queries**: Total number of saved queries in the Redash instance

## Key Features

- ⚡ **Fast**: Concurrent processing for optimal performance
- 🔄 **Robust**: Automatic retry logic with exponential backoff
- 🎯 **Smart filtering**: Only counts widgets that have associated queries
- 🌐 **Version-aware**: Automatically detects Redash version for compatibility
- 📊 **Clean output**: Focused summary instead of overwhelming JSON dumps

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Copy `.env.example` to `.env` and fill in your credentials:
```bash
REDASH_API_URL=https://your.redash.instance
REDASH_API_KEY=your_redash_api_key
```

### 3. Run
```bash
python redash/main.py
```

## Sample Output

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

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `REDASH_API_URL` | Your Redash instance URL | Yes |
| `REDASH_API_KEY` | API key with read access | Yes |

## Performance Features

- **Concurrent processing**: Runs all operations in parallel
- **Automatic pagination**: Handles large datasets efficiently
- **Smart retry logic**: Recovers from temporary network issues
- **Version detection**: Adapts to different Redash versions automatically

## Requirements

- Python 3.8+
- Redash instance access
- API key with read permissions for dashboards and queries

## API Permissions Required

Your Redash API key needs access to:
- `/api/dashboards` - List and read dashboard details
- `/api/queries` - List saved queries
- `/api/status` - Check connection and version

## Testing

Run the integration test:
```bash
python redash/test_redash.py
```

This will test the connector with your configured credentials or use placeholders for basic functionality testing.

## Architecture

Built for production use with:
- Async/await concurrency patterns
- Tenacity-based retry logic for API calls
- Clean error handling and structured logging
- Modular, testable code structure 