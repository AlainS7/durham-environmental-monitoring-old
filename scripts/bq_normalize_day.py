#!/usr/bin/env python3
"""Normalize staging BigQuery day tables (timestamp + lat/lon types).

Actions per table (pattern: staging_{source}_{YYYYMMDD} and tmp_{source}_auto_{YYYYMMDD}):
 1. Add canonical TIMESTAMP column ts if missing (from epoch seconds or high-resolution integer timestamp).
 2. Add FLOAT latitude_f / longitude_f if original latitude/longitude are INTEGER or STRING.
 3. (Optional future) Backfill and drop obsolete integer timestamp columns.

Usage:
  python scripts/bq_normalize_day.py --project durham-weather-466502 --dataset sensors --date 2025-08-20 --execute

Without --execute it performs a dry-run and prints planned SQL statements.
"""
from __future__ import annotations
import argparse
import re
from typing import List
from google.cloud import bigquery
from dataclasses import dataclass

TIME_COL_CANDIDATES_NS = ["timestamp"]  # high-res ints (ns/us/ms) when very large
EPOCH_SECONDS_COL = "epoch"


def detect_time_derivation(table: bigquery.Table) -> str | None:
    names = {f.name: f for f in table.schema}
    # If we already have a TIMESTAMP column named ts, nothing to do
    if "ts" in names and names["ts"].field_type.upper() == "TIMESTAMP":
        return None
    # Prefer existing epoch seconds
    if EPOCH_SECONDS_COL in names and names[EPOCH_SECONDS_COL].field_type.upper() == "INTEGER":
        return f"ts = TIMESTAMP_SECONDS({EPOCH_SECONDS_COL})"
    # Otherwise look for high-res integer timestamp
    for cand in TIME_COL_CANDIDATES_NS:
        if cand in names and names[cand].field_type.upper() == "INTEGER":
            # Determine scale by value magnitude (sample min/max)
            return f"ts = CASE WHEN {cand} >= 1e18 THEN TIMESTAMP_MICROS(CAST(DIV({cand},1000) AS INT64)) " \
                   f"WHEN {cand} >= 1e15 THEN TIMESTAMP_MICROS({cand}) " \
                   f"WHEN {cand} >= 1e12 THEN TIMESTAMP_MILLIS({cand}) ELSE TIMESTAMP_SECONDS({cand}) END"
    return None


def detect_latlon_alter(table: bigquery.Table) -> List[str]:
    names = {f.name: f for f in table.schema}
    stmts: List[str] = []
    for col in ["latitude", "longitude"]:
        if col in names:
            f = names[col]
            if f.field_type.upper() in {"INTEGER", "STRING"}:
                alias = col + "_f"
                if alias not in names:
                    stmts.append(f"ADD COLUMN {alias} FLOAT64")
    return stmts


def plan_for_table(client: bigquery.Client, dataset: str, table_id: str) -> List[str]:
    try:
        tbl = client.get_table(f"{dataset}.{table_id}")
    except Exception:
        return []
    alterations: List[str] = []
    ts_expr = detect_time_derivation(tbl)
    if ts_expr:
        # Add ts column first if missing
        if all(f.name != 'ts' for f in tbl.schema):
            alterations.append("ADD COLUMN ts TIMESTAMP")
        # Backfill ts
        alterations.append(f"UPDATE `{client.project}.{dataset}.{table_id}` SET {ts_expr} WHERE ts IS NULL")
    # Lat/Lon
    latlon_adds = detect_latlon_alter(tbl)
    if latlon_adds:
        # Insert individual ADD COLUMN statements at beginning
        alterations[0:0] = latlon_adds
        # Backfill statements
        for col in ["latitude", "longitude"]:
            alias = col + "_f"
            if any(alias in a for a in latlon_adds):
                alterations.append(f"UPDATE `{client.project}.{dataset}.{table_id}` SET {alias} = CAST({col} AS FLOAT64) WHERE {alias} IS NULL AND {col} IS NOT NULL")
    return alterations


@dataclass(slots=True)
class Args:
    project: str | None
    dataset: str
    date: str
    execute: bool
    drop_int_time: bool
    drop_original_latlon: bool


def parse() -> Args:
    p = argparse.ArgumentParser(description="Normalize a day's staging tables (timestamp + lat/lon)")
    p.add_argument('--project', required=False, default=None)
    p.add_argument('--dataset', required=True)
    p.add_argument('--date', required=True, help='Date YYYY-MM-DD')
    p.add_argument('--execute', action='store_true', help='Execute changes (otherwise dry-run)')
    p.add_argument('--drop-int-time', action='store_true', help='Drop original integer timestamp/epoch columns once ts added')
    p.add_argument('--drop-original-latlon', action='store_true', help='Drop original latitude/longitude if *_f columns created')
    a = p.parse_args()
    return Args(a.project, a.dataset, a.date, a.execute, a.drop_int_time, a.drop_original_latlon)


def list_target_tables(client: bigquery.Client, dataset: str, date: str) -> list[str]:
    ymd = date.replace('-', '')
    pattern = re.compile(rf'^(staging|tmp)_(wu|tsi)_.*{ymd}$', re.IGNORECASE)
    return [t.table_id for t in client.list_tables(dataset) if pattern.match(t.table_id)]


def build_plans(client: bigquery.Client, args: Args, tables: list[str]) -> tuple[dict[str, List[str]], set[str]]:
    plans: dict[str, List[str]] = {}
    cleanup_only: set[str] = set()
    for t in tables:
        stmts = plan_for_table(client, args.dataset, t)
        if stmts:
            plans[t] = stmts
            continue
        # Consider cleanup-only if drop flags requested
        if args.execute and (args.drop_int_time or args.drop_original_latlon):
            tbl = client.get_table(f"{args.dataset}.{t}")
            field_map = {f.name: f.field_type.upper() for f in tbl.schema}
            needs_int_drop = args.drop_int_time and ('ts' in field_map and field_map['ts']=='TIMESTAMP' and any(field_map.get(c)=='INTEGER' for c in ['timestamp','epoch']))
            needs_latlon_drop = False
            if args.drop_original_latlon:
                for col in ['latitude','longitude']:
                    if col in field_map and f'{col}_f' in field_map and field_map[col] != 'FLOAT':
                        needs_latlon_drop = True
            if needs_int_drop or needs_latlon_drop:
                cleanup_only.add(t)
    return plans, cleanup_only


def print_plan(args: Args, plans: dict[str, List[str]], cleanup_only: set[str]):
    if not plans and not cleanup_only:
        print('No normalization actions required.')
        return False
    for table, stmts in plans.items():
        print(f"-- Table: {table}")
        for s in stmts:
            print(f"ALTER/UPDATE: {s}")
    for table in cleanup_only:
        print(f"-- Table: {table} (cleanup only)")
        if args.drop_int_time:
            print("CLEANUP: drop integer timestamp/epoch columns")
        if args.drop_original_latlon:
            print("CLEANUP: drop original latitude/longitude columns")
    return True


def execute_plan(client: bigquery.Client, args: Args, plans: dict[str, List[str]], cleanup_only: set[str]):
    # Execute add/update/backfill
    for table, stmts in plans.items():
        for s in stmts:
            if s.startswith('ADD COLUMN'):
                alter_sql = f"ALTER TABLE `{client.project}.{args.dataset}.{table}` {s}"
                client.query(alter_sql).result()
            elif s.startswith('UPDATE '):
                client.query(s).result()
        # Optional cleanup
        tbl = client.get_table(f"{args.dataset}.{table}")
        field_map = {f.name: f.field_type.upper() for f in tbl.schema}
        if args.drop_int_time and ('ts' in field_map and field_map['ts']=='TIMESTAMP'):
            for col in ['timestamp','epoch']:
                if col in field_map and field_map[col]=='INTEGER':
                    client.query(f"ALTER TABLE `{client.project}.{args.dataset}.{table}` DROP COLUMN {col}").result()
        if args.drop_original_latlon:
            tbl = client.get_table(f"{args.dataset}.{table}")
            field_map = {f.name: f.field_type.upper() for f in tbl.schema}
            for col in ['latitude','longitude']:
                if col in field_map and f'{col}_f' in field_map and field_map[col] != 'FLOAT':
                    client.query(f"ALTER TABLE `{client.project}.{args.dataset}.{table}` DROP COLUMN {col}").result()
    # Cleanup-only tables
    for table in cleanup_only:
        tbl = client.get_table(f"{args.dataset}.{table}")
        field_map = {f.name: f.field_type.upper() for f in tbl.schema}
        if args.drop_int_time and ('ts' in field_map and field_map['ts']=='TIMESTAMP'):
            for col in ['timestamp','epoch']:
                if col in field_map and field_map[col]=='INTEGER':
                    client.query(f"ALTER TABLE `{client.project}.{args.dataset}.{table}` DROP COLUMN {col}").result()
        if args.drop_original_latlon:
            tbl = client.get_table(f"{args.dataset}.{table}")
            field_map = {f.name: f.field_type.upper() for f in tbl.schema}
            for col in ['latitude','longitude']:
                if col in field_map and f'{col}_f' in field_map and field_map[col] != 'FLOAT':
                    client.query(f"ALTER TABLE `{client.project}.{args.dataset}.{table}` DROP COLUMN {col}").result()
    print('Normalization executed.')


def main():
    args = parse()
    client = bigquery.Client(project=args.project)
    tables = list_target_tables(client, args.dataset, args.date)
    plans, cleanup_only = build_plans(client, args, tables)
    any_plan = print_plan(args, plans, cleanup_only)
    if not any_plan:
        return
    if args.execute:
        execute_plan(client, args, plans, cleanup_only)
    else:
        print('Dry-run (no changes made). Use --execute to apply.')

if __name__ == '__main__':
    main()
