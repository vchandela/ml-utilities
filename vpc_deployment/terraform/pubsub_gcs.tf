# Google Cloud Pub/Sub and Cloud Storage configuration
# Creates the Pub/Sub topic for messaging and the GCS bucket for file storage.

# Create a GCS bucket. Names must be globally unique.
resource "google_storage_bucket" "main_bucket" {
  name                        = "${var.gcp_project_id}-pavo-vpc-storage-bucket"
  location                    = var.gcp_region
  force_destroy               = true # Allows deletion of the bucket even if it's not empty. Use with care.
  uniform_bucket_level_access = true # Required by organizational policy
}

# Create a Pub/Sub topic.
resource "google_pubsub_topic" "main_topic" {
  name = "pavo-vpc-tasks-topic"
} 