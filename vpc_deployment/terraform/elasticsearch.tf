# Elasticsearch deployment using Elastic Cloud
# Provisions a managed Elasticsearch deployment using the Elastic Cloud service from the GCP Marketplace.
# Pre-requisite: You must have an Elastic Cloud account and have generated an API key.

# This resource creates a new Elasticsearch deployment.
# It is managed by Elastic and orchestrated via our vendor API key, but the underlying
# infrastructure (VMs, disks) is provisioned within the customer's GCP project,
# ensuring data residency and direct billing to the customer.

resource "ec_deployment" "pavo_vpc_es" {
  name                   = "pavo-vpc-es-deployment"
  region                 = "gcp-${var.gcp_region}" # e.g., "gcp-us-central1"
  version                = "8.11.0"               # Specify a recent, stable version
  deployment_template_id = "gcp-io-optimized-v2"  # A good general-purpose template

  # --- CRITICAL ADDITION ---
  # This 'gcp' block explicitly links the Elastic deployment to the customer's GCP project.
  # This tells Elastic to provision the infrastructure in this project and, more
  # importantly, to bill the usage to this project's linked billing account via the
  # GCP Marketplace agreement.
  gcp {
    project_id = var.gcp_project_id
  }
  # --- END OF CRITICAL ADDITION ---

  elasticsearch {
    hot {
      size          = "1g" # Smallest size for demo purposes
      size_resource = "memory"
    }
  }

  kibana {} # Also provision a Kibana instance for visualization.
} 