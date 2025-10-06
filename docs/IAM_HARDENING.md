# IAM Hardening Guide

This guide outlines least-privilege IAM for the Durham Environmental Monitoring pipeline on GCP.

## Principals & Identities

| Principal | Purpose | Recommended Form |
|-----------|---------|------------------|
| GitHub Actions Verifier | Runs daily verification script | Workload Identity Federation + dedicated service account |
| Ingestion Job (Data Loader) | Writes raw Parquet to GCS & loads to BigQuery staging | GKE / Cloud Run SA (workload identity) |
| Normalization / Backfill Tooling | One-off maintenance / ad-hoc | Human identity + short‑lived token |
| Analytics / BI Consumers | Read fact & snapshot tables | Group with read-only dataset access |

## Service Accounts

Three dedicated service accounts are used to ensure a separation of duties:

1.  **`weather-ingest@...`**: Used by the data collection pipeline to ingest data from APIs and upload it to Cloud Storage.
2.  **`weather-transform@...`**: Used by the transformation pipeline to run BigQuery jobs that transform raw data into analytics-ready tables.
3.  **`weather-verify@...`**: Used by the data quality and verification pipelines to run checks against the data in BigQuery.

## Roles & Permissions

Each service account is granted the minimum set of permissions required for its task:

### `weather-ingest@...`

*   `roles/storage.objectCreator`: To write Parquet files to the GCS bucket.
*   `roles/secretmanager.secretAccessor`: To access API keys stored in Secret Manager.
*   `roles/run.invoker`: To invoke the Cloud Run job for data collection.

### `weather-transform@...`

*   `roles/bigquery.dataEditor`: To create, update, and delete tables in the BigQuery dataset.
*   `roles/bigquery.jobUser`: To run BigQuery jobs.

### `weather-verify@...`

*   `roles/bigquery.dataViewer`: To read data from the BigQuery dataset.
*   `roles/bigquery.jobUser`: To run BigQuery jobs.

## Workload Identity Federation (GitHub → GCP)

Workload Identity Federation is used to allow GitHub Actions to securely authenticate to GCP without using service account keys. Each of the three service accounts is configured to be used by GitHub Actions workflows.

1.  **Create a Workload Identity Pool and Provider:**

    ```bash
    gcloud iam workload-identity-pools create github-pool --location=global --display-name="GitHub Pool"
    gcloud iam workload-identity-pools providers create-oidc github-provider \
      --workload-identity-pool=github-pool \
      --display-name="GitHub OIDC" \
      --issuer-uri="https://token.actions.githubusercontent.com" \
      --allowed-audiences="https://github.com/AlainS7/durham-environmental-monitoring" \
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"
    ```

2.  **Bind the Service Accounts to the Workload Identity Pool:**

    ```bash
    # Bind the ingest service account
    gcloud iam service-accounts add-iam-policy-binding weather-ingest@... \
      --role=roles/iam.workloadIdentityUser \
      --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/AlainS7/durham-environmental-monitoring"

    # Bind the transform service account
    gcloud iam service-accounts add-iam-policy-binding weather-transform@... \
      --role=roles/iam.workloadIdentityUser \
      --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/AlainS7/durham-environmental-monitoring"

    # Bind the verify service account
    gcloud iam service-accounts add-iam-policy-binding weather-verify@... \
      --role=roles/iam.workloadIdentityUser \
      --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/AlainS7/durham-environmental-monitoring"
    ```

3.  **Store the Workload Identity Provider and Service Account Emails as GitHub Secrets:**

    *   `GCP_WORKLOAD_IDENTITY_PROVIDER`
    *   `GCP_SERVICE_ACCOUNT_INGEST`
    *   `GCP_SERVICE_ACCOUNT_TRANSFORM`
    *   `GCP_SERVICE_ACCOUNT_VERIFY`

\n## Bucket Hardening
\n* Enforce uniform bucket-level access.
* Enable Object Versioning only if needed (cost tradeoff).
* Add lifecycle rule: delete objects under prefix sensor_readings/source=*/_verify/ after 1 day.
* Optional: Public access prevention (enforced).

\n## BigQuery Hardening
\n* Restrict dataset location.
* Require CMEK if compliance requires (configure default key on dataset).
 
* Enable table expiration for staging\_\* and tmp\_\* tables via defaultTableExpirationMs.

\n## Secrets Management
\n* Prefer Secret Manager + ADC for ingestion credentials.
 
* Rotate client secrets every 90 days; enforce via calendar reminder.

\n## Auditing & Monitoring
\n* Enable Data Access logs (ADMIN + READ for BigQuery) – review monthly.
 
* Configure log-based alert when permission denied events exceed threshold.
* Track service account key count (should be zero if only WIF used).

\n## Future Enhancements
 
\n* Add org policy constraints: disable SA key creation, restrict public IAM grants.
 
* Add automated policy diff in CI to detect drift.
* Integrate Cloud DLP scans for sensitive fields before external sharing.

 