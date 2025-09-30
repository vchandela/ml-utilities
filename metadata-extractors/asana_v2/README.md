# Asana Golden Task Ranking System

An automated system that programmatically extracts task data from Asana to calculate a `golden_task_score` for each task, providing clear, data-driven insights into organizational priorities and potential risks.

## 🎯 Overview

This system implements a fully automated 3-phase workflow:

1. **Phase 1: High-Performance Data Extraction** - Securely fetches comprehensive task metadata from all accessible Asana workspaces
2. **Phase 2: Golden Task Scoring Logic** - Calculates transparent, quantitative task importance scores
3. **Phase 3: Final Output Generation** - Produces ranked CSV and JSON files for analysis and decision-making

## 🏗️ System Architecture

### Guiding Principles
- **API-First Approach**: Non-intrusive, secure, and maintainable solution using official Asana REST API
- **Impact and Activity as Proxies for Value**: Uses measurable signals (dependencies, engagement) as objective indicators
- **Actionable and Transparent Output**: Complete traceability of scoring components

### Golden Task Score Components

The `golden_task_score` (max 10 points) consists of:

**1. Impact Score (max 5 points)**
- Based on dependency relationships with log-transformation
- Weighted: 70% dependents + 30% dependencies
- Tasks blocking others score higher (critical path identification)

**2. Engagement Score (max 3 points)**  
- Based on collaboration intensity with log-transformation
- Weighted: 50% subtasks + 30% comments + 20% followers
- Measures task complexity and human attention

**3. Timeliness & Recency Score (max 2 points)**
- Urgency: 1.0 if overdue, 0.5 if due within 7 days, 0.0 otherwise
- Recency: Exponential decay based on last modification date
- Rewards both urgent and recently active tasks

**Completion Penalty**: Completed tasks receive 0.2× multiplier

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Asana Personal Access Token** ([get one here](https://developers.asana.com/docs/personal-access-token))
3. **Optional**: Asana refresh token for long-running operations

### Installation

```bash
# Clone or copy the asana_v2 directory
cd asana_v2

# Install dependencies  
pip install -r requirements.txt
```

### Environment Setup

```bash
# Required
export ASANA_ACCESS_TOKEN="your_access_token_here"

# Required for automatic token refresh (recommended for long-running operations)
export ASANA_REFRESH_TOKEN="your_refresh_token_here"
export ASANA_CLIENT_ID="your_oauth_app_client_id"
export ASANA_CLIENT_SECRET="your_oauth_app_client_secret"

# Optional (default: current directory)
export OUTPUT_DIR="./output"

# Optional: Control task processing concurrency (default: 5)
export ASANA_TASK_CONCURRENCY="5"

# Optional: Limit total tasks extracted for faster testing (default: 100)
export ASANA_MAX_TASKS="100"
```

### Getting OAuth Credentials for Token Refresh

For automatic token refresh functionality, you need to create an Asana OAuth app:

1. **Create OAuth App**:
   - Go to https://developers.asana.com/docs/oauth
   - Create a new OAuth application
   - Note down your `Client ID` and `Client Secret`

2. **Get Refresh Token**:
   - Follow Asana's OAuth flow to get an access token and refresh token
   - Or use your existing refresh token if you have one

3. **Set Environment Variables**:
   - Set all four credentials (access_token, refresh_token, client_id, client_secret)
   - The system will automatically refresh expired tokens

### Run the Complete System

```bash
python main.py
```

This will:
1. Connect to Asana and discover all accessible workspaces
2. Extract all tasks with comprehensive metadata (dependencies, comments, subtasks)
3. Calculate golden_task_score for each task
4. Generate ranked output files: `golden_tasks_output.csv` and `golden_tasks_output.json`

## 📊 Output Files

### CSV Format (`golden_tasks_output.csv`)
Human-readable format with logical column ordering:
```
id,name,golden_task_score,impact_score,engagement_score,timeliness_recency_score,is_completed,dependent_count,dependency_count,subtask_count,comment_count,follower_count,due_date,last_modified_at,url
```

### JSON Format (`golden_tasks_output.json`)
Machine-consumable format with complete task data:
```json
[
  {
    "id": "task123",
    "name": "Critical Backend Refactor", 
    "golden_task_score": 8.427,
    "impact_score": 4.876,
    "engagement_score": 2.341,
    "timeliness_recency_score": 1.210,
    "is_completed": false,
    "dependent_count": 8,
    "dependency_count": 3,
    ...
  }
]
```

## 🧪 Testing

### Test Individual Phases

```bash
# Test Phase 1: Data Extraction
python test_extraction.py

# Test Phase 2: Scoring Logic  
python test_scoring.py

# Test Phase 3: Output Generation
python test_output.py
```

### Test with Sample Data (No API Required)

```bash
# Test scoring logic
python test_scoring.py
# Choose option 2: "Scoring logic test with sample data"

# Test output generation
python test_output.py  
# Choose option 1: "Full Phase 3 test with sample data"
```

## 📈 Understanding the Scores

### High Impact Tasks
- Have many **dependents** (tasks waiting on them)
- Are on the critical path
- Blocking significant downstream work

### High Engagement Tasks
- Have many **subtasks** (complex work breakdown)
- High **comment volume** (active collaboration)
- Many **followers** (high visibility)

### High Timeliness Tasks
- Are **overdue** or **due soon**
- Have been **recently modified** (active work)

### Completion Penalty
- **Completed tasks** receive 20% of their calculated score
- Keeps focus on active, actionable work
- Preserves historical context for analysis

## 🔧 Advanced Usage

### Custom Output Directory

```bash
export OUTPUT_DIR="/path/to/your/output/directory"
python main.py
```

### Programmatic Usage

```python
import asyncio
from asana_v2 import AsanaConnector, GoldenTaskScorer, GoldenTaskOutputGenerator

async def run_custom_analysis():
    # Phase 1: Extract data
    connector = AsanaConnector()
    await connector.connect(credentials)
    
    tasks = []
    async for task in connector.workspace_data():
        tasks.append(task)
    
    # Phase 2: Score tasks
    scorer = GoldenTaskScorer()  
    scored_tasks = scorer.process_all_tasks(tasks)
    
    # Phase 3: Generate output
    generator = GoldenTaskOutputGenerator("./custom_output")
    results = generator.generate_outputs(scored_tasks)
    
    await connector.close()
    return results

# Run the analysis
results = asyncio.run(run_custom_analysis())
```

### Performance Tuning & Concurrency Control

The system is designed for high performance with **three levels of concurrency**:

#### **Multi-Level Concurrency Architecture:**
1. **Workspace Level**: All workspaces processed in parallel (unlimited)
2. **Project Level**: All projects within each workspace processed in parallel (unlimited)  
3. **Task Level**: Configurable concurrent task processing per project (default: 5)
4. **API Call Level**: Each task makes 3 concurrent API calls (details + comments + subtasks)

#### **Concurrency & Limits Configuration:**
```bash
# Control task processing concurrency (default: 5 tasks per project)
export ASANA_TASK_CONCURRENCY="10"  # Increase for faster processing
export ASANA_TASK_CONCURRENCY="3"   # Decrease to reduce API load

# Control total tasks extracted (default: 100 for faster testing)
export ASANA_MAX_TASKS="500"   # Extract more tasks for comprehensive analysis
export ASANA_MAX_TASKS="50"    # Quick test with minimal data
export ASANA_MAX_TASKS="0"     # Extract ALL tasks (remove limit - may take very long!)
```

#### **Performance Optimization:**
- **Higher concurrency** = Faster extraction but more API load
- **Lower concurrency** = Slower extraction but gentler on API limits
- **Current setup**: Each project processes up to N tasks in parallel, each task makes 3 concurrent API calls
- **Total concurrent calls**: Workspaces × Projects × Task_Concurrency × 3

#### **For Large Asana Instances:**
- **Start with low concurrency** (`ASANA_TASK_CONCURRENCY="3"`) to test API limits
- **Monitor logs** for rate limiting messages
- **Increase gradually** if no rate limiting issues
- **Run during off-peak hours** for large extractions
- **Use refresh tokens** for long-running operations

## 🏆 Use Cases

### Project Management
- **Identify bottlenecks**: High-impact tasks blocking multiple others
- **Prioritize work**: Focus on highest golden_task_score items
- **Resource allocation**: Support high-engagement tasks

### Risk Management  
- **Critical path analysis**: Tasks with high dependent counts
- **Overdue tracking**: Tasks with high timeliness scores
- **Activity monitoring**: Recently modified high-importance tasks

### Team Analytics
- **Collaboration patterns**: High-engagement tasks show active teamwork
- **Completion trends**: Compare scores before/after completion penalty
- **Historical analysis**: Track score changes over time

## 🛠️ Architecture Details

### Phase 1: Data Extraction
- **AsanaConnection**: Secure API client with automatic token refresh
- **AsanaConnector**: Orchestrates parallel workspace processing  
- **API utilities**: Handle pagination, error recovery, and cycle detection

### Phase 2: Scoring Engine
- **GoldenTaskScorer**: Calculates all score components
- **Log-transformation**: Normalizes count distributions
- **Dataset normalization**: Ensures fair scoring across all tasks

### Phase 3: Output Generation
- **GoldenTaskOutputGenerator**: Handles DataFrame operations and file I/O
- **Pandas integration**: Efficient sorting and formatting
- **Multiple formats**: CSV (human) and JSON (machine) outputs

## 🔍 Troubleshooting

### Common Issues

**Connection Errors**
```bash
Error: "Failed to establish connection to Asana"
```
- Verify `ASANA_ACCESS_TOKEN` is correct
- Check internet connectivity
- Ensure token has required permissions

**No Tasks Found**
```bash
Warning: "No tasks found to score"  
```
- Verify you have access to workspaces with tasks
- Check if tasks are in archived projects
- Confirm API token permissions

**Rate Limiting**
```bash
Error: "429 Too Many Requests"
```
- The system handles rate limits automatically
- For large instances, run during off-peak hours
- Consider using refresh tokens

### Debug Logging

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python main.py
```

View log file:
```bash
tail -f golden_task_ranking.log
```

## 📝 API Requirements

### Asana Permissions
Your Personal Access Token needs access to:
- **Workspaces**: Read workspace information
- **Projects**: Read project details and tasks
- **Tasks**: Read task details, dependencies, subtasks
- **Stories**: Read comments on tasks
- **Users**: Read user information

### Rate Limits
The system respects Asana's rate limits:
- Automatic retry on rate limit responses
- Concurrent request management
- Efficient batching of API calls

## 🤝 Contributing

This system implements the complete specification from the project plan. For modifications:

1. **Scoring Components**: Modify `golden_task_scorer.py`
2. **Data Extraction**: Enhance `api_utils.py` or `connector.py`  
3. **Output Formats**: Extend `output_generator.py`
4. **Testing**: Add tests to existing test files

## 📄 License

This implementation follows the architectural principles and specifications outlined in the original project plan.
