# Cloud SQL PostgreSQL database configuration
# Creates the managed PostgreSQL database, a random password, and stores that password 
# securely in Secret Manager.

# Create a strong, random password for the database.
resource "random_password" "db_password" {
  length  = 24
  special = true
}

# Store the generated password in Google Secret Manager. Our app will read it from here.
resource "google_secret_manager_secret" "db_password_secret" {
  secret_id = "pavo-vpc-db-password"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "db_password_secret_version" {
  secret      = google_secret_manager_secret.db_password_secret.id
  secret_data = random_password.db_password.result
}

# Create the Cloud SQL for PostgreSQL instance.
resource "google_sql_database_instance" "postgres" {
  name             = "pavo-vpc-postgres-instance"
  database_version = "POSTGRES_14"
  region           = var.gcp_region

  settings {
    tier = "db-custom-1-3840" # A small instance tier for this demo.

    # This section configures the database to be accessible only via a private IP
    # from within our VPC. This is highly secure.
    ip_configuration {
      ipv4_enabled    = false # No public IP address.
      private_network = google_compute_network.main_vpc.id
    }

    # Backup and high availability settings for production.
    backup_configuration {
      enabled = true
    }
  }

  root_password = random_password.db_password.result

  # Ensures the private networking "tunnel" is ready before creating the instance.
  depends_on = [google_service_networking_connection.default]
} 