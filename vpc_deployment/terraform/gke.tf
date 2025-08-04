# Google Kubernetes Engine (GKE) cluster configuration
# Provisions the GKE Autopilot cluster. Autopilot manages the underlying nodes for us, 
# making it simpler and more cost-effective for variable workloads.

resource "google_container_cluster" "primary" {
  name     = "pavo-vpc-autopilot-cluster"
  location = var.gcp_region
  network    = google_compute_network.main_vpc.id
  subnetwork = google_compute_subnetwork.main_subnet.id

  # This enables Autopilot mode. All clusters are VPC-native by default in Autopilot.
  enable_autopilot = true

  # Recommended for production: configure a maintenance window.
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
} 