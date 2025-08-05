# Elasticsearch deployment using Elastic Cloud
# Provisions a managed Elasticsearch deployment using the Elastic Cloud service from the GCP Marketplace.
# Pre-requisite: You must have an Elastic Cloud account and have generated an API key.

# This resource creates a new Elasticsearch deployment.
# It is managed by Elastic and orchestrated via our vendor API key, but the underlying
# infrastructure (VMs, disks) is provisioned within the customer's GCP project,
# ensuring data residency and direct billing to the customer.

resource "ec_deployment" "vpc_es" {
  name                   = "vpc-es-deployment"
  region                 = "gcp-${var.gcp_region}" # e.g., "gcp-us-central1"
  version                = "8.11.0"               # Specify a recent, stable version
  deployment_template_id = "gcp-general-purpose"  # Use current general-purpose template

  # Elasticsearch topology (hot tier only, 1 GB for demo)
  elasticsearch = {
    hot = {
      size          = "1g"
      size_resource = "memory"
      autoscaling   = {}
    }
  }

  # Minimal Kibana instance
  kibana = {
    topology = {}
  }
} 