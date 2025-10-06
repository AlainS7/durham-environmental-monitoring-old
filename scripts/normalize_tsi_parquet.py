#!/usr/bin/env python3
"""Normalize TSI parquet files to have consistent schemas across all dates.

This script reads existing TSI parquet files from GCS, normalizes their schemas
to ensure consistent types even for null columns, and writes them back.

The issue: Days with all-null measurements store those columns as null type in parquet,
which BigQuery interprets as INT32. Days with actual data store them as proper types
(FLOAT64, STRING, BOOLEAN). This creates incompatible schemas.

The fix: Explicitly define a consistent schema for all columns and cast/fill missing
columns appropriately.
"""
from __future__ import annotations

import argparse
import datetime as dt
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage


# Define the canonical schema for TSI data
TSI_SCHEMA = pa.schema([
    pa.field('cloud_account_id', pa.string()),
    pa.field('native_sensor_id', pa.string()),
    pa.field('timestamp', pa.timestamp('ns', tz='UTC')),
    pa.field('is_indoor', pa.bool_()),
    pa.field('is_public', pa.bool_()),
    pa.field('latitude', pa.float64()),
    pa.field('longitude', pa.float64()),
    pa.field('pm10', pa.float64()),
    pa.field('pm10_aqi', pa.float64()),
    pa.field('pm1_0', pa.float64()),
    pa.field('pm2_5', pa.float64()),
    pa.field('pm2_5_aqi', pa.float64()),
    pa.field('pm4_0', pa.float64()),
    pa.field('ncpm4_0', pa.float64()),
    pa.field('model', pa.string()),
    pa.field('ncpm0_5', pa.float64()),
    pa.field('ncpm10', pa.float64()),
    pa.field('ncpm1_0', pa.float64()),
    pa.field('ncpm2_5', pa.float64()),
    pa.field('humidity', pa.float64()),
    pa.field('serial', pa.string()),
    pa.field('temperature', pa.float64()),
    pa.field('tpsize', pa.float64()),
    pa.field('co2_ppm', pa.float64()),
    pa.field('co_ppm', pa.float64()),
    pa.field('baro_inhg', pa.float64()),
    pa.field('o3_ppb', pa.float64()),
    pa.field('no2_ppb', pa.float64()),
    pa.field('so2_ppb', pa.float64()),
    pa.field('ch2o_ppb', pa.float64()),
    pa.field('voc_mgm3', pa.float64()),
    pa.field('ts', pa.timestamp('ns', tz='UTC')),
    pa.field('latitude_f', pa.float64()),
    pa.field('longitude_f', pa.float64()),
])


def daterange(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    """Generate dates from start to end inclusive."""
    cur = start
    while cur <= end:
        yield cur
        cur = cur + dt.timedelta(days=1)


def normalize_table(table: pa.Table) -> pa.Table:
    """Convert a table to the canonical TSI schema.
    
    Handles:
    - Null-type columns (cast to proper type with all nulls)
    - Missing columns (add with all nulls)
    - Type mismatches (cast to target type)
    - Extra columns (drop them)
    - Column ordering (reorder to match schema)
    """
    arrays = []
    
    for field in TSI_SCHEMA:
        if field.name in table.column_names:
            col = table.column(field.name)
            
            # Handle null-type columns (all nulls, no defined type)
            if pa.types.is_null(col.type):
                # Create null array with proper type
                arrays.append(pa.nulls(len(table), type=field.type))
            elif col.type != field.type:
                # Cast to target type
                try:
                    arrays.append(col.cast(field.type))
                except pa.ArrowInvalid as e:
                    print(f"  Warning: Could not cast {field.name} from {col.type} to {field.type}: {e}")
                    print(f"  Creating null column for {field.name}")
                    arrays.append(pa.nulls(len(table), type=field.type))
            else:
                # Type matches
                arrays.append(col)
        else:
            # Column missing, add null column
            arrays.append(pa.nulls(len(table), type=field.type))
    
    return pa.Table.from_arrays(arrays, schema=TSI_SCHEMA)


def process_date(bucket_name: str, prefix: str, date: dt.date, dry_run: bool = False) -> bool:
    """Process a single date's parquet file.
    
    Args:
        bucket_name: GCS bucket name
        prefix: GCS prefix (e.g., 'raw')
        date: Date to process
        dry_run: If True, don't write back to GCS
        
    Returns:
        True if successful, False otherwise
    """
    date_str = date.isoformat()
    path = f"{prefix}/source=TSI/agg=raw/dt={date_str}/TSI-{date_str}.parquet"
    uri = f"gs://{bucket_name}/{path}"
    
    try:
        # Read existing parquet file
        table = pq.read_table(uri)
        original_rows = len(table)
        original_cols = len(table.column_names)
        
        # Check if already normalized
        if table.schema == TSI_SCHEMA:
            print(f"✓ {date_str}: Already normalized ({original_rows:,} rows)")
            return True
        
        # Normalize schema
        normalized = normalize_table(table)
        
        if len(normalized) != original_rows:
            print(f"✗ {date_str}: Row count mismatch! {original_rows} → {len(normalized)}")
            return False
        
        # Write back to GCS (unless dry run)
        if dry_run:
            print(f"[DRY RUN] {date_str}: Would normalize ({original_rows:,} rows, {original_cols} → {len(TSI_SCHEMA)} cols)")
            return True
        
        # Write to temporary path first
        temp_path = f"{prefix}/source=TSI/agg=raw/dt={date_str}/.tmp.TSI-{date_str}.parquet"
        temp_uri = f"gs://{bucket_name}/{temp_path}"
        
        pq.write_table(normalized, temp_uri)
        
        # Rename to final location (atomic operation)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        temp_blob = bucket.blob(temp_path)
        bucket.rename_blob(temp_blob, path)
        
        print(f"✓ {date_str}: Normalized ({original_rows:,} rows, {original_cols} → {len(TSI_SCHEMA)} cols)")
        return True
        
    except FileNotFoundError:
        print(f"⊘ {date_str}: File not found")
        return False
    except Exception as e:
        print(f"✗ {date_str}: Error - {e}")
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Normalize TSI parquet files to consistent schema"
    )
    ap.add_argument("--bucket", required=True, help="GCS bucket name")
    ap.add_argument("--prefix", default="raw", help="GCS prefix (default: raw)")
    ap.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    ap.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="Don't write changes, just report")
    ap.add_argument("--parallel", type=int, default=1, help="Number of parallel workers (default: 1)")
    args = ap.parse_args()
    
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    
    dates = list(daterange(start, end))
    total = len(dates)
    
    print(f"Normalizing {total} days of TSI parquet files")
    print(f"Bucket: gs://{args.bucket}/{args.prefix}")
    print(f"Date range: {start} to {end}")
    if args.dry_run:
        print("DRY RUN MODE - No changes will be written")
    print()
    
    if args.parallel > 1:
        # Parallel processing
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {
                executor.submit(process_date, args.bucket, args.prefix, date, args.dry_run): date
                for date in dates
            }
            
            succeeded = 0
            failed = 0
            
            for future in as_completed(futures):
                if future.result():
                    succeeded += 1
                else:
                    failed += 1
    else:
        # Sequential processing
        succeeded = 0
        failed = 0
        
        for i, date in enumerate(dates, 1):
            if process_date(args.bucket, args.prefix, date, args.dry_run):
                succeeded += 1
            else:
                failed += 1
            
            # Progress indicator
            if i % 10 == 0:
                print(f"Progress: {i}/{total} ({100*i//total}%)")
    
    print()
    print(f"Summary: {succeeded} succeeded, {failed} failed, {total} total")
    
    if not args.dry_run and succeeded > 0:
        print()
        print("✓ Normalization complete! You can now materialize these files to BigQuery.")


if __name__ == "__main__":
    main()
