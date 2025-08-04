# Network infrastructure configuration
# Creates our private network (VPC) and configures the "private tunnel" (Private Service Access) 
# needed for Cloud SQL and Redis.

# Create the main VPC network for all our resources.
resource "google_compute_network" "main_vpc" {
  name                    = "pavo-vpc"
  auto_create_subnetworks = false # We want to create subnets manually for more control.
}

# Create a subnet within the VPC. Our GKE cluster will live here.
resource "google_compute_subnetwork" "main_subnet" {
  name          = "pavo-vpc-subnet"
  ip_cidr_range = "10.10.0.0/24" # A private IP range for our services.
  region        = var.gcp_region
  network       = google_compute_network.main_vpc.id
}

# Reserve a global IP address range required for Private Service Access.
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "private-ip-alloc-for-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main_vpc.id
}

# This is the "private tunnel". It connects our VPC to Google's managed services network.
resource "google_service_networking_connection" "default" {
  network                 = google_compute_network.main_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
} 