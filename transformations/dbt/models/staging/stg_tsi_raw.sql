-- Simple staging model selecting from raw TSI table
select * from `{{ var('project') }}`.{{ target.schema }}.sensor_readings_tsi_raw
