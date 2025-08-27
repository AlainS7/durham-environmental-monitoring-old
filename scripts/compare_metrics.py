#!/usr/bin/env python3
"""Compare collected Parquet columns with expected metrics manifest.

Usage:
  python scripts/compare_metrics.py --manifest config/metrics_manifest.json \
     --inspection reports/inspections/wu_2025-08-20.json --source WU

Outputs JSON summary to stdout and optional file.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, Any

RESERVED_NON_METRIC = {"timestamp", "native_sensor_id", "device_id", "stationID", "obsTimeUtc", "qc_status", "latitude", "longitude"}


def load_manifest(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def load_inspection(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def compare(manifest: Dict[str, Any], inspection: Dict[str, Any], source: str) -> Dict[str, Any]:
    src_info = manifest[source]
    expected = set(src_info["metrics"].keys())
    cols = set(inspection["columns"]) - RESERVED_NON_METRIC
    missing = sorted(expected - cols)
    extra = sorted(cols - expected)
    coverage_pct = (1 - len(missing)/len(expected)) * 100 if expected else 100.0
    return {
        "source": source,
        "row_count": inspection.get("row_count"),
        "expected_metric_count": len(expected),
        "present_metric_count": len(expected) - len(missing),
        "coverage_pct": coverage_pct,
        "missing_metrics": missing,
        "extra_metrics": extra,
        "all_columns": sorted(cols)
    }


def main():
    ap = argparse.ArgumentParser(description="Compare metrics vs manifest")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--inspection", required=True, help="Inspection JSON produced by inspect_gcs_parquet.py")
    ap.add_argument("--source", required=True, choices=["WU", "TSI"]) 
    ap.add_argument("--out", help="Optional output JSON path")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    inspection = load_inspection(args.inspection)
    summary = compare(manifest, inspection, args.source)
    print(json.dumps(summary, indent=2))
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
