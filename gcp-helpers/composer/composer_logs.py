#!/usr/bin/env python3
"""
Show *all* Airflow import-error traces for the Composer env
  project  : ml-tool-playground
  location : us-central1
  env      : tool-testing
"""

from google.auth import default
from google.auth.transport.requests import Request
from google.cloud.orchestration.airflow.service_v1 import EnvironmentsClient
import requests, textwrap
import subprocess

PROJECT, LOCATION, COMPOSER_ENV = "ml-tool-playground", "us-central1", "tool-testing"

def main() -> None:
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
    env_path   = env_client.environment_path(PROJECT, LOCATION, COMPOSER_ENV)
    base_url   = env_client.get_environment(name=env_path).config.airflow_uri.rstrip("/")

    r = requests.get(f"{base_url}/api/v1/importErrors?limit=1000",
                     headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    r.raise_for_status()

    errors = r.json().get("import_errors", [])
    if not errors:
        print("✅  No import errors in this Composer environment.")
        return

    for e in errors:
        print("\n" + "=" * 88)
        print(f"FILE : {e['filename']}")
        print("TRACE:")
        print(textwrap.dedent(e["stack_trace"]).rstrip())
        print("=" * 88)

if __name__ == "__main__":
    main()
