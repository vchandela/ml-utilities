# Stand-Alone Coding Agent

A self-contained service that accepts code-editing tasks, spawns one-off worker containers, and opens PRs on GitHub with full private repository support.

## ✅ Status: **FULLY OPERATIONAL**

Complete end-to-end workflow working:
- ✅ API accepts tasks → Worker spawns → Code applied → Tests run → PR created
- ✅ GitHub authentication for private repositories  
- ✅ Redis state management with real-time progress tracking  
- ✅ **File-mounted instructions**: Auto-load task instructions from `task_instructions.md`
- ✅ **Gemini Engine**: Working with Gemini-2.5-Pro model and auto-approval (`-y` flag)
- ✅ **Codex Engine**: Working with O3 model and full automation (`--full-auto` flag)
- ✅ **Claude Engine**: Working with Opus model and enhanced tool permissions

## 📝 Quick Start: File-Mounted Instructions

The recommended approach uses a simple file-based workflow:

```bash
# 1. Write your task instructions  
echo "• Add comprehensive error handling
• Implement input validation
• Add unit tests for new functions
• Update API documentation" > task_instructions.md

# 2. Submit task (auto-loads instructions from file)
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo":"https://github.com/your-org/repo", "engine":"gemini"}'

# 3. Monitor progress  
curl http://localhost:8000/tasks/{task_id}
# Returns enhanced status: ⏳ QUEUED → 🔄 PROCESSING... → ✅ COMPLETED SUCCESSFULLY
```

**Key advantages:** Clean API calls, live instruction updates, no JSON payload limits, enhanced status tracking.

## 🚀 Quick Setup

### 1. Environment Setup
```bash
# Copy and configure environment
cp env.example .env

# Add required credentials
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

**Option 1: File-mounted instructions (Recommended)**
```bash
# 1. Write task instructions
echo "• Add comprehensive error handling
• Implement input validation  
• Update documentation" > task_instructions.md

# 2. Submit task (no instructions field needed)
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo":"https://github.com/your-org/repo", "engine":"gemini"}'
```

**Option 2: Inline instructions**
```bash
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo":"https://github.com/your-org/repo", "instructions":"Add error handling"}'
```

Both return: `{"task_id":"uuid","status":"queued"}`

### 4. Monitor Progress
```bash
# Check status
curl http://localhost:8000/tasks/{task_id}

# Real-time monitoring
watch -n 2 'curl -s http://localhost:8000/tasks/{task_id} | jq'
```

## 📋 API

### POST /tasks

**File-mounted approach (recommended):**
```json
{
  "repo": "https://github.com/owner/repo",
  "branch_base": "main",     // optional  
  "engine": "gemini"         // optional: gemini, claude, codex
}
```
*Instructions auto-loaded from `task_instructions.md`*

**Inline instructions approach:**
```json
{
  "repo": "https://github.com/owner/repo",
  "instructions": "Your coding task description",
  "branch_base": "main",     // optional
  "engine": "gemini"         // optional: gemini, claude, codex
}
```

### GET /tasks/{task_id}

**Successful completion:**
```json
{
  "task_id": "uuid",
  "state": "done",
  "status": "✅ COMPLETED SUCCESSFULLY",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "github_pr": "https://github.com/owner/repo/pull/123",
  "created_at": "1751369960",
  "started_at": "1751369962",
  "completed_at": "1751369969",
  "test_status": "passed",
  "instructions": "Your task instructions...",
  "repo": "https://github.com/owner/repo",
  "engine": "gemini"
}
```

**While processing:**
```json
{
  "task_id": "uuid",
  "state": "running",
  "status": "🔄 PROCESSING...",
  "created_at": "1751369960",
  "started_at": "1751369962",
  "instructions": "Your task instructions...",
  "repo": "https://github.com/owner/repo",
  "engine": "gemini"
}
```

**If failed:**
```json
{
  "task_id": "uuid",
  "state": "failed",
  "status": "❌ FAILED",
  "error": "Error details...",
  "created_at": "1751369960",
  "started_at": "1751369962",
  "instructions": "Your task instructions...",
  "repo": "https://github.com/owner/repo",
  "engine": "gemini"
}
```

## 🔄 Worker Flow

1. **Clone** → Private repo with GitHub token
2. **Branch** → Create `pavo-coding-agent/{engine}/{task_id}`  
3. **Apply** → Run selected engine (Gemini/Claude/Codex) with instructions
4. **Test** → Execute available test frameworks (pytest, npm test, make test, etc.)
5. **Push** → Authenticated push to GitHub
6. **PR** → Create pull request via GitHub API with detailed task information

## 💡 Examples

### File-mounted Instructions (Recommended)

```bash
# 1. Write task instructions
echo "• Append the word 'claude-codex-test' at the end of README.md file
• Add a comment that says 'This was added via file-mounted instructions'" > task_instructions.md

# 2. Test with different engines (✅ All verified - create PRs successfully)

# Gemini engine  
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo": "https://github.com/pavoai/intern", "engine": "gemini"}'

# Claude engine
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo": "https://github.com/pavoai/intern", "engine": "claude"}'

# Codex engine  
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"repo": "https://github.com/pavoai/intern", "engine": "codex"}'

# Private repository with custom branch
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/myorg/private-repo",
    "branch_base": "develop", 
    "engine": "gemini"
  }'
```

### Inline Instructions (Alternative)

```bash
# Direct instruction passing (no file needed)
curl -X POST http://localhost:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "repo": "https://github.com/pavoai/intern",
    "instructions": "Add comprehensive input validation and security checks",
    "engine": "gemini"
  }'
```

## 🔧 Configuration

**Required in `.env`:**
- `GITHUB_TOKEN` - Personal access token with repo permissions
- `GEMINI_API_KEY` - Google Gemini API key (for `engine: "gemini"`)
- `GEMINI_MODEL` - Gemini model to use (default: `gemini-2.5-pro`)
- `ANTHROPIC_API_KEY` - Anthropic API key (for `engine: "claude"`)
- `ANTHROPIC_MODEL` - Claude model to use (default: `claude-3-5-sonnet-20241022`)
- `OPENAI_API_KEY` - OpenAI API key (for `engine: "codex"`)
- `REDIS_URL` - Redis connection URL (default: `redis://redis:6379/0`)

**Engine Details:**
- **Gemini**: Uses `@google/gemini-cli` with Gemini-2.5-Pro model, auto-approval (`-y`), debug mode (`-d`), and memory usage monitoring (`--show_memory_usage`)
- **Codex**: Uses `@openai/codex` with O3 model, full automation (`--full-auto`), quiet mode (`-q`), and full stdout output (`--full-stdout`)
- **Claude**: Uses `@anthropic-ai/claude-code` with Opus model, debug mode (`-d`), and comprehensive tool permissions (`--allowedTools`)

## 🔍 Debugging

```bash
# Check system health (enhanced endpoint)
curl http://localhost:8000/health
# Returns: {"status":"healthy","redis":{"status":"connected","details":"ping successful","url":"redis://redis:6379/0"},"github_token_configured":true}

# API logs
docker compose logs agent-b-api -f

# Redis inspection
docker compose exec redis redis-cli HGETALL task:{task_id}

# Task status with detailed response
curl http://localhost:8000/tasks/{task_id} | jq

# Clean restart
docker compose down && COMPOSE_PROFILES=api docker compose up -d
```

## 📊 Task States

- `queued` → ⏳ **QUEUED** - Task created, waiting for worker
- `running` → 🔄 **PROCESSING...** - Worker processing with timestamps
- `done` → ✅ **COMPLETED SUCCESSFULLY** - Completed successfully with PR URL
- `failed` → ❌ **FAILED** - Error occurred (check error field in response)

## 🔮 Architecture & Future Improvements

### Current Architecture: File-Mounted Instructions
The system supports both inline and file-mounted instruction approaches:

**File-Mounted Workflow (Recommended):**
1. **Host File**: User/agent writes to `task_instructions.md` in project root
2. **API Mount**: File mounted read-only at `/tasks/task_instructions.md` in API container  
3. **Auto-Loading**: API automatically reads file content when `instructions` field is empty
4. **Worker Execution**: Instructions passed to worker via environment variables (no file sharing)
5. **Live Updates**: Changes to host file immediately available to new tasks

**Key Benefits:**
- ✅ **Simple API calls** - No large instruction payloads in JSON
- ✅ **Live updates** - Change instructions without rebuilding containers
- ✅ **Clean separation** - File management separate from API calls
- ✅ **Ephemeral workers** - No file mounts or cleanup needed in worker containers

**Example workflow:**
```bash
# 1. Update instructions (live updates)
echo "• Fix authentication bug
• Add rate limiting  
• Update tests" > task_instructions.md

# 2. Submit task (auto-loads from file)
curl -X POST http://localhost:8000/tasks \
  -d '{"repo":"https://github.com/myorg/repo","engine":"gemini"}' \
  -H 'Content-Type: application/json'
```

### Future Enhancements

#### Multi-File Support
- **Directory Mount**: Mount `task_files/` directory with multiple `.md` files  
- **Dynamic Selection**: API endpoint parameter to specify which file to use
- **Use Case**: Multiple task templates or concurrent task types

#### Advanced File Management
- **Auto-cleanup**: Clear `task_instructions.md` after successful PR creation
- **Task History**: Archive completed instructions with task IDs for tracking  
- **Validation**: Pre-validate instruction syntax before task submission

#### High-Throughput Optimizations
- **Shared Volume**: Mount same volume in worker for very large instruction files
- **Instruction Caching**: Cache frequently-used instruction templates
- **Batch Processing**: Process multiple tasks with same instructions simultaneously

## ✅ TODO

1. **Remove engine from branch name and PR title** - Simplify branch naming back to `pavo-coding-agent/{task_id}`. ALso, fix PR title.
2. **Make worker containers ephemeral** - Ensure complete cleanup and removal after task completion
