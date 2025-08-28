#!/usr/bin/env python3
"""Check data freshness for sensor_readings table.

Exits non-zero if MAX(timestamp) is older than an allowed lag (days).

Example:
  python scripts/check_freshness.py \
    --project durham-weather-466502 --dataset sensors \
    --table sensor_readings --max-lag-days 1
"""
from __future__ import annotations
import argparse
import datetime as dt
import logging
import os
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("freshness")


def parse_args():
    p = argparse.ArgumentParser(description="Check MAX(timestamp) freshness")
    p.add_argument('--project', default=os.getenv('BQ_PROJECT'))
    p.add_argument('--dataset', required=True)
    p.add_argument('--table', default='sensor_readings')
    p.add_argument('--location', default=os.getenv('BQ_LOCATION', 'US'))
    p.add_argument('--max-lag-days', type=int, default=1, help='Allowed lag in days (default 1)')
    return p.parse_args()


def main():
    a = parse_args()
    client = bigquery.Client(project=a.project, location=a.location)
    fq = f"{client.project}.{a.dataset}.{a.table}"
    sql = f"SELECT MAX(timestamp) AS max_ts FROM `{fq}`"
    log.info("Querying MAX(timestamp) from %s", fq)
    rows = list(client.query(sql))
    if not rows or rows[0].get('max_ts') is None:
        log.error("No data in table %s", fq)
        raise SystemExit(2)
    max_ts = rows[0]['max_ts']
    now_utc = dt.datetime.utcnow().replace(tzinfo=max_ts.tzinfo)
    lag_days = (now_utc.date() - max_ts.date()).days
    log.info("max_ts=%s now=%s lag_days=%d", max_ts, now_utc, lag_days)
    if lag_days > a.max_lag_days:
        log.error("Freshness check failed: lag %d > allowed %d", lag_days, a.max_lag_days)
        raise SystemExit(1)
    log.info("Freshness OK (lag %d <= %d)", lag_days, a.max_lag_days)


if __name__ == '__main__':  # pragma: no cover
    main()
