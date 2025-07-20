### gcp-helpers

- curl request for using feature_view_request.json to create a feature view
- Note: Use default (same service account) as user otherwise sync operations will fail.
```
curl -X POST \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     -H "Content-Type: application/json; charset=utf-8" \
     -d @feature_view_request.json \
     "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-tool-playground/locations/us-central1/featureOnlineStores/pipeline_output_btfos/featureViews?feature_view_id=pipeline_output_feature_view"
```

- curl request to manually sync a feature view
```
curl -X POST \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     -H "Content-Type: application/json; charset=utf-8" \
     -d "" \
     "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-tool-playground/locations/us-central1/featureOnlineStores/pipeline_output_btfos/featureViews/pipeline_output_feature_view:sync"
```

- check issues with a sync operation
```
SYNC_ID=3068345724551823360          # ← the value you saw in the UI
PROJECT=ml-tool-playground
REGION=us-central1
ONLINE_STORE=pipeline_output_online_store
FEATURE_VIEW=pipeline_output_feature_view

curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/featureOnlineStores/${ONLINE_STORE}/featureViews/${FEATURE_VIEW}/featureViewSyncs/${SYNC_ID}"
```

- get the PUBLIC_ENDPOINT_DOMAIN_NAME for optimised online store
```
curl -X GET \
     -H "Authorization: Bearer $(gcloud auth print-access-token)" \
     "https://us-central1-aiplatform.googleapis.com/v1/projects/ml-tool-playground/locations/us-central1/featureOnlineStores/pipeline_output_online_store"
```