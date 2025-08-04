# This file grants the necessary IAM permissions for the GKE nodes and Workload Identity to function.

# --- Permission for GKE Nodes to Pull Images ---

# Get the email address of the default Compute Engine service account.
data "google_compute_default_service_account" "default" {
  project = var.gcp_project_id
}

# Grant the Artifact Registry Reader role to the node service account.
resource "google_project_iam_member" "node_sa_artifact_reader" {
  project = var.gcp_project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}


# --- Permission for Workload Identity to Function ---

# First, create the GCP Service Account that our application will impersonate.
# This gives us a concrete resource to grant permissions to.
resource "google_service_account" "vendor_sa" {
  account_id   = "vendor-deployment-sa"
  display_name = "GCP Service Account for Pavo App"
  project      = var.gcp_project_id
}

# This is the CRITICAL binding that fixes the error.
# It grants the Workload Identity User role to the GKE identity, allowing it
# to impersonate our application's GCP service account.
resource "google_service_account_iam_member" "workload_identity_user" {
  # The service account that will BE impersonated.
  service_account_id = google_service_account.vendor_sa.name 
  
  # The role that allows impersonation.
  role = "roles/iam.workloadIdentityUser"
  
  # The identity that is ALLOWED to do the impersonating.
  # This special string format represents our Kubernetes Service Account.
  # format: "serviceAccount:PROJECT_ID.svc.id.goog[K8S_NAMESPACE/K8S_SERVICE_ACCOUNT]"
  member = "serviceAccount:${var.gcp_project_id}.svc.id.goog[pavo-services/pavo-vpc-app-sa]"
}

# --- Permissions FOR the Application's Service Account ---
# Now, we grant the necessary roles TO the service account our app uses.

resource "google_project_iam_member" "app_sa_owner" {
  # For simplicity, we are still granting the Owner role to this SA.
  # In a production system, you would replace this one block with multiple,
  # more granular roles (cloudsql.client, storage.objectAdmin, etc.).
  project = var.gcp_project_id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.vendor_sa.email}"
}