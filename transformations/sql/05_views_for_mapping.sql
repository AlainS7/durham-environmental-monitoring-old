-- Views to simplify mapping in Looker Studio.

-- Latest canonical position per sensor (by as_of_date)
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.sensor_canonical_latest` AS
SELECT AS VALUE x FROM (
  SELECT
    c.*,
    ROW_NUMBER() OVER (PARTITION BY c.native_sensor_id ORDER BY c.as_of_date DESC) AS rn
  FROM `${PROJECT}.${DATASET}.sensor_canonical_location` c
) x
WHERE x.rn = 1;

-- Daily enriched summaries with canonical positions
CREATE OR REPLACE VIEW `${PROJECT}.${DATASET}.sensor_readings_daily_enriched` AS
SELECT
  d.day_ts,
  d.native_sensor_id,
  d.metric_name,
  d.avg_value,
  d.min_value,
  d.max_value,
  d.samples,
  c.canonical_latitude AS latitude,
  c.canonical_longitude AS longitude,
  c.canonical_geog AS geog
FROM `${PROJECT}.${DATASET}.sensor_readings_daily` d
LEFT JOIN `${PROJECT}.${DATASET}.sensor_canonical_latest` c
  USING (native_sensor_id);
