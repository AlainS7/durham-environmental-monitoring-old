-- Standardized view layer for dashboards
CREATE OR REPLACE VIEW `durham-weather-466502.sensors.v_wu_clean` AS
SELECT
  timestamp,
  native_sensor_id,
  -- add more standardized field renames here as needed
  * EXCEPT(timestamp)
FROM `durham-weather-466502.sensors.wu_raw_materialized`;

CREATE OR REPLACE VIEW `durham-weather-466502.sensors.v_tsi_clean` AS
SELECT
  timestamp,
  native_sensor_id,
  * EXCEPT(timestamp)
FROM `durham-weather-466502.sensors.tsi_raw_materialized`;
