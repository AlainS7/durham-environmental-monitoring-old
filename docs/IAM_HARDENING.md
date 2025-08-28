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

Create dedicated service accounts:

```bash
gcloud iam service-accounts create verifier-sa --display-name="Daily Verifier"
gcloud iam service-accounts create ingestion-sa --display-name="Ingestion Pipeline"
```

## Roles & Permissions

Principle of granting the narrowest predefined roles first; only use custom roles if required.

### Verifier SA
Needs to list tables, read schemas, count rows, and perform a GCS round trip (write + read one object).

Grant:
* roles/storage.objectAdmin (scoped to the specific bucket) – if you want write/read test object. For pure read, split into objectViewer + a dedicated prefix writer via bucket IAM conditions.
* roles/bigquery.dataViewer (dataset level)
* roles/bigquery.metadataViewer (project or dataset)
* roles/bigquery.jobUser (project) – to run queries

Optional hardening: replace objectAdmin with objectCreator + objectViewer and a lifecycle rule to expire test objects.

### Ingestion SA
Needs to write Parquet objects and load into staging tables.

Grant:
* roles/storage.objectCreator (bucket)
* roles/storage.objectViewer (bucket) – (optional, if it needs to list)
* roles/bigquery.dataEditor (dataset) – to insert & create staging tables
* roles/bigquery.jobUser (project)

Hardening improvement: move from dataEditor to a custom role that only allows bigquery.tables.create + bigquery.tables.get + bigquery.tables.updateData.

### Normalization / Backfill (Human)
Grant temporarily via gcloud CLI:
* roles/bigquery.dataEditor (dataset)
* roles/storage.objectViewer (bucket)
Revoke after completion (use IAM Conditions with expiration when possible).

### Analytics / BI Users
* roles/bigquery.dataViewer (dataset list)
* roles/bigquery.jobUser (if they need ad-hoc queries outside Looker/BI tool – otherwise skip)

## Dataset Policy Example

```bash
gcloud bigquery datasets add-iam-policy-binding sensors \
  --member=serviceAccount:verifier-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/bigquery.dataViewer
```

Repeat for ingestion-sa with dataEditor or custom role.

## Workload Identity Federation (GitHub → GCP)

1. Create provider:

```bash
gcloud iam workload-identity-pools create github-pool --location=global --display-name="GitHub Pool"
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --display-name="GitHub OIDC" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --allowed-audiences="https://github.com/AlainS7/durham-environmental-monitoring" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"
```

1. Bind attribute condition to verifier SA:

```bash
gcloud iam service-accounts add-iam-policy-binding verifier-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/AlainS7/durham-environmental-monitoring"
```

1. Store provider and SA email as GitHub secrets: GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_VERIFIER_SA.

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

 