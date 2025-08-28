#!/usr/bin/env python3
import argparse
import logging
import os
from dataclasses import dataclass
from typing import Sequence

from google.cloud import bigquery
from google.cloud.exceptions import NotFound


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bq_loader")


def ensure_dataset(client: bigquery.Client, dataset_id: str, location: str | None = None) -> bigquery.Dataset:
    ds_ref = client.dataset(dataset_id)
    try:
        return client.get_dataset(ds_ref)
    except NotFound:
        log.info(f"Creating dataset {client.project}.{dataset_id} (location={location})...")
        ds = bigquery.Dataset(ds_ref)
        if location:
            ds.location = location
        return client.create_dataset(ds)


@dataclass(slots=True)
class PartitionSpec:
    bucket: str
    prefix: str
    source: str
    aggregation: str
    date: str  # YYYY-MM-DD

    def uri_glob(self) -> str:
        return f"gs://{self.bucket}/{self.prefix}/source={self.source}/agg={self.aggregation}/dt={self.date}/*.parquet"


@dataclass(slots=True)
class LoadSpec:
    dataset_id: str
    table_id: str
    uris: Sequence[str]
    partition_field: str = "timestamp"
    clustering_fields: Sequence[str] | None = None
    write_disposition: str = "WRITE_APPEND"
    create_disposition: str = "CREATE_IF_NEEDED"


def load_parquet(client: bigquery.Client, spec: LoadSpec):
    fq_table = f"{client.project}.{spec.dataset_id}.{spec.table_id}"
    log.info(f"Loading into {fq_table} from {len(spec.uris)} URI(s)...")
    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.PARQUET
    job_config.write_disposition = getattr(bigquery.WriteDisposition, spec.write_disposition)
    job_config.create_disposition = getattr(bigquery.CreateDisposition, spec.create_disposition)
    job_config.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field=spec.partition_field)
    if spec.clustering_fields:
        job_config.clustering_fields = list(spec.clustering_fields)

    load_job = client.load_table_from_uri(list(spec.uris), fq_table, job_config=job_config)
    result = load_job.result()
    dest = client.get_table(fq_table)
    rows_loaded = getattr(load_job, "output_rows", None) or getattr(result, "output_rows", None)
    if rows_loaded is None:
        rows_str = "unknown"
    else:
        rows_str = str(rows_loaded)
    log.info(f"Loaded {rows_str} rows into {fq_table}. Current table rows: {dest.num_rows}")


# Backward-compatible shim for tests importing build_gcs_uri
def build_gcs_uri(bucket: str, prefix: str, source: str, agg: str, date: str) -> str:  # pragma: no cover - simple wrapper
    return PartitionSpec(bucket=bucket, prefix=prefix, source=source, aggregation=agg, date=date).uri_glob()


def main():
    parser = argparse.ArgumentParser(description="Load GCS Parquet data into BigQuery with partitioning and clustering.")
    parser.add_argument("--dataset", required=False, default=os.getenv("BQ_DATASET"), help="BigQuery dataset ID")
    parser.add_argument("--project", required=False, default=os.getenv("BQ_PROJECT"), help="GCP project ID (defaults to ADC)")
    parser.add_argument("--location", required=False, default=os.getenv("BQ_LOCATION", "US"), help="BigQuery location")

    parser.add_argument("--bucket", required=False, default=os.getenv("GCS_BUCKET"), help="GCS bucket name")
    parser.add_argument("--prefix", required=False, default=os.getenv("GCS_PREFIX", "sensor_readings"), help="GCS prefix root")

    parser.add_argument("--date", required=True, help="Date partition to load (YYYY-MM-DD)")
    parser.add_argument("--source", choices=["WU", "TSI", "all"], default="all", help="Select source to load")
    parser.add_argument("--agg", default="raw", help="Aggregation label to match (e.g., raw, h, 15min)")

    parser.add_argument("--table-prefix", default="sensor_readings", help="Base table name prefix in BigQuery")
    parser.add_argument("--partition-field", default="timestamp", help="Partitioning field (default: timestamp)")
    parser.add_argument("--cluster-by", default="native_sensor_id", help="Comma-separated clustering fields")

    parser.add_argument("--write", choices=["WRITE_APPEND", "WRITE_TRUNCATE", "WRITE_EMPTY"], default="WRITE_APPEND")
    parser.add_argument("--create", choices=["CREATE_IF_NEEDED", "CREATE_NEVER"], default="CREATE_IF_NEEDED")

    args = parser.parse_args()

    if not args.dataset:
        raise SystemExit("--dataset or BQ_DATASET env var is required")
    if not args.bucket:
        raise SystemExit("--bucket or GCS_BUCKET env var is required")

    project = args.project or None
    client = bigquery.Client(project=project, location=args.location)
    ensure_dataset(client, args.dataset, args.location)

    sources = ["WU", "TSI"] if args.source == "all" else [args.source]
    cluster_fields = [f.strip() for f in args.cluster_by.split(",") if f.strip()]

    for src in sources:
        part = PartitionSpec(bucket=args.bucket, prefix=args.prefix, source=src, aggregation=args.agg, date=args.date)
        table = f"{args.table_prefix}_{src.lower()}_{args.agg}"
        load_parquet(
            client,
            LoadSpec(
                dataset_id=args.dataset,
                table_id=table,
                uris=[part.uri_glob()],
                partition_field=args.partition_field,
                clustering_fields=cluster_fields,
                write_disposition=args.write,
                create_disposition=args.create,
            )
        )


if __name__ == "__main__":
    main()
