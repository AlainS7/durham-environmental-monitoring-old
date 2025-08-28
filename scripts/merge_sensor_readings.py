#!/usr/bin/env python3
"""Upsert (MERGE) sensor readings from staging into canonical fact table.

Workflow expectation:
 1. Raw parquet files loaded into staging table via load_to_bigquery.py using --table-prefix staging_sensor_readings
 2. Run this script to MERGE rows for a given date partition into the target table (default sensor_readings)
 3. Optionally cleanup staging partition

Idempotent: running again for the same date only updates changed values or inserts missing rows.

Natural key used: (timestamp, deployment_fk, metric_name)

Example:
  python scripts/merge_sensor_readings.py \
    --project $BQ_PROJECT --dataset sensors --date 2025-08-20 \
    --staging-table staging_sensor_readings_raw \
    --target-table sensor_readings \
    --cleanup
"""
from __future__ import annotations
import argparse
import logging
import os
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger("merge_sensor_readings")


def parse_args():
    p = argparse.ArgumentParser(description="MERGE staging sensor readings into target fact table")
    p.add_argument('--project', default=os.getenv('BQ_PROJECT'))
    p.add_argument('--dataset', required=True, help='BigQuery dataset ID')
    p.add_argument('--date', required=True, help='Date (YYYY-MM-DD) partition to merge')
    p.add_argument('--location', default=os.getenv('BQ_LOCATION', 'US'))
    p.add_argument('--staging-table', default='staging_sensor_readings_raw', help='Staging table name (partitioned)')
    p.add_argument('--target-table', default='sensor_readings', help='Target fact table name (partitioned)')
    p.add_argument('--update-only-if-changed', action='store_true', help='Skip UPDATE when value unchanged')
    p.add_argument('--cleanup', action='store_true', help='Delete staging rows for the date after merge')
    return p.parse_args()


def ensure_tables_exist(client: bigquery.Client, dataset: str, staging: str, target: str):
    # Create target table if missing (schema copy from staging subset fields)
    try:
        client.get_table(f"{dataset}.{target}")
    except Exception:
        try:
            st = client.get_table(f"{dataset}.{staging}")
            schema = [f for f in st.schema if f.name in {'timestamp','deployment_fk','metric_name','value'}]
            tbl = bigquery.Table(f"{client.project}.{dataset}.{target}", schema=schema)
            tbl.time_partitioning = bigquery.TimePartitioning(field='timestamp')
            client.create_table(tbl)
            log.info(f"Created target table {dataset}.{target}")
        except Exception as e:  # pragma: no cover - defensive
            log.error(f"Failed to create target table: {e}")
            raise


def build_merge_sql(project: str, dataset: str, staging: str, target: str, date: str, update_if_changed: bool) -> str:
    predicate = "T.value != S.value" if update_if_changed else "TRUE"
    return f"""
MERGE `{project}.{dataset}.{target}` T
USING (
  SELECT timestamp, deployment_fk, metric_name, value
  FROM `{project}.{dataset}.{staging}`
  WHERE DATE(timestamp) = @d
) S
ON T.timestamp = S.timestamp
 AND T.deployment_fk = S.deployment_fk
 AND T.metric_name = S.metric_name
WHEN MATCHED AND {predicate} THEN UPDATE SET value = S.value
WHEN NOT MATCHED THEN INSERT (timestamp, deployment_fk, metric_name, value) VALUES (S.timestamp, S.deployment_fk, S.metric_name, S.value)
""".strip()


def merge_partition(client: bigquery.Client, args):
    ensure_tables_exist(client, args.dataset, args.staging_table, args.target_table)
    sql = build_merge_sql(client.project, args.dataset, args.staging_table, args.target_table, args.date, args.update_only_if_changed)
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('d', 'DATE', args.date)])
    log.info("Running MERGE...")
    job = client.query(sql, job_config=cfg)
    job.result()
    log.info("MERGE complete. Affected rows: %s", job.num_dml_affected_rows)


def cleanup_staging(client: bigquery.Client, args):
    if not args.cleanup:
        return
    sql = f"DELETE FROM `{client.project}.{args.dataset}.{args.staging_table}` WHERE DATE(timestamp)=@d"
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('d', 'DATE', args.date)])
    log.info("Cleaning up staging partition %s...", args.date)
    job = client.query(sql, job_config=cfg)
    job.result()
    log.info("Cleanup complete (deleted rows: %s)", job.num_dml_affected_rows)


def main():
    a = parse_args()
    client = bigquery.Client(project=a.project, location=a.location)
    merge_partition(client, a)
    cleanup_staging(client, a)

if __name__ == '__main__':  # pragma: no cover
    main()
