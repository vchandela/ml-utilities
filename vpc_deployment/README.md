# Grafana Integration Demo (FastAPI + Prometheus)

This project demonstrates a simple FastAPI application that exposes metrics
to Prometheus and can be visualized in Grafana.

## Features

*   **FastAPI Backend:** A web framework for building APIs.
*   **Prometheus Metrics:** Tracks the number of requests to the `/task` endpoint
    using the `prometheus_client` library.
*   **`/task` Endpoint:** The primary endpoint for performing some simulated work.
*   **`/health` Endpoint:** A basic health check.
*   **`/metrics` Endpoint:** Exposes Prometheus metrics in the required format.

## Local Development and Testing

1.  **Install Dependencies:**
    ```bash
    pip install -r app/requirements.txt
    ```

2.  **Run the application:**
    ```bash
    cd app
    uvicorn main:app --reload --port 8000
    ```

3.  **Test the endpoints:**
    *   Open `http://127.0.0.1:8000/` in your browser.
    *   Open `http://127.0.0.1:8000/task` in your browser (multiple times).
    *   Open `http://127.0.0.1:8000/health` in your browser.
    *   Open `http://127.0.0.1:8000/metrics` in your browser to see the Prometheus metrics. You should see a line like:
        ```
        # HELP task_requests_total Total number of /task endpoint requests received
        # TYPE task_requests_total counter
        task_requests_total 5.0
        ```
        (The `5.0` will update as you hit `/task`).

## Building the Docker Image

1.  **Build the image:**
    ```bash
    docker build -t vpc-deployment:latest .
    ```

2.  **Run the Docker container locally (optional):**
    ```bash
    docker run -p 8080:80 vpc-deployment:latest
    ```
    You can then access the endpoints at `http://127.0.0.1:8080/`.

## GKE Deployment

Now, deploy your application on GKE using cloud build or relevant CI/CD. We'll use a temp namespace `vpc-deployment`
- I'm using manual docker image build → push → deploy for now

1. **Build the Docker image:**
   ```bash
   docker build -t vpc-deployment:latest .
   ```

2. **Create Artifact Registry repository (if not created already):**
   ```bash
   gcloud artifacts repositories create vpc-deployment \
     --repository-format=docker \
     --location=us-central1 \
     --description="Docker repo for vpc-deployment"
   ```

3. **Authenticate with Google Cloud and configure Docker:**
   ```bash
   gcloud auth login                       # if not already logged in
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

4. **Tag your image with full registry path:**
   ```bash
   docker tag vpc-deployment:latest \
     us-central1-docker.pkg.dev/onboarding-455713/vpc-deployment/vpc-deployment:latest
   ```

5. **Push the image to Artifact Registry:**
   ```bash
   docker push us-central1-docker.pkg.dev/onboarding-455713/vpc-deployment/vpc-deployment:latest
   ```

6. **Deploy to GKE:**
   ```bash
   kubectl apply -f infra/values.yaml
   ```

## Next Steps

1. **Configure Prometheus** in your Kubernetes cluster to scrape metrics from your service.
2. **Configure Grafana** to connect to Prometheus and create a dashboard to visualize `task_requests_total`. 