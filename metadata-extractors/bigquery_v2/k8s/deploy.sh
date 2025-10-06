#!/bin/bash
# Deploy BigQuery v2 Job to Kubernetes
# 
# This script deploys the BigQuery analysis job using the latest built image.
# It reads the TAG from the most recent build and applies the job manifest.

echo "BigQuery v2 Kubernetes Deployment Script"
echo "========================================"
echo ""

# Check if job.yaml exists
if [ ! -f "job.yaml" ]; then
    echo "❌ ERROR: job.yaml not found in current directory!"
    echo "Please run this script from the k8s/ directory."
    exit 1
fi

# Get the TAG from user input or use latest
if [ -z "$1" ]; then
    echo "Usage: $0 <TAG>"
    echo ""
    echo "Example: $0 20251006-180835"
    echo ""
    echo "💡 TIP: The TAG is displayed at the end of './build-commands.sh'"
    echo "You can also check recent tags with: docker images | grep bigquery-v2"
    exit 1
fi

TAG=$1
echo "🏗️  Using TAG: ${TAG}"
echo "📦 Full image: us-central1-docker.pkg.dev/onboarding-455713/donboard-v1/bigquery-v2:${TAG}"
echo ""

# Check if kubectl is working
echo "🔍 Checking kubectl connection..."
kubectl cluster-info --request-timeout=5s > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ ERROR: kubectl is not connected to a cluster!"
    echo ""
    echo "Please connect to your GKE cluster first:"
    echo "  gcloud container clusters get-credentials donboard_v1 --region us-central1 --project onboarding-455713"
    echo "  kubectl config set-context --current --namespace=default"
    exit 1
fi

echo "✅ kubectl connected"
echo ""

# Create the job with TAG replacement (use create, not apply, for generateName)
echo "🚀 Deploying Job..."
sed -e "s/REPLACE_WITH_TAG/${TAG}/" job.yaml | kubectl create -f -

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Job deployed successfully!"
    echo ""
    echo "📊 Monitor the job:"
    echo "  kubectl get jobs -n default | grep bqv2-run"
    echo "  kubectl get pods -n default -l job-name=\$(kubectl get job -n default -o name | tail -n1 | cut -d'/' -f2)"
    echo ""
    echo "📋 View logs:"
    echo "  kubectl logs -f \$(kubectl get pods -n default -o name | grep bqv2-run | tail -n1)"
    echo ""
    echo "💾 Retrieve outputs (after job completes):"
    echo "  POD=\$(kubectl get pods -n default -o name | grep bqv2-run | tail -n1 | cut -d'/' -f2)"
    echo "  kubectl cp -n default \${POD}:/app/bq_golden_queries_output.json ./bq_golden_queries_output.json"
    echo "  kubectl cp -n default \${POD}:/app/bq_golden_queries_output.csv ./bq_golden_queries_output.csv"
else
    echo ""
    echo "❌ Failed to deploy job. Check the error messages above."
fi
