-- Hourly summary aggregation from long fact table.
-- Creates/refreshes partition for a specific process date (yesterday typically)
CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.sensor_readings_hourly`
PARTITION BY DATE(hour_ts)
CLUSTER BY native_sensor_id, metric_name AS
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS hour_ts,
  native_sensor_id,
  metric_name,
  AVG(value) AS avg_value,
  MIN(value) AS min_value,
  MAX(value) AS max_value,
  COUNT(*) AS samples
FROM `${PROJECT}.${DATASET}.sensor_readings_long`
WHERE DATE(timestamp) = @proc_date
GROUP BY 1,2,3;
