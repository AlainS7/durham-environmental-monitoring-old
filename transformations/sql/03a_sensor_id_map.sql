-- Stable logical sensor ID mapping to native_sensor_id.
-- Allows optional date-bounded mappings to account for renames/replacements.

CREATE TABLE IF NOT EXISTS `${PROJECT}.${DATASET}.sensor_id_map` (
  sensor_id STRING NOT NULL,           -- stable logical ID used in BI
  native_sensor_id STRING NOT NULL,    -- physical/native identifier from sources
  effective_start_date DATE,           -- inclusive; NULL means since beginning
  effective_end_date DATE,             -- inclusive; NULL means open-ended
  source STRING,                       -- notes/source of mapping decision
  updated_at TIMESTAMP                 -- audit timestamp
);

-- Optional seed: identity mapping for any native ids observed in facts but not present yet
-- (Run manually if desired; commented to avoid implicit churn.)
-- INSERT INTO `${PROJECT}.${DATASET}.sensor_id_map` (sensor_id, native_sensor_id, source, updated_at)
-- SELECT DISTINCT native_sensor_id AS sensor_id, native_sensor_id, 'seed:identity', CURRENT_TIMESTAMP()
-- FROM `${PROJECT}.${DATASET}.sensor_readings_long` f
-- LEFT JOIN `${PROJECT}.${DATASET}.sensor_id_map` m USING (native_sensor_id)
-- WHERE m.native_sensor_id IS NULL;
