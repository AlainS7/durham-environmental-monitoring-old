-- Write freshness / row count metrics into a monitoring table.
-- Create table if missing.
CREATE TABLE IF NOT EXISTS `durham-weather-466502.sensors.ingestion_metrics` (
  run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  source STRING,
  latest_ts TIMESTAMP,
  row_count INT64
);

INSERT INTO `durham-weather-466502.sensors.ingestion_metrics` (source, latest_ts, row_count)
SELECT 'WU' as source,
       MAX(timestamp) AS latest_ts,
       COUNT(*) AS row_count
FROM `durham-weather-466502.sensors.wu_raw_materialized`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
UNION ALL
SELECT 'TSI', MAX(timestamp), COUNT(*)
FROM `durham-weather-466502.sensors.tsi_raw_materialized`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);
