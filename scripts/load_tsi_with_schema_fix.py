#!/usr/bin/env python3
"""Load TSI parquet files with schema normalization to handle type inconsistencies."""

import argparse
import datetime as dt
from pathlib import Path

from google.cloud import bigquery
import pyarrow.parquet as pq
import pyarrow as pa


def daterange(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur = cur + dt.timedelta(days=1)


def normalize_schema(table: pa.Table) -> pa.Table:
    """Convert null-type columns and fix type mismatches to match target schema."""
    
    # Target schema with consistent types
    target_schema = {
        'cloud_account_id': pa.string(),
        'native_sensor_id': pa.string(),
        'timestamp': pa.timestamp('ns', tz='UTC'),
        'is_indoor': pa.bool_(),  # boolean, not int
        'is_public': pa.bool_(),  # boolean, not int
        'latitude': pa.float64(),
        'longitude': pa.float64(),
        'pm10': pa.float64(),
        'pm10_aqi': pa.float64(),
        'pm1_0': pa.float64(),
        'pm2_5': pa.float64(),
        'pm2_5_aqi': pa.float64(),
        'pm4_0': pa.float64(),  # May be missing in some files
        'ncpm4_0': pa.float64(),
        'model': pa.string(),
        'ncpm0_5': pa.float64(),
        'ncpm10': pa.float64(),
        'ncpm1_0': pa.float64(),
        'ncpm2_5': pa.float64(),
        'humidity': pa.float64(),
        'serial': pa.string(),
        'temperature': pa.float64(),
        'tpsize': pa.float64(),
        'co2_ppm': pa.float64(),
        'co_ppm': pa.float64(),
        'baro_inhg': pa.float64(),
        'o3_ppb': pa.float64(),
        'no2_ppb': pa.float64(),
        'so2_ppb': pa.float64(),
        'ch2o_ppb': pa.float64(),
        'voc_mgm3': pa.float64(),
        'ts': pa.timestamp('ns', tz='UTC'),
        'latitude_f': pa.float64(),
        'longitude_f': pa.float64(),
    }
    
    # Build new column arrays with proper types
    new_arrays = []
    new_names = []
    
    for field_name, target_type in target_schema.items():
        if field_name in table.column_names:
            col = table.column(field_name)
            # Handle null columns (type is null)
            if pa.types.is_null(col.type):
                # Create null array with target type
                new_arrays.append(pa.nulls(len(table), type=target_type))
            elif col.type != target_type:
                # Cast to target type
                try:
                    new_arrays.append(col.cast(target_type))
                except Exception as e:
                    print(f"  Warning: Could not cast {field_name} from {col.type} to {target_type}: {e}")
                    # If cast fails, keep original
                    new_arrays.append(col)
            else:
                # Type matches
                new_arrays.append(col)
        else:
            # Column missing, add null column
            new_arrays.append(pa.nulls(len(table), type=target_type))
        
        new_names.append(field_name)
    
    return pa.Table.from_arrays(new_arrays, names=new_names)


def load_date(client: bigquery.Client, bucket: str, prefix: str, dataset: str, table: str, date: dt.date):
    """Load a single date's parquet file with schema normalization."""
    
    # Read parquet
    uri = f"gs://{bucket}/{prefix}/source=TSI/agg=raw/dt={date.isoformat()}/TSI-{date.isoformat()}.parquet"
    try:
        tbl = pq.read_table(uri)
        print(f"Read {len(tbl)} rows from {date}")
    except Exception as e:
        print(f"Skipping {date}: {e}")
        return
    
    # Normalize schema
    normalized = normalize_schema(tbl)
    
    # Delete existing partition
    fq = f"{client.project}.{dataset}.{table}"
    delete_sql = f"DELETE FROM `{fq}` WHERE DATE(ts) = @d"
    job = client.query(delete_sql, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", date.isoformat())]
    ))
    job.result()
    
    # Load to BigQuery
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    
    # Write normalized table to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        pq.write_table(normalized, tmp.name)
        tmp_path = tmp.name
    
    try:
        load_job = client.load_table_from_file(
            open(tmp_path, 'rb'),
            fq,
            job_config=job_config
        )
        load_job.result()
        print(f"✓ Loaded {date} into {table}")
    finally:
        Path(tmp_path).unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--table", default="tsi_raw_materialized")
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--prefix", default="raw")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    
    client = bigquery.Client(project=args.project)
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    
    for date in daterange(start, end):
        load_date(client, args.bucket, args.prefix, args.dataset, args.table, date)


if __name__ == "__main__":
    main()
