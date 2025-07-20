
from google.cloud import aiplatform
from vertexai.resources.preview import feature_store


def create_feature_sample(
    project: str,
    location: str,
    existing_feature_group_id: str,
    feature_id: str,
):
    aiplatform.init(project=project, location=location)
    feature_group = feature_store.FeatureGroup(existing_feature_group_id)
    feature = feature_group.create_feature(
        name=feature_id
    )
    return feature

project = "ml-tool-playground"
location = "us-central1"
existing_feature_group_id = "pipeline_output_fg"
feature_id = "distinct_event_types"

create_feature_sample(project, location, existing_feature_group_id, feature_id)