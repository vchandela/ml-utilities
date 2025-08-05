# Main FastAPI application for Pavo VPC Deployment project
# This is the heart of our application with complete service integration
# Includes startup/shutdown lifecycle, all GCP service clients, and comprehensive endpoints

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

# --- Import Clients and Configuration ---
import sqlalchemy
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, Column, String, DateTime, func
from google.cloud import pubsub_v1, storage, secretmanager
from redis import asyncio as aioredis
from elasticsearch import AsyncElasticsearch
from prometheus_client import Counter, generate_latest
from starlette.responses import Response

from config import settings

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global Client Variables (to be initialized on startup) ---
db_engine = None
DBSessionLocal = None
redis_client = None
gcs_client = None
pubsub_publisher = None
es_client = None

# --- Prometheus Metrics ---
TASK_REQUEST_COUNT = Counter('task_requests_total', 'Total number of /task endpoint requests received')
POSTGRES_WRITES_SUCCESS = Counter('postgres_writes_success_total', 'Total successful writes to PostgreSQL')
REDIS_WRITES_SUCCESS = Counter('redis_writes_success_total', 'Total successful writes to Redis')
GCS_UPLOADS_SUCCESS = Counter('gcs_uploads_success_total', 'Total successful uploads to GCS')
PUBSUB_MESSAGES_SUCCESS = Counter('pubsub_messages_success_total', 'Total successful messages published to Pub/Sub')
ELASTIC_INDEX_SUCCESS = Counter('elastic_index_success_total', 'Total successful documents indexed in Elasticsearch')

# --- Helper Function to Fetch Secrets ---
def get_secret(secret_name: str, project_id: str) -> str:
    """Fetches a secret from Google Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to fetch secret '{secret_name}': {e}")
        raise

# --- FastAPI Lifespan Manager (for startup/shutdown events) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    global db_engine, DBSessionLocal, redis_client, gcs_client, pubsub_publisher, es_client

    logger.info("Application starting up...")

    # 1. Fetch DB Password from Secret Manager
    logger.info(f"Fetching DB password from secret: {settings.DB_PASSWORD_SECRET_NAME}")
    settings.DB_PASSWORD = get_secret(settings.DB_PASSWORD_SECRET_NAME, settings.GCP_PROJECT_ID)

    # 2. Initialize Database Connection (SQLAlchemy)
    logger.info(f"Initializing database connection to {settings.DB_HOST}:{settings.DB_PORT}")
    db_engine = create_engine(settings.DATABASE_URL)
    DBSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    Base.metadata.create_all(bind=db_engine) # Create tables if they don't exist

    # 3. Initialize Redis Client
    logger.info(f"Initializing Redis connection to {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    redis_client = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True)

    # 4. Initialize Google Cloud Storage Client
    logger.info(f"Initializing GCS client for bucket: {settings.GCS_BUCKET_NAME}")
    gcs_client = storage.Client(project=settings.GCP_PROJECT_ID)

    # 5. Initialize Pub/Sub Publisher Client
    logger.info(f"Initializing Pub/Sub publisher for topic: {settings.PUBSUB_TOPIC_NAME}")
    pubsub_publisher = pubsub_v1.PublisherClient()

    # 6. Initialize Elasticsearch Client
    logger.info(f"Initializing Elasticsearch client to {settings.ELASTIC_HOST}")
    es_client = AsyncElasticsearch(
        hosts=[settings.ELASTIC_HOST],
        basic_auth=("elastic", settings.ELASTIC_PASSWORD)
    )

    yield  # Application is now running

    # --- Shutdown Logic ---
    logger.info("Application shutting down...")
    await redis_client.close()
    await es_client.close()
    logger.info("Connections closed.")

app = FastAPI(lifespan=lifespan)

# --- Database Model (SQLAlchemy) ---
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, index=True)
    content = Column(String)
    status = Column(String, default="received")
    created_at = Column(DateTime, default=func.now())

# --- API Request/Response Models (Pydantic) ---
class TaskData(BaseModel):
    content: str = Field(..., example="This is my important task content.")

# --- API Endpoints ---
@app.get("/")
async def root():
    return {"message": "Pavo VPC Service is running!"}

@app.get("/health")
async def health_check():
    # A simple health check. In production, you'd check connections.
    try:
        await redis_client.ping()
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy", "reason": "Redis ping failed"}

@app.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {"status": "ready"}

@app.post("/task", status_code=201)
async def perform_task(task_data: TaskData, request: Request):
    """The main endpoint to process a new task."""
    TASK_REQUEST_COUNT.inc()
    task_id = str(uuid.uuid4())

    try:
        # 1. Write to Postgres
        with DBSessionLocal() as db:
            new_task = Task(id=task_id, content=task_data.content, status="processing")
            db.add(new_task)
            db.commit()
            POSTGRES_WRITES_SUCCESS.inc()
            logger.info(f"Task {task_id}: Successfully wrote to PostgreSQL.")

        # 2. Write to Redis
        await redis_client.set(f"task_status:{task_id}", "processing", ex=3600) # 1 hour expiry
        REDIS_WRITES_SUCCESS.inc()
        logger.info(f"Task {task_id}: Successfully wrote to Redis.")

        # 3. Write to Elasticsearch
        await es_client.index(
            index="tasks_index",
            id=task_id,
            document={"id": task_id, "content": task_data.content}
        )
        ELASTIC_INDEX_SUCCESS.inc()
        logger.info(f"Task {task_id}: Successfully indexed in Elasticsearch.")

        # 4. Upload to GCS
        bucket = gcs_client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(f"tasks/{task_id}.txt")
        blob.upload_from_string(task_data.content)
        GCS_UPLOADS_SUCCESS.inc()
        logger.info(f"Task {task_id}: Successfully uploaded to GCS.")

        # 5. Publish to Pub/Sub
        topic_path = pubsub_publisher.topic_path(settings.GCP_PROJECT_ID, settings.PUBSUB_TOPIC_NAME)
        message_data = f'{{"task_id": "{task_id}", "status": "submitted"}}'.encode("utf-8")
        pubsub_publisher.publish(topic_path, data=message_data)
        PUBSUB_MESSAGES_SUCCESS.inc()
        logger.info(f"Task {task_id}: Successfully published to Pub/Sub.")

    except Exception as e:
        logger.error(f"Task {task_id}: FAILED during processing. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

    return {"message": "Task received and processing started.", "task_id": task_id}

@app.get("/metrics")
async def metrics():
    """Endpoint to expose Prometheus metrics."""
    return Response(generate_latest(), media_type="text/plain") 