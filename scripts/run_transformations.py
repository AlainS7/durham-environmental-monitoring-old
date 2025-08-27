#!/usr/bin/env python3
"""Render and optionally execute transformation SQL files.

Supports simple token replacement for ${PROJECT} and ${DATASET} plus
parameter @proc_date (passed as --date) using BigQuery query parameters.

Usage:
  python scripts/run_transformations.py --project my-proj --dataset sensors --dir transformations/sql --date 2025-08-26 --execute

Without --execute it prints the SQL (dry run). Execution order is lexical (filenames sorted).
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from typing import List
import re

from google.cloud import bigquery

TOKEN_PATTERN = re.compile(r"\$\{(PROJECT|DATASET)\}")

def render(sql: str, project: str, dataset: str) -> str:
    def repl(match):
        key = match.group(1)
        return project if key == 'PROJECT' else dataset
    return TOKEN_PATTERN.sub(repl, sql)

def list_sql_files(dir_path: Path) -> List[Path]:
    return sorted([p for p in dir_path.glob('*.sql') if p.is_file()])

def execute_sql(client: bigquery.Client, sql: str, process_date: str):
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter('proc_date', 'DATE', process_date)]
    )
    job = client.query(sql, job_config=job_config)
    job.result()


def main():
    ap = argparse.ArgumentParser(description="Run transformation SQL files")
    ap.add_argument('--project', default=os.getenv('BQ_PROJECT'))
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--dir', default='transformations/sql')
    ap.add_argument('--date', required=True, help='Processing date (e.g. yesterday) for parameter @proc_date')
    ap.add_argument('--execute', action='store_true', help='Execute instead of print')
    args = ap.parse_args()

    if not args.project:
        raise SystemExit("--project or BQ_PROJECT env var required")

    client = bigquery.Client(project=args.project)
    dir_path = Path(args.dir)
    if not dir_path.exists():
        raise SystemExit(f"Directory not found: {dir_path}")

    for sql_file in list_sql_files(dir_path):
        raw = sql_file.read_text()
        sql = render(raw, args.project, args.dataset)
        print(f"-- {sql_file.name} --")
        if args.execute:
            execute_sql(client, sql, args.date)
            print(f"Executed {sql_file.name}")
        else:
            print(sql)

if __name__ == '__main__':
    main()
