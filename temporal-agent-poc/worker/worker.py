"""
Temporal worker process that executes durable workflows and activities.
Connects to Temporal server and processes workflow tasks from the orchestrator queue.
Replaces Celery workers with crash-resilient, automatically-resuming execution.
"""
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
