#!/usr/bin/env python3
"""Backfill a date range into the consolidated sensor_readings table.

For each day in the inclusive range, performs the same MERGE as merge_sensor_readings.py.

Example:
  python scripts/merge_backfill_range.py \
    --project durham-weather-466502 --dataset sensors \
    --start 2025-08-21 --end 2025-08-28 --staging-table staging_sensor_readings_raw
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from typing import Iterator, List

from google.cloud import bigquery

# We reuse ensure_tables_exist from the single-table merge script to bootstrap target if needed.
from merge_sensor_readings import ensure_tables_exist  # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger("merge_backfill_range")


def parse_args():
    p = argparse.ArgumentParser(description="Backfill a date range with MERGE operations")
    p.add_argument('--project', default=os.getenv('BQ_PROJECT'))
    p.add_argument('--dataset', required=True)
    p.add_argument('--start', required=True, help='Start date (YYYY-MM-DD) inclusive')
    p.add_argument('--end', required=True, help='End date (YYYY-MM-DD) inclusive')
    p.add_argument('--location', default=os.getenv('BQ_LOCATION', 'US'))
    p.add_argument('--staging-table', default=None, help='(Legacy) single staging table name')
    p.add_argument('--sources', default='tsi,wu', help='Comma list of source ids (matches staging_<src>_YYYYMMDD)')
    p.add_argument('--target-table', default='sensor_readings')
    p.add_argument('--update-only-if-changed', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args()


def dr(start: dt.date, end: dt.date) -> Iterator[dt.date]:
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def main():
    a = parse_args()
    try:
        start_date = dt.date.fromisoformat(a.start)
        end_date = dt.date.fromisoformat(a.end)
    except ValueError as e:  # pragma: no cover
        log.error("Invalid date: %s", e)
        sys.exit(1)
    if end_date < start_date:
        log.error("End date before start date")
        sys.exit(1)

    client = bigquery.Client(project=a.project, location=a.location)
    if a.staging_table:
        # Legacy path: one staging table partitioned by date.
        ensure_tables_exist(client, a.dataset, a.staging_table, a.target_table)
    else:
        # We'll validate existence of at least one day's tables for first source to infer readiness.
        pass  # target creation handled later per-day if needed.

    sources: List[str] = [s.strip() for s in a.sources.split(',') if s.strip()]
    if not sources:
        log.error('No sources resolved (empty --sources).')
        sys.exit(2)

    def day_merge_sql(day: dt.date) -> str:
        if a.staging_table:
            # Use parameterized MERGE from original script logic (simpler) - replicate inline here.
            predicate = "T.value != S.value" if a.update_only_if_changed else "TRUE"
            return f"""
MERGE `{client.project}.{a.dataset}.{a.target_table}` T
USING (
  SELECT timestamp, deployment_fk, metric_name, value
  FROM `{client.project}.{a.dataset}.{a.staging_table}`
  WHERE DATE(timestamp) = @d
) S
ON T.timestamp = S.timestamp AND T.deployment_fk = S.deployment_fk AND T.metric_name = S.metric_name
WHEN MATCHED AND {predicate} THEN UPDATE SET value = S.value
WHEN NOT MATCHED THEN INSERT (timestamp, deployment_fk, metric_name, value) VALUES (S.timestamp, S.deployment_fk, S.metric_name, S.value)
""".strip()
        # Multi-source dated tables pattern staging_<src>_YYYYMMDD (not partitioned) per ingest.
        ds = day.strftime('%Y%m%d')
        staging_tables = [f'staging_{src}_{ds}' for src in sources]
        selects = []
        # Probe existence; skip missing tables gracefully
        existing = []
        for t in staging_tables:
            try:
                client.get_table(f"{a.dataset}.{t}")
                existing.append(t)
            except Exception:
                log.warning('Missing staging table %s - skipping for %s', t, ds)
        if not existing:
            log.warning('No staging tables found for %s; skipping day.', ds)
            return ''  # Caller will skip empty SQL
        for t in existing:
            selects.append(f"SELECT timestamp, deployment_fk, metric_name, value FROM `{client.project}.{a.dataset}.{t}`")
        union = "\n  UNION ALL\n  ".join(selects)
        predicate = "T.value != S.value" if a.update_only_if_changed else "TRUE"
        return f"""
MERGE `{client.project}.{a.dataset}.{a.target_table}` T
USING (
  {union}
) S
ON T.timestamp = S.timestamp AND T.deployment_fk = S.deployment_fk AND T.metric_name = S.metric_name
WHEN MATCHED AND {predicate} THEN UPDATE SET value = S.value
WHEN NOT MATCHED THEN INSERT (timestamp, deployment_fk, metric_name, value) VALUES (S.timestamp, S.deployment_fk, S.metric_name, S.value)
""".strip()

    # Ensure target exists (use single-table path if provided; else try to copy schema from first available staging for start_date)
    if not a.staging_table:
        probe_ds = start_date.strftime('%Y%m%d')
        probe_table = f'staging_{sources[0]}_{probe_ds}'
        try:
            ensure_tables_exist(client, a.dataset, probe_table, a.target_table)
        except Exception as e:  # pragma: no cover
            log.warning('Could not bootstrap target from %s: %s (will attempt per-day)', probe_table, e)

    for day in dr(start_date, end_date):
        sql = day_merge_sql(day)
        if not sql:
            continue
        if a.dry_run:
            log.info('[DRY RUN] Would MERGE %s', day)
            continue
        log.info('Merging %s', day)
        # Non-parameterized (dated tables), so no query parameters for multi-source path.
        if a.staging_table:
            cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('d', 'DATE', day.isoformat())])
            job = client.query(sql, job_config=cfg)
        else:
            job = client.query(sql)
        try:
            job.result()
        except Exception as e:
            log.error('Failed merging %s: %s', day, e)
            continue
        log.info('Merged %s (affected rows: %s)', day, getattr(job, 'num_dml_affected_rows', 'n/a'))

    log.info("Backfill complete %s -> %s", start_date, end_date)


if __name__ == '__main__':  # pragma: no cover
    main()
