# Google Cloud Memorystore for Redis configuration
# Creates the Memorystore for Redis instance for caching.

resource "google_redis_instance" "cache" {
  name           = "pavo-vpc-redis-cache"
  tier           = "BASIC" # BASIC tier is for a standalone instance.
  memory_size_gb = 1
  location_id    = "${var.gcp_region}-a"

  # Connects the Redis instance to our VPC so it gets a private IP.
  connect_mode              = "PRIVATE_SERVICE_ACCESS"
  authorized_network        = google_compute_network.main_vpc.id

  # Ensures the private networking "tunnel" is ready before creating the instance.
  depends_on = [google_service_networking_connection.default]
} 