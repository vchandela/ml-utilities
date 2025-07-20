
from google.cloud import aiplatform
from vertexai.resources.preview import feature_store

def create_optimized_public_feature_online_store_sample(
    project: str,
    location: str,
    feature_online_store_id: str,
):
    aiplatform.init(project=project, location=location)
    fos = feature_store.FeatureOnlineStore.create_optimized_store(
        feature_online_store_id
    )
    return fos

project = "ml-tool-playground"
location = "us-central1"
feature_online_store_id = "pipeline_output_fos"

create_optimized_public_feature_online_store_sample(project, location, feature_online_store_id)