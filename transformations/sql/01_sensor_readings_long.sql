-- Create or replace the long (tall) unified fact table from raw WU + TSI.
-- Reads from materialized native raw tables (partitioned by DATE(ts)).
-- Partition on DATE(timestamp) and cluster by native_sensor_id, metric_name.

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.sensor_readings_long`
PARTITION BY DATE(timestamp)
CLUSTER BY native_sensor_id, metric_name AS
WITH
  wu_src AS (
    SELECT
      ts AS timestamp,
      native_sensor_id,
      -- Location (WU typically exposes lat/lon; float copies were created at ingestion)
      COALESCE(CAST(lat_f AS FLOAT64), CAST(lat AS FLOAT64)) AS latitude,
      COALESCE(CAST(lon_f AS FLOAT64), CAST(lon AS FLOAT64)) AS longitude,
      -- Metrics subset (cast to FLOAT64) mapped from WU external schema
      CAST(temperature AS FLOAT64) AS temperature,
      CAST(humidity AS FLOAT64) AS humidity,
      CAST(precip_rate AS FLOAT64) AS precip_rate,
      CAST(precip_total AS FLOAT64) AS precip_total,
      CAST(wind_speed_avg AS FLOAT64) AS wind_speed_avg,
      CAST(wind_gust_avg AS FLOAT64) AS wind_gust_avg,
      CAST(wind_direction_avg AS FLOAT64) AS wind_direction_avg,
      CAST(solar_radiation AS FLOAT64) AS solar_radiation,
      CAST(uv_high AS FLOAT64) AS uv_high
    FROM `${PROJECT}.${DATASET}.wu_raw_materialized`
    WHERE ts IS NOT NULL
      AND DATE(ts) BETWEEN DATE_SUB(@proc_date, INTERVAL 0 DAY) AND @proc_date
  ),
  tsi_src AS (
    SELECT
      ts AS timestamp,
      native_sensor_id,
      -- Location (TSI typically exposes latitude/longitude; float copies exist)
      COALESCE(CAST(latitude_f AS FLOAT64), CAST(latitude AS FLOAT64)) AS latitude,
      COALESCE(CAST(longitude_f AS FLOAT64), CAST(longitude AS FLOAT64)) AS longitude,
      CAST(pm2_5 AS FLOAT64) AS pm2_5,
      CAST(humidity AS FLOAT64) AS humidity,
      CAST(temperature AS FLOAT64) AS temperature
    FROM `${PROJECT}.${DATASET}.tsi_raw_materialized`
    WHERE ts IS NOT NULL
      AND DATE(ts) BETWEEN DATE_SUB(@proc_date, INTERVAL 0 DAY) AND @proc_date
  ),
  wu_long AS (
    SELECT timestamp, native_sensor_id, latitude, longitude, metric_name, value FROM wu_src
    UNPIVOT (value FOR metric_name IN (temperature, humidity, precip_rate, precip_total, wind_speed_avg, wind_gust_avg, wind_direction_avg, solar_radiation, uv_high))
  ),
  tsi_long AS (
    SELECT timestamp, native_sensor_id, latitude, longitude, metric_name, value FROM tsi_src
    UNPIVOT (value FOR metric_name IN (pm2_5, humidity, temperature))
  )
SELECT timestamp, native_sensor_id, metric_name, value,
       latitude, longitude,
       -- Construct GEOGRAPHY point when both coords are present
       IF(latitude IS NULL OR longitude IS NULL, NULL, ST_GEOGPOINT(longitude, latitude)) AS geog
FROM wu_long
UNION ALL
SELECT timestamp, native_sensor_id, metric_name, value,
       latitude, longitude,
       IF(latitude IS NULL OR longitude IS NULL, NULL, ST_GEOGPOINT(longitude, latitude)) AS geog
FROM tsi_long;
