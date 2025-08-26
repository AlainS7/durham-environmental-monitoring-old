# Sapiens Sensor Integration

This document explains how Sapiens sensors are integrated into the Durham Environmental Monitoring pipeline.

## Overview

A new client `SapiensClient` implements the same pattern used for TSI and WU. Data flows:

Sapiens API -> `SapiensClient.fetch_data()` -> `daily_data_collector.clean_and_transform_data()` -> melt -> `insert_sensor_readings`.

## Configuration

Add Sapiens devices to the production sensor config JSON (`config/environments/production.json`) under a new key:

```json
{
  "sapiens": [
    {"id": "SAPIENS_DEV_1", "location": "Example", "active": true}
  ]
}
```

(Structure can be merged with existing `wu` and `tsi` keys.)

Environment variable expected: `SAPIENS_API_KEY` (Bearer token). If Sapiens later requires OAuth, extend `SapiensClient._authenticate` accordingly.

## Data Mapping

Raw fields standardized in `clean_and_transform_data` with source `SAPIENS`:

- device_id -> native_sensor_id (pre-normalized by client)
- timestamp -> timestamp (UTC)
- temperature_c -> temperature
- humidity_percent -> humidity
- pm2_5 -> pm2_5
- pm10 -> pm10
- co2_ppm -> co2_ppm (optional)

## Adding Deployments

Insert rows into `sensors_master` with `sensor_type='SAPIENS'` and create corresponding `deployments` row (end_date NULL for active).

## Running Collection

```bash
python -m src.data_collection.daily_data_collector --start_date 2025-08-25 --end_date 2025-08-25 --source all
```

Or Sapiens only:

```bash
python -m src.data_collection.daily_data_collector --source sapiens
```

## Tests

`tests/unit/test_sapiens_integration.py` validates cleaning and DB transformation.

## Future Enhancements

- Implement dynamic device discovery from Sapiens API.
- Add Pydantic schema reflecting actual Sapiens response.
- Include latency / error metrics.
