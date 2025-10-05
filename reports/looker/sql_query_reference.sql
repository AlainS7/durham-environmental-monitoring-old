-- Durham Sensors: Looker Studio SQL Query Reference
-- Use these queries directly in Looker Studio custom queries if needed
-- Most of the time, using the enriched view directly is sufficient!

-- ============================================================================
-- BASIC QUERIES - Use these as starting points
-- ============================================================================

-- 1. Latest readings for all active sensors
SELECT 
  day_ts,
  native_sensor_id,
  metric_name,
  avg_value,
  min_value,
  max_value,
  samples,
  latitude,
  longitude
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND (status = 'active' OR status IS NULL)
ORDER BY day_ts DESC, native_sensor_id;

-- 2. Sensor summary (last 7 days)
SELECT 
  native_sensor_id,
  status,
  COUNT(DISTINCT metric_name) as metrics_count,
  COUNT(DISTINCT DATE(day_ts)) as days_active,
  MAX(day_ts) as last_reading,
  AVG(samples) as avg_samples_per_day
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY native_sensor_id, status
ORDER BY last_reading DESC;

-- 3. Temperature trends (30 days)
SELECT 
  DATE(day_ts) as date,
  native_sensor_id,
  AVG(avg_value) as avg_temp,
  MIN(min_value) as min_temp,
  MAX(max_value) as max_temp
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  metric_name = 'temperature_c'
  AND day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY date, native_sensor_id
ORDER BY date DESC;

-- ============================================================================
-- DATA QUALITY QUERIES
-- ============================================================================

-- 4. Sensors with low sample counts (potential issues)
SELECT 
  native_sensor_id,
  metric_name,
  DATE(day_ts) as date,
  samples,
  avg_value
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  samples < 10
  AND day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (status = 'active' OR status IS NULL)
ORDER BY samples ASC, date DESC;

-- 5. Data coverage by sensor (last 30 days)
SELECT 
  native_sensor_id,
  COUNT(DISTINCT DATE(day_ts)) as days_with_data,
  COUNT(DISTINCT metric_name) as metrics_reported,
  ROUND(COUNT(DISTINCT DATE(day_ts)) / 30.0 * 100, 1) as coverage_percent
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY native_sensor_id
ORDER BY coverage_percent DESC;

-- 6. Missing data dates by sensor
WITH date_spine AS (
  SELECT DATE_ADD(DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY), INTERVAL day DAY) as date
  FROM UNNEST(GENERATE_ARRAY(0, 30)) as day
),
sensor_list AS (
  SELECT DISTINCT native_sensor_id
  FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
  WHERE status = 'active' OR status IS NULL
)
SELECT 
  s.native_sensor_id,
  d.date,
  CASE WHEN e.day_ts IS NULL THEN 'MISSING' ELSE 'PRESENT' END as data_status
FROM sensor_list s
CROSS JOIN date_spine d
LEFT JOIN `durham-weather-466502.sensors.sensor_readings_daily_enriched` e
  ON s.native_sensor_id = e.native_sensor_id 
  AND DATE(e.day_ts) = d.date
  AND e.metric_name = 'temperature_c'
WHERE CASE WHEN e.day_ts IS NULL THEN 'MISSING' ELSE 'PRESENT' END = 'MISSING'
ORDER BY s.native_sensor_id, d.date;

-- ============================================================================
-- ENVIRONMENTAL ANALYSIS QUERIES
-- ============================================================================

-- 7. Air quality summary (PM2.5)
SELECT 
  DATE(day_ts) as date,
  AVG(avg_value) as avg_pm25,
  MIN(min_value) as min_pm25,
  MAX(max_value) as max_pm25,
  CASE 
    WHEN AVG(avg_value) <= 12 THEN 'Good'
    WHEN AVG(avg_value) <= 35 THEN 'Moderate'
    WHEN AVG(avg_value) <= 55 THEN 'Unhealthy for Sensitive'
    ELSE 'Unhealthy'
  END as aqi_category,
  COUNT(DISTINCT native_sensor_id) as sensors_reporting
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  metric_name = 'pm25'
  AND day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY date
ORDER BY date DESC;

-- 8. Temperature and humidity correlation
SELECT 
  DATE(day_ts) as date,
  native_sensor_id,
  MAX(CASE WHEN metric_name = 'temperature_c' THEN avg_value END) as temperature,
  MAX(CASE WHEN metric_name = 'humidity' THEN avg_value END) as humidity,
  MAX(CASE WHEN metric_name = 'pm25' THEN avg_value END) as pm25
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY date, native_sensor_id
HAVING temperature IS NOT NULL AND humidity IS NOT NULL
ORDER BY date DESC;

-- 9. Extreme weather events
SELECT 
  DATE(day_ts) as date,
  native_sensor_id,
  metric_name,
  avg_value,
  min_value,
  max_value,
  CASE 
    WHEN metric_name = 'temperature_c' AND max_value >= 35 THEN 'Extreme Heat'
    WHEN metric_name = 'temperature_c' AND min_value <= 0 THEN 'Freezing'
    WHEN metric_name = 'humidity' AND avg_value >= 90 THEN 'Very Humid'
    WHEN metric_name = 'pm25' AND avg_value >= 55 THEN 'Unhealthy Air'
    WHEN metric_name = 'uv_high' AND max_value >= 8 THEN 'Very High UV'
  END as event_type
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  AND (status = 'active' OR status IS NULL)
  AND (
    (metric_name = 'temperature_c' AND (max_value >= 35 OR min_value <= 0))
    OR (metric_name = 'humidity' AND avg_value >= 90)
    OR (metric_name = 'pm25' AND avg_value >= 55)
    OR (metric_name = 'uv_high' AND max_value >= 8)
  )
ORDER BY date DESC, native_sensor_id;

-- ============================================================================
-- COMPARATIVE ANALYSIS QUERIES
-- ============================================================================

-- 10. Sensor rankings by metric (last 7 days avg)
SELECT 
  native_sensor_id,
  metric_name,
  AVG(avg_value) as avg_value,
  RANK() OVER (PARTITION BY metric_name ORDER BY AVG(avg_value) DESC) as sensor_rank
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY native_sensor_id, metric_name
ORDER BY metric_name, sensor_rank;

-- 11. Week-over-week metric changes
WITH current_week AS (
  SELECT 
    native_sensor_id,
    metric_name,
    AVG(avg_value) as current_avg
  FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
  WHERE day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY native_sensor_id, metric_name
),
previous_week AS (
  SELECT 
    native_sensor_id,
    metric_name,
    AVG(avg_value) as previous_avg
  FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
  WHERE day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
    AND day_ts < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY native_sensor_id, metric_name
)
SELECT 
  c.native_sensor_id,
  c.metric_name,
  c.current_avg,
  p.previous_avg,
  ROUND(c.current_avg - p.previous_avg, 2) as change,
  ROUND((c.current_avg - p.previous_avg) / p.previous_avg * 100, 1) as percent_change
FROM current_week c
LEFT JOIN previous_week p USING (native_sensor_id, metric_name)
WHERE p.previous_avg IS NOT NULL
ORDER BY ABS(percent_change) DESC;

-- ============================================================================
-- GEOGRAPHIC ANALYSIS QUERIES
-- ============================================================================

-- 12. Latest values with location (for mapping)
SELECT 
  native_sensor_id,
  metric_name,
  avg_value,
  latitude,
  longitude,
  geog,
  day_ts,
  status
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE day_ts = (SELECT MAX(day_ts) FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`)
  AND (status = 'active' OR status IS NULL)
ORDER BY native_sensor_id, metric_name;

-- 13. Spatial summary by area (example with clustering)
SELECT 
  ROUND(latitude, 2) as lat_cluster,
  ROUND(longitude, 2) as lng_cluster,
  COUNT(DISTINCT native_sensor_id) as sensors_in_area,
  AVG(CASE WHEN metric_name = 'temperature_c' THEN avg_value END) as avg_temperature,
  AVG(CASE WHEN metric_name = 'pm25' THEN avg_value END) as avg_pm25
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY lat_cluster, lng_cluster
ORDER BY sensors_in_area DESC;

-- ============================================================================
-- AGGREGATION EXAMPLES FOR LOOKER STUDIO
-- ============================================================================

-- 14. Pivot-style metric matrix (for tables)
SELECT 
  native_sensor_id,
  MAX(CASE WHEN metric_name = 'temperature_c' THEN avg_value END) as temperature_c,
  MAX(CASE WHEN metric_name = 'humidity' THEN avg_value END) as humidity,
  MAX(CASE WHEN metric_name = 'pm25' THEN avg_value END) as pm25,
  MAX(CASE WHEN metric_name = 'uv_high' THEN avg_value END) as uv_high,
  MAX(CASE WHEN metric_name = 'solar_radiation' THEN avg_value END) as solar_radiation,
  MAX(day_ts) as last_reading
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY native_sensor_id
ORDER BY native_sensor_id;

-- 15. Time-of-week patterns (day of week analysis)
SELECT 
  EXTRACT(DAYOFWEEK FROM day_ts) as day_of_week,
  CASE EXTRACT(DAYOFWEEK FROM day_ts)
    WHEN 1 THEN 'Sunday'
    WHEN 2 THEN 'Monday'
    WHEN 3 THEN 'Tuesday'
    WHEN 4 THEN 'Wednesday'
    WHEN 5 THEN 'Thursday'
    WHEN 6 THEN 'Friday'
    WHEN 7 THEN 'Saturday'
  END as day_name,
  metric_name,
  AVG(avg_value) as avg_value,
  STDDEV(avg_value) as std_dev
FROM `durham-weather-466502.sensors.sensor_readings_daily_enriched`
WHERE 
  day_ts >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND (status = 'active' OR status IS NULL)
GROUP BY day_of_week, day_name, metric_name
ORDER BY day_of_week, metric_name;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 
-- Best Practices:
-- 1. Always include date range filters (use last 30/60/90 days)
-- 2. Filter by status: (status = 'active' OR status IS NULL)
-- 3. Use native_sensor_id for grouping (it's the primary key)
-- 4. metric_name values: temperature_c, humidity, pm25, uv_high, solar_radiation
-- 5. Check 'samples' field for data quality (should be >= 10)
--
-- Performance Tips:
-- - Limit queries to specific date ranges
-- - Use metric_name filters when analyzing single metrics
-- - Aggregate before joining when possible
-- - The enriched view is already optimized - use it directly
--
-- In Looker Studio:
-- - These queries can be used as "Custom SQL" data sources
-- - But using the view directly with Looker's UI is usually better
-- - Reserve custom SQL for complex aggregations not possible in UI
