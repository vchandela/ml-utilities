"""
Simulated agent execution engine with stateful progress tracking.
Mimics long-running agent work with database state persistence and real-time progress updates.
Supports resume from last checkpoint, heartbeat signaling, and configurable batch execution.
"""
from ..events import publish_event_sync
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
            publish_event_sync(task_id, {"type": "tick", "progress": progress})

            if heartbeat:
                heartbeat()

            time.sleep(0.1) # Simulate work

            # Define completion
            if progress >= 200:
                return steps_done_this_batch, True

        return steps_done_this_batch, False
