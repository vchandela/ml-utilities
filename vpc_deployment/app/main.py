from fastapi import FastAPI, Request, HTTPException
from prometheus_client import Counter, generate_latest
from starlette.responses import Response
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Prometheus Metrics ---
# Define a counter metric to track the number of /task requests
TASK_REQUEST_COUNT = Counter(
    'task_requests_total',  # Metric name
    'Total number of /task endpoint requests received' # Help text
)

# --- Endpoints ---

@app.get("/")
async def root():
    """
    A simple root endpoint to check if the application is running.
    """
    logger.info("Received request on /")
    return {"message": "Welcome to the Grafana Integration Demo!"}

@app.get("/task")
async def perform_task():
    """
    The main task endpoint that we want to monitor.
    """
    logger.info("Received request on /task. Incrementing task_requests_total.")
    # Increment the counter metric
    TASK_REQUEST_COUNT.inc()

    # In a real application, you would perform your task here.
    # For this demo, we're just returning a success message.
    return {"message": "Task performed successfully!"}

@app.get("/health")
async def health_check():
    """
    A health check endpoint.
    """
    logger.info("Received request on /health")
    # In a real app, you'd check database connections, service availability, etc.
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    """
    Endpoint to expose Prometheus metrics.
    """
    logger.info("Received request on /metrics. Returning Prometheus metrics.")
    return Response(generate_latest(), media_type="text/plain")

# --- Running the application (for local testing) ---
if __name__ == "__main__":
    # This block is for running the app locally with uvicorn.
    # When deploying to GKE, you'll typically use a deployment configuration
    # that specifies how to run this app.
    logger.info("Starting FastAPI application with uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 