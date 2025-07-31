#!/usr/bin/env python3
"""
Trigger a DAG run in a Cloud Composer 3 environment
  project  : ml-tool-playground
  location : us-central1
  env      : tool-testing
  dag_id   : user_sessionization_v2
"""

import datetime
import json
import subprocess
import sys
from typing import Any, Dict, Optional

import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud.orchestration.airflow.service_v1 import EnvironmentsClient

# ── Composer identifiers (edit as needed) ────────────────────────────────────
PROJECT, LOCATION, COMPOSER_ENV = "ml-tool-playground", "us-central1", "tool-testing"
DAG_ID = "user_sessionization_v2"


def trigger_dag(
    project: str,
    location: str,
    env_name: str,
    dag_id: str,
    run_id: Optional[str] = None,
    conf: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """POST /api/v1/dags/{dag_id}/dagRuns and return the API response."""
    try:
        access_token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], 
            text=True, 
            stderr=subprocess.PIPE
        ).strip()
    except subprocess.CalledProcessError as e:
        error_message = f"Failed to get access token: {e.stderr}"
        raise RuntimeError(error_message)

    env_client = EnvironmentsClient()
    env_path = env_client.environment_path(project, location, env_name)
    airflow_uri = env_client.get_environment(name=env_path).config.airflow_uri.rstrip(
        "/"
    )  # exposes the public Airflow web UI URL :contentReference[oaicite:0]{index=0}

    payload = {
        "dag_run_id": run_id or f"manual__{datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        "conf": conf or {},
    }

    resp = requests.post(
        f"{airflow_uri}/api/v1/dags/{dag_id}/dagRuns",  # Stable Airflow 2 endpoint :contentReference[oaicite:1]{index=1}
        headers={"Authorization": f"Bearer {access_token}"},
        json=payload,
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()


# ── Entry-point ──────────────────────────────────────────────────────────────
def main() -> None:
    try:
        result = trigger_dag(PROJECT, LOCATION, COMPOSER_ENV, DAG_ID)
    except Exception as exc:
        print(f"❌  Failed to trigger DAG: {exc}", file=sys.stderr)
        sys.exit(1)

    print("✅  DAG triggered successfully!\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
