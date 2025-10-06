-- Source-specific enriched views for Looker Studio
-- These views properly separate TSI air quality sensors from Weather Underground stations
-- and include ALL metrics measured by each source (not just a subset).

-- Helper view: Identify TSI sensors
-- TSI sensors are those that measure air quality metrics like pm2_5, pm10, etc.
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.tsi_sensor_list` AS
SELECT DISTINCT native_sensor_id
FROM `${PROJECT}.${DATASET}.sensor_readings_daily`
WHERE metric_name IN ('pm2_5', 'pm1_0', 'pm10')  -- TSI-specific air quality metrics
  AND samples > 0;  -- Must have actual data

-- Helper view: Identify Weather Underground sensors
-- WU sensors follow the KNCDURHA### pattern
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.wu_sensor_list` AS
SELECT DISTINCT native_sensor_id
FROM `${PROJECT}.${DATASET}.sensor_readings_daily`
WHERE native_sensor_id LIKE 'KNCDURHA%'
   OR native_sensor_id LIKE 'KNCDURHM%'  -- Additional WU patterns if any
   OR native_sensor_id IN (
     -- Explicitly list any WU stations that don't follow pattern
     SELECT DISTINCT native_sensor_id 
     FROM `${PROJECT}.${DATASET}.sensor_readings_daily`
     WHERE metric_name IN ('solar_radiation', 'wind_speed_avg', 'precip_total')
       AND samples > 0
       AND native_sensor_id NOT IN (SELECT native_sensor_id FROM `${PROJECT}.${DATASET}.tsi_sensor_list`)
   );

-- TSI Air Quality Sensors - Daily Enriched View
-- Contains: 27 TSI sensors with ALL their air quality metrics (~22 metrics)
-- Excludes: 0.0 placeholder values (only shows actual measurements)
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.tsi_daily_enriched` AS
SELECT
  d.day_ts,
  d.native_sensor_id,
  COALESCE(m.sensor_id, d.native_sensor_id) AS sensor_id,
  d.metric_name,
  -- Aliases for Looker compatibility
  d.metric_name AS metric,
  d.avg_value AS value,
  d.avg_value,
  d.min_value,
  d.max_value,
  d.samples,
  lc.latitude,
  lc.longitude,
  lc.geog,
  lc.status,
  lc.effective_date,
  'TSI' AS sensor_source,
  'Air Quality' AS sensor_category
FROM `${PROJECT}.${DATASET}.sensor_readings_daily` d
-- Only include TSI sensors
INNER JOIN `${PROJECT}.${DATASET}.tsi_sensor_list` tsi
  ON d.native_sensor_id = tsi.native_sensor_id
-- Add sensor ID mapping
LEFT JOIN `${PROJECT}.${DATASET}.sensor_id_map` m
  ON d.native_sensor_id = m.native_sensor_id
  AND (m.effective_start_date IS NULL OR DATE(d.day_ts) >= m.effective_start_date)
  AND (m.effective_end_date IS NULL OR DATE(d.day_ts) <= m.effective_end_date)
-- Add location data
LEFT JOIN `${PROJECT}.${DATASET}.sensor_location_current` lc
  ON d.native_sensor_id = lc.native_sensor_id
-- Only include actual measurements (exclude 0.0 placeholders)
WHERE d.samples > 0;

-- Weather Underground Stations - Daily Enriched View
-- Contains: 13 WU stations with ALL their weather metrics (~29 metrics)
-- Excludes: 0.0 placeholder values (only shows actual measurements)
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.wu_daily_enriched` AS
SELECT
  d.day_ts,
  d.native_sensor_id,
  COALESCE(m.sensor_id, d.native_sensor_id) AS sensor_id,
  d.metric_name,
  -- Aliases for Looker compatibility
  d.metric_name AS metric,
  d.avg_value AS value,
  d.avg_value,
  d.min_value,
  d.max_value,
  d.samples,
  lc.latitude,
  lc.longitude,
  lc.geog,
  lc.status,
  lc.effective_date,
  'WU' AS sensor_source,
  'Weather' AS sensor_category
FROM `${PROJECT}.${DATASET}.sensor_readings_daily` d
-- Only include WU sensors
INNER JOIN `${PROJECT}.${DATASET}.wu_sensor_list` wu
  ON d.native_sensor_id = wu.native_sensor_id
-- Add sensor ID mapping
LEFT JOIN `${PROJECT}.${DATASET}.sensor_id_map` m
  ON d.native_sensor_id = m.native_sensor_id
  AND (m.effective_start_date IS NULL OR DATE(d.day_ts) >= m.effective_start_date)
  AND (m.effective_end_date IS NULL OR DATE(d.day_ts) <= m.effective_end_date)
-- Add location data
LEFT JOIN `${PROJECT}.${DATASET}.sensor_location_current` lc
  ON d.native_sensor_id = lc.native_sensor_id
-- Only include actual measurements (exclude 0.0 placeholders)
WHERE d.samples > 0;

-- Combined view with source identification (optional - for cross-source analysis)
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.all_sensors_daily_enriched` AS
SELECT
  day_ts,
  native_sensor_id,
  sensor_id,
  metric_name,
  metric,
  value,
  avg_value,
  min_value,
  max_value,
  samples,
  latitude,
  longitude,
  geog,
  status,
  effective_date,
  sensor_source,
  sensor_category
FROM `${PROJECT}.${DATASET}.tsi_daily_enriched`
UNION ALL
SELECT
  day_ts,
  native_sensor_id,
  sensor_id,
  metric_name,
  metric,
  value,
  avg_value,
  min_value,
  max_value,
  samples,
  latitude,
  longitude,
  geog,
  status,
  effective_date,
  sensor_source,
  sensor_category
FROM `${PROJECT}.${DATASET}.wu_daily_enriched`;

-- Verification view: Sensor counts by source
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.sensor_source_summary` AS
SELECT
  sensor_source,
  sensor_category,
  COUNT(DISTINCT native_sensor_id) AS sensor_count,
  COUNT(DISTINCT metric_name) AS metric_count,
  MIN(day_ts) AS earliest_data,
  MAX(day_ts) AS latest_data,
  SUM(samples) AS total_samples
FROM `${PROJECT}.${DATASET}.all_sensors_daily_enriched`
GROUP BY sensor_source, sensor_category;
