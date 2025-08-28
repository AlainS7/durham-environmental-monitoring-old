#!/usr/bin/env python3
"""Backfill a date range into the consolidated sensor_readings table.

Automatically discovers staging tables (per-source) and performs a MERGE per day.

Example:
  python scripts/merge_backfill_range.py \
    --project durham-weather-466502 --dataset sensors \
    --start 2025-08-21 --end 2025-08-28

Environment fallbacks:
  BQ_PROJECT, BQ_LOCATION
"""
from __future__ import annotations
import argparse
import datetime as dt
import logging
import os
from google.cloud import bigquery
from merge_sensor_readings import (
    resolve_staging_tables, ensure_target_exists_from_reference, build_merge_sql  # type: ignore
)  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger("merge_backfill_range")


def parse_args():
    p = argparse.ArgumentParser(description="Backfill a date range with MERGE operations")
    p.add_argument('--project', default=os.getenv('BQ_PROJECT'))
    p.add_argument('--dataset', required=True)
    p.add_argument('--start', required=True, help='Start date (YYYY-MM-DD) inclusive')
    p.add_argument('--end', required=True, help='End date (YYYY-MM-DD) inclusive')
    p.add_argument('--location', default=os.getenv('BQ_LOCATION', 'US'))
    p.add_argument('--auto-detect-staging', action='store_true', default=True, help='Auto detect staging tables (default)')
    p.add_argument('--staging-prefix', default='sensor_readings_')
    p.add_argument('--staging-suffix', default='_raw')
    p.add_argument('--staging-tables', default=None, help='Explicit comma list override')
    p.add_argument('--target-table', default='sensor_readings')
    p.add_argument('--update-only-if-changed', action='store_true')
    return p.parse_args()


def daterange(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def main():
    a = parse_args()
    client = bigquery.Client(project=a.project, location=a.location)
    # Build a lightweight args-like object for staging resolution reuse
    from types import SimpleNamespace
    tmp = SimpleNamespace(
        staging_table=None,
        staging_tables=a.staging_tables,
        auto_detect_staging=(a.auto_detect_staging and not a.staging_tables),
        staging_prefix=a.staging_prefix,
        staging_suffix=a.staging_suffix,
        target_table=a.target_table,
    )
    staging_tables = resolve_staging_tables(client, a.dataset, tmp)  # type: ignore
    ensure_target_exists_from_reference(client, a.dataset, staging_tables[0], a.target_table)

    for d in daterange(dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)):
        date_str = d.isoformat()
        sql = build_merge_sql(client.project, a.dataset, staging_tables, a.target_table, a.update_only_if_changed)
        cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('d', 'DATE', date_str)])
        log.info("Merging date %s", date_str)
        job = client.query(sql, job_config=cfg)
        job.result()
        log.info("Date %s merged (affected: %s)", date_str, job.num_dml_affected_rows)


if __name__ == '__main__':  # pragma: no cover
    main()
