# Stand-Alone Coding Agent

A self-contained service that accepts code-editing tasks, spawns one-off worker containers, and opens PRs on GitHub with full private repository support.

## ✅ Status: **FULLY OPERATIONAL**

Complete end-to-end workflow working:
- ✅ API accepts tasks → Worker spawns → Code applied → Tests run → PR created
- ✅ GitHub authentication for private repositories  
- ✅ Redis state management with real-time progress tracking

## 🚀 Quick Setup

### 1. GitHub Authentication
```bash
# Copy and configure environment
cp env.example .env

# Add your GitHub token
echo "GITHUB_TOKEN=ghp_your_token_here" >> .env
```

### 2. Launch System
```bash
# Start API and Redis
COMPOSE_PROFILES=api docker compose up -d

# Build worker image  
docker compose build worker

# Verify system
curl http://localhost:8000/health
```

### 3. Submit Task
```bash
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo":"https://github.com/your-org/repo", "instructions":"Add error handling"}'

# Returns: {"task_id":"uuid","status":"queued"}
```

### 4. Monitor Progress
```bash
# Check status
curl http://localhost:8000/tasks/{task_id}

# Real-time monitoring
watch -n 2 'curl -s http://localhost:8000/tasks/{task_id} | jq'
```

## 📋 API

### POST /tasks
```json
{
  "repo": "https://github.com/owner/repo",
  "instructions": "Your coding task description",
  "branch_base": "main",     // optional
  "engine": "gemini"         // optional: gemini, claude, codex
}
```

### GET /tasks/{task_id}
```json
{
  "state": "done",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "started_at": "1751369960",
  "completed_at": "1751369969"
}
```

## 🔄 Worker Flow

1. **Clone** → Private repo with GitHub token
2. **Branch** → Create `pavo-coding-agent/{task_id}`  
3. **Apply** → Run Gemini engine with instructions
4. **Test** → Execute available test frameworks
5. **Push** → Authenticated push to GitHub
6. **PR** → Create pull request via GitHub API

## 💡 Examples

```bash
# Private repository with custom instructions
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/myorg/private-repo",
    "instructions": "Add comprehensive input validation and security checks"
  }'

# Custom branch and engine
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/myorg/project",
    "instructions": "Optimize database queries",
    "branch_base": "develop", 
    "engine": "claude"
  }'
```

## 🔧 Configuration

**Required in `.env`:**
- `GITHUB_TOKEN` - Personal access token with repo permissions
- `REDIS_URL` - Default: `redis://redis:6379/0`

## 🔍 Debugging

```bash
# API logs
docker compose logs agent-b-api -f

# Redis inspection
docker compose exec redis redis-cli HGETALL task:{task_id}

# Clean restart
docker compose down && COMPOSE_PROFILES=api docker compose up -d
```

## 📊 Task States

- `queued` → Task created, waiting for worker
- `running` → Worker processing with timestamps
- `done` → Completed successfully with PR URL
- `failed` → Error occurred (check error field in Redis) 