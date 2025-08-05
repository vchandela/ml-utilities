# Pavo VPC Deployment

A production-ready, enterprise-grade microservices stack built on Google Cloud Platform (GCP) with complete infrastructure automation, comprehensive monitoring, and Kubernetes deployment capabilities.

## 🏗️ Project Overview

The Pavo VPC deployment is a comprehensive cloud-native application that demonstrates best practices for:
- **Infrastructure as Code** with Terraform
- **Microservices Architecture** with FastAPI
- **Container Orchestration** with Kubernetes (GKE Autopilot)
- **Observability** with Prometheus metrics and monitoring
- **Security** with private networking and secret management
- **CI/CD** with Helm-based deployments

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Phase-by-Phase Implementation](#-phase-by-phase-implementation)
- [Deployment Guide](#-deployment-guide)
- [Testing & Validation](#-testing--validation)
- [Monitoring & Observability](#-monitoring--observability)
- [Security](#-security)
- [Contributing](#-contributing)

## 🏛️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kubernetes    │    │   Applications  │    │   GCP Services  │
│                 │    │                 │    │                 │
│  ┌──────────┐   │    │  ┌──────────┐   │    │  ┌──────────┐   │
│  │ Main App │◄──┼────┼──┤FastAPI   │◄──┼────┤  │PostgreSQL│   │
│  │ Service  │   │    │  │Multi-Svc │   │    │  │Cloud SQL │   │
│  └──────────┘   │    │  └──────────┘   │    │  └──────────┘   │
│                 │    │                 │    │                 │
│  ┌──────────┐   │    │  ┌──────────┐   │    │  ┌──────────┐   │
│  │ Metrics  │◄──┼────┼──┤GCP       │◄──┼────┤  │Redis     │   │
│  │ Exporter │   │    │  │Monitor   │   │    │  │Cache     │   │
│  └──────────┘   │    │  └──────────┘   │    │  └──────────┘   │
│                 │    │                 │    │                 │
│  ┌──────────┐   │    │                 │    │  ┌──────────┐   │
│  │Prometheus│   │    │                 │    │  │Elasticsearch│ │
│  │          │   │    │                 │    │  │& Kibana  │   │
│  └──────────┘   │    │                 │    │  └──────────┘   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ✨ Features

### 🚀 Application Capabilities
- **Multi-Service Integration**: Single API call writes to 5 different services
- **Async Processing**: FastAPI with proper lifespan management
- **Configuration Management**: Environment-based settings with pydantic
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Error Handling**: Comprehensive exception management and logging

### 📊 Monitoring & Observability
- **Application Metrics**: 6 Prometheus metrics tracking service interactions
- **Infrastructure Metrics**: Real-time GCP resource monitoring
- **Distributed Tracing**: Per-request tracking with unique task IDs
- **Health Monitoring**: Service health checks and status reporting

### 🔒 Security & Networking
- **Private VPC**: All services communicate via private IPs
- **Secret Management**: Automated password generation and secure storage
- **IAM Integration**: Kubernetes ServiceAccount with GCP binding
- **Network Isolation**: No public internet access to databases

### 🏗️ Infrastructure Automation
- **Infrastructure as Code**: Complete Terraform configuration
- **Container Orchestration**: GKE Autopilot for cost-effective scaling
- **Helm Deployment**: Production-ready Kubernetes manifests
- **CI/CD Ready**: Versioned deployments with rollback capabilities

## 📁 Project Structure

```
pavo-vpc-deployment/
├── .gitignore                           # Security: prevents credential leaks
├── Dockerfile                          # Main application container
├── README.md                           # This file
├── app/                                # 🚀 Main FastAPI Application
│   ├── __init__.py
│   ├── config.py                      # Environment configuration
│   ├── main.py                        # Multi-service FastAPI app
│   └── requirements.txt               # Python dependencies
├── helm-chart/                        # 🎛️ Kubernetes Deployment
│   ├── Chart.yaml                     # Helm chart metadata
│   ├── values.yaml                    # Configuration values
│   ├── .helmignore                    # Chart packaging rules
│   └── templates/                     # Kubernetes manifests
│       ├── _helpers.tpl               # Template helpers
│       ├── configmap.yaml             # Environment variables
│       ├── deployment.yaml            # Application deployments
│       ├── NOTES.txt                  # Post-install instructions
│       ├── secret.yaml                # Elasticsearch credentials
│       ├── service.yaml               # Network services
│       ├── serviceaccount.yaml        # GCP IAM integration
│       └── servicemonitor.yaml        # Prometheus monitoring
├── metrics_exporter/                  # 📊 Infrastructure Monitoring
│   ├── Dockerfile                     # Metrics service container
│   ├── main.py                        # GCP monitoring integration
│   └── requirements.txt               # Monitoring dependencies
└── terraform/                         # ☁️ Infrastructure as Code
    ├── versions.tf                    # Provider requirements
    ├── main.tf                        # Provider configuration
    ├── variables.tf                   # Input variables
    ├── networking.tf                  # VPC and networking
    ├── gke.tf                         # Kubernetes cluster
    ├── cloudsql.tf                    # PostgreSQL database
    ├── redis.tf                       # Redis cache
    ├── elasticsearch.tf               # Search service
    ├── pubsub_gcs.tf                  # Messaging and storage
    └── outputs.tf                     # Infrastructure outputs
```

## 🛠️ Prerequisites

### Required Tools
- **Terraform** >= 1.0
- **Helm** >= 3.0
- **kubectl** (configured for GKE)
- **Docker** (for building images)
- **gcloud CLI** (authenticated)

### Required Credentials
- **GCP Service Account JSON** (`gcp-credentials.json`)
- **Elastic Cloud API Key** (`elastic-api-key.txt`)

### GCP APIs to Enable
```bash
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable pubsub.googleapis.com
```

## 🚀 Quick Start

### Prerequisites
```bash
# Install tools (macOS)
brew install terraform helm kubectl jq

# Verify installations
terraform --version && helm version && kubectl version --client
```

### Setup
```bash
git clone <repository-url>
cd pavo-vpc-deployment

# Add credentials
cp /path/to/gcp-credentials.json .
cp /path/to/pavo-elastic-api-key.txt .

# Authenticate GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## 📋 Deployment

### 1. Infrastructure (Terraform)
```bash
cd terraform/

# Deploy all infrastructure
terraform init
export EC_API_KEY=$(cat ../pavo-elastic-api-key.txt)
terraform apply

# Save outputs
terraform output -json > ../terraform-outputs.json
cd ..
```

### 2. Container Images
```bash
# Set variables
export IMAGE_VERSION="1.0.4"
export GCP_PROJECT_ID="ml-tool-playground"  # Replace with your project
export GCP_REGION="us-central1"

# Build and push images
docker build -t ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/pavo-vpc/pavo-vpc-main-app:${IMAGE_VERSION} .
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/pavo-vpc/pavo-vpc-main-app:${IMAGE_VERSION}

docker build -t ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/pavo-vpc/pavo-vpc-metrics-exporter:1.0.0 -f metrics_exporter/Dockerfile ./metrics_exporter
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/pavo-vpc/pavo-vpc-metrics-exporter:1.0.0
```

### 3. Monitoring Stack
```bash
# Setup Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

kubectl create namespace monitoring

# Create secrets (replace with your actual values)
kubectl create secret generic grafana-cloud-credentials \
  --namespace monitoring \
  --from-literal=admin-user='admin' \
  --from-literal=admin-password='your_strong_password' \
  --from-literal=username='YOUR_GRAFANA_CLOUD_INSTANCE_ID' \
  --from-literal=password='YOUR_GRAFANA_CLOUD_API_KEY'

# Deploy monitoring
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f monitoring/kube-prometheus-stack-values.yaml
```

### 4. Application
```bash
# Generate values file
cat > customer-values.yaml << EOL
global:
  gcp:
    projectID: "$(jq -r '.gcp_project_id.value' terraform-outputs.json)"
    region: "$(jq -r '.gcp_region.value' terraform-outputs.json)"
    serviceAccountEmail: "$(jq -r '.app_gcp_service_account_email.value' terraform-outputs.json)"

mainApp:
  image:
    repository: "$(jq -r '.gcp_region.value' terraform-outputs.json)-docker.pkg.dev/$(jq -r '.gcp_project_id.value' terraform-outputs.json)/pavo-vpc/pavo-vpc-main-app"
    tag: "1.0.4"

metricsExporter:
  image:
    repository: "$(jq -r '.gcp_region.value' terraform-outputs.json)-docker.pkg.dev/$(jq -r '.gcp_project_id.value' terraform-outputs.json)/pavo-vpc/pavo-vpc-metrics-exporter"

connections:
  dbInstanceConnectionName: "$(jq -r '.cloud_sql_connection_name.value' terraform-outputs.json)"
  dbPasswordSecretName: "$(jq -r '.db_password_secret_name.value' terraform-outputs.json)"
  redisHost: "$(jq -r '.redis_host_ip.value' terraform-outputs.json)"
  gcsBucketName: "$(jq -r '.gcs_bucket_name.value' terraform-outputs.json)"
  pubsubTopicName: "$(jq -r '.pubsub_topic_name.value' terraform-outputs.json)"
  elasticHost: "$(jq -r '.elasticsearch_endpoint.value' terraform-outputs.json)"
  elasticPassword: "$(jq -r '.elasticsearch_password.value' terraform-outputs.json)"
  dbInstanceId: "pavo-vpc-postgres-instance"
  redisInstanceId: "pavo-vpc-redis-cache"

serviceMonitor:
  enabled: true
EOL

# Deploy application
helm upgrade --install pavo-vpc-app ./helm-chart \
  --namespace pavo-services \
  --create-namespace \
  -f customer-values.yaml
```

## ✅ Verification

### Test Application
```bash
# Check pods
kubectl get pods -n pavo-services

# Port forward and test
kubectl port-forward -n pavo-services svc/pavo-vpc-app-helm-chart-main-app 8080:80 &
curl -X POST http://localhost:8080/task \
  -H "Content-Type: application/json" \
  -d '{"content": "Integration test"}'

# Check logs for success
kubectl logs -n pavo-services -l app.kubernetes.io/component=main-app -c pavo-vpc-app --tail=10
```

### Expected Success Logs
```
INFO:main:Task xxx: Successfully wrote to PostgreSQL.
INFO:main:Task xxx: Successfully wrote to Redis.
INFO:main:Task xxx: Successfully indexed in Elasticsearch.
INFO:main:Task xxx: Successfully uploaded to GCS.
INFO:main:Task xxx: Successfully published to Pub/Sub.
```

### Test Monitoring
```bash
# Check monitoring
kubectl get pods -n monitoring
kubectl get servicemonitors -n pavo-services

# Port forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &
curl -s http://localhost:9090/api/v1/targets?state=active | jq '.data.activeTargets[] | select(.labels.job | contains("pavo-vpc-app"))'
```

## 🔄 Management

### Updates
```bash
# Update application
helm upgrade pavo-vpc-app ./helm-chart \
  -n pavo-services \
  -f customer-values.yaml \
  --set mainApp.image.tag=NEW_VERSION

# Update infrastructure
cd terraform/
terraform apply
terraform output -json > ../terraform-outputs.json
# Regenerate customer-values.yaml and run helm upgrade
```

### Rollbacks

#### Helm Rollback
```bash
# List releases
helm history pavo-vpc-app -n pavo-services

# Rollback to previous version
helm rollback pavo-vpc-app -n pavo-services

# Rollback to specific revision
helm rollback pavo-vpc-app 2 -n pavo-services

# Check rollback status
kubectl rollout status deployment/pavo-vpc-app-helm-chart-main-app -n pavo-services
```

#### Terraform Rollback
```bash
cd terraform/

# View state
terraform show

# Import existing resource if needed
terraform import google_sql_database_instance.main your-instance-name

# Rollback to previous state (if you have backup)
terraform apply -backup=terraform.tfstate.backup

# Or destroy and recreate specific resources
terraform destroy -target=resource.name
terraform apply -target=resource.name
```

### Troubleshooting
```bash
# Restart pods
kubectl delete pod -n pavo-services -l app.kubernetes.io/component=main-app

# Check resources
kubectl describe pod -n pavo-services deployment/pavo-vpc-app-helm-chart-main-app
kubectl top pods -n pavo-services

# Debug connectivity
kubectl exec -n pavo-services deployment/pavo-vpc-app-helm-chart-main-app -c pavo-vpc-app -- nslookup google.com
```

### Cleanup
```bash
# Remove application
helm uninstall pavo-vpc-app -n pavo-services

# Remove monitoring
helm uninstall prometheus -n monitoring

# Destroy infrastructure
cd terraform/
terraform destroy
```

## 📊 Available Metrics (Grafana Cloud)

### Application Metrics
- `task_requests_total` - Total requests
- `postgres_writes_success_total` - PostgreSQL writes
- `redis_writes_success_total` - Redis writes  
- `elastic_index_success_total` - Elasticsearch indexes
- `gcs_uploads_success_total` - GCS uploads
- `pubsub_messages_success_total` - Pub/Sub messages

### GCP Infrastructure Metrics
- `gcp_cloudsql_cpu_utilization` - Cloud SQL CPU usage percentage
- `gcp_redis_memory_usage_ratio` - Redis memory consumption ratio
- `gcp_cloudsql_database_up` - Cloud SQL instance availability
- `gcp_redis_instance_up` - Redis instance availability
- `gcp_monitoring_api_calls_total` - Cloud Monitoring API calls made 