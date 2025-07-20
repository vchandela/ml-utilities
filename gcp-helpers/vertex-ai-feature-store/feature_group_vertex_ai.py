from google.cloud import aiplatform
from vertexai.resources.preview import feature_store
from typing import List


def create_feature_group_sample(
    project: str,
    location: str,
    feature_group_id: str,
    bq_table_uri: str,
    entity_id_columns: List[str],
):
    aiplatform.init(project=project, location=location)
    fg = feature_store.FeatureGroup.create(
        name=feature_group_id,
        source=feature_store.utils.FeatureGroupBigQuerySource(
            uri=bq_table_uri, entity_id_columns=entity_id_columns
        ),
    )
    return fg

project = "ml-tool-playground"
location = "us-central1"
feature_group_id = "pipeline_output_fg"
bq_table_uri = "bq://ml-tool-playground.user_data_temp.pipeline_output"
entity_id_columns = ["user_id"]

create_feature_group_sample(project, location, feature_group_id, bq_table_uri, entity_id_columns)