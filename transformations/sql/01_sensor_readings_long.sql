-- Create or replace the long (tall) unified fact table from raw WU + TSI
-- Requires raw tables already loaded: sensor_readings_wu_raw, sensor_readings_tsi_raw
-- Partition on DATE(timestamp) and cluster by native_sensor_id, metric_name.

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.sensor_readings_long`
PARTITION BY DATE(timestamp)
CLUSTER BY native_sensor_id, metric_name AS
WITH
  wu_src AS (
    SELECT
      obsTimeUtc AS timestamp,
      stationID AS native_sensor_id,
      -- Metrics from manifest subset (cast to FLOAT64)
      CAST(tempAvg AS FLOAT64) AS temperature,
      CAST(humidityAvg AS FLOAT64) AS humidity,
      CAST(precipRate AS FLOAT64) AS precip_rate,
      CAST(precipTotal AS FLOAT64) AS precip_total,
      CAST(windspeedAvg AS FLOAT64) AS wind_speed_avg,
      CAST(windgustAvg AS FLOAT64) AS wind_gust_avg,
      CAST(winddirAvg AS FLOAT64) AS wind_direction_avg,
      CAST(solarRadiationHigh AS FLOAT64) AS solar_radiation,
      CAST(uvHigh AS FLOAT64) AS uv_high
    FROM `${PROJECT}.${DATASET}.sensor_readings_wu_raw`
    WHERE timestamp IS NOT NULL
      AND DATE(obsTimeUtc) BETWEEN DATE_SUB(@proc_date, INTERVAL 0 DAY) AND @proc_date
  ),
  tsi_src AS (
    SELECT
      cloud_timestamp AS timestamp,
      device_id AS native_sensor_id,
      CAST(mcpm2x5 AS FLOAT64) AS pm2_5,
      CAST(rh AS FLOAT64) AS humidity,
      CAST(temperature AS FLOAT64) AS temperature
    FROM `${PROJECT}.${DATASET}.sensor_readings_tsi_raw`
    WHERE timestamp IS NOT NULL
      AND DATE(cloud_timestamp) BETWEEN DATE_SUB(@proc_date, INTERVAL 0 DAY) AND @proc_date
  ),
  wu_long AS (
    SELECT timestamp, native_sensor_id, metric_name, value FROM wu_src
    UNPIVOT (value FOR metric_name IN (temperature, humidity, precip_rate, precip_total, wind_speed_avg, wind_gust_avg, wind_direction_avg, solar_radiation, uv_high))
  ),
  tsi_long AS (
    SELECT timestamp, native_sensor_id, metric_name, value FROM tsi_src
    UNPIVOT (value FOR metric_name IN (pm2_5, humidity, temperature))
  )
SELECT * FROM wu_long
UNION ALL
SELECT * FROM tsi_long;
