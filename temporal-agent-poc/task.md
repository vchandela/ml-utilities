### **Project Plan: "Pavo-Temporal" - A Durable Agent Orchestration POC**

#### **1. Background & Project Goals**

**1.1. Current System Analysis:**
The existing system uses a combination of FastAPI for its API, Celery for background task execution, and a PostgreSQL database with specific flags (e.g., `agent_working_on_task`, `stage_status`) to manage the state of long-running agent tasks. Real-time updates are pushed to the frontend via a Redis Pub/Sub to a Server-Sent Events (SSE) bridge. The core agent logic is encapsulated within a `MasterOrchestrator` class, whose state is pickled to disk between runs.

**1.2. Identified Challenges:**
This architecture, while functional, presents several challenges common in stateful systems built on stateless tools:
*   **State Management Complexity:** State is spread across the database (flags), Celery's backend, and pickled files on disk. This makes reasoning about the true state of a task difficult.
*   **Fragile Stop/Resume:** Stopping tasks relies on Celery's `revoke` command and a timeout-based cleanup worker, which can be racy and unreliable.
*   **Orphaned Tasks:** If a Celery worker crashes mid-execution, the `Task` in the database can be left in an inconsistent "running" state, requiring a separate, complex cleanup process (`cleanup_orphaned_tasks`) to fix.
*   **Lack of Durability:** A worker crash means the entire task execution must be restarted from the last saved state, potentially losing significant progress from within a long-running `_process_message` loop.

**1.3. POC Objectives:**
This Proof-of-Concept will build a new, standalone system that replaces the Celery execution engine with **Temporal**. The goal is to demonstrate a more robust and simpler alternative for the agent's orchestration layer.

We will validate the following success criteria:
1.  **Durable Execution:** A task can survive a complete crash and restart of the worker process, automatically resuming from its last known state without losing progress.
2.  **Reliable Stop/Resume:** A running task can be reliably stopped and later resumed via explicit API calls, without race conditions or timeouts.
3.  **Seamless Integration:** The new Temporal-based engine can integrate with our existing frontend-facing infrastructure, specifically the Redis-to-SSE bridge for real-time UI updates.
4.  **Simplified Logic:** The core orchestration logic becomes simpler and easier to reason about by moving state management into the Temporal workflow itself.

---

#### **2. High-Level Architecture & Data Flow**

The POC will consist of four main services, managed by Docker Compose for easy local setup.

1.  **FastAPI Backend:** A lightweight web server that:
    *   Exposes a minimal set of REST endpoints (`/create_task_id`, `/tasks/...`) for a simple UI.
    *   Acts as the **initiator** of Temporal Workflows.
    *   Receives real-time events from Redis and streams them to the UI via SSE.

2.  **PostgreSQL Database:** Stores minimal, persistent records for `User` and `Task` entities. It acts as the source of truth for task metadata but **not for execution state**.

3.  **Redis:** Functions solely as a message broker for the SSE stream, exactly as in the current system. This isolates the POC to the execution engine and proves integration with existing infrastructure.

4.  **Temporal Worker (Python):** This is the new core engine.
    *   It connects to the Temporal Server.
    *   It hosts the code for the `OrchestrateTaskWorkflow` and all its associated `Activities`.
    *   It's the only component that executes the agent's business logic.

**Data Flow for a Task:**

1.  **UI → API:** User creates a task via a `POST /create_task_id` call. A `Task` row is created in Postgres.
2.  **UI → API:** User starts the task via `POST /tasks/{id}/message`.
3.  **API → Temporal Server:** The API tells the Temporal Server to start a new `OrchestrateTaskWorkflow` with a unique ID (e.g., `user:123|task:456`).
4.  **Temporal Server → Worker:** The Temporal Server assigns the workflow execution to an available Temporal Worker.
5.  **Worker (Workflow) → Worker (Activity):** The workflow begins executing. It calls Activities to perform actions.
6.  **Worker (Activity) → External Services:** Activities interact with the outside world. For example:
    *   `create_plan_v1` runs placeholder logic and updates the Postgres DB.
    *   `execute_batch` runs steps from your `MasterOrchestrator`'s `_process_message` generator.
    *   Any activity can publish events to **Redis**.
7.  **Redis → API → UI:** The FastAPI backend's SSE endpoint listens to the Redis channel and streams updates to the UI in real-time.
8.  **UI → API → Temporal Server (Signal):** When the user clicks "Stop," the API sends a **Signal** to the specific workflow instance, which then gracefully stops.

---

#### **3. Step-by-Step Implementation Plan**

This section contains the complete, runnable code for every file in the project.

##### **3.1. Project Structure**

Create a new, standalone directory for the POC (`temporal-intern-poc/`).

```
temporal-intern-poc/
├── backend/
│   ├── __init__.py
│   ├── app.py              # FastAPI application
│   ├── db.py               # SQLAlchemy setup
│   ├── models.py           # Database models (User, Task, etc.)
│   ├── schema.py           # Pydantic schemas for API
│   ├── sse.py              # Server-Sent Events streamer
│   ├── routes_tasks.py     # API routes for tasks
│   ├── auth.py             # Minimal user auth endpoint
│   └── minimal_logic/      # Placeholder business logic
│       ├── __init__.py
│       ├── tribal_search.py
│       ├── planner.py
│       └── exec_engine.py
├── worker/
│   ├── __init__.py
│   ├── activities.py       # Temporal Activities
│   ├── workflows.py        # Temporal Workflows
│   └── worker.py           # Temporal Worker entrypoint
├── docker-compose.yml      # For Postgres, Redis, and Temporal
├── requirements-backend.txt
├── requirements-worker.txt
├── index.html              # Minimal UI
└── README.md
```

##### **3.2. Infrastructure Setup: `docker-compose.yml`**

This file defines the necessary services.

```yaml
# docker-compose.yml
version: "3.9"
services:
  # PostgreSQL Database for storing minimal task metadata
  postgres:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: dev
      POSTGRES_USER: dev
      POSTGRES_DB: intern
    ports: [ "5432:5432" ]
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis for Server-Sent Events (SSE) message passing
  redis:
    image: redis:7-alpine
    ports: [ "6379:6379" ]

  # Temporal Server using the easy auto-setup image
  temporal:
    image: temporalio/auto-setup:1.24
    environment:
      DB: sqlite  # Simple persistence for the POC
      DYNAMIC_CONFIG_FILE_PATH: /etc/temporal/dynamicconfig/development-sqlite.yaml
    ports: [ "7233:7233" ] # gRPC port for workers/clients

  # Temporal Web UI for observing workflows
  temporal-web:
    image: temporalio/web:2.24.0
    environment:
      TEMPORAL_GRPC_ENDPOINT: temporal:7233
    ports: [ "8088:8088" ] # Web UI port
    depends_on: [ temporal ]

volumes:
  postgres_data: # Persists PostgreSQL data across restarts
```

**Reasoning:** Using Docker Compose provides a one-command setup for all developers, ensuring a consistent and reproducible environment. Using official images for Postgres, Redis, and Temporal is best practice. `temporalio/auto-setup` is perfect for a POC as it requires zero configuration.

##### **3.3. Dependencies: `requirements-*.txt`**

**File: `requirements-backend.txt`**
```
fastapi==0.111.0
uvicorn==0.30.1
pydantic==2.8.2
SQLAlchemy==2.0.31
psycopg2-binary==2.9.9
redis==5.0.7
temporalio==1.7.0
```

**File: `requirements-worker.txt`**
```
temporalio==1.7.0
redis==5.0.7
SQLAlchemy==2.0.31
psycopg2-binary==2.9.9
```
**Reasoning:** We separate dependencies for the backend and worker. The backend needs `fastapi` and `uvicorn`, while the worker does not. This is a good microservice practice, keeping each component's environment lean.

##### **3.4. Database and Models (`backend/` directory)**

These files define the minimal data structures needed for the POC.

**File: `backend/db.py`**
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Connect to PostgreSQL using environment variable, with a fallback for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://dev:dev@localhost:5432/intern")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# This function creates all tables defined in models.py if they don't exist
def init_db():
    from . import models  # This import is necessary to register the models with Base
    Base.metadata.create_all(bind=engine)
```

**File: `backend/models.py`**
```python
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from uuid import uuid4
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Task(Base):
    __tablename__ = "tasks"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    agent_type = Column(String, nullable=False, default="intern")
    stage = Column(String, nullable=False, server_default=expression.literal("INIT"))
    stage_status = Column(String, nullable=False, server_default=expression.literal("PENDING"))
    workflow_id = Column(String, nullable=True, index=True) # Link to Temporal execution
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", lazy="joined")

class TaskDocument(Base):
    __tablename__ = "task_documents"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    version = Column(String, nullable=False, default="1")
    kind = Column(String, nullable=False, default="PLAN") # e.g., PLAN, REPORT
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="DRAFT") # DRAFT, REVIEW, LOCKED
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("task_documents.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class TribalCorpus(Base): # For simulating tribal search
    __tablename__ = "tribal_corpus"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant = Column(String, nullable=False, default="default")
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
```

**File: `backend/schema.py`**
```python
from pydantic import BaseModel, Field
from typing import Optional

class TaskCreate(BaseModel):
    title: str
    agent_type: Optional[str] = Field("intern", description="intern | tribal_search")

class FeedbackCreate(BaseModel):
    body: str

class FeedbackUpdate(BaseModel):
    body: str

class DocumentStatusAction(BaseModel):
    action: str  # expect "done_reviewing"
```
**Reasoning:** This setup provides a minimal yet realistic database layer. The `Task` model includes `stage` and `stage_status`, which will be updated by Temporal Activities, demonstrating how the workflow can interact with the existing persistence layer. The `workflow_id` field is the crucial link between the database record and the durable execution in Temporal.

##### **3.5. Placeholder Agent Logic (`backend/minimal_logic/`)**

These files simulate the work your `MasterOrchestrator` would do.

**File: `backend/minimal_logic/tribal_search.py`**
```python
from sqlalchemy import select
from ..db import SessionLocal
from ..models import TribalCorpus, Task
from uuid import UUID

def search(task_id: str) -> list[dict]:
    """Simulates searching tribal knowledge. Returns a few dummy rows."""
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task:
            return []
        # Create dummy data if it doesn't exist
        if db.query(TribalCorpus).count() == 0:
            db.add_all([
                TribalCorpus(title="Onboarding Guide", content="..."),
                TribalCorpus(title="SQL Style Guide", content="..."),
            ])
            db.commit()
        rows = db.execute(select(TribalCorpus).limit(2)).scalars().all()
        return [{"id": str(r.id), "title": r.title} for r in rows]
```

**File: `backend/minimal_logic/planner.py`**
```python
from uuid import UUID
from ..db import SessionLocal
from ..models import Task, TaskDocument
from .tribal_search import search

def plan_v1(task_id: str) -> str:
    """Simulates generating the first version of a plan."""
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        title = task.title if task else "Untitled Task"
    
    hits = search(task_id)
    bullets = "\\n".join([f"- Use context: {h['title']}" for h in hits]) or "- No context found."
    return f"# Plan v1 for: {title}\\n\\n## Steps\\n1. Analyze requirements.\\n2. Gather context.\\n   {bullets}\\n3. Produce report."

def persist_plan(task_id: str, body: str, version: int = 1) -> str:
    """Saves the generated plan to the database."""
    with SessionLocal() as db:
        doc = TaskDocument(task_id=UUID(task_id), kind="PLAN", body=body, status="REVIEW", version=str(version))
        db.add(doc)
        db.commit()
        return str(doc.id)
```

**File: `backend/minimal_logic/exec_engine.py`**
```python
from ..sse import publish_event
from ..db import SessionLocal
from ..models import Task
from uuid import UUID
import time

def run_steps(task_id: str, max_steps: int = 50, heartbeat=None):
    """Simulates the agent's execution loop.
    It increments a progress counter and publishes ticks to Redis.
    It heartbeats to Temporal to signal liveness.
    """
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task:
            return 0, True # Task was deleted, end gracefully.
        
        progress = 0
        try:
            # Resumes progress from the DB status field
            if task.stage_status and ":" in task.stage_status:
                _, s = task.stage_status.split(":", 1)
                progress = int(s)
        except Exception:
            progress = 0

        steps_done_this_batch = 0
        for _ in range(max_steps):
            progress += 1
            steps_done_this_batch += 1
            
            # Update DB state
            task.stage = "EXECUTING"
            task.stage_status = f"RUNNING:{progress}"
            db.add(task)
            db.commit()

            # Publish real-time event
            publish_event(task_id, {"type": "tick", "progress": progress})

            if heartbeat:
                heartbeat()

            time.sleep(0.1) # Simulate work

            # Define completion
            if progress >= 200:
                return steps_done_this_batch, True

        return steps_done_this_batch, False
```
**Reasoning:** This logic is simple but stateful. The `exec_engine` reads and writes its progress to the database, just as a real system might checkpoint its state. This allows us to test if Temporal can correctly manage a stateful, long-running activity.

##### **3.6. Temporal Worker Implementation**

This is the core replacement for your Celery workers.

**File: `worker/workflows.py`**
```python
from datetime import timedelta
from temporalio import workflow
from . import activities as act

@workflow.defn
class OrchestrateTaskWorkflow:
    def __init__(self):
        self.stopping = False
        self.paused = False
        self.accepted = False

    @workflow.run
    async def run(self, task_id: str, user_id: str, agent_type: str, title: str):
        # INIT → PLANNING
        await workflow.execute_activity(
            act.init_task, task_id, user_id, agent_type, title,
            schedule_to_close_timeout=timedelta(seconds=30)
        )

        # Optional context (tribal_search)
        if agent_type == "tribal_search":
            await workflow.execute_activity(
                act.gather_context, task_id,
                start_to_close_timeout=timedelta(seconds=30)
            )

        # PLAN v1 then wait for RFC
        await workflow.execute_activity(
            act.create_plan_v1, task_id,
            start_to_close_timeout=timedelta(seconds=30)
        )
        self.paused = True
        await workflow.execute_activity(
            act.mark_wait_rfc, task_id,
            schedule_to_close_timeout=timedelta(seconds=15)
        )

        # Wait for accept / stop
        while self.paused and not self.accepted and not self.stopping:
            await workflow.sleep(1)

        if self.stopping:
            await workflow.execute_activity(act.mark_stopped, task_id)
            return

        # EXECUTION in durable batches
        while True:
            if self.stopping:
                await workflow.execute_activity(act.mark_stopped, task_id)
                return
            if self.paused:
                await workflow.sleep(1)
                continue

            res = await workflow.execute_activity(
                act.execute_batch, task_id, 50,
                # long batch but heartbeat inside activity
                start_to_close_timeout=timedelta(minutes=2),
                heartbeat_timeout=timedelta(seconds=10)
            )
            if res.get("done"):
                await workflow.execute_activity(act.mark_done, task_id)
                break

            # (optional) Continue-As-New policy placeholder
            if res.get("should_continue_as_new"):
                return workflow.continue_as_new(task_id, user_id, agent_type, title)

    # -------- Signals / Queries ----------
    @workflow.signal
    def signal_stop(self, reason: str = ""):
        self.stopping = True

    @workflow.signal
    def signal_resume(self, feedback_text: str | None = None):
        self.paused = False

    @workflow.signal
    def signal_accept_rfc(self):
        self.accepted = True
        self.paused = False

    @workflow.query
    def query_status(self) -> dict:
        return {"stopping": self.stopping, "paused": self.paused, "accepted": self.accepted}
```

**File: `worker/activities.py`**
```python
from temporalio import activity
from backend.minimal_logic import tribal_search, planner, exec_engine
from backend.db import SessionLocal
from backend.models import Task
from backend.sse import publish_event
from uuid import UUID

@activity.defn
async def init_task(task_id, user_id, agent_type, title):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t:
            return
        t.stage = "PLANNING"
        t.stage_status = "RUNNING"
        db.add(t); db.commit()
    publish_event(task_id, {"type":"stage","stage":"PLANNING","status":"RUNNING"})

@activity.defn
async def gather_context(task_id):
    hits = tribal_search.search(task_id)
    publish_event(task_id, {"type":"context","n":len(hits)})

@activity.defn
async def create_plan_v1(task_id):
    plan_text = planner.plan_v1(task_id)
    doc_id = planner.persist_plan(task_id, plan_text, version=1)
    publish_event(task_id, {"type":"plan","doc_id":str(doc_id),"version":1})

@activity.defn
async def mark_wait_rfc(task_id):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t: return
        t.stage = "WAIT_RFC"
        t.stage_status = "PAUSED"
        db.add(t); db.commit()
    publish_event(task_id, {"type":"stage","stage":"WAIT_RFC","status":"PAUSED"})

@activity.defn
async def execute_batch(task_id, max_steps:int=50) -> dict:
    steps_done, done = exec_engine.run_steps(task_id, max_steps=max_steps, heartbeat=activity.heartbeat)
    publish_event(task_id, {"type":"progress","steps":steps_done})
    return {"done": done}

@activity.defn
async def mark_done(task_id):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t: return
        t.stage = "DONE"
        t.stage_status = "COMPLETED"
        db.add(t); db.commit()
    publish_event(task_id, {"type":"stage","stage":"DONE","status":"COMPLETED"})

@activity.defn
async def mark_stopped(task_id):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t: return
        t.stage = "STOPPED"
        t.stage_status = "PAUSED"
        db.add(t); db.commit()
    publish_event(task_id, {"type":"stage","stage":"STOPPED","status":"PAUSED"})
```

**File: `worker/worker.py`**
```python
import asyncio, os, sys
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import OrchestrateTaskWorkflow
from .activities import (
    init_task, gather_context, create_plan_v1, mark_wait_rfc,
    execute_batch, mark_done, mark_stopped
)

async def main():
    target = os.getenv("TEMPORAL_TARGET", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "orchestrator")
    client = await Client.connect(target, namespace=namespace)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[OrchestrateTaskWorkflow],
        activities=[
            init_task, gather_context, create_plan_v1, mark_wait_rfc,
            execute_batch, mark_done, mark_stopped
        ],
    )
    print(f"[worker] connected to {target} ns={namespace} tq={task_queue}")
    await worker.run()

if __name__ == "__main__":
    # ensure backend/ is importable when running from project root
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    asyncio.run(main())
```

**Reasoning:**
*   **Workflow:** The `OrchestrateTaskWorkflow` is the "brain." It contains the high-level business logic and is fully durable. It uses `workflow.sleep` to wait and `await workflow.execute_activity` to perform actions. Its state is automatically saved by Temporal.
*   **Activities:** These are the "hands." They perform all I/O operations (DB calls, publishing to Redis, calling placeholder logic). They are designed to be short and retryable. `activity.heartbeat()` is used in the `execute_batch` activity to tell Temporal it's still making progress on a potentially long-running task.

##### **3.7. Backend API and SSE Implementation**

These files connect the UI to the Temporal backend.

**File: `backend/app.py`**
```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes_tasks import router as tasks_router
from .auth import router as auth_router

app = FastAPI(title="Temporal Intern POC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router, prefix="")
app.include_router(tasks_router, prefix="")

@app.get("/healthz")
async def health(): return {"ok": True}
```

**File: `backend/auth.py`**
```python
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4
from .db import SessionLocal, init_db
from .models import User, Task

router = APIRouter()

class MeResponse(BaseModel):
    user_id: str
    email: str
    tasks: list[dict]

@router.get("/me_v2", response_model=MeResponse)
def me_v2(x_user_id: str = Header(None), x_user_email: str = Header(None)):
    init_db()
    with SessionLocal() as db:
        user = None
        if x_user_id:
            try: user = db.get(User, UUID(x_user_id))
            except Exception: raise HTTPException(status_code=400, detail="Invalid X-User-Id")
        if not user:
            if not x_user_email: x_user_email = f"anon-{uuid4().hex[:8]}@example.com"
            user = db.query(User).filter(User.email == x_user_email).first() or User(id=uuid4(), email=x_user_email)
            db.add(user); db.commit()
        tasks = db.query(Task).filter(Task.user_id == user.id).order_by(Task.created_at.desc()).limit(50).all()
        return MeResponse(user_id=str(user.id), email=user.email,
                          tasks=[{"id": str(t.id), "title": t.title, "agent_type": t.agent_type,
                                  "stage": t.stage, "stage_status": t.stage_status} for t in tasks])
```

**File: `backend/sse.py`**
```python
import os, json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
router = APIRouter()

def _format_sse(data: dict) -> bytes:
    return f"data: {json.dumps(data)}\n\n".encode("utf-8")

async def _stream_channel(channel: str) -> AsyncGenerator[bytes, None]:
    redis = Redis.from_url(REDIS_URL, decode_responses=False)
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        async for msg in pubsub.listen():
            if msg and msg.get("type") == "message":
                payload = msg.get("data")
                if isinstance(payload, (bytes, bytearray)):
                    yield b"data: " + payload + b"\\n\\n"
                else:
                    yield _format_sse(payload)
    finally:
        await redis.close(close_connection_pool=True)

@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    channel = f"sse:{task_id}"
    return StreamingResponse(_stream_channel(channel), media_type="text/event-stream")

# publisher utility for activities
def publish_event(task_id: str, payload: dict):
    from redis import Redis as SyncRedis
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SyncRedis.from_url(url).publish(f"sse:{task_id}", json.dumps(payload))
```

**File: `backend/routes_tasks.py`**
```python
import os
from uuid import uuid4, UUID
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from temporalio.client import Client

from .db import SessionLocal, init_db
from .models import User, Task, TaskDocument, Feedback
from .schema import TaskCreate, FeedbackCreate, FeedbackUpdate, DocumentStatusAction
from .sse import router as sse_router

router = APIRouter()
router.include_router(sse_router)

TEMPORAL_TARGET   = os.getenv("TEMPORAL_TARGET", "localhost:7233")
TEMPORAL_NAMESPACE= os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE        = os.getenv("TEMPORAL_TASK_QUEUE", "orchestrator")

_temporal_client: Optional[Client] = None
async def get_temporal_client() -> Client:
    global _temporal_client
    if _temporal_client is None:
        _temporal_client = await Client.connect(TEMPORAL_TARGET, namespace=TEMPORAL_NAMESPACE)
    return _temporal_client

def ensure_user(x_user_id: Optional[str], x_user_email: Optional[str]) -> User:
    init_db()
    with SessionLocal() as db:
        user = None
        if x_user_id:
            try:
                user = db.get(User, UUID(x_user_id))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid X-User-Id")
        if not user:
            if not x_user_email:
                raise HTTPException(status_code=400, detail="Provide X-User-Email or X-User-Id")
            user = db.query(User).filter(User.email == x_user_email).first()
            if not user:
                user = User(id=uuid4(), email=x_user_email)
                db.add(user); db.commit()
        return user

def workflow_id_for(user_id: str, task_id: str, agent_type: str) -> str:
    return f"u:{user_id}|t:{task_id}|a:{agent_type}"

@router.post("/create_task_id")
async def create_task_id(payload: TaskCreate, x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = Task(id=uuid4(), user_id=user.id, title=payload.title,
                    agent_type=payload.agent_type or "intern",
                    stage="INIT", stage_status="PENDING")
        db.add(task); db.commit()
        wf_id = workflow_id_for(str(user.id), str(task.id), task.agent_type)
        return {"task_id": str(task.id), "workflow_id": wf_id}

@router.post("/tasks/{task_id}/message")
async def start_message(task_id: str, x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        wf_id = task.workflow_id or workflow_id_for(str(user.id), str(task.id), task.agent_type)

    client = await get_temporal_client()

    # If already running, no-op
    handle = client.get_workflow_handle(wf_id)
    try:
        await handle.describe()
        return {"workflow_id": wf_id, "already_running": True}
    except Exception:
        pass

    # Start new run
    from worker.workflows import OrchestrateTaskWorkflow  # type: ignore
    await client.start_workflow(
        OrchestrateTaskWorkflow.run,
        str(task.id), str(user.id), task.agent_type, task.title,
        id=wf_id, task_queue=TASK_QUEUE
    )
    with SessionLocal() as db2:
        db2.query(Task).filter(Task.id==task.id).update({"workflow_id": wf_id, "stage": "PLANNING", "stage_status":"RUNNING"})
        db2.commit()
    return {"workflow_id": wf_id, "started": True}

@router.post("/tasks/{task_id}/accept_rfc")
async def accept_rfc(task_id: str, x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        wf_id = task.workflow_id or workflow_id_for(str(user.id), str(task.id), task.agent_type)
    client = await get_temporal_client()
    handle = client.get_workflow_handle(wf_id)
    await handle.signal("signal_accept_rfc")
    return {"ok": True}

@router.post("/tasks/{task_id}/document/{document_id}/feedback/add")
async def add_feedback(task_id: str, document_id: str, payload: FeedbackCreate,
                       x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        fb = Feedback(document_id=UUID(document_id), body=payload.body)
        db.add(fb); db.commit()
        return {"feedback_id": str(fb.id)}

@router.post("/tasks/{task_id}/document/{document_id}/feedback/{feedback_id}/update")
async def update_feedback(task_id: str, document_id: str, feedback_id: str, payload: FeedbackUpdate,
                          x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        n = db.query(Feedback).filter(Feedback.id==UUID(feedback_id),
                                      Feedback.document_id==UUID(document_id)).update({"body": payload.body})
        if n == 0:
            raise HTTPException(status_code=404, detail="Feedback not found")
        db.commit()
        return {"ok": True}

@router.post("/tasks/{task_id}/document/{document_id}/status")
async def doc_status(task_id: str, document_id: str, payload: DocumentStatusAction,
                     x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    if payload.action != "done_reviewing":
        raise HTTPException(status_code=400, detail="Unsupported action")
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        n = db.query(TaskDocument).filter(TaskDocument.id==UUID(document_id),
                                          TaskDocument.task_id==UUID(task_id)).update({"status": "LOCKED"})
        if n == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        db.commit()
        wf_id = task.workflow_id or workflow_id_for(str(user.id), str(task.id), task.agent_type)
    client = await get_temporal_client()
    handle = client.get_workflow_handle(wf_id)
    await handle.signal("signal_resume", None)
    return {"ok": True}

@router.post("/tasks/{task_id}/force-stop")
async def force_stop(task_id: str, x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task or task.user_id != user.id:
            raise HTTPException(status_code=404, detail="Task not found")
        wf_id = task.workflow_id or workflow_id_for(str(user.id), str(task.id), task.agent_type)
    client = await get_temporal_client()
    handle = client.get_workflow_handle(wf_id)
    await handle.signal("signal_stop", "user")
    return {"ok": True}

@router.get("/agent_status")
async def agent_status(task_id: Optional[str] = None, x_user_id: str = Header(None), x_user_email: str = Header(None)):
    if not task_id:
        return {"ok": True}
    with SessionLocal() as db:
        try:
            task = db.get(Task, UUID(task_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid task_id")
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"task_id": task_id, "stage": task.stage, "stage_status": task.stage_status}
```
**Reasoning:** The API layer is kept "thin." Its job is to handle HTTP requests, authenticate the user, and then delegate the complex orchestration work to Temporal by starting or signaling a workflow. This design makes the API stateless and highly scalable. It reuses your existing SSE bridge via Redis, proving that Temporal can integrate with your current real-time infrastructure.

##### **3.8. Minimal Frontend (`index.html`)**

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Temporal Intern POC</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 20px; background: #f0f2f5; color: #333; }
    .row { display:flex; gap:20px; }
    .col { flex:1; background: #fff; border:1px solid #ddd; padding:18px; border-radius:12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    h2, h3, h4 { color: #1a202c; }
    input, select, button, textarea { font-family: inherit; font-size: 14px; padding:10px; margin:6px 0; width:100%; box-sizing: border-box; border-radius: 6px; border: 1px solid #ccc; }
    button { background: #4a90e2; color: white; border: none; cursor: pointer; font-weight: bold; }
    button:hover { background: #357abd; }
    pre { background:#2d3748; color:#9ae6b4; padding:12px; height:300px; overflow:auto; border-radius: 6px; font-family: 'Courier New', Courier, monospace; font-size: 13px; }
    .task { padding:10px; border-bottom:1px solid #eee; cursor:pointer; transition: background 0.2s; }
    .task:hover { background:#f7fafc; }
    .pill { display:inline-block; padding:3px 9px; border-radius:999px; background:#e2e8f0; margin-left:8px; font-size: 12px; font-weight: 500; }
    #sel { background: #edf2f7; padding: 10px; border-radius: 6px; white-space: pre-wrap; font-family: monospace; }
  </style>
</head>
<body>
  <h2>Temporal Intern POC</h2>
  <div class="row">
    <div class="col">
      <h3>Login</h3>
      <label for="email">Email</label>
      <input id="email" placeholder="you@company.com"/>
      <button onclick="login()">Login / Refresh Tasks</button>
      <div id="me"></div>
      <hr/>
      <h3>Create Task</h3>
      <label for="title">Title</label>
      <input id="title" placeholder="Analyze churn drivers"/>
      <label for="agent">Agent Type</label>
      <select id="agent"><option value="intern">Intern (Complex Flow)</option><option value="tribal_search">Tribal Search</option></select>
      <button onclick="createTask()">Create Task</button>
      <div id="taskList"></div>
    </div>
    <div class="col">
      <h3>Selected Task</h3>
      <pre id="sel">No task selected</pre>
      <button onclick="startTask()">Start</button>
      <button onclick="acceptRFC()">Accept Plan</button>
      <button onclick="doneReviewing()">Done Reviewing Plan</button>
      <button onclick="stopTask()">Stop</button>
      <hr/>
      <h4>Feedback on Plan</h4>
      <textarea id="fb" placeholder="Your feedback for plan revision..."></textarea>
      <button onclick="addFeedback()">Add Feedback</button>
      <hr/>
      <h3>Real-time Stream</h3>
      <pre id="stream"></pre>
    </div>
  </div>

<script>
let user = null, tasks = [], selected = null, evtSrc = null;
const API = "http://localhost:8000";

function headers() {
  const h = {"Content-Type": "application/json"};
  if (user && user.user_id) { h["X-User-Id"] = user.user_id; }
  if (user && user.email) { h["X-User-Email"] = user.email; }
  return h;
}

async function login() {
  const emailInput = document.getElementById("email");
  const email = emailInput.value || emailInput.placeholder;
  const res = await fetch(API+"/me_v2", {headers: {"X-User-Email": email}});
  user = (await res.json()); renderUser(); await refreshTasks();
}

function renderUser() {
  if (!user) return;
  document.getElementById("me").innerHTML = `<div><b>Logged in as: ${user.email}</b><br/>user_id=${user.user_id}</div>`;
}

async function refreshTasks() {
  const res = await fetch(API+"/me_v2", {headers: headers()});
  user = (await res.json());
  tasks = user.tasks || [];
  const list = tasks.map(t => `<div class="task" onclick='selectTask("${t.id}")'>
    <b>${t.title}</b><span class="pill">${t.agent_type}</span>
    <div>Status: ${t.stage || 'N/A'} / ${t.stage_status || 'N/A'}</div>
  </div>`).join("");
  document.getElementById("taskList").innerHTML = `<h4>My Tasks (${tasks.length})</h4>${list}`;
}

async function createTask() {
  const title = document.getElementById("title").value;
  if (!title) { alert("Please enter a title."); return; }
  const agent_type = document.getElementById("agent").value;
  const res = await fetch(API+"/create_task_id", {
    method: "POST", headers: headers(),
    body: JSON.stringify({title, agent_type})
  });
  const data = await res.json();
  await refreshTasks();
  selectTask(data.task_id);
}

function selectTask(id) {
  selected = tasks.find(t => t.id === id) || {id};
  document.getElementById("sel").innerText = JSON.stringify(selected, null, 2);
  if (evtSrc) { evtSrc.close(); }
  const streamEl = document.getElementById("stream");
  streamEl.innerText = "Connecting to stream...\n";
  evtSrc = new EventSource(API+`/tasks/${id}/stream`);
  evtSrc.onmessage = (e) => {
    streamEl.innerText += e.data + "\\n";
    streamEl.scrollTop = streamEl.scrollHeight; // Auto-scroll
    refreshTasks();
  };
  evtSrc.onerror = () => { streamEl.innerText += "Stream connection error.\\n"; };
}

async function startTask() {
  if (!selected) { alert("Select a task first."); return; }
  await fetch(API+`/tasks/${selected.id}/message`, {method:"POST", headers: headers()});
}

async function acceptRFC() {
  if (!selected) { alert("Select a task first."); return; }
  await fetch(API+`/tasks/${selected.id}/accept_rfc`, {method:"POST", headers: headers()});
}

async function doneReviewing() {
  if (!selected) { alert("Select a task first."); return; }
  const docId = findLastDocId();
  if (!docId) { alert("No plan document found in stream to review."); return; }
  await fetch(API+`/tasks/${selected.id}/document/${docId}/status`, {
    method:"POST", headers: headers(), body: JSON.stringify({action:"done_reviewing"})
  });
}

async function addFeedback() {
  if (!selected) { alert("Select a task first."); return; }
  const docId = findLastDocId();
  if (!docId) { alert("No plan document found in stream to add feedback to."); return; }
  const body = document.getElementById("fb").value;
  if (!body) { alert("Feedback text cannot be empty."); return; }
  await fetch(API+`/tasks/${selected.id}/document/${docId}/feedback/add`, {
    method:"POST", headers: headers(), body: JSON.stringify({body})
  });
  document.getElementById("fb").value = "";
}

async function stopTask() {
  if (!selected) { alert("Select a task first."); return; }
  await fetch(API+`/tasks/${selected.id}/force-stop`, {method:"POST", headers: headers()});
}

function findLastDocId() {
  const lines = document.getElementById("stream").innerText.trim().split("\\n");
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const evt = JSON.parse(lines[i]);
      if (evt && evt.type === "plan" && evt.doc_id) return evt.doc_id;
    } catch(e) {}
  }
  return null;
}
</script>
</body>
</html>
```
**Reasoning:** A simple HTML page with vanilla JavaScript is all that's needed to prove the end-to-end functionality. It makes direct calls to the API endpoints and connects to the SSE stream, demonstrating that the frontend can remain blissfully unaware of the backend's orchestration technology.

---

#### **4. Runbook and Validation**

**4.1. Setup and Execution Steps (`README.md`)**
```markdown
# Temporal Intern POC (Standalone)

## 1. Start Infrastructure
In your terminal, run Docker Compose to start Postgres, Redis, and Temporal.

```bash
docker compose up -d
```

## 2. Start API Backend
Open a new terminal, create a virtual environment, and run the FastAPI server.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export DATABASE_URL="postgresql+psycopg2://dev:dev@localhost:5432/intern"
export REDIS_URL="redis://localhost:6379/0"
uvicorn backend.app:app --reload --port 8000
```

## 3. Start Temporal Worker
Open a third terminal, create another virtual environment, and run the Temporal worker.

```bash
python -m venv .venv-worker
source .venv-worker/bin/activate
pip install -r worker/requirements.txt
export DATABASE_URL="postgresql+psycopg2://dev:dev@localhost:5432/intern"
export REDIS_URL="redis://localhost:6379/0"
export TEMPORAL_TARGET="localhost:7233"
export TEMPORAL_NAMESPACE="default"
export TEMPORAL_TASK_QUEUE="orchestrator"
PYTHONPATH=$(pwd) python worker/worker.py
```

## 4. Access the UI
Open `index.html` in your browser.

## 5. Observe with Temporal Web UI
Navigate to [http://localhost:8088](http://localhost:8088) to see your workflows running.
```

**4.2. Validation Scenarios**
To prove the POC is successful, perform these tests:

1.  **Happy Path:**
    *   **Action:** In the UI, enter an email and click "Login". Create a new task. Select it from the list, then click "Start". After the plan appears in the stream, click "Accept Plan".
    *   **Observe:** The stream should show progress ticks until it completes. The task status in the UI should update to `DONE`. The workflow in the Temporal Web UI will show a single, successful workflow execution.

2.  **Crash Recovery Test:**
    *   **Action:** Start a task and accept the plan. While the progress ticks are streaming, find the container ID for the worker (`docker ps | grep worker`) and kill it (`docker kill <container_id>`).
    *   **Observe:** The UI stream will stop. The workflow in Temporal Web will show a pending activity with a red timeout indicator.
    *   **Action:** Restart the worker using the command from step 3 of the runbook.
    *   **Observe:** The new worker process will immediately pick up the timed-out activity. The workflow will resume exactly where it left off, and the UI stream will continue. The task will run to completion. **This demonstrates durability.**

3.  **Clean Stop Signal Test:**
    *   **Action:** Start a task and accept the plan. While it's running, click the "Stop" button.
    *   **Observe:** The workflow will gracefully finish its current small batch of work and then stop. The status in the UI and DB will update to `STOPPED`. The workflow in Temporal Web will show "Completed" (as it handled the stop signal gracefully).

By following this detailed plan, you will have a robust, standalone POC that validates Temporal's capabilities for your specific use case without disrupting your current production system.