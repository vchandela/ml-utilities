# Input variables for Terraform configuration
# Defines input variables for our Terraform code. This makes our code reusable 
# and easy to configure without changing the code itself.

variable "gcp_project_id" {
  description = "The GCP project ID to deploy resources into."
  type        = string
  default     = "ml-tool-playground" // Change if customer project ID is different
}

variable "gcp_region" {
  description = "The GCP region for all resources."
  type        = string
  default     = "us-central1"
}

variable "gcp_credentials_path" {
  description = "Path to the GCP service account JSON key file."
  type        = string
  default     = "../gcp-credentials.json" // Assumes key is in root
}

# variable "elastic_api_key" {
#   description = "API Key for Elastic Cloud."
#   type        = string
#   sensitive   = true # Prevents it from being shown in logs
# } 