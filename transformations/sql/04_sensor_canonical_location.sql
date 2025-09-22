-- Compute a per-sensor canonical location to stabilize mapping when minor jitter occurs.
-- Strategy:
--  - Consider the last 90 days up to @proc_date
--  - For each sensor, derive daily distinct rounded positions (ROUND to 5 decimals ~1m)
--  - Choose the most frequent rounded position (mode); tie-breaker = most recent day seen
--  - Output canonical_latitude/longitude and a GEOGRAPHY point

CREATE OR REPLACE TABLE `${PROJECT}.${DATASET}.sensor_canonical_location`
CLUSTER BY native_sensor_id AS
WITH windowed AS (
  SELECT native_sensor_id, timestamp, latitude, longitude
  FROM `${PROJECT}.${DATASET}.sensor_readings_long`
  WHERE DATE(timestamp) BETWEEN DATE_SUB(@proc_date, INTERVAL 89 DAY) AND @proc_date
    AND latitude IS NOT NULL AND longitude IS NOT NULL
),
daily_positions AS (
  SELECT
    native_sensor_id,
    DATE(timestamp) AS day,
    ROUND(latitude, 5) AS lat_r,
    ROUND(longitude, 5) AS lon_r
  FROM windowed
  GROUP BY 1,2,3,4
),
coord_stats AS (
  SELECT
    native_sensor_id,
    lat_r,
    lon_r,
    COUNT(*) AS days_count,
    MAX(day) AS last_day
  FROM daily_positions
  GROUP BY 1,2,3
),
mode_coord AS (
  SELECT native_sensor_id, lat_r, lon_r, days_count, last_day
  FROM (
    SELECT
      native_sensor_id, lat_r, lon_r, days_count, last_day,
      ROW_NUMBER() OVER (
        PARTITION BY native_sensor_id
        ORDER BY days_count DESC, last_day DESC
      ) AS rn
    FROM coord_stats
  )
  WHERE rn = 1
),
sensor_window_stats AS (
  SELECT
    native_sensor_id,
    COUNT(DISTINCT day) AS days_observed,
    COUNT(DISTINCT CONCAT(CAST(lat_r AS STRING), ',', CAST(lon_r AS STRING))) AS distinct_locations
  FROM daily_positions
  GROUP BY 1
)
SELECT
  m.native_sensor_id,
  m.lat_r AS canonical_latitude,
  m.lon_r AS canonical_longitude,
  ST_GEOGPOINT(m.lon_r, m.lat_r) AS canonical_geog,
  @proc_date AS as_of_date,
  s.days_observed,
  s.distinct_locations,
  m.days_count AS coord_mode_count,
  m.last_day AS coord_mode_last_day
FROM mode_coord m
LEFT JOIN sensor_window_stats s USING (native_sensor_id);
