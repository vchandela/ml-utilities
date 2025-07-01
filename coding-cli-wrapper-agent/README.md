# Stand-Alone Coding Agent

A self-contained service that accepts code-editing tasks, spawns one-off worker containers, and opens PRs on GitHub with full private repository support.

## ✅ Status: **FULLY OPERATIONAL**

Complete end-to-end workflow working:
- ✅ API accepts tasks → Worker spawns → Code applied → Tests run → PR created
- ✅ GitHub authentication for private repositories  
- ✅ Redis state management with real-time progress tracking
- ✅ **Gemini Engine**: Working with auto-approval (`--yolo` flag)
- ✅ **Codex Engine**: Working with GPT-4.1 model and full automation (`--full-auto` flag)

## 🚀 Quick Setup

### 1. Environment Setup
```bash
# Copy and configure environment
cp env.example .env

# Add required credentials
cat >> .env << EOF
GITHUB_TOKEN=ghp_your_token_here
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
EOF
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
# Test Gemini engine (✅ Verified - creates PRs successfully)
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/pavoai/intern",
    "instructions": "Append the word \"gemini\" at the end of README.md file",
    "engine": "gemini"
  }'

# Test Codex engine with GPT-4.1 (✅ Verified - creates PRs successfully)
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/pavoai/intern",
    "instructions": "Append the word \"gpt41-test\" at the end of README.md file",
    "engine": "codex"
  }'

# Custom private repository
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/myorg/private-repo",
    "instructions": "Add comprehensive input validation and security checks",
    "branch_base": "develop", 
    "engine": "gemini"
  }'
```

## 🔧 Configuration

**Required in `.env`:**
- `GITHUB_TOKEN` - Personal access token with repo permissions
- `GEMINI_API_KEY` - Google Gemini API key (for `engine: "gemini"`)
- `OPENAI_API_KEY` - OpenAI API key (for `engine: "codex"`)
- `ANTHROPIC_API_KEY` - Anthropic API key (for `engine: "claude"`)
- `REDIS_URL` - Default: `redis://redis:6379/0`

**Engine Details:**
- **Gemini**: Uses `@google/gemini-cli` with `--yolo` flag for auto-approval
- **Codex**: Uses `@openai/codex` with GPT-4.1 model and `--full-auto` flag
- **Claude**: Uses `@anthropic-ai/claude-code` (configured but not yet tested)

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