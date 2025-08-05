# Terraform outputs configuration
# Prints important values after Terraform runs. We will use these outputs to configure 
# our application in Kubernetes.

output "gke_cluster_name" {
  value = google_container_cluster.primary.name
}

output "gke_cluster_endpoint" {
  value = google_container_cluster.primary.endpoint
}

output "cloud_sql_connection_name" {
  description = "The connection name of the Cloud SQL instance, used by the proxy."
  value       = google_sql_database_instance.postgres.connection_name
}

output "db_password_secret_name" {
  description = "The name of the secret in Secret Manager holding the DB password."
  value       = google_secret_manager_secret.db_password_secret.secret_id
}

output "redis_host_ip" {
  description = "The private IP address of the Redis instance."
  value       = google_redis_instance.cache.host
}

output "gcs_bucket_name" {
  value = google_storage_bucket.main_bucket.name
}

output "pubsub_topic_name" {
  value = google_pubsub_topic.main_topic.name
}

output "app_gcp_service_account_email" {
  description = "The email of the GCP service account the application will use."
  value       = google_service_account.vendor_sa.email
}

output "elasticsearch_endpoint" {
  description = "The HTTPS endpoint for the Elasticsearch cluster."
  value       = ec_deployment.vpc_es.elasticsearch.https_endpoint
}

output "elasticsearch_password" {
  description = "The password for the 'elastic' superuser."
  value       = ec_deployment.vpc_es.elasticsearch_password
  sensitive   = true
} 