#!/bin/bash
# Create Kubernetes Secret for BigQuery Service Account Credentials
# 
# This script creates a secret where the VALUE of key 'BIGQUERY_SA_CREDS_JSON' 
# is the entire JSON file content from your service account file.

echo "Creating Kubernetes secret for BigQuery credentials..."
echo ""
echo "IMPORTANT: This script expects your service account JSON file to be at: ./sa.json"
echo "If your file is elsewhere, update the path in the kubectl command below."
echo ""

# Check if sa.json exists
if [ ! -f "./sa.json" ]; then
    echo "❌ ERROR: Service account file './sa.json' not found!"
    echo ""
    echo "Please ensure you have your BigQuery service account JSON file saved as 'sa.json' in the current directory."
    echo "You can download it from: https://console.cloud.google.com/iam-admin/serviceaccounts"
    echo ""
    exit 1
fi

echo "✅ Found service account file: ./sa.json"
echo ""

# Create the secret
echo "Creating secret 'bqv2-creds' in namespace 'default'..."
kubectl -n default create secret generic bqv2-creds \
  --from-file=BIGQUERY_SA_CREDS_JSON=./sa.json

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Secret created successfully!"
    echo ""
    echo "To verify the secret was created:"
    echo "  kubectl -n default get secret bqv2-creds"
    echo ""
    echo "To view secret details (without showing the actual credentials):"
    echo "  kubectl -n default describe secret bqv2-creds"
else
    echo ""
    echo "❌ Failed to create secret. Please check your kubectl configuration and try again."
    echo ""
    echo "Common issues:"
    echo "  - Not connected to the correct GKE cluster"
    echo "  - Insufficient permissions"
    echo "  - Secret already exists (delete it first with: kubectl -n default delete secret bqv2-creds)"
fi
