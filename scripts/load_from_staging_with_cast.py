#!/usr/bin/env python3
"""Load TSI data from staging tables with explicit type casting."""

import argparse
import datetime as dt
from google.cloud import bigquery


def daterange(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur = cur + dt.timedelta(days=1)


def load_from_staging(client: bigquery.Client, dataset: str, target_table: str, date: dt.date):
    """Load one day from staging table with explicit casting."""
    
    stage_table = f"tsi_raw_stage_{date.isoformat().replace('-', '')}"
    fq_stage = f"{client.project}.{dataset}.{stage_table}"
    fq_target = f"{client.project}.{dataset}.{target_table}"
    
    # Check if staging table exists
    try:
        client.get_table(fq_stage)
    except Exception:
        print(f"Skipping {date}: staging table not found")
        return
    
    # Delete existing data for this date
    delete_sql = f"DELETE FROM `{fq_target}` WHERE DATE(ts) = @d"
    job = client.query(delete_sql, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", date.isoformat())]
    ))
    job.result()
    
    # Insert with explicit casting
    # Handle null columns by using CAST(NULL AS type)
    insert_sql = f"""
    INSERT INTO `{fq_target}` (
      ts,
      cloud_account_id,
      native_sensor_id,
      timestamp,
      is_indoor,
      is_public,
      latitude,
      longitude,
      pm10,
      pm10_aqi,
      pm1_0,
      pm2_5,
      pm2_5_aqi,
      pm4_0,
      ncpm4_0,
      model,
      ncpm0_5,
      ncpm10,
      ncpm1_0,
      ncpm2_5,
      humidity,
      serial,
      temperature,
      tpsize,
      co2_ppm,
      co_ppm,
      baro_inhg,
      o3_ppb,
      no2_ppb,
      so2_ppb,
      ch2o_ppb,
      voc_mgm3,
      latitude_f,
      longitude_f
    )
    SELECT
      ts,
      CAST(cloud_account_id AS STRING),
      CAST(native_sensor_id AS STRING),
      timestamp,
      CAST(is_indoor AS BOOLEAN),
      CAST(is_public AS BOOLEAN),
      CAST(latitude AS FLOAT64),
      CAST(longitude AS FLOAT64),
      CAST(pm10 AS FLOAT64),
      CAST(pm10_aqi AS FLOAT64),
      CAST(pm1_0 AS FLOAT64),
      CAST(pm2_5 AS FLOAT64),
      CAST(pm2_5_aqi AS FLOAT64),
      CAST(IFNULL(pm4_0, NULL) AS FLOAT64),
      CAST(ncpm4_0 AS FLOAT64),
      CAST(model AS STRING),
      CAST(ncpm0_5 AS FLOAT64),
      CAST(ncpm10 AS FLOAT64),
      CAST(ncpm1_0 AS FLOAT64),
      CAST(ncpm2_5 AS FLOAT64),
      CAST(humidity AS FLOAT64),
      CAST(serial AS STRING),
      CAST(temperature AS FLOAT64),
      CAST(tpsize AS FLOAT64),
      CAST(co2_ppm AS FLOAT64),
      CAST(co_ppm AS FLOAT64),
      CAST(baro_inhg AS FLOAT64),
      CAST(o3_ppb AS FLOAT64),
      CAST(no2_ppb AS FLOAT64),
      CAST(so2_ppb AS FLOAT64),
      CAST(ch2o_ppb AS FLOAT64),
      CAST(voc_mgm3 AS FLOAT64),
      CAST(latitude_f AS FLOAT64),
      CAST(longitude_f AS FLOAT64)
    FROM `{fq_stage}`
    WHERE DATE(ts) = @d
    """
    
    try:
        job = client.query(insert_sql, job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", date.isoformat())]
        ))
        job.result()
        print(f"✓ Loaded {date}")
    except Exception as e:
        print(f"✗ Failed {date}: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--table", default="tsi_raw_materialized")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    
    client = bigquery.Client(project=args.project)
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    
    for date in daterange(start, end):
        load_from_staging(client, args.dataset, args.table, date)


if __name__ == "__main__":
    main()
