-- Daily summary aggregation from long fact table.
CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.sensor_readings_daily`
PARTITION BY DATE(day_ts)
CLUSTER BY native_sensor_id, metric_name AS
SELECT
  TIMESTAMP_TRUNC(timestamp, DAY) AS day_ts,
  native_sensor_id,
  metric_name,
  ANY_VALUE(latitude) AS latitude,
  ANY_VALUE(longitude) AS longitude,
  ANY_VALUE(geog) AS geog,
  AVG(value) AS avg_value,
  MIN(value) AS min_value,
  MAX(value) AS max_value,
  COUNT(*) AS samples
FROM `${PROJECT}.${DATASET}.sensor_readings_long`
WHERE DATE(timestamp) BETWEEN DATE_SUB(@proc_date, INTERVAL 6 DAY) AND @proc_date
GROUP BY 1,2,3;
