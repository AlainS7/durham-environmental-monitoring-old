-- Simple staging model selecting from raw WU table
select * from `{{ var('project') }}`.{{ target.schema }}.sensor_readings_wu_raw
