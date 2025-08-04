# Provider configuration for Terraform
# Configures the Google Cloud and Elastic Cloud providers
# Tells Terraform which project to work in, what region to use, and how to authenticate

provider "google" {
  project     = var.gcp_project_id
  region      = var.gcp_region
  credentials = file(var.gcp_credentials_path)
}

# provider "ec" {
#   # The Elastic Cloud API key should be stored securely, not in code.
#   # We will pass it as an environment variable when running Terraform.
#   # Command: export EC_API_KEY=$(cat /path/to/elastic-api-key.txt)
#   apikey = var.elastic_api_key
# } 