#!/usr/bin/env python3
"""Helper to manage curated sensor locations in BigQuery.

Usage examples:
  # Upsert a single sensor location
  python scripts/manage_sensor_locations.py \
    --project $BQ_PROJECT --dataset sensors \
    --sensor-id AA-123 \
    --latitude 35.9940 --longitude -78.8986 \
    --notes "Pinned to building centroid"

  # Seed missing sensors from current canonical (for convenience)
  python scripts/manage_sensor_locations.py \
    --project $BQ_PROJECT --dataset sensors --seed-from-canonical
"""
from __future__ import annotations

import argparse
from google.cloud import bigquery


def upsert_location(client: bigquery.Client, dataset: str, sensor_id: str, lat: float, lon: float, notes: str | None):
    sql = f"""
    MERGE `{client.project}.{dataset}.sensor_location_dim` T
    USING (
      SELECT @sid AS native_sensor_id,
             @lat AS latitude,
             @lon AS longitude,
             ST_GEOGPOINT(@lon, @lat) AS geog,
             'active' AS status,
             CURRENT_DATE() AS effective_date,
             @notes AS notes,
             CURRENT_TIMESTAMP() AS updated_at
    ) S
    ON T.native_sensor_id = S.native_sensor_id
    WHEN MATCHED THEN
      UPDATE SET latitude = S.latitude,
                 longitude = S.longitude,
                 geog = S.geog,
                 notes = S.notes,
                 -- keep existing status/effective_date if already set
                 status = COALESCE(T.status, S.status),
                 effective_date = COALESCE(T.effective_date, S.effective_date),
                 updated_at = S.updated_at
    WHEN NOT MATCHED THEN
      INSERT (native_sensor_id, latitude, longitude, geog, status, effective_date, notes, updated_at)
      VALUES (S.native_sensor_id, S.latitude, S.longitude, S.geog, S.status, S.effective_date, S.notes, S.updated_at)
    """
    job = client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("sid", "STRING", sensor_id),
        bigquery.ScalarQueryParameter("lat", "FLOAT64", lat),
        bigquery.ScalarQueryParameter("lon", "FLOAT64", lon),
        bigquery.ScalarQueryParameter("notes", "STRING", notes),
    ]))
    job.result()


def seed_from_canonical(client: bigquery.Client, dataset: str):
    sql = f"""
    INSERT INTO `{client.project}.{dataset}.sensor_location_dim` (native_sensor_id, latitude, longitude, geog, notes, updated_at)
    SELECT
      c.native_sensor_id,
      c.canonical_latitude,
      c.canonical_longitude,
      c.canonical_geog,
      'seeded from canonical',
      CURRENT_TIMESTAMP()
    FROM `{client.project}.{dataset}.sensor_canonical_latest` c
    LEFT JOIN `{client.project}.{dataset}.sensor_location_dim` d USING (native_sensor_id)
    WHERE d.native_sensor_id IS NULL
    """
    job = client.query(sql)
    job.result()


def main():
    ap = argparse.ArgumentParser(description="Manage curated sensor locations in BigQuery")
    ap.add_argument("--project", required=False, help="GCP project (defaults to ADC)")
    ap.add_argument("--dataset", required=True, help="BigQuery dataset")
    ap.add_argument("--sensor-id", help="native_sensor_id to upsert")
    ap.add_argument("--latitude", type=float, help="Latitude for curated location")
    ap.add_argument("--longitude", type=float, help="Longitude for curated location")
    ap.add_argument("--notes", default=None, help="Optional notes/justification")
    ap.add_argument("--seed-from-canonical", action="store_true", help="Seed missing sensors from canonical positions")
    args = ap.parse_args()

    client = bigquery.Client(project=args.project or None)

    if args.seed_from_canonical:
        seed_from_canonical(client, args.dataset)
        print("Seeded missing sensors from canonical positions.")
        return

    if not (args.sensor_id and args.latitude is not None and args.longitude is not None):
        raise SystemExit("For upsert, provide --sensor-id, --latitude, and --longitude (or use --seed-from-canonical)")

    upsert_location(client, args.dataset, args.sensor_id, args.latitude, args.longitude, args.notes)
    print(f"Upserted curated location for {args.sensor_id}.")


if __name__ == "__main__":
    main()
