# Temporal Agent POC

**Durable workflow orchestration replacing Celery with crash-resilient, signal-controlled agent execution.**

Demonstrates Temporal's advantages: automatic crash recovery, reliable stop/resume, stateful execution, and real-time UI integration.

## Architecture
- **Backend**: FastAPI + PostgreSQL + Redis (SSE streaming)
- **Worker**: Temporal workflows + activities (replaces Celery)  
- **Frontend**: Single-page HTML app with real-time updates
- **Infrastructure**: Docker Compose (Postgres, Redis, Temporal server + Web UI)

## Quick Start

**1. Start Infrastructure**
```bash
docker compose up -d

#Login into postgres
psql -h localhost -p 5432 -U dev -d intern
```

**2. Start Backend** (Terminal 1)
```bash
python3.12 -m venv --copies .venv && source .venv/bin/activate
pip install -r requirements-backend.txt
export DATABASE_URL="postgresql+psycopg2://dev:dev@localhost:5432/intern"
export REDIS_URL="redis://localhost:6379/0"
uvicorn backend.app:app --reload --port 8000

# Test if the app is up
curl http://localhost:8000/health
```

**3. Start Worker** (Terminal 2)  
```bash
#Open a new terminal
source .venv/bin/activate  # Reuse same venv and variables as backend
export DATABASE_URL="postgresql+psycopg2://dev:dev@localhost:5432/intern"
export REDIS_URL="redis://localhost:6379/0"
#Run it as a module
python -m worker.worker


#To make sure worker was killed nicely. Normally Ctrl+C is enough
# Find the process ID
ps aux | grep "worker.worker"
# Kill gracefully first
kill <PID>  
# Force kill if needed
kill -9 <PID>
```

**4. Access UI**
- **Main App**: Open `index.html` in browser
- **Temporal UI**: http://localhost:8088 (observe workflows)

## Testing Scenarios

**✅ Test 1: Happy Path**
1. **Login**: Enter email → Click "Login / Refresh Tasks" (invokes `/me_v2`)
   - Creates user in database, returns user_id + existing tasks list (empty on first login)
2. **Create**: Title "Analyze user engagement metrics" → Click "Create Task" (invokes `POST /create_task_id`)
   - Creates Task record in database with stage=INIT/PENDING, returns task_id, auto-selects task
3. **Start**: Click "Start" button (invokes `POST /tasks/{task_id}/message`) 
   - Starts Temporal workflow, worker executes init_task → create_plan_v1 → mark_wait_rfc activities
   - Status updates to PLANNING/RUNNING → WAIT_RFC/PAUSED, SSE stream shows planning events
4. **Accept**: Click "Accept Plan" (invokes `POST /tasks/{task_id}/accept_rfc`)
   - Sends signal_accept_rfc to workflow, transitions from waiting to execution phase  
5. **Complete**: Watch execution (via `GET /tasks/{task_id}/stream` SSE)
   - execute_batch activities run with progress ticks, heartbeat signals, status → DONE

**✅ Test 2: Feedback Path**
1. **Setup**: Complete steps 1-3 from Happy Path (task in WAIT_RFC/PAUSED state)
2. **Add Feedback**: Type "Add more details about data sources" → Click "Add Feedback"
   - Saves feedback to database linked to plan document (invokes `POST /tasks/{task_id}/document/{doc_id}/feedback/add`)
3. **Submit Review**: Click "Done Reviewing Plan" (invokes `POST /tasks/{task_id}/document/{doc_id}/status`)
   - Sends signal_resume with feedback to workflow, workflow creates Plan v2 incorporating feedback
   - New TaskDocument saved with version="2", status updates to PLANNING → WAIT_RFC again
4. **Accept Revised**: Click "Accept Plan" to accept Plan v2 → execution begins with revised plan
   - Tests iterative human-AI collaboration and plan versioning

**✅ Test 3: Crash Recovery (Key Feature!)**  
1. Start task → Accept plan → During execution: `Ctrl+C` worker
2. Restart worker → Observe: **Automatic resume from last checkpoint**
3. Verify: No lost progress, workflow continues exactly where stopped

**✅ Test 4: Graceful Stop**
1. Start task → Accept plan → Click "Stop" button  
2. Verify: Clean shutdown, status = `STOPPED`

## Testing Log
- [x] Infrastructure setup completed ✅
- [x] Backend API server started ✅  
- [x] Temporal worker started ✅
- [x] Happy path test passed
- [x] Crash recovery test passed  
- [x] Graceful stop test passed
