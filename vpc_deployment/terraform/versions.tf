# Terraform version and provider requirements
# Declares the required providers (Google and Elastic) and their versions
# This ensures a consistent environment across different deployments

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    ec = {
      source  = "elastic/ec"
      version = "~> 0.12"
    }
  }
} 