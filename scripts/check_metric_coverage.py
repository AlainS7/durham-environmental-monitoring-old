#!/usr/bin/env python3
"""Check metric coverage in sensor_readings_long vs manifest for a date.
Exits non-zero if coverage < threshold.

Usage:
  python scripts/check_metric_coverage.py --project p --dataset sensors --date 2025-08-26 --manifest config/metrics_manifest.json --threshold 0.9
"""
from __future__ import annotations
import argparse
import json
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None
from pathlib import Path
from typing import Dict, Set
from google.cloud import bigquery

# Columns that shouldn't count as metrics
NON_METRIC = {"native_sensor_id", "timestamp"}


def load_manifest(path: str) -> Dict[str, Set[str]]:
    data = json.loads(Path(path).read_text())
    return {k: set(v['metrics'].keys()) for k,v in data.items()}


def fetch_present_metrics(client: bigquery.Client, dataset: str, date: str) -> Dict[str, Set[str]]:
    # Determine presence per source by scanning raw tables (faster than long union if raw wide exists)
    present: Dict[str, Set[str]] = {}
    for src in ["wu", "tsi"]:
        table_id = f"{dataset}.sensor_readings_{src}_raw"
        # INFORMATION_SCHEMA to get columns quickly
        cols = client.get_table(table_id).schema
        metrics = {c.name for c in cols if c.name not in NON_METRIC and c.field_type != 'RECORD'}
        present[src.upper()] = metrics
    return present


def fetch_long_metrics(client: bigquery.Client, project: str, dataset: str, date: str) -> Set[str]:
    fq = f"{project}.{dataset}.sensor_readings_long"
    q = f"SELECT DISTINCT metric_name FROM `{fq}` WHERE DATE(timestamp)=@d"
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('d','DATE',date)])
    rows = client.query(q, job_config=cfg).result()
    return {r.metric_name for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--dataset', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--threshold', type=float, default=None, help='Minimum fraction of manifest metrics that must appear (overrides config)')
    ap.add_argument('--config', help='Optional YAML config file (default config/data_quality.yaml)')
    args = ap.parse_args()

    client = bigquery.Client(project=args.project)
    manifest = load_manifest(args.manifest)
    # Load config threshold if not explicitly set
    threshold = args.threshold
    if threshold is None:
        cfg_path = args.config or (Path('config/data_quality.yaml') if Path('config/data_quality.yaml').exists() else None)
        if cfg_path and yaml:
            try:
                data = yaml.safe_load(open(cfg_path)) or {}
                threshold = float(data.get('metric_coverage', {}).get('min_fraction', 0.9))
            except Exception:  # pragma: no cover
                threshold = 0.9
        else:
            threshold = 0.9
    long_metrics = fetch_long_metrics(client, args.project, args.dataset, args.date)

    expected_all = set().union(*manifest.values())
    present = long_metrics
    coverage = len(present & expected_all) / len(expected_all) if expected_all else 1.0

    result = {
        'date': args.date,
        'expected_metric_count': len(expected_all),
        'present_metric_count': len(present & expected_all),
        'coverage_fraction': coverage,
        'threshold': threshold,
        'missing_metrics': sorted(list(expected_all - present)),
    }
    print(json.dumps(result, indent=2))
    if coverage < threshold:
        raise SystemExit(f"Coverage {coverage:.2%} below threshold {threshold:.2%}")

if __name__ == '__main__':
    main()
