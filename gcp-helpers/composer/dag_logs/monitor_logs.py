#!/usr/bin/env python3
# Filename: dag_log_fetcher.py
"""
State-aware monitor for Cloud Composer DAG runs.
Reads log entries from Cloud Logging, tracks per-task status, and stops
when the DAG has either succeeded or any task has failed.
"""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ─────────────── logging config for library users ───────────────
logger = logging.getLogger(__name__)

# ─────────────── dependencies ───────────────
try:
    from google.cloud import logging_v2
    from google.api_core import exceptions as google_exceptions
    from google.protobuf.json_format import MessageToJson
except ImportError:  # pragma: no cover
    print(
        "Error: Required Google Cloud libraries are not installed.\n"
        "Install with:  pip install google-cloud-logging google-auth"
    )
    sys.exit(1)

# ─────────────── constants ───────────────
TASK_STATE_REGEX = re.compile(
    r"Marking task as (?P<state>\w+)\..*task_id=(?P<task_id>[\w.-]+)"
)

# ────────────────────────────────────────────────────────────────────
#  Fetch logs
# ────────────────────────────────────────────────────────────────────
async def fetch_airflow_logs_async(
    dag_id: str,
    composer_project_id: str,
    composer_environment_name: Optional[str],
    composer_location: Optional[str],
    fetch_start_time_iso: str,
) -> Dict[str, Any]:
    """
    Fetch log entries for *dag_id* newer than *fetch_start_time_iso*.
    Returns a dict with keys: status, logs, latest_log_timestamp, error_message.
    """
    fetch_logger = logging.getLogger(__name__)

    try:
        logging_client = logging_v2.Client(project=composer_project_id)
    except Exception as exc:  # pragma: no cover
        msg = f"Failed to initialise Cloud Logging client: {exc}"
        fetch_logger.error(msg)
        return {"status": "error", "error_message": msg}

    # 1) Build filter  ---------------------------------------------------------
    resource_filter = 'resource.type="cloud_composer_environment"'
    if composer_environment_name:
        resource_filter += (
            f' AND resource.labels.environment_name="{composer_environment_name}"'
        )
    if composer_location:
        resource_filter += (
            f' AND resource.labels.location="{composer_location}"'
        )

    dag_id_filter = f'textPayload:"{dag_id}"'
    # logName (case-sensitive) not log_name
    log_name_filter = f'logName=~"projects/{composer_project_id}/logs/airflow"'

    base_filter = f"({resource_filter}) AND {log_name_filter} AND ({dag_id_filter})"
    filter_with_time = f'{base_filter} AND timestamp > "{fetch_start_time_iso}"'

    fetch_logger.debug("Cloud Logging filter: %s", filter_with_time)

    # 2) Pull entries  ---------------------------------------------------------
    fetched_logs: List[Dict[str, Any]] = []

    try:
        iterator = logging_client.list_entries(
            filter_=filter_with_time,
            order_by="timestamp asc",
        )

        for entry in iterator:
            # 🟢 UPDATED: use the universal `.payload` attribute
            try:
                payload_data = entry.payload
            except AttributeError:  # pre-3.0 client fallback
                payload_data = (
                    getattr(entry, "text_payload", None)
                    or getattr(entry, "json_payload", None)
                    or getattr(entry, "struct_payload", None)
                )

            # Ensure struct payloads become serialisable JSON
            if not isinstance(payload_data, (str, dict)):
                try:
                    payload_data = json.loads(MessageToJson(payload_data))
                except Exception:  # pragma: no cover
                    payload_data = str(payload_data)

            # 🟢 UPDATED: severity may be enum in 3.x
            sev = (
                entry.severity.name
                if hasattr(entry.severity, "name")
                else str(entry.severity)
            )

            fetched_logs.append(
                {
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "severity": sev,
                    "payload": payload_data,
                    "log_name": entry.log_name,
                    "resource_type": entry.resource.type if entry.resource else None,
                    "resource_labels": dict(entry.resource.labels)
                    if entry.resource
                    else None,
                }
            )

    except google_exceptions.GoogleAPIError as exc:
        msg = f"Cloud Logging API error: {exc}"
        fetch_logger.error(msg)
        return {"status": "error", "error_message": msg}
    except Exception as exc:  # pragma: no cover
        msg = f"Unexpected error while fetching logs: {exc}"
        fetch_logger.error(msg)
        return {"status": "error", "error_message": msg}

    latest_ts = fetched_logs[-1]["timestamp"] if fetched_logs else None
    return {"status": "success", "logs": fetched_logs, "latest_log_timestamp": latest_ts}


# ────────────────────────────────────────────────────────────────────
#  Analyse logs for task state changes
# ────────────────────────────────────────────────────────────────────
def analyse_logs_for_dag_state(
    logs: List[Dict[str, Any]],
    current_task_states: Dict[str, str],
) -> Tuple[Dict[str, str], bool]:
    """
    Update `current_task_states` according to any “Marking task as …” lines.
    Returns (updated_task_states, dag_is_failed).
    """
    analysis_logger = logging.getLogger(__name__)
    dag_is_failed = False

    for log in logs:
        payload = log.get("payload", "")
        if not isinstance(payload, str):
            continue

        match = TASK_STATE_REGEX.search(payload)
        if not match:
            continue

        task_id = match.group("task_id")
        state = match.group("state").upper()  # SUCCESS | FAILED | UP_FOR_RETRY …

        if current_task_states.get(task_id) != state:
            analysis_logger.info("State change: %s → %s", task_id, state)
            current_task_states[task_id] = state
            if state == "FAILED":
                analysis_logger.error("Terminal failure for task %s", task_id)
                dag_is_failed = True

    return current_task_states, dag_is_failed


# ────────────────────────────────────────────────────────────────────
#  Main monitoring loop
# ────────────────────────────────────────────────────────────────────
async def monitor_airflow_dag_logs(
    dag_id: str,
    composer_project_id: str,
    relative_log_file_path: str,
    composer_environment_name: Optional[str] = None,
    composer_location: Optional[str] = None,
    max_monitor_duration_minutes: int = 30,
    check_interval_seconds: int = 60,
    log_lookback_minutes: int = 15,
):
    """
    Poll Cloud Logging, track per-task status, and stop on success/failure.
    """
    function_logger = logging.getLogger(__name__)
    function_logger.info("Monitoring DAG %s …", dag_id)

    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=max_monitor_duration_minutes)
    last_ts_iso = (start_time - timedelta(minutes=log_lookback_minutes)).isoformat()

    all_logs: List[Dict[str, Any]] = []
    task_states: Dict[str, str] = {}
    known_tasks: Set[str] = set()
    final_status = "monitoring_timed_out"

    while datetime.now(timezone.utc) < end_time:
        result = await fetch_airflow_logs_async(
            dag_id=dag_id,
            composer_project_id=composer_project_id,
            composer_environment_name=composer_environment_name,
            composer_location=composer_location,
            fetch_start_time_iso=last_ts_iso,
        )

        if result["status"] == "error":
            function_logger.error("Log fetch failed: %s", result["error_message"])
            final_status = "error_in_tool"
            break

        new_logs = result["logs"]
        if new_logs:
            function_logger.info("Fetched %d new entries", len(new_logs))
            all_logs.extend(new_logs)
            last_ts_iso = result["latest_log_timestamp"]

            task_states, dag_failed = analyse_logs_for_dag_state(new_logs, task_states)
            known_tasks.update(task_states.keys())

            if dag_failed:
                final_status = "dag_failed"
                break

            if known_tasks and all(task_states.get(t) == "SUCCESS" for t in known_tasks):
                function_logger.info("All tasks SUCCESS – DAG succeeded")
                final_status = "dag_succeeded"
                break
        else:
            function_logger.info("No new logs")

        function_logger.info("Sleeping %ds", check_interval_seconds)
        await asyncio.sleep(check_interval_seconds)

    # ── write out collected logs & summary ─────────────────────────
    log_file_path = Path(relative_log_file_path).resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file_path, "w", encoding="utf-8") as fh:
        json.dump(
            {"summary": {"final_status": final_status, "task_states": task_states}, "logs": all_logs},
            fh,
            indent=2,
        )

    status_msg = {
        "dag_succeeded": "🟢 DAG run succeeded",
        "dag_failed": "🔴 DAG run failed",
        "error_in_tool": "❗ Error inside monitor",
        "monitoring_timed_out": "🟡 Monitoring timed out",
    }[final_status]
    print(f"\n{status_msg}  –  details saved to {log_file_path}")
    return {"final_status": final_status, "task_states": task_states, "log_file": str(log_file_path)}


# ────────────────────────────────────────────────────────────────────
#  CLI wrapper
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor Cloud Composer DAG by reading Cloud Logging.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dag_id", required=True)
    parser.add_argument("--composer_project_id", required=True)
    parser.add_argument("--relative_log_file_path", required=True)
    parser.add_argument("--composer_environment_name")
    parser.add_argument("--composer_location")
    parser.add_argument("--max_monitor_duration_minutes", type=int, default=5)
    parser.add_argument("--check_interval_seconds", type=int, default=60)
    parser.add_argument("--log_lookback_minutes", type=int, default=15)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        asyncio.run(
            monitor_airflow_dag_logs(
                dag_id=args.dag_id,
                composer_project_id=args.composer_project_id,
                relative_log_file_path=args.relative_log_file_path,
                composer_environment_name=args.composer_environment_name,
                composer_location=args.composer_location,
                max_monitor_duration_minutes=args.max_monitor_duration_minutes,
                check_interval_seconds=args.check_interval_seconds,
                log_lookback_minutes=args.log_lookback_minutes,
            )
        )
    except KeyboardInterrupt:  # pragma: no cover
        print("\nInterrupted by user.")