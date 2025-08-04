# GCP Infrastructure Metrics Exporter Service
# This service queries GCP's Cloud Monitoring API for infrastructure metrics
# and exposes them in Prometheus format for monitoring our Pavo VPC deployment

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from google.cloud import monitoring_v3
from prometheus_client import Gauge, generate_latest
from starlette.responses import Response
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Settings ---
class Settings(BaseSettings):
    GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID")
    GCP_REGION: str = os.environ.get("GCP_REGION")
    DB_INSTANCE_ID: str = os.environ.get("DB_INSTANCE_ID") # e.g., "pavo-vpc-postgres-instance"
    REDIS_INSTANCE_ID: str = os.environ.get("REDIS_INSTANCE_ID") # e.g., "pavo-vpc-redis-cache"

settings = Settings()

# --- Prometheus Gauges ---
# Gauges are used because the value can go up or down.
GCP_CLOUDSQL_CPU = Gauge('gcp_cloudsql_cpu_utilization', 'Cloud SQL CPU Utilization', ['project_id', 'database_id'])
GCP_REDIS_MEMORY = Gauge('gcp_redis_memory_usage_ratio', 'Redis Memory Usage Ratio', ['project_id', 'instance_id'])
GCP_PUBSUB_UNACKED_MESSAGES = Gauge('gcp_pubsub_oldest_unacked_message_age', 'Age of the oldest unacknowledged Pub/Sub message', ['project_id', 'subscription_id'])

# --- Global Clients ---
monitoring_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global monitoring_client
    logger.info("Metrics exporter starting up...")
    monitoring_client = monitoring_v3.MetricServiceClient()
    yield
    logger.info("Metrics exporter shutting down.")

app = FastAPI(lifespan=lifespan)

def get_latest_metric(project_id, metric_filter):
    """Generic function to fetch the latest value for a given GCP monitoring metric."""
    try:
        project_name = f"projects/{project_id}"
        now = datetime.utcnow()
        interval = monitoring_v3.TimeInterval(
            {"end_time": {"seconds": int(now.timestamp())},
             "start_time": {"seconds": int((now - timedelta(minutes=5)).timestamp())}}
        )

        results = monitoring_client.list_time_series(
            request={
                "name": project_name,
                "filter": metric_filter,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            }
        )
        # Get the most recent point from the first time series found
        for result in results:
            if result.points:
                return result.points[0].value.double_value
    except Exception as e:
        logger.error(f"Failed to fetch metric with filter '{metric_filter}': {e}")
    return 0.0 # Return 0 if metric not found or error

@app.get("/metrics")
async def metrics():
    """Scrapes GCP and returns Prometheus metrics."""
    logger.info("Received request on /metrics. Scraping GCP Monitoring.")

    # 1. Scrape Cloud SQL CPU
    sql_cpu_filter = (f'metric.type = "cloudsql.googleapis.com/database/cpu/utilization" AND '
                      f'resource.labels.database_id = "{settings.GCP_PROJECT_ID}:{settings.DB_INSTANCE_ID}"')
    sql_cpu_val = get_latest_metric(settings.GCP_PROJECT_ID, sql_cpu_filter)
    GCP_CLOUDSQL_CPU.labels(
        project_id=settings.GCP_PROJECT_ID,
        database_id=settings.DB_INSTANCE_ID
    ).set(sql_cpu_val)

    # 2. Scrape Redis Memory Usage
    redis_mem_filter = (f'metric.type = "redis.googleapis.com/instance/memory/usage_ratio" AND '
                        f'resource.labels.instance_id = "{settings.REDIS_INSTANCE_ID}"')
    redis_mem_val = get_latest_metric(settings.GCP_PROJECT_ID, redis_mem_filter)
    GCP_REDIS_MEMORY.labels(
        project_id=settings.GCP_PROJECT_ID,
        instance_id=settings.REDIS_INSTANCE_ID
    ).set(redis_mem_val)

    # Note: For Pub/Sub, you'd typically monitor a subscription. We haven't created one,
    # but the logic would be similar if we did.
    # subscription_id = "your-subscription-id"
    # pubsub_filter = (f'metric.type = "pubsub.googleapis.com/subscription/oldest_unacked_message_age" AND '
    #                  f'resource.labels.subscription_id = "{subscription_id}"')
    # pubsub_val = get_latest_metric(settings.GCP_PROJECT_ID, pubsub_filter)
    # GCP_PUBSUB_UNACKED_MESSAGES.labels(project_id=settings.GCP_PROJECT_ID, subscription_id=subscription_id).set(pubsub_val)

    return Response(generate_latest(), media_type="text/plain")

@app.get("/health")
async def health():
    return {"status": "healthy"} 