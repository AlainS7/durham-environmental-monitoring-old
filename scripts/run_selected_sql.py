#!/usr/bin/env python3
"""Render and optionally execute specific SQL files with parameterization.

Tokens supported: ${PROJECT}, ${DATASET}
Query parameter: @proc_date (DATE)

Usage:
  python scripts/run_selected_sql.py \
    --project my-proj --dataset sensors --date 2025-09-21 --execute \
    transformations/sql/06_sensor_location_dim.sql \
    transformations/sql/04_sensor_canonical_location.sql \
    transformations/sql/05_views_for_mapping.sql
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List  # noqa: F401 (kept for future extension)

from google.cloud import bigquery  # type: ignore


TOKEN_PATTERN = re.compile(r"\$\{(PROJECT|DATASET)\}")


def render(sql: str, project: str, dataset: str) -> str:
    def repl(match):
        key = match.group(1)
        return project if key == 'PROJECT' else dataset
    return TOKEN_PATTERN.sub(repl, sql)


def execute_sql(client: bigquery.Client, sql: str, process_date: str):
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter('proc_date', 'DATE', process_date)]
    )
    job = client.query(sql, job_config=job_config)
    job.result()


def main():
    ap = argparse.ArgumentParser(description="Run selected SQL files")
    ap.add_argument('--project', default=None, help='BigQuery project (defaults to ADC)')
    ap.add_argument('--dataset', required=True, help='BigQuery dataset')
    ap.add_argument('--date', required=True, help='@proc_date value (YYYY-MM-DD)')
    ap.add_argument('--execute', action='store_true', help='Execute instead of printing rendered SQL')
    ap.add_argument('files', nargs='+', help='SQL file paths to run, in order')
    args = ap.parse_args()

    client = bigquery.Client(project=args.project) if args.execute else None

    for f in args.files:
        p = Path(f)
        if not p.exists():
            raise SystemExit(f"SQL file not found: {p}")
        raw = p.read_text()
        sql = render(raw, args.project or '', args.dataset)
        print(f"-- {p.name} --")
        if args.execute:
            execute_sql(client, sql, args.date)  # type: ignore[arg-type]
            print(f"Executed {p.name}")
        else:
            print(sql)


if __name__ == '__main__':
    main()
