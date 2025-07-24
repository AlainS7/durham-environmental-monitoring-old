#!/bin/bash
# Fetch the instance connection name from Secret Manager
echo "Fetching Cloud SQL instance connection name from Secret Manager..."
INSTANCE_CONNECTION_NAME=$(gcloud secrets versions access latest --secret="YOUR_SECRET_NAME")

# Start the Cloud SQL Auth Proxy
exec /usr/local/bin/cloud-sql-proxy --address 0.0.0.0 "$INSTANCE_CONNECTION_NAME"