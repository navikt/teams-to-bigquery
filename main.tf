terraform {
  backend "gcs" {
    bucket = "nais-analyse-prod-gcp-teams-to-bigquery-tfstate"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.4.0"
    }
  }
}

provider "google" {
  project = "nais-analyse-prod-2dcc"
  region  = "europe-west1"
}

data "archive_file" "function_archive" {
  type        = "zip"
  source_dir  = "./cloud-function-src"
  output_path = "source.zip"
}

resource "google_storage_bucket" "bucket" {
  name     = "nais-analyse-prod-cf-team-to-bigquery-source"
  location = "EU"
}

resource "google_storage_bucket_object" "archive" {
  name                = format("%s-%s", data.archive_file.function_archive.output_md5, data.archive_file.function_archive.output_path)
  bucket              = google_storage_bucket.bucket.name
  source              = data.archive_file.function_archive.output_path
  content_disposition = "attachment"
  content_encoding    = "gzip"
  content_type        = "application/zip"
}

resource "google_project_service" "service" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "bigquery.googleapis.com",
    "cloudfunctions.googleapis.com",
    "compute.googleapis.com"
  ])
  service                    = each.key
  disable_dependent_services = false
}

resource "google_cloudfunctions_function" "function" {
  name        = "teams-to-bigquery"
  description = "My function"
  runtime     = "python312"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.bucket.name
  source_archive_object = google_storage_bucket_object.archive.name
  trigger_http          = true
  timeout               = 60
  entry_point           = "main"
  labels = {
    team = "nais"
  }
  service_account_email = data.google_service_account.projects-to-bigquery.email
}

# IAM entry for a single user to invoke the function
resource "google_service_account" "scheduler-teams-to-bigquery" {
  account_id = "scheduler-teams-to-bq"
}

resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = google_cloudfunctions_function.function.project
  region         = google_cloudfunctions_function.function.region
  cloud_function = google_cloudfunctions_function.function.name

  role   = "roles/cloudfunctions.invoker"
  member = "serviceAccount:${google_service_account.scheduler-teams-to-bigquery.email}"
}

data "google_service_account" "projects-to-bigquery" {
  account_id = "projects-to-bigquery"
}

resource "google_cloud_scheduler_job" "job" {
  name             = "teams-to-bigquery"
  description      = "Reads teams from project folders and writes to BQ"
  schedule         = "0 4 * * *"
  time_zone        = "Europe/Oslo"
  attempt_deadline = "60s"
  region           = "europe-west3"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.function.https_trigger_url

    oidc_token {
      service_account_email = google_service_account.scheduler-teams-to-bigquery.email
    }
  }
}
