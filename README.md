# Teams to BigQuery
Cloud Function that reads Resource Manager API to extract team names and write these to BigQuery.
Cloud Scheduler to trigger the Function every day. 

## Requirements
* service account `projects-to-bigquery` with org level permissions to read resource manager API