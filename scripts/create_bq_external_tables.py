#!/usr/bin/env python
"""Utility to (re)create external BigQuery tables over raw Parquet GCS partitions.

Assumptions:
  - GCS layout: gs://<bucket>/<prefix>/source=<SRC>/agg=<interval>/dt=<YYYY-MM-DD>/<SRC>-<YYYY-MM-DD>.parquet
  - Variables supplied via environment or arguments.

Creates two external tables (if data present):
  sensors.wu_raw_external
  sensors.tsi_raw_external

Idempotent: it issues CREATE OR REPLACE EXTERNAL TABLE.

Usage examples:
  python scripts/create_bq_external_tables.py \
      --bucket sensor-data-to-bigquery \
      --prefix raw \
      --dataset sensors \
      --project durham-weather-466502

You can set env vars instead of flags: GCS_BUCKET, GCS_PREFIX, BQ_DATASET, BQ_PROJECT.
"""
from __future__ import annotations
import argparse
import os
from google.cloud import bigquery, storage
from google.api_core.exceptions import Forbidden

SOURCES = ["WU", "TSI"]

DDL_TEMPLATE = """CREATE OR REPLACE EXTERNAL TABLE `{project}.{dataset}.{table}`\nOPTIONS (\n  format = 'PARQUET',\n  uris = [\n{uris}\n  ]\n)"""

def _wildcard_uri(bucket: str, prefix: str, source: str) -> str:
  """Return a broad wildcard URI covering all partitions for a source.

  This avoids the need to list objects when permissions are limited. BigQuery
  will resolve the wildcard at query time. Creation of the external table does
  not read data and thus will succeed even if no objects currently match.
  """
  # Use a single wildcard to include all objects under agg=raw for the given source.
  # BigQuery supports a single '*' in the object name; using one broad wildcard here
  # avoids multiple-wildcard limitations while covering all date partitions/files.
  return f"gs://{bucket}/{prefix}/source={source}/agg=raw/*"


def discover_uris(bucket: str, prefix: str, source: str):
  """Enumerate individual parquet object URIs (avoid multi-* wildcard restriction).

  Lists dt=YYYY-MM-DD/ directories and returns explicit file URIs.
  Limits to a reasonable number (e.g., 500) to keep DDL manageable.
  """
  client = storage.Client()
  try:
    blobs = client.list_blobs(bucket, prefix=f"{prefix}/source={source}/agg=raw/dt=")
    uris: list[str] = []
    for b in blobs:
      name = b.name
      if name.endswith('.parquet'):
        uris.append(f"gs://{bucket}/{name}")
        if len(uris) >= 500:
          break
    if not uris:
      # Fall back to wildcard when nothing is discovered (table will be empty until data arrives)
      return [_wildcard_uri(bucket, prefix, source)]
    return uris
  except Forbidden:
    # No permission to list objects in the bucket: fall back to a wildcard URI so that
    # external table creation remains possible in restricted CI environments.
    print(f"[external] No permission to list gs://{bucket}/{prefix} (storage.objects.list). Using wildcard URI for {source}.")
    return [_wildcard_uri(bucket, prefix, source)]

def create_external_tables(project: str, dataset: str, bucket: str, prefix: str):
  client = bigquery.Client(project=project or None)
  for src in SOURCES:
    table = f"{src.lower()}_raw_external"
    uris = discover_uris(bucket, prefix, src)
    formatted_uris = ",\n".join([f"    '{u}'" for u in uris])
    ddl = DDL_TEMPLATE.format(project=client.project, dataset=dataset, table=table, uris=formatted_uris)
    job = client.query(ddl)
    job.result()
    print(f"[external] Created table {client.project}.{dataset}.{table} -> {uris[0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default=os.getenv('BQ_PROJECT') or os.getenv('PROJECT_ID'))
    ap.add_argument('--dataset', default=os.getenv('BQ_DATASET', 'sensors'))
    ap.add_argument('--bucket', default=os.getenv('GCS_BUCKET'))
    ap.add_argument('--prefix', default=os.getenv('GCS_PREFIX', 'raw'))
    args = ap.parse_args()

    if not args.bucket:
        raise SystemExit("Bucket must be provided via --bucket or GCS_BUCKET env var")

    create_external_tables(args.project, args.dataset, args.bucket, args.prefix)

if __name__ == '__main__':
    main()
