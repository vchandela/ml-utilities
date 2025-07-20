from google.cloud import aiplatform
from vertexai.resources.preview.feature_store import FeatureOnlineStore, FeatureView

project = "ml-tool-playground"
location = "us-central1"
online_store_name = "pipeline_output_btfos"
feature_view_name = "pipeline_output_feature_view"

aiplatform.init(project=project, location=location)
fos = FeatureOnlineStore(online_store_name)
fv = FeatureView(feature_view_name, feature_online_store_id=fos.name)
data = fv.read(["user123"])
print(data)