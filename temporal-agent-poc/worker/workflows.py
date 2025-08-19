"""
Temporal workflow definitions for durable agent orchestration.
OrchestrateTaskWorkflow manages the complete agent lifecycle: planning → review → execution.
Provides signal-based control for stop/resume operations and maintains workflow state across crashes.
"""
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
            act.init_task,
            args=[task_id, user_id, agent_type, title],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Optional context (tribal_search)
        if agent_type == "tribal_search":
            await workflow.execute_activity(
                act.gather_context,
                args=[task_id],
                start_to_close_timeout=timedelta(seconds=30),
            )

        # PLAN v1 then wait for RFC
        await workflow.execute_activity(
            act.create_plan_v1,
            args=[task_id],
            start_to_close_timeout=timedelta(seconds=30),
        )
        self.paused = True
        await workflow.execute_activity(
            act.mark_wait_rfc,
            args=[task_id],
            start_to_close_timeout=timedelta(seconds=15),
        )

        # Wait until accepted or stopped (no polling)
        await workflow.wait_condition(lambda: self.accepted or self.stopping)

        if self.stopping:
            await workflow.execute_activity(
                act.mark_stopped, args=[task_id], start_to_close_timeout=timedelta(seconds=15)
            )
            return

        # EXECUTION in durable batches
        while True:
            # If paused, park until resumed or stopped
            if self.paused and not self.stopping:
                await workflow.wait_condition(lambda: (not self.paused) or self.stopping)

            if self.stopping:
                await workflow.execute_activity(
                    act.mark_stopped, args=[task_id], start_to_close_timeout=timedelta(seconds=15)
                )
                return

            res = await workflow.execute_activity(
                act.execute_batch,
                args=[task_id, 50],  # max steps per batch
                start_to_close_timeout=timedelta(minutes=2),
                heartbeat_timeout=timedelta(seconds=10),
            )

            if res.get("done"):
                await workflow.execute_activity(
                    act.mark_done, args=[task_id], start_to_close_timeout=timedelta(seconds=15)
                )
                break

            # (optional) Continue-As-New policy placeholder
            if res.get("should_continue_as_new"):
                return workflow.continue_as_new(self.run, task_id, user_id, agent_type, title)

    # -------- Signals / Queries ----------
    @workflow.signal
    def signal_stop(self, reason: str = ""):
        self.stopping = True

    @workflow.signal
    def signal_resume(self, feedback_text: str | None = None):
        # You can persist feedback via an activity if needed
        self.paused = False

    @workflow.signal
    def signal_accept_rfc(self):
        self.accepted = True
        self.paused = False

    @workflow.query
    def query_status(self) -> dict:
        return {"stopping": self.stopping, "paused": self.paused, "accepted": self.accepted}