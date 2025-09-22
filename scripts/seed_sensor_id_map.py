#!/usr/bin/env python3
"""Seed identity mapping into sensor_id_map for all known native_sensor_id values.

By default, seeds from sensor_readings_long and sensor_readings_daily to capture all
sensors seen historically. Safe to re-run; only inserts rows that don't exist.

Usage:
  python scripts/seed_sensor_id_map.py --project durham-weather-466502 --dataset sensors [--execute]

Without --execute it prints the SQL only.
"""
from __future__ import annotations
import argparse
from google.cloud import bigquery

SQL = """
INSERT INTO `{project}.{dataset}.sensor_id_map` (sensor_id, native_sensor_id, source, updated_at)
SELECT DISTINCT native_sensor_id AS sensor_id, native_sensor_id, 'seed:identity', CURRENT_TIMESTAMP()
FROM (
  SELECT native_sensor_id FROM `{project}.{dataset}.sensor_readings_long`
  UNION DISTINCT
  SELECT native_sensor_id FROM `{project}.{dataset}.sensor_readings_daily`
) s
LEFT JOIN `{project}.{dataset}.sensor_id_map` m USING (native_sensor_id)
WHERE m.native_sensor_id IS NULL
"""


def main():
    ap = argparse.ArgumentParser(description="Seed identity rows into sensor_id_map")
    ap.add_argument('--project', required=True)
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--execute', action='store_true', help='Execute the insert; otherwise print SQL')
    args = ap.parse_args()

    sql = SQL.format(project=args.project, dataset=args.dataset)
    if not args.execute:
        print(sql)
        return

    client = bigquery.Client(project=args.project)
    job = client.query(sql)
    job.result()
    print(f"Seed completed. Affected rows: {job.num_dml_affected_rows}")


if __name__ == '__main__':
    main()
