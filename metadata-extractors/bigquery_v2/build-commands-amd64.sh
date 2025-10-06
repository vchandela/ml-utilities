#!/bin/bash
# Build & Push Commands for BigQuery v2 Container
# Updated for Option B (build context from bigquery_v2/ directory)

export PROJECT_ID=onboarding-455713
export REGION=us-central1
export REPO=donboard-v1         # existing AR repo name
export IMAGE=bigquery-v2        # image name
export TAG=latest

echo "Building with TAG: ${TAG}"
echo "Full image name: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:${TAG}"

# Build from repo root for AMD64 platform (to access both bigquery and bigquery_v2 modules)
cd .. && docker buildx build --platform linux/amd64 -f bigquery_v2/Dockerfile -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:${TAG} . --push

# Note: Image is built and pushed automatically with --push flag in buildx command above

echo "Build and push complete!"
echo "TAG to use in Kubernetes: ${TAG}"
echo "Keep this TAG value for the Job manifest."
