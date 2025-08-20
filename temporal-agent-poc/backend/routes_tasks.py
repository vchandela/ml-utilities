"""
Task management API endpoints for the Temporal Agent POC.
Handles task creation, workflow initiation, control signals (start/stop/accept), and feedback management.
Integrates with Temporal client to start workflows and send signals for workflow control.
"""
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
                user = User(email=x_user_email)
                db.add(user); db.commit()
        return user

def workflow_id_for(user_id: str, task_id: str, agent_type: str) -> str:
    return f"u:{user_id}|t:{task_id}|a:{agent_type}"

@router.post("/create_task_id")
async def create_task_id(payload: TaskCreate, x_user_id: str = Header(None), x_user_email: str = Header(None)):
    user = ensure_user(x_user_id, x_user_email)
    with SessionLocal() as db:
        task = Task(user_id=user.id, title=payload.title,
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
        args=[str(task.id), str(user.id), task.agent_type, task.title],
        id=wf_id, 
        task_queue=TASK_QUEUE
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
        
        # Update document status
        n = db.query(TaskDocument).filter(TaskDocument.id==UUID(document_id),
                                          TaskDocument.task_id==UUID(task_id)).update({"status": "LOCKED"})
        if n == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Gather all feedback for this document
        feedback_list = db.query(Feedback).filter(Feedback.document_id==UUID(document_id)).all()
        combined_feedback = " | ".join([f.body for f in feedback_list]) if feedback_list else None
        
        db.commit()
        wf_id = task.workflow_id or workflow_id_for(str(user.id), str(task.id), task.agent_type)
    
    client = await get_temporal_client()
    handle = client.get_workflow_handle(wf_id)
    await handle.signal("signal_resume", combined_feedback)
    return {"ok": True, "feedback_count": len(feedback_list) if feedback_list else 0}

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
