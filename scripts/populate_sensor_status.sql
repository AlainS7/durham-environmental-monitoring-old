-- Populate sensor_location_dim with status for all active sensors
-- Run this once to set all current sensors to 'active' status

MERGE INTO `durham-weather-466502.sensors.sensor_location_dim` AS target
USING (
  SELECT
    native_sensor_id,
    'active' AS status,
    CURRENT_DATE() AS effective_date,
    ANY_VALUE(latitude) AS latitude,
    ANY_VALUE(longitude) AS longitude,
    ANY_VALUE(geog) AS geog,
    'Auto-populated from sensor_readings_daily' AS notes,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `durham-weather-466502.sensors.sensor_readings_daily`
  GROUP BY native_sensor_id
) AS source
ON target.native_sensor_id = source.native_sensor_id
WHEN MATCHED THEN
  UPDATE SET
    status = source.status,
    effective_date = source.effective_date,
    latitude = COALESCE(target.latitude, source.latitude),
    longitude = COALESCE(target.longitude, source.longitude),
    geog = COALESCE(target.geog, source.geog),
    notes = source.notes,
    updated_at = source.updated_at
WHEN NOT MATCHED THEN
  INSERT (native_sensor_id, status, effective_date, latitude, longitude, geog, notes, updated_at)
  VALUES (source.native_sensor_id, source.status, source.effective_date, source.latitude, source.longitude, source.geog, source.notes, source.updated_at);

-- Verify the update
SELECT native_sensor_id, status, effective_date, notes
FROM `durham-weather-466502.sensors.sensor_location_dim`
ORDER BY native_sensor_id;
