"""
Temporal activity implementations for agent task execution.
Activities handle all I/O operations: database updates, plan generation, execution steps.
Each activity updates task status and publishes real-time events for UI updates.
"""
from temporalio import activity
from backend.minimal_logic import tribal_search, planner, exec_engine
from backend.db import SessionLocal
from backend.models import Task
from backend.events import publish_event
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
    await publish_event(task_id, {"type":"stage","stage":"PLANNING","status":"RUNNING"})

@activity.defn
async def gather_context(task_id):
    hits = tribal_search.search(task_id)
    await publish_event(task_id, {"type":"context","n":len(hits)})

@activity.defn
async def create_plan_v1(task_id):
    plan_text = planner.plan_v1(task_id)
    doc_id = planner.persist_plan(task_id, plan_text, version=1)
    await publish_event(task_id, {"type":"plan","doc_id":str(doc_id),"version":1})

@activity.defn
async def mark_wait_rfc(task_id):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t: return
        t.stage = "WAIT_RFC"
        t.stage_status = "PAUSED"
        db.add(t); db.commit()
    await publish_event(task_id, {"type":"stage","stage":"WAIT_RFC","status":"PAUSED"})

@activity.defn
async def execute_batch(task_id, max_steps:int=50) -> dict:
    steps_done, done = exec_engine.run_steps(task_id, max_steps=max_steps, heartbeat=activity.heartbeat)
    await publish_event(task_id, {"type":"progress","steps":steps_done})
    return {"done": done}

@activity.defn
async def mark_done(task_id):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t: return
        t.stage = "DONE"
        t.stage_status = "COMPLETED"
        db.add(t); db.commit()
    await publish_event(task_id, {"type":"stage","stage":"DONE","status":"COMPLETED"})

@activity.defn
async def mark_stopped(task_id):
    with SessionLocal() as db:
        t = db.get(Task, UUID(task_id))
        if not t: return
        t.stage = "STOPPED"
        t.stage_status = "PAUSED"
        db.add(t); db.commit()
    await publish_event(task_id, {"type":"stage","stage":"STOPPED","status":"PAUSED"})
