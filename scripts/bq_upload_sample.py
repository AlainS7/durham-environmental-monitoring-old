"""Small harness to test uploading a sample DataFrame to BigQuery locally.

Usage:
  # Dry-run (no network): builds a sample DataFrame and validates the upload path
  python scripts/bq_upload_sample.py --dry-run

  # Real run (requires Google Application Default Credentials and REAL_BQ=1)
  REAL_BQ=1 python scripts/bq_upload_sample.py --dataset your_dataset --table test_upload

The script is conservative: it will not DROP or DELETE any tables; it will create the table if missing and insert rows.
"""
import os
import argparse
import pandas as pd
import logging
from google.cloud import bigquery

log = logging.getLogger("bq_upload_sample")

SAMPLE = [
    {"timestamp": "2025-08-20T12:00:00Z", "deployment_fk": 1, "metric_name": "temperature", "value": 23.5},
    {"timestamp": "2025-08-20T13:00:00Z", "deployment_fk": 1, "metric_name": "humidity", "value": 55.0},
]

def build_sample_df():
    return pd.DataFrame(SAMPLE)

def upload_to_bigquery(df: pd.DataFrame, dataset: str, table: str, dry_run: bool = True):
    if df.empty:
        raise ValueError("No data to upload")
    if dry_run:
        log.info("Dry run: would upload %d rows to %s.%s", len(df), dataset, table)
        print(df.head())
        return True
    client = bigquery.Client()
    dataset_ref = client.dataset(dataset)
    table_ref = dataset_ref.table(table)
    try:
        client.get_dataset(dataset_ref)
        log.info("Dataset %s exists.", dataset)
    except Exception:
        log.info("Dataset %s not found; creating.", dataset)
        ds = bigquery.Dataset(dataset_ref)
        ds = client.create_dataset(ds, exists_ok=True)
    job = client.load_table_from_dataframe(df, table_ref)
    job.result()
    log.info("Uploaded %d rows to %s.%s", len(df), dataset, table)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, default="durham_weather_test", help="BigQuery dataset")
    parser.add_argument("--table", type=str, default="test_upload", help="BigQuery table name")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Do not perform network upload")
    args = parser.parse_args()
    dry = args.dry_run or os.environ.get("REAL_BQ", "0") != "1"
    df = build_sample_df()
    upload_to_bigquery(df, args.dataset, args.table, dry_run=dry)
