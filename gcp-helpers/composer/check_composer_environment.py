#!/usr/bin/env python3
import sys
from google.auth import default
from google.auth.transport.requests import Request
from google.api_core.exceptions import NotFound
from google.cloud.orchestration.airflow.service_v1 import EnvironmentsClient

PROJECT  = "ml-tool-playground"
LOCATION = "us-central1"
ENV_NAME = "tool-testing"

client   = EnvironmentsClient(credentials=creds)
env_path = client.environment_path(PROJECT, LOCATION, ENV_NAME)

try:
    client.get_environment(name=env_path)
    print(f"✅  Composer environment '{ENV_NAME}' exists.")
    sys.exit(0)
except NotFound:
    print(f"❌  Composer environment '{ENV_NAME}' not found.")
    sys.exit(1)
