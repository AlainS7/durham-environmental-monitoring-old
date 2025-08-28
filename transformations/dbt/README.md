# dbt project (initial scaffold)

This lightweight dbt scaffold provides a future path for:

- Column-level lineage & exposures
- Built-in tests (unique, not_null) for key fields
- Documentation site generation

Current contents:

- staging/stg_wu_raw.sql
- staging/stg_tsi_raw.sql

Next steps:

1. Add a `profiles.yml` (outside repo or via ENV) mapping profile `sensor_transforms` to BigQuery.
2. Add sources and tests in `models/schema.yml`.
3. Convert existing hand-written transformation SQL into dbt models with refs.
