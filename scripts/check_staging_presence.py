#!/usr/bin/env python3
"""Check that expected per-source staging tables for a given date exist.

Supports two patterns:
 1. Partitioned unified staging table: --unified-table staging_sensor_readings_raw (DATE(timestamp)=date)
 2. Per-source dated tables: staging_<source>_YYYYMMDD (default pattern) for sources list.

Exit codes:
 0 success (all required present)
 1 partial/missing
 2 invalid arguments
"""
from __future__ import annotations
import argparse
import datetime as dt
import logging
from typing import List
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger("check_staging_presence")


def parse_args():
    p = argparse.ArgumentParser(description="Validate staging ingestion presence for a date")
    p.add_argument('--project', required=False, help='GCP project (ADC if omitted)')
    p.add_argument('--dataset', required=True, help='BigQuery dataset')
    p.add_argument('--date', required=False, help='Date (YYYY-MM-DD); default yesterday UTC')
    p.add_argument('--sources', default='tsi,wu', help='Comma list of sources for per-source pattern')
    p.add_argument('--unified-table', help='Name of unified partitioned staging table (if used)')
    return p.parse_args()


def table_exists(client: bigquery.Client, dataset: str, table: str) -> bool:
    try:
        client.get_table(f"{dataset}.{table}")
        return True
    except Exception:
        return False


def main():
    a = parse_args()
    date_str = a.date or (dt.datetime.utcnow() - dt.timedelta(days=1)).date().isoformat()
    ds_compact = date_str.replace('-', '')
    client = bigquery.Client(project=a.project) if a.project else bigquery.Client()

    missing: List[str] = []
    checked: List[str] = []

    if a.unified_table:
        if not table_exists(client, a.dataset, a.unified_table):
            missing.append(a.unified_table)
        checked.append(a.unified_table)
    else:
        sources = [s.strip() for s in a.sources.split(',') if s.strip()]
        for src in sources:
            t = f"staging_{src}_{ds_compact}"
            checked.append(t)
            if not table_exists(client, a.dataset, t):
                missing.append(t)

    if missing:
        log.error("Missing staging tables for %s: %s", date_str, ', '.join(missing))
        log.info("Checked tables: %s", ', '.join(checked))
        raise SystemExit(1)
    log.info("All expected staging tables present for %s (%s)", date_str, ', '.join(checked))


if __name__ == '__main__':  # pragma: no cover
    main()
