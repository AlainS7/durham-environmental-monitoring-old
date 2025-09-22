-- Static curated sensor location dimension.
-- Populate/maintain via scripts/manage_sensor_locations.py or manual SQL.

CREATE TABLE IF NOT EXISTS `${PROJECT}.${DATASET}.sensor_location_dim` (
  native_sensor_id STRING NOT NULL,
  latitude FLOAT64,
  longitude FLOAT64,
  geog GEOGRAPHY,
  notes STRING,
  updated_at TIMESTAMP
);

-- Optionally backfill rows with current canonical for convenience (no-op when dim already curated).
-- Uncomment the block below if you want an initial seed using canonical positions for missing sensors.
-- INSERT INTO `${PROJECT}.${DATASET}.sensor_location_dim` (native_sensor_id, latitude, longitude, geog, notes, updated_at)
-- SELECT
--   c.native_sensor_id,
--   c.canonical_latitude,
--   c.canonical_longitude,
--   c.canonical_geog,
--   'seeded from canonical',
--   CURRENT_TIMESTAMP()
-- FROM `${PROJECT}.${DATASET}.sensor_canonical_latest` c
-- LEFT JOIN `${PROJECT}.${DATASET}.sensor_location_dim` d USING (native_sensor_id)
-- WHERE d.native_sensor_id IS NULL;
