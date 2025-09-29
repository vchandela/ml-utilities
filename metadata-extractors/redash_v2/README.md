# Redash Golden Asset Ranking System

A system that programmatically analyzes a Redash instance to score and rank its most valuable "golden" assets (queries and dashboards).

## Implementation Status

### ✅ Phase 1: Foundational Layer - High-Performance Data Extraction
**Status: COMPLETED**

Implements the foundational infrastructure for the Golden Asset Ranking System:

#### ✅ 2.1 Secure Configuration and Connection
- Environment variable configuration (`REDASH_API_URL`, `REDASH_API_KEY`)
- Credential validation with clear error messages
- Persistent `requests.Session` with authentication headers
- Connection testing via `/api/session` endpoint

#### ✅ 2.2 Robust Redash Version Detection
- Automatic version detection from session data
- Boolean flag `use_slug_for_dashboards` for API compatibility
- Handles version parsing edge cases with fallbacks

#### ✅ 2.3 Concurrent Metadata Ingestion and Dependency Mapping
- **Master Lists**: Parallel fetching of all dashboards and queries using `asyncio.gather`
- **Detailed Objects**: Concurrent fetching of detailed dashboard and query data
- **Dependency Mapping**: Real-time building of three critical maps:
  - `query_to_dashboards_map`: `{query_id: {dashboard_id_1, dashboard_id_2}}`
  - `query_to_charts_map`: `{query_id: {widget_id_1, widget_id_2}}`
  - `dashboard_to_queries_map`: `{dashboard_id: {query_id_1, query_id_2}}`

### ✅ Phase 2: Golden Saved Query Scoring Logic
**Status: COMPLETED**

Implements the complete query scoring system with transparent component scores:

#### ✅ 3.1 Raw Feature Assembly
- Extracts comprehensive features from detailed query objects
- Includes: `id`, `name`, `description`, `query` (SQL), `created_at`, `user_name`, `schedule`, `last_executed_at`
- Calculates downstream dependency counts using Phase 1 dependency maps
- Creates feature-rich dictionaries ready for scoring

#### ✅ 3.2 Component Score Calculations
- **✅ Impact Score (Max: 6 points)**:
  - Uses downstream dependencies as proxy for importance
  - Log-transform dampens outliers: `log(1 + count)`
  - 80/20 weighting: dashboards (0.8) vs charts (0.2)
  - Normalized to 0-6 point scale
  
- **✅ Recency Score (Max: 3 points)**:
  - Exponential decay: `3 * exp(-0.02 * days_since_last_execution)`
  - Rewards queries with fresh data
  - Handles multiple timestamp formats gracefully
  
- **✅ Curation & Trust Score (Max: 1 point)**:
  - 0.5 points for having description (documentation)
  - 0.5 points for having schedule (operational reliability)

#### ✅ 3.3 Final Score Calculation and Storage
- Combines all component scores: `golden_query_score = impact + recency + curation`
- **All component scores stored** in feature dictionaries (transparency requirement)
- Queries sorted by final golden score for easy analysis

### ✅ Phase 3: Golden Dashboard Scoring Logic
**Status: COMPLETED**

Implements the complete dashboard scoring system that evaluates dashboards based on their content quality, maintenance, and curation:

#### ✅ 4.1 Raw Feature Assembly
- Extracts comprehensive features from detailed dashboard objects
- Includes: `id`, `name`, `slug`, `created_at`, `updated_at`, `user_name`, `widgets`, `is_draft`, `tags`
- Prepares feature-rich dictionaries ready for scoring

#### ✅ 4.2 Component Score Calculations
- **✅ Content Quality Score (Max: 7 points)**:
  - A dashboard's value is the sum of its parts
  - Uses `dashboard_to_queries_map` to find dependent queries
  - Sums `golden_query_scores` for raw content score
  - Normalizes to 7-point scale: `7 * (raw_score / max_raw_score)`
  - Rewards dashboards that synthesize multiple high-quality sources
  
- **✅ Recency Score (Max: 2 points)**:
  - Exponential decay: `2 * exp(-0.01 * days_since_last_updated)`
  - Rewards actively maintained dashboards
  - Gentler decay than queries (0.01 vs 0.02 coefficient)
  
- **✅ Curation Score (Max: 1 point)**:
  - Uses "top-left text box" heuristic for descriptions
  - Finds top-leftmost widget by position (`row`, `col`)
  - 1.0 points for text widget with content (description)
  - 0.5 points for empty text widget (placeholder)
  - 0.0 points for no text widgets

#### ✅ 4.3 Final Score Calculation and Storage
- Combines all component scores: `golden_dashboard_score = content_quality + recency + curation`
- **All component scores stored** in feature dictionaries (transparency requirement)
- Dashboards sorted by final golden score for easy analysis

### ✅ Phase 4: Final Output Generation
**Status: COMPLETED**

Implements the final output generation system that creates ranked CSV and JSON files with full transparency:

#### ✅ 5.1 DataFrame Creation and Sorting
- Converts scored feature dictionaries to pandas DataFrames
- Sorts by golden scores in descending order (highest first)
- Handles both queries and dashboards with separate processing

#### ✅ 5.2 CSV Output Generation
- **✅ Query CSV**: `golden_queries_output.csv`
  - Column order: `id`, `name`, `golden_query_score`, `impact_score`, `recency_score`, `curation_score`, `downstream_dashboard_count`, `downstream_chart_count`, `user_name`, `last_executed_at`, `created_at`, `query`
  - Uses `index=False` to prevent pandas row indices
  - Uses `quoting=csv.QUOTE_ALL` for fields with special characters (SQL)

- **✅ Dashboard CSV**: `golden_dashboards_output.csv`  
  - Column order: `id`, `name`, `golden_dashboard_score`, `content_quality_score`, `recency_score`, `curation_score`, `user_name`, `updated_at`, `created_at`
  - Proper quoting and formatting for reliability

#### ✅ 5.3 JSON Output Generation  
- **✅ Query JSON**: `golden_queries_output.json`
- **✅ Dashboard JSON**: `golden_dashboards_output.json`
- Uses `orient='records'` for list of JSON objects format
- Uses `indent=2` for human readability
- Uses `date_format='iso'` for standardized timestamps
- **All component scores automatically included** for full transparency

#### ✅ 5.4 Complete Analysis Pipeline
- End-to-end `run_complete_analysis()` method
- Executes all 4 phases in sequence
- Generates comprehensive results and file paths
- Includes error handling and pandas dependency checking

## 🎯 Project Status: **COMPLETE**
All phases implemented and fully operational!

## Quick Start

### 1. Install Dependencies
```bash
pip install -r ../requirements.txt
pip install pandas  # Required for Phase 4 output generation
```

### 2. Set Up Environment
Create a `.env` file in the project root:
```bash
REDASH_API_URL=https://your.redash.instance
REDASH_API_KEY=your_redash_api_key
```

### 3. Test Phase 1
```bash
python redash_v2/main.py
```

## Sample Output

```
🔧 Redash Golden Asset Ranking System
==================================================
Phase 1: Foundational Layer - High-Performance Data Extraction
==================================================
🌐 Redash URL: https://your.redash.instance
🔑 API Key: ************5678

🔄 Starting Phase 1 extraction...
✅ Phase 1 completed in 4.35 seconds!

📊 Phase 1 Results:
   🔗 Connection: Connection successful to Redash: https://your.redash.instance (User: Admin)
   🏷️  Version: 8.0.0 (slug mode: True)

📈 Data Extraction:
   - Total Dashboards: 15
   - Detailed Dashboards: 13
   - Total Queries: 128
   - Detailed Queries: 125

🔗 Dependency Mapping:
   - Queries with dashboard dependencies: 42
   - Queries with chart widgets: 38
   - Dashboards with queries: 11

🎉 Phase 1 foundation is ready for scoring phases!

==================================================
🔄 Starting Phase 2: Golden Saved Query Scoring Logic...
✅ Phase 2 completed in 1.23 seconds!

📊 Phase 2 Query Scoring Results:
   - Total Scored Queries: 125

   
🏆 Top 5 Golden Queries:
      1. Customer Revenue Dashboard Data Feed
         Golden Score: 7.85 (Impact: 5.20, Recency: 2.15, Curation: 0.50)
         Dashboards: 3, Charts: 8

      2. Daily Active Users Metrics
         Golden Score: 6.42 (Impact: 4.12, Recency: 1.80, Curation: 0.50)
         Dashboards: 2, Charts: 5

      3. Product Performance Analysis
         Golden Score: 5.78 (Impact: 3.28, Recency: 1.50, Curation: 1.00)
         Dashboards: 1, Charts: 7

   📈 Score Distribution:
      - Highest: 7.85
      - Average: 2.34
      - Lowest: 0.00

==================================================
🔄 Starting Phase 3: Golden Dashboard Scoring Logic...
✅ Phase 3 completed in 0.87 seconds!

📊 Phase 3 Dashboard Scoring Results:
   - Total Scored Dashboards: 13

   
🏆 Top 5 Golden Dashboards:
      1. Executive KPI Dashboard
         Golden Score: 8.45 (Content: 7.00, Recency: 1.45, Curation: 0.00)
         Queries Used: 5, Is Draft: False

      2. Sales Performance Analytics
         Golden Score: 6.72 (Content: 4.52, Recency: 1.20, Curation: 1.00)
         Queries Used: 3, Is Draft: False

      3. User Engagement Overview
         Golden Score: 5.98 (Content: 4.78, Recency: 1.20, Curation: 0.00)
         Queries Used: 4, Is Draft: False

   📈 Dashboard Score Distribution:
      - Highest: 8.45
      - Average: 3.21
      - Lowest: 0.00

==================================================
🔄 Starting Phase 4: Final Output Generation...
✅ Phase 4 completed in 0.45 seconds!

📊 Phase 4 Output Generation Results:
   📁 Generated Files:
      - queries_csv: golden_queries_output.csv
      - queries_json: golden_queries_output.json
      - dashboards_csv: golden_dashboards_output.csv
      - dashboards_json: golden_dashboards_output.json
   📋 File Details:
      - golden_queries_output.csv: 156.8 KB
      - golden_queries_output.json: 287.3 KB
      - golden_dashboards_output.csv: 12.4 KB
      - golden_dashboards_output.json: 18.7 KB

💾 Complete analysis results saved to complete_golden_analysis_results.json

======================================================================
🎉 GOLDEN ASSET RANKING SYSTEM COMPLETE! 🎉
⏱️  Total execution time: 6.90 seconds
📊 Analysis Summary:
   • 125 queries scored and ranked
   • 13 dashboards scored and ranked
   • 4 output files generated
======================================================================
```

## Architecture

### Performance Features
- **Concurrent Processing**: All API calls run in parallel using `asyncio.gather`
- **Smart Error Handling**: Graceful handling of deleted/archived assets
- **Version Compatibility**: Automatic adaptation to different Redash API versions
- **Memory Efficient**: Processes data in streams rather than loading everything at once

### Data Structures
The `RedashMetadataExtractor` class maintains several key data structures:
- `all_dashboards`: Raw dashboard list from API
- `all_queries`: Raw query list from API  
- `detailed_dashboards`: Full dashboard objects with widget data
- `detailed_queries`: Full query objects with execution metadata
- Dependency maps for relationship tracking

## API Permissions Required

Your Redash API key needs access to:
- `/api/dashboards` - List and read dashboard details
- `/api/queries` - List and read saved queries
- `/api/session` - Connection testing and version detection

## Generated Output Files

The Golden Asset Ranking System generates 4 output files with complete transparency:

### 📊 Query Rankings
- **`golden_queries_output.csv`**: Ranked queries with all component scores in CSV format
- **`golden_queries_output.json`**: Same data in JSON format for programmatic consumption

### 📊 Dashboard Rankings  
- **`golden_dashboards_output.csv`**: Ranked dashboards with all component scores in CSV format
- **`golden_dashboards_output.json`**: Same data in JSON format for programmatic consumption

### 📋 Output File Structure

**Query Columns**: `id`, `name`, `golden_query_score`, `impact_score`, `recency_score`, `curation_score`, `downstream_dashboard_count`, `downstream_chart_count`, `user_name`, `last_executed_at`, `created_at`, `query`

**Dashboard Columns**: `id`, `name`, `golden_dashboard_score`, `content_quality_score`, `recency_score`, `curation_score`, `user_name`, `updated_at`, `created_at`

## Usage Scenarios

1. **Data Discovery**: Find the most valuable queries and dashboards in your Redash instance
2. **Infrastructure Planning**: Identify critical dependencies and high-impact assets  
3. **Cleanup Prioritization**: Focus on improving low-scoring but important assets
4. **Quality Assessment**: Use component scores to understand what makes assets valuable
5. **Automated Reporting**: Integrate JSON outputs into monitoring and governance systems
