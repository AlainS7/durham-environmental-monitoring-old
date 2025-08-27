#!/usr/bin/env python3
"""Inspect a Parquet file stored in GCS (or local path) and emit a JSON summary.

Usage:
  python scripts/inspect_gcs_parquet.py --uri gs://bucket/prefix/source=WU/agg=raw/dt=2025-08-20/WU-2025-08-20.parquet \
      --out reports/inspections/wu_2025-08-20.json

If the path is local (no gs:// prefix) it is read directly.
The summary includes:
  - columns list
  - dtypes
  - row_count
  - non_null_counts
  - basic numeric stats (min, max, mean) for up to N numeric columns

Requires GOOGLE_APPLICATION_CREDENTIALS or Workload Identity for GCS access.
"""
from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd

try:
    from google.cloud import storage  # type: ignore
except Exception:  # pragma: no cover
    storage = None

log = logging.getLogger("inspect_parquet")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _download_gcs(uri: str) -> Path:
    assert uri.startswith("gs://"), "_download_gcs only accepts gs:// URIs"
    if storage is None:
        raise RuntimeError("google-cloud-storage not installed")
    # Parse bucket and blob
    no_scheme = uri[len("gs://"):]
    bucket_name, _, blob_path = no_scheme.partition("/")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    if not blob.exists():
        raise FileNotFoundError(f"GCS object does not exist: {uri}")
    tmp_dir = Path("/tmp/parquet_inspect")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    local_path = tmp_dir / Path(blob_path).name
    blob.download_to_filename(str(local_path))
    return local_path


def inspect_parquet(uri: str, sample_numeric_limit: int = 40) -> Dict[str, Any]:
    if uri.startswith("gs://"):
        local = _download_gcs(uri)
    else:
        local = Path(uri)
    if not local.exists():
        raise FileNotFoundError(f"File not found: {local}")

    log.info(f"Reading Parquet file: {local}")
    df = pd.read_parquet(local)
    summary: Dict[str, Any] = {}
    summary["source_uri"] = uri
    summary["local_path"] = str(local)
    summary["row_count"] = len(df)
    summary["columns"] = list(df.columns)
    summary["dtypes"] = {c: str(t) for c, t in df.dtypes.items()}
    summary["non_null_counts"] = {c: int(df[c].notna().sum()) for c in df.columns}

    numeric_cols = df.select_dtypes(include="number").columns.tolist()[:sample_numeric_limit]
    stats: Dict[str, Dict[str, float]] = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        stats[col] = {
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
        }
    summary["numeric_stats"] = stats
    ts_cols = [c for c in df.columns if "time" in c.lower() or c == "timestamp"]
    ts_preview: Dict[str, Any] = {}
    for c in ts_cols:
        try:
            s = pd.to_datetime(df[c], errors="coerce")
            s = s.dropna()
            if s.empty:
                continue
            ts_preview[c] = {"min": s.min().isoformat(), "max": s.max().isoformat()}
        except Exception:
            pass
    summary["timestamp_preview"] = ts_preview
    return summary


def main():
    parser = argparse.ArgumentParser(description="Inspect a Parquet file from GCS or local path")
    parser.add_argument("--uri", required=True, help="gs:// or local path to parquet file")
    parser.add_argument("--out", required=False, help="Output JSON path (will create directories)")
    parser.add_argument("--print", action="store_true", help="Print JSON to stdout")
    args = parser.parse_args()

    summary = inspect_parquet(args.uri)
    out_path = None
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2))
        log.info(f"Wrote summary to {out_path}")
    if args.print or not args.out:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
