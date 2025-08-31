-- Create or replace partitioned native tables from external sources.
-- Run ad-hoc for backfill; afterwards use incremental refresh script for daily partitions.

CREATE SCHEMA IF NOT EXISTS `durham-weather-466502.sensors`;

CREATE OR REPLACE TABLE `durham-weather-466502.sensors.wu_raw_materialized`
PARTITION BY DATE(timestamp) AS
SELECT * FROM `durham-weather-466502.sensors.wu_raw_external`;

CREATE OR REPLACE TABLE `durham-weather-466502.sensors.tsi_raw_materialized`
PARTITION BY DATE(timestamp) AS
SELECT * FROM `durham-weather-466502.sensors.tsi_raw_external`;
