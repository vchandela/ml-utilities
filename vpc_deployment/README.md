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

### 1. Clone and Setup
```bash
git clone <repository-url>
cd pavo-vpc-deployment

# Place your credentials in the root directory
cp /path/to/your/gcp-credentials.json .
cp /path/to/your/elastic-api-key.txt .
```

Install terraform: 
- `brew install terraform` (MacOs)
- `terraform --version`


### 2. Deploy Infrastructure (TBD by Customer)
```bash
cd terraform/

# Initialize Terraform
terraform init

# Set Elastic API key
export EC_API_KEY=$(cat ../elastic-api-key.txt)

# Deploy infrastructure (-out makes sure there's no drift between planning and applying)
terraform plan -out=tfplan
terraform apply "tfplan"
```

### 3. Build and Push Images (TBD by Vendor)
```bash
# configure docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build main application
export MAIN_APP_IMAGE_NAME="us-central1-docker.pkg.dev/ml-tool-playground/pavo-vpc/pavo-vpc-main-app:1.0.0"
docker build -t ${MAIN_APP_IMAGE_NAME} -f Dockerfile .
docker push ${MAIN_APP_IMAGE_NAME}

# Build metrics exporter
export METRICS_EXPORTER_IMAGE_NAME="us-central1-docker.pkg.dev/ml-tool-playground/pavo-vpc/pavo-vpc-metrics-exporter:1.0.0"
docker build -t ${METRICS_EXPORTER_IMAGE_NAME} -f metrics_exporter/Dockerfile ./metrics_exporter
docker push ${METRICS_EXPORTER_IMAGE_NAME}
```

### 4. Deploy Applications (TBD by Customer)
```bash
# Create values file from Terraform outputs
cd terraform && terraform output -json

cat > customer-values.yaml << EOF
global:
  gcp:
    projectID: "YOUR_PROJECT_ID"
    region: "us-central1"
    serviceAccountEmail: "your-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com"

connections:
  dbInstanceConnectionName: "$(terraform output -raw cloud_sql_connection_name)"
  dbPasswordSecretName: "$(terraform output -raw db_password_secret_name)"
  redisHost: "$(terraform output -raw redis_host_ip)"
  gcsBucketName: "$(terraform output -raw gcs_bucket_name)"
  pubsubTopicName: "$(terraform output -raw pubsub_topic_name)"
  elasticHost: "$(terraform output -raw elasticsearch_endpoint)"
  elasticPassword: "$(terraform output -raw elasticsearch_password)"
  dbInstanceId: "pavo-vpc-postgres-instance"
  redisInstanceId: "pavo-vpc-redis-cache"
EOF

#Check helm version
helm version

#Validate helm chart
helm lint helm-chart/

#Dry run to see what resources will be created
helm upgrade --install pavo-vpc-app ./helm-chart -f customer-values.yaml --namespace pavo-services --create-namespace --dry-run

# Deploy with Helm (first time)
helm upgrade --install pavo-vpc-app ./helm-chart -f customer-values.yaml --namespace pavo-services --create-namespace --set mainApp.image.tag=1.0.0 --set metricsExporter.image.tag=1.0.0

# deploy with Helm (subsequent runs; image tag will be picked from customer-values.yaml)
helm upgrade pavo-vpc-app ./helm-chart -f customer-values.yaml -n pavo-services
```

### 5. Verification
```bash
# Check all pods are running properly
kubectl get pods -n pavo-services -l app.kubernetes.io/instance=pavo-vpc-app

#Check pod logs

#Setup port forwarding for main-app from local machine to Kubernetes (& means run in background)
kubectl port-forward -n pavo-services svc/pavo-vpc-app-helm-chart-main-app 8080:80 &

# Create a task
curl -X POST http://localhost:8080/task -H "Content-Type: application/json" -d '{"content": "Test task from successful deployment!"}'

# Expected output
# INFO:main:Task 899e2a41-4ea9-42a1-bfec-b15f3e37c310: Successfully wrote to PostgreSQL.
# INFO:main:Task 899e2a41-4ea9-42a1-bfec-b15f3e37c310: Successfully wrote to Redis.
# INFO:main:Task 899e2a41-4ea9-42a1-bfec-b15f3e37c310: Skipping Elasticsearch write as client is not available.
# INFO:main:Task 899e2a41-4ea9-42a1-bfec-b15f3e37c310: Successfully uploaded to GCS.
# INFO:main:Task 899e2a41-4ea9-42a1-bfec-b15f3e37c310: Successfully published to Pub/Sub.
```

## Prometheus Monitoring Support (TBD by customer)
- `kube-prometheus-stack-values.yaml` is for GKE Autopilot cluster and not GKE Standard cluster
- Make sure you're in the right cluster: `kubectl config current-context`
```bash
# Add Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
# [Optional] update the helm repos
helm repo update

kubectl create namespace monitoring
# Create secrets (if not already present)
kubectl create secret generic grafana-cloud-credentials --namespace monitoring --from-literal=admin-user='admin' --from-literal=admin-password='your_strong_password' --from-literal=username='YOUR_GRAFANA_CLOUD_INSTANCE_ID' --from-literal=password='YOUR_GRAFANA_CLOUD_API_KEY'
# Install kube-prometheus-stack into the 'monitoring' namespace
helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring -f monitoring/kube-prometheus-stack-values.yaml
# Verify monitoring pods
kubectl get pods -n monitoring
# Re-deploy the application using helm (with service monitors enabled)
RELEASE_NAME="pavo-vpc-app" && NAMESPACE="pavo-services" && echo "Upgrading application release to enable ServiceMonitors..." && helm upgrade --install ${RELEASE_NAME} ./helm-chart --namespace ${NAMESPACE} -f customer-values.yaml
# Check servicemonitors were created
kubectl get servicemonitors -n pavo-services
# Check prometheus targets (Discovery verification)
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &
# Test Prometheus Access and Check Targets Discovery
curl -s http://localhost:9090/api/v1/targets?state=active | jq '.data.activeTargets[] | select(.labels.job | contains("pavo-vpc-app")) | {job: .labels.job, health: .health, lastScrape: .lastScrape}' # you should see no. of target = no. of total pods
```
## 📋 Phase-by-Phase Implementation

### Phase 1: Repository Restructuring ✅
**Objective**: Clean, organized project structure

**Deliverables**:
- ✅ Proper directory structure with clear separation of concerns
- ✅ Security-focused `.gitignore` preventing credential leaks
- ✅ Pavo-VPC naming convention throughout project
- ✅ Placeholder files and basic structure

### Phase 2: Infrastructure as Code ✅
**Objective**: Automated GCP infrastructure provisioning

**Deliverables**:
- ✅ **10 Terraform files** creating complete infrastructure
- ✅ **VPC with private networking** (`pavo-vpc`)
- ✅ **GKE Autopilot cluster** (`pavo-vpc-autopilot-cluster`)
- ✅ **Cloud SQL PostgreSQL** with auto-generated secrets
- ✅ **Redis cache** + **Elasticsearch** + **GCS** + **Pub/Sub**
- ✅ **Secret Manager** integration for credential security

### Phase 3: FastAPI Application Enhancement ✅
**Objective**: Production-ready microservice with full GCP integration

**Deliverables**:
- ✅ **Multi-service writes**: PostgreSQL, Redis, Elasticsearch, GCS, Pub/Sub
- ✅ **pydantic-settings** configuration management
- ✅ **Async lifespan management** with proper startup/shutdown
- ✅ **SQLAlchemy ORM** with database models
- ✅ **6 Prometheus metrics** for comprehensive monitoring
- ✅ **Health checks** for Kubernetes readiness/liveness

### Phase 4: Cross-Project Metrics Exporter ✅
**Objective**: Separate service for GCP infrastructure monitoring

**Deliverables**:
- ✅ **Independent FastAPI service** for metrics collection
- ✅ **Real GCP Cloud Monitoring API** integration
- ✅ **Prometheus-compatible metrics** for infrastructure
- ✅ **Monitoring**: Cloud SQL CPU, Redis memory usage
- ✅ **Production deployment** with proper error handling

### Phase 5: Helm-based Deployment ✅
**Objective**: Production-ready Kubernetes deployment system

**Deliverables**:
- ✅ **Complete Helm chart** with 9 template files
- ✅ **Both applications** deployed with proper networking
- ✅ **Cloud SQL Proxy sidecar** for secure database access
- ✅ **Prometheus ServiceMonitors** for automatic discovery
- ✅ **GCP IAM integration** via Kubernetes service accounts
- ✅ **Comprehensive configuration** management
- ✅ **Post-deployment instructions** and testing commands

## 🚀 Deployment Guide

### Infrastructure Deployment

1. **Initialize Terraform**:
```bash
cd terraform/
terraform init
```

2. **Configure Variables** (optional):
```bash
# Edit terraform/variables.tf or create terraform.tfvars
echo 'gcp_project_id = "your-project-id"' > terraform.tfvars
echo 'gcp_region = "us-central1"' >> terraform.tfvars
```

3. **Deploy Infrastructure**:
```bash
export EC_API_KEY=$(cat ../elastic-api-key.txt)
terraform plan
terraform apply
```

### Application Deployment

1. **Prepare Configuration**:
```bash
# Extract Terraform outputs for Helm values
terraform output -json > terraform-outputs.json
```

2. **Install with Helm**:
```bash
helm upgrade --install pavo-vpc ./helm-chart \
  --namespace pavo-vpc-services \
  --create-namespace \
  --set global.gcp.projectID="your-project-id" \
  --set connections.elasticPassword="your-elastic-password"
```

### Rollback Strategy

```bash
# View deployment history
helm history pavo-vpc -n pavo-vpc-services

# Rollback to previous version
helm rollback pavo-vpc 1 -n pavo-vpc-services
```

## 🧪 Testing & Validation

### Application Testing

1. **Port Forward to Application**:
```bash
kubectl port-forward -n pavo-vpc-services svc/pavo-vpc-main-app 8080:80
```

2. **Test Task Creation**:
```bash
curl -X POST http://localhost:8080/task \
  -H "Content-Type: application/json" \
  -d '{"content": "Test task from Pavo VPC deployment"}'
```

3. **Verify Multi-Service Writes**:
```bash
# Check application logs
kubectl logs -n pavo-vpc-services -l app.kubernetes.io/component=main-app -c pavo-vpc-app --tail=50

# Expected log entries:
# - Successfully wrote to PostgreSQL
# - Successfully wrote to Redis  
# - Successfully indexed in Elasticsearch
# - Successfully uploaded to GCS
# - Successfully published to Pub/Sub
```

### Infrastructure Validation

1. **Check Pod Status**:
```bash
kubectl get pods -n pavo-vpc-services
```

2. **Verify Metrics Collection**:
```bash
# Port forward to metrics exporter
kubectl port-forward -n pavo-vpc-services svc/pavo-vpc-metrics-exporter 8082:80

# Check GCP infrastructure metrics
curl http://localhost:8082/metrics
```

3. **Database Connectivity**:
```bash
# Exec into main app pod
kubectl exec -it -n pavo-vpc-services deployment/pavo-vpc-main-app -c pavo-vpc-app -- /bin/bash

# Test database connection (inside pod)
python -c "
from app.config import settings
print(f'DB Host: {settings.DB_HOST}')
print(f'Redis Host: {settings.REDIS_HOST}')
"
```

## 📊 Monitoring & Observability

### Application Metrics

The main application exposes the following Prometheus metrics:

- `task_requests_total` - Total API requests received
- `postgres_writes_success_total` - Successful PostgreSQL writes
- `redis_writes_success_total` - Successful Redis writes  
- `gcs_uploads_success_total` - Successful GCS uploads
- `pubsub_messages_success_total` - Successful Pub/Sub messages
- `elastic_index_success_total` - Successful Elasticsearch indexing

### Infrastructure Metrics

The metrics exporter provides:

- `gcp_cloudsql_cpu_utilization` - Cloud SQL CPU usage
- `gcp_redis_memory_usage_ratio` - Redis memory consumption

### Accessing Metrics

```bash
# Application metrics
kubectl port-forward -n pavo-vpc-services svc/pavo-vpc-main-app 8081:80
curl http://localhost:8081/metrics

# Infrastructure metrics  
kubectl port-forward -n pavo-vpc-services svc/pavo-vpc-metrics-exporter 8082:80
curl http://localhost:8082/metrics
```

### Prometheus Integration

If you have Prometheus Operator installed, the ServiceMonitors will automatically configure scraping:

```bash
# Check ServiceMonitor status
kubectl get servicemonitor -n pavo-vpc-services

# Verify Prometheus targets
# Visit Prometheus UI → Status → Targets
# Look for pavo-vpc-main-app and pavo-vpc-metrics-exporter
```

## 🔐 Security

### Network Security
- **Private VPC**: All resources communicate via private IPs
- **No Public Database Access**: Cloud SQL accessible only within VPC
- **Secure Service Communication**: Kubernetes internal networking

### Credential Management
- **Secret Manager**: Database passwords auto-generated and stored securely
- **Kubernetes Secrets**: Elasticsearch credentials managed by K8s
- **IAM Integration**: Service accounts with minimal required permissions

### Container Security
- **Non-root Containers**: All containers run as unprivileged users
- **Security Contexts**: Proper security context configuration
- **Image Scanning**: Recommended for production deployments

## 🛠️ Development

### Local Development

1. **Setup Python Environment**:
```bash
cd app/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Run Application Locally**:
```bash
# Set required environment variables
export GCP_PROJECT_ID=your-project-id
export DB_HOST=127.0.0.1
export REDIS_HOST=your-redis-host
# ... other environment variables

uvicorn app.main:app --reload --port 8000
```

### Building Images

```bash
# Main application
docker build -t pavo-vpc-main-app:latest .

# Metrics exporter
docker build -t pavo-vpc-metrics-exporter:latest ./metrics_exporter/
```

### Helm Chart Development

```bash
# Lint Helm chart
helm lint ./helm-chart/

# Debug template rendering
helm template pavo-vpc ./helm-chart/ --values ./helm-chart/values.yaml

# Dry run deployment
helm upgrade --install pavo-vpc ./helm-chart/ --dry-run --debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Add comprehensive logging for new features
- Include proper error handling
- Update tests for new functionality
- Document configuration changes in values.yaml

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Cloud Platform for infrastructure services
- Elastic for search capabilities  
- Prometheus community for monitoring standards
- Helm community for Kubernetes package management
- FastAPI team for the excellent Python framework

---

**🎯 Pavo VPC Deployment - Production-Ready Cloud-Native Microservices Stack**

*Built with ❤️ for enterprise-grade deployments* 