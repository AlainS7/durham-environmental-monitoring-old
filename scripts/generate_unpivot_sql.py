#!/usr/bin/env python3
"""Generate BigQuery SQL to UNPIVOT staging tables using metrics manifest.

Example:
  python scripts/generate_unpivot_sql.py --manifest config/metrics_manifest.json \
     --date 2025-08-20 --dataset my_dataset --wu-table sensor_readings_wu_raw \
     --tsi-table sensor_readings_tsi_raw

Outputs SQL to stdout (optionally to a file) that:
  1. Creates temp CTEs for each source selecting expected columns (coalescing missing to NULL)
  2. UNPIVOTs each into (timestamp, native_sensor_id, metric_name, value)
  3. UNION ALL both sources

You can then JOIN to deployments/sensors_master to get deployment_fk prior to MERGE.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List

FLOAT_CAST_EXCLUDE = {"native_sensor_id", "timestamp"}


def load_manifest(path: str) -> dict:
    return json.loads(Path(path).read_text())


def build_source_cte(source: str, table: str, manifest: dict, date: str) -> str:
    info = manifest[source]
    metrics: List[str] = list(info["metrics"].keys())
    # Build safe select list (explicit columns)
    select_cols = [f"{info['timestamp_field']} AS timestamp", f"{info['native_id_field']} AS native_sensor_id"]
    for m in metrics:
        # Column may already match standardized name after load; wrap with safe cast
        if m in FLOAT_CAST_EXCLUDE:
            continue
        select_cols.append(f"CAST({m} AS FLOAT64) AS {m}")
    select_clause = ",\n        ".join(select_cols)
    # Filter by date partition (DATE(timestamp) = date)
    cte = f"{source.lower()}_src AS (\n  SELECT\n        {select_clause}\n  FROM `{table}`\n  WHERE DATE(timestamp) = DATE('{date}')\n)"
    return cte


def build_unpivot_block(source: str, manifest: dict) -> str:
    info = manifest[source]
    metrics: List[str] = list(info["metrics"].keys())
    metric_list = ",\n        ".join([f"`{m}`" for m in metrics])
    return f"{source.lower()}_long AS (\n  SELECT timestamp, native_sensor_id, metric_name, value FROM {source.lower()}_src\n  UNPIVOT (value FOR metric_name IN (\n        {metric_list}\n  ))\n)"


def build_union_sql(manifest: dict, wu_table: str, tsi_table: str, date: str) -> str:
    wu_cte = build_source_cte("WU", wu_table, manifest, date)
    tsi_cte = build_source_cte("TSI", tsi_table, manifest, date)
    wu_unpivot = build_unpivot_block("WU", manifest)
    tsi_unpivot = build_unpivot_block("TSI", manifest)
    sql = f"WITH\n{wu_cte},\n{tsi_cte},\n{wu_unpivot},\n{tsi_unpivot}\nSELECT * FROM wu_long UNION ALL SELECT * FROM tsi_long;"
    return sql


def main():
    ap = argparse.ArgumentParser(description="Generate UNPIVOT SQL from manifest")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--wu-table", required=True, help="Fully qualified WU raw table")
    ap.add_argument("--tsi-table", required=True, help="Fully qualified TSI raw table")
    ap.add_argument("--out", help="Optional output .sql path")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    sql = build_union_sql(manifest, args.wu_table, args.tsi_table, args.date)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(sql)
    print(sql)


if __name__ == "__main__":  # pragma: no cover
    main()
