# This file defines the Artifact Registry repository where our application's
# Docker images will be stored. Creating this explicitly is a best practice.

resource "google_artifact_registry_repository" "main_repo" {
  # The name of the repository itself. Think of this like a folder.
  repository_id = "pavo-vpc"
  
  # The project where this repository will be created.
  project = var.gcp_project_id
  
  # The GCP region for the repository. It's best to keep this the same
  # as your GKE cluster region to minimize latency and data transfer costs.
  location = var.gcp_region
  
  # The format of the packages that will be stored.
  # We are storing Docker images. Other options include MAVEN, NPM, etc.
  format = "DOCKER"
  
  # A description for clarity in the GCP console.
  description = "Docker image repository for the pavo-vpc managed service."

  # Simple cleanup policy to allow destruction
  cleanup_policy_dry_run = false
} 