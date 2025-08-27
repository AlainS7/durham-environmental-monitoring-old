#!/usr/bin/env python3
"""End-to-end cloud verification for GCS + BigQuery pipeline.

Checks performed:
 1. GCS write/read round trip (temp Parquet file via GCSUploader logic analogue)
 2. BigQuery dataset existence (create optional)
 3. Expected staging/fact tables presence (list + optional row counts for a partition date)
 4. Optional load simulation: dry-run style inspection of URIs that would be loaded

Exit code non-zero if any required check fails.
"""
from __future__ import annotations
import argparse
import logging
import os
import sys
import uuid
import io
import re
from typing import List, Optional, Tuple

import pandas as pd

from google.cloud import storage, bigquery
from google.cloud.exceptions import NotFound

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger("verify_cloud")


def check_gcs_round_trip(bucket: str, prefix: str) -> dict:
    try:
        client = storage.Client()
        b = client.bucket(bucket)
        test_df = pd.DataFrame({
            'timestamp': [pd.Timestamp.now(tz='UTC')],
            'test_value': [42],
            'marker': [str(uuid.uuid4())]
        })
        path = f"{prefix.strip('/')}/_verify/test-{uuid.uuid4().hex}.parquet"
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except Exception as e:  # pragma: no cover
            return {"ok": False, "error": f"pyarrow import failed: {e}"}
        table = pa.Table.from_pandas(test_df)
        buf = io.BytesIO()
        pq.write_table(table, buf, compression='snappy')
        buf.seek(0)
        blob = b.blob(path)
        blob.upload_from_file(buf, content_type='application/octet-stream')
        log.info(f"Uploaded test object gs://{bucket}/{path}")
        downloaded = b.get_blob(path)
        exists = downloaded is not None
        size = downloaded.size if downloaded else None
        return {"ok": exists, "object_path": f"gs://{bucket}/{path}", "size": size}
    except Exception as e:
        return {"ok": False, "error": f"GCS round trip exception: {e}"}


def ensure_dataset(client: bigquery.Client, dataset_id: str, location: str, create: bool) -> dict:
    ds_ref = bigquery.DatasetReference(client.project, dataset_id)
    try:
        ds = client.get_dataset(ds_ref)
        return {"ok": True, "created": False, "location": ds.location}
    except NotFound:
        if not create:
            return {"ok": False, "error": "Dataset not found"}
        ds_obj = bigquery.Dataset(ds_ref)
        ds_obj.location = location
        client.create_dataset(ds_obj)
        return {"ok": True, "created": True, "location": location}


def list_tables(client: bigquery.Client, dataset_id: str) -> List[str]:
    return [t.table_id for t in client.list_tables(dataset_id)]


EPOCH_CANDIDATE_RE = re.compile(r"(epoch|ts|time|timestamp)", re.IGNORECASE)

def _pick_time_column(schema: List[bigquery.SchemaField]) -> Tuple[Optional[str], Optional[str]]:
    """Heuristically select a temporal column & its type category.

    Returns (column_name, category) where category in {TIMESTAMP, DATETIME, DATE, EPOCH_INT, NONE}.
    """
    # Direct TIMESTAMP/DATETIME/DATE preference order
    ts_types = {"TIMESTAMP": [], "DATETIME": [], "DATE": []}
    epoch_ints: List[str] = []
    for field in schema:
        ftype = field.field_type.upper()
        name = field.name
        if ftype in ts_types:
            ts_types[ftype].append(name)
        elif ftype in {"INT64"} and EPOCH_CANDIDATE_RE.search(name):
            epoch_ints.append(name)
    for t in ["TIMESTAMP", "DATETIME", "DATE"]:
        if ts_types[t]:
            return ts_types[t][0], t
    if epoch_ints:
        return epoch_ints[0], "EPOCH_INT"
    return None, None

def _build_row_count_query(client: bigquery.Client, dataset_id: str, table: str, date: Optional[str]) -> Tuple[str, Optional[bigquery.QueryJobConfig]]:
    """Construct a safe COUNT query with adaptive filtering.

    Logic:
      - If table name ends with _YYYYMMDD (8 digits) treat as date-specific table -> simple COUNT(*).
      - Else introspect schema: pick a temporal column.
        * TIMESTAMP/DATETIME: DATE(col) = @dt
        * DATE: col = @dt
        * EPOCH_INT: if date provided, compute millis range [date, date+1) and do range filter; else COUNT(*).
      - If no date provided, ALWAYS just COUNT(*).
      - If no temporal column found, fallback COUNT(*).
    """
    fq = f"{client.project}.{dataset_id}.{table}"
    # Pattern for suffixed date
    suffixed_date = re.search(r"_(\d{8})$", table)
    if not date or suffixed_date:
        return f"SELECT COUNT(*) cnt FROM `{fq}`", None
    # Need schema
    try:
        table_obj = client.get_table(f"{dataset_id}.{table}")
    except Exception:
        return "SELECT 0 cnt", None  # Will resolve to 0 and be flagged maybe elsewhere
    col, category = _pick_time_column(table_obj.schema)
    if not col or not category:
        return f"SELECT COUNT(*) cnt FROM `{fq}`", None
    if category in {"TIMESTAMP", "DATETIME"}:
        q = f"SELECT COUNT(*) cnt FROM `{fq}` WHERE DATE(`{col}`) = @dt"
        cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('dt', 'DATE', date)])
        return q, cfg
    if category == "DATE":
        q = f"SELECT COUNT(*) cnt FROM `{fq}` WHERE `{col}` = @dt"
        cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('dt', 'DATE', date)])
        return q, cfg
    if category == "EPOCH_INT":
        # Assume milliseconds or seconds? Heuristic: if max value > 10^12 treat as ms else seconds.
        # We can't scan without cost; approximate by using range for both seconds and ms and OR them.
        # Compute start/end timestamps via parameter substitution.
        # We'll rely on BigQuery to parse TIMESTAMP(@dt) and TIMESTAMP_ADD.
        q = (
            "WITH bounds AS ("\
            " SELECT @dt AS d) "
            f"SELECT COUNT(*) cnt FROM `{fq}`, bounds "
            f"WHERE ( (`{col}` BETWEEN UNIX_SECONDS(TIMESTAMP(d)) AND UNIX_SECONDS(TIMESTAMP(DATE_ADD(d, INTERVAL 1 DAY)))-1) "
            f" OR (`{col}` BETWEEN UNIX_MILLIS(TIMESTAMP(d)) AND UNIX_MILLIS(TIMESTAMP(DATE_ADD(d, INTERVAL 1 DAY)))-1) )"
        )
        cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('dt', 'DATE', date)])
        return q, cfg
    return f"SELECT COUNT(*) cnt FROM `{fq}`", None

def table_row_count(client: bigquery.Client, dataset_id: str, table: str, date: str | None) -> int | None:
    fq = f"{client.project}.{dataset_id}.{table}"
    try:
        query, cfg = _build_row_count_query(client, dataset_id, table, date)
        job = client.query(query, job_config=cfg)
        return list(job.result())[0]['cnt']
    except Exception as e:
        log.warning(f"Row count query failed for {fq}: {e}")
        return None


def simulate_load_paths(bucket: str, prefix: str, date: str) -> List[str]:
    paths = []
    for src in ["WU", "TSI"]:
        for agg in ["raw", "h", "15min"]:
            paths.append(f"gs://{bucket}/{prefix.strip('/')}/source={src}/agg={agg}/dt={date}/*.parquet")
    return paths


def main():
    parser = argparse.ArgumentParser(description="Verify GCS + BigQuery integration")
    parser.add_argument('--project', default=os.getenv('BQ_PROJECT'))
    parser.add_argument('--dataset', required=True, help='BigQuery dataset ID')
    parser.add_argument('--location', default=os.getenv('BQ_LOCATION', 'US'))
    parser.add_argument('--bucket', required=True, help='GCS bucket')
    parser.add_argument('--prefix', default=os.getenv('GCS_PREFIX', 'sensor_readings'))
    parser.add_argument('--date', help='Partition date (YYYY-MM-DD) to inspect row counts')
    parser.add_argument('--create-dataset', action='store_true', help='Create dataset if missing')
    parser.add_argument('--show-tables', action='store_true', help='List tables')
    parser.add_argument('--check-rows', action='store_true', help='Fetch row counts (with optional --date filter)')
    parser.add_argument('--show-schema', action='store_true', help='Show schema per table when listing tables')
    parser.add_argument('--epoch-diagnostics', action='store_true', help='Analyze INT timestamp-like columns (epoch secs/millis)')
    parser.add_argument('--enforce-normalized', action='store_true', help='Fail if staging/tmp tables lack ts TIMESTAMP or float lat/lon')
    parser.add_argument('--simulate-loads', action='store_true', help='Show expected load URIs for date')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable JSON summary')
    parser.add_argument('--skip-gcs', action='store_true', help='Skip GCS round trip test')

    args = parser.parse_args()

    client = bigquery.Client(project=args.project)  # ADC project fallback

    summary: dict = {"steps": {}}

    # 1. GCS round trip
    if args.skip_gcs:
        gcs_res = {"ok": True, "skipped": True}
    else:
        gcs_res = check_gcs_round_trip(args.bucket, args.prefix)
    summary['steps']['gcs_round_trip'] = gcs_res
    if not gcs_res.get('ok'):
        log.error(f"GCS round trip failed: {gcs_res}")

    # 2. Dataset
    ds_res = ensure_dataset(client, args.dataset, args.location, args.create_dataset)
    summary['steps']['dataset'] = ds_res
    if not ds_res.get('ok'):
        log.error(f"Dataset check failed: {ds_res}")

    # 3. Tables list
    tables = []
    if args.show_tables:
        try:
            tables = list_tables(client, args.dataset)
        except Exception as e:
            log.error(f"List tables failed: {e}")
        summary['steps']['tables'] = tables

    # 4. Row counts
    if args.check_rows and tables:
        row_counts = {}
        schemas = {}
        epoch_diag: dict = {}
        norm_issues: dict = {}
        for t in tables:
            row_counts[t] = table_row_count(client, args.dataset, t, args.date)
            if args.show_schema:
                try:
                    tbl = client.get_table(f"{args.dataset}.{t}")
                    schemas[t] = {f.name: f.field_type for f in tbl.schema}
                except Exception as e:
                    schemas[t] = {"_error": str(e)}
            if args.enforce_normalized and (t.startswith('staging_') or t.startswith('tmp_')):
                # Skip analytical / derived tables
                if t.startswith('tmp_unpivot_') or t.startswith('snapshot_') or t.startswith('view_'):
                    pass
                else:
                    try:
                        tbl = client.get_table(f"{args.dataset}.{t}")
                        field_map = {f.name: f.field_type.upper() for f in tbl.schema}
                        issues = []
                        # Accept either ts or timestamp TIMESTAMP
                        has_ts = field_map.get('ts') == 'TIMESTAMP'
                        has_timestamp = field_map.get('timestamp') == 'TIMESTAMP'
                        if not (has_ts or has_timestamp):
                            issues.append('missing_canonical_timestamp')
                        if 'latitude' in field_map and field_map['latitude'] != 'FLOAT' and 'latitude_f' not in field_map:
                            issues.append('latitude_not_float')
                        if 'longitude' in field_map and field_map['longitude'] != 'FLOAT' and 'longitude_f' not in field_map:
                            issues.append('longitude_not_float')
                        int_time_cols = [n for n, ttype in field_map.items() if ttype == 'INTEGER' and n in ('timestamp','epoch')]
                        if (has_ts or has_timestamp) and len(int_time_cols) > 1:
                            issues.append('redundant_int_time_cols')
                        if issues:
                            norm_issues[t] = issues
                    except Exception as e:
                        norm_issues[t] = [f'_error:{e}']
            if args.epoch_diagnostics:
                try:
                    tbl = client.get_table(f"{args.dataset}.{t}")
                    # Identify INT64 columns matching time patterns
                    cand_cols = [f.name for f in tbl.schema if f.field_type.upper()=="INTEGER" and EPOCH_CANDIDATE_RE.search(f.name)]
                    if cand_cols:
                        diag_cols = []
                        for col in cand_cols:
                            q = f"SELECT MIN(`{col}`) mn, MAX(`{col}`) mx, COUNT(*) c FROM `{client.project}.{args.dataset}.{t}`"
                            try:
                                res = list(client.query(q).result())[0]
                                mn = res['mn']
                                mx = res['mx']
                                c = res['c']
                                if mn is None or mx is None:
                                    diag_cols.append({"column": col, "rows": c, "min": None, "max": None})
                                    continue
                                # Determine scale by magnitude (rough thresholds):
                                # seconds < 1e12, millis < 1e15, micros < 1e18, nanos >= 1e18
                                if mx < 10**12:
                                    scale = 'seconds'
                                    convert_expr_min = f"TIMESTAMP_SECONDS({mn})"
                                    convert_expr_max = f"TIMESTAMP_SECONDS({mx})"
                                elif mx < 10**15:
                                    scale = 'milliseconds'
                                    convert_expr_min = f"TIMESTAMP_MILLIS({mn})"
                                    convert_expr_max = f"TIMESTAMP_MILLIS({mx})"
                                elif mx < 10**18:
                                    scale = 'microseconds'
                                    # BigQuery: no TIMESTAMP_MICROS literal function; use TIMESTAMP_MICROS()
                                    convert_expr_min = f"TIMESTAMP_MICROS({mn})"
                                    convert_expr_max = f"TIMESTAMP_MICROS({mx})"
                                else:
                                    scale = 'nanoseconds'
                                    # Convert by dividing to micros then TIMESTAMP_MICROS (integer division)
                                    convert_expr_min = f"TIMESTAMP_MICROS(CAST(DIV({mn},1000) AS INT64))"
                                    convert_expr_max = f"TIMESTAMP_MICROS(CAST(DIV({mx},1000) AS INT64))"
                                conv_query = (
                                    "SELECT "
                                    f"FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', {convert_expr_min}) AS iso_min, "
                                    f"FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', {convert_expr_max}) AS iso_max"
                                )
                                try:
                                    conv_res = list(client.query(conv_query).result())[0]
                                    iso_min = conv_res['iso_min']
                                    iso_max = conv_res['iso_max']
                                except Exception:
                                    iso_min = iso_max = None
                                diag_cols.append({
                                    "column": col,
                                    "rows": c,
                                    "min": mn,
                                    "max": mx,
                                    "scale": scale,
                                    "iso_min": iso_min,
                                    "iso_max": iso_max
                                })
                            except Exception as ie:
                                diag_cols.append({"column": col, "error": str(ie)})
                        if diag_cols:
                            epoch_diag[t] = diag_cols
                except Exception as e:
                    epoch_diag[t] = [{"_error": str(e)}]
        summary['steps']['row_counts'] = row_counts
        if args.show_schema:
            summary['steps']['schemas'] = schemas
        if args.epoch_diagnostics:
            summary['steps']['epoch_diagnostics'] = epoch_diag
        if args.enforce_normalized:
            summary['steps']['normalization_issues'] = norm_issues

    # 5. Simulated load URIs
    if args.simulate_loads and args.date:
        summary['steps']['load_uris'] = simulate_load_paths(args.bucket, args.prefix, args.date)

    if args.json:
        import json
        print(json.dumps(summary, default=str, indent=2))
    else:
        for k, v in summary['steps'].items():
            log.info(f"{k}: {v}")

    failed = any([not gcs_res.get('ok'), not ds_res.get('ok')])
    if args.enforce_normalized and summary['steps'].get('normalization_issues'):
        if any(summary['steps']['normalization_issues'].values()):
            failed = True
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
