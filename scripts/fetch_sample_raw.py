#!/usr/bin/env python3
"""Fetch a raw sample from WU or TSI APIs for a single date and emit diagnostics.

Goals:
 - Bypass full daily collection pipeline to quickly inspect *raw* API payloads
 - Show validation outcomes (counts, columns, non-null metrics) using existing Pydantic models
 - Allow limiting to a subset of stations/devices
 - Output optional JSON dumps (raw + validated) for offline diffing

Usage examples:
  python scripts/fetch_sample_raw.py --source WU --date 2025-08-20 --stations STATIONID1 STATIONID2 \
      --endpoint-strategy hourly --raw-out /tmp/wu_raw.json --validated-out /tmp/wu_validated.parquet

  python scripts/fetch_sample_raw.py --source TSI --date 2025-08-20 --devices DEVICE123 \
      --raw-out /tmp/tsi_raw.json --validated-out /tmp/tsi_validated.parquet

Environment variables for GCP credentials (e.g., GOOGLE_APPLICATION_CREDENTIALS)
must be set for the script to load secrets via app_config.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd

# Ensure repository root is on sys.path when running as a script (e.g. `python scripts/fetch_sample_raw.py`)
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Reuse existing clients & models (must follow sys.path adjustment above)
from src.config.app_config import app_config  # noqa: E402
from src.data_collection.clients.wu_client import WUClient, EndpointStrategy  # noqa: E402
from src.data_collection.clients.tsi_client import TSIClient  # noqa: E402
from src.utils.config_loader import get_wu_stations, get_tsi_devices  # noqa: E402

log = logging.getLogger("fetch_sample_raw")

# ---------- Helpers ----------

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def summarize_df(df: pd.DataFrame, id_field: str, ts_field: str) -> dict:
    if df.empty:
        return {"rows": 0, "columns": [], "non_null_counts": {}, "id_count": 0}
    # Ensure timestamp is datetime
    if ts_field in df.columns and not pd.api.types.is_datetime64_any_dtype(df[ts_field]):
        df[ts_field] = pd.to_datetime(df[ts_field], errors='coerce')

    non_null = df.notna().sum().to_dict()

    # Determine expected frequency & build expected index for coverage calculations
    freq = None
    expected_count = None
    missing_slots: list[str] = []
    if ts_field in df.columns:
        ts_min = df[ts_field].min()
        ts_max = df[ts_field].max()
        if pd.isna(ts_min) or pd.isna(ts_max):
            freq = None
        else:
            # Heuristic: if median diff < 30 min assume 15min cadence else hourly
            diffs = df[ts_field].sort_values().diff().dropna()
            if not diffs.empty:
                median_diff = diffs.median()
                # Convert median diff to seconds for comparison to threshold (1200s = 20m)
                median_seconds = getattr(median_diff, 'total_seconds', lambda: float(median_diff))()
                if median_seconds <= 20 * 60:
                    freq = '15T'
                else:
                    freq = 'H'
            if freq:
                full_range = pd.date_range(start=ts_min.floor(freq), end=ts_max.ceil(freq), freq=freq)
                expected_count = len(full_range)
                present = set(df[ts_field].dt.floor(freq))
                missing = [t.isoformat() for t in full_range if t not in present]
                # Limit to first 25 to keep output manageable
                if len(missing) > 25:
                    missing_slots = missing[:25] + [f"... (+{len(missing)-25} more)"]
                else:
                    missing_slots = missing

    # Metric coverage percentage (excluding id & timestamp like fields)
    coverage_pct = {}
    row_count = len(df)
    for col, count in non_null.items():
        if col in {id_field, ts_field}:
            continue
        coverage_pct[col] = round((count / row_count) * 100, 2) if row_count else 0.0

    return {
        "rows": row_count,
        "expected_rows": expected_count,
        "columns": list(df.columns),
        "non_null_counts": non_null,
        "coverage_pct": coverage_pct,
        "id_count": df[id_field].nunique() if id_field in df.columns else None,
        "time_min": df[ts_field].min().isoformat() if ts_field in df.columns else None,
        "time_max": df[ts_field].max().isoformat() if ts_field in df.columns else None,
        "missing_time_slots": missing_slots,
        "inferred_freq": freq
    }


async def fetch_wu(date: str, stations_filter: Optional[List[str]], endpoint_strategy: str) -> Tuple[pd.DataFrame, list]:
    api_key = app_config.wu_api_config.get("api_key")
    if not api_key:
        raise SystemExit("WU API key not found in app_config. Ensure GCP secrets are loaded.")
    try:
        strat = EndpointStrategy(endpoint_strategy.lower())
    except ValueError:
        raise SystemExit(f"Invalid endpoint strategy {endpoint_strategy}; choose from {[e.value for e in EndpointStrategy]}")

    stations = get_wu_stations()
    if stations_filter:
        station_ids = set(stations_filter)
        stations = [s for s in stations if s.get('stationId') in station_ids]
        if not stations:
            raise SystemExit("No matching stations after filter")

    # Monkeypatch filtered stations into client instance
    async with WUClient(api_key=api_key, endpoint_strategy=strat) as client:  # type: ignore
        client.stations = stations
        df = await client.fetch_data(date, date, aggregate=False)
        # We want raw validation outputs; client already removed imperial block
        raw_payloads = []  # placeholder if future: expose pre-validated
        return df, raw_payloads


async def fetch_tsi(date: str, devices_filter: Optional[List[str]]) -> Tuple[pd.DataFrame, list]:
    cfg = app_config.tsi_api_config
    client_id = cfg.get("client_id")
    client_secret = cfg.get("client_secret")
    auth_url = cfg.get("auth_url")
    if not all([client_id, client_secret, auth_url]):
        raise SystemExit("TSI credentials not found in app_config. Ensure GCP secrets are loaded.")

    devices = get_tsi_devices()
    if devices_filter:
        device_ids = set(devices_filter)
        devices = [d for d in devices if d in device_ids]
        if not devices:
            raise SystemExit("No matching devices after filter")

    async with TSIClient(client_id=client_id, client_secret=client_secret, auth_url=auth_url) as client:  # type: ignore
        client.device_ids = devices
        df = await client.fetch_data(date, date, aggregate=False)
        raw_payloads = []
        return df, raw_payloads


async def main():
    parser = argparse.ArgumentParser(description="Fetch raw sample day from source API for diagnostics")
    parser.add_argument('--source', choices=['WU', 'TSI'], required=True)
    parser.add_argument('--date', required=True, help='Date (YYYY-MM-DD) to fetch (single day)')
    parser.add_argument('--stations', nargs='*', help='Subset of WU station IDs')
    parser.add_argument('--devices', nargs='*', help='Subset of TSI device IDs')
    parser.add_argument('--endpoint-strategy', default='hourly', help='WU endpoint strategy (hourly|all|multiday)')
    parser.add_argument('--raw-out', help='Path to write raw JSON payload (if available)')
    parser.add_argument('--validated-out', help='Path to write validated DataFrame (parquet)')
    parser.add_argument('--verbose', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.source == 'WU':
        df, raw_payloads = await fetch_wu(args.date, args.stations, args.endpoint_strategy)
        summary = summarize_df(df, 'stationID', 'obsTimeUtc')
    else:
        df, raw_payloads = await fetch_tsi(args.date, args.devices)
        summary = summarize_df(df, 'device_id', 'timestamp')

    print("SUMMARY:\n" + json.dumps(summary, indent=2))

    if args.raw_out and raw_payloads:
        Path(args.raw_out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.raw_out, 'w') as f:
            json.dump(raw_payloads, f, indent=2)
        log.info(f"Wrote raw payloads to {args.raw_out}")
    elif args.raw_out:
        log.info("No separate raw payloads available (client does not expose pre-validation list yet).")

    if args.validated_out:
        Path(args.validated_out).parent.mkdir(parents=True, exist_ok=True)
        if not df.empty:
            df.to_parquet(args.validated_out, index=False)
            log.info(f"Wrote validated DataFrame to {args.validated_out}")
        else:
            log.warning("Validated DataFrame empty; nothing written.")

if __name__ == '__main__':
    asyncio.run(main())
