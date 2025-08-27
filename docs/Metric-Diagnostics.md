# Metric Diagnostics Workflow

This guide explains how to detect and troubleshoot missing metrics between raw Parquet ingestion (GCS) and the normalized fact table (sensor_readings) / BigQuery transformations.

## Components Added

1. `config/metrics_manifest.json` – Canonical list of expected metrics per source (WU, TSI) with descriptions.
2. `scripts/inspect_gcs_parquet.py` – Generates a JSON profile of a single Parquet file (columns, dtypes, counts, numeric stats, timestamp ranges).
3. `scripts/compare_metrics.py` – Compares an inspection JSON to the manifest, reporting missing or unexpected metrics and coverage percentage.
4. `scripts/generate_unpivot_sql.py` – Produces a deterministic BigQuery UNPIVOT + UNION ALL SQL using the manifest for a specific date.

## When To Use This

- Row counts for the latest partition suddenly drop (e.g., 20K → 1.6K).
- A class of metrics (e.g., all PM or gas metrics) is absent for the most recent date.
- You need to confirm whether the issue originates in collection, storage, or transformation.

## Quick Start

### 1. Inspect Raw Parquet (per source & date)

Obtain (or locate) the Parquet object path. Pattern:

```text
gs://<bucket>/<prefix>/source=<SRC>/agg=raw/dt=YYYY-MM-DD/<SRC>-YYYY-MM-DD.parquet
```

Run inspection (example WU):

```bash
python scripts/inspect_gcs_parquet.py \
  --uri gs://my-bucket/sensor_readings/source=WU/agg=raw/dt=2025-08-20/WU-2025-08-20.parquet \
  --out reports/inspections/wu_2025-08-20.json
```

Repeat for TSI.

### 2. Compare With Manifest

```bash
python scripts/compare_metrics.py \
  --manifest config/metrics_manifest.json \
  --inspection reports/inspections/wu_2025-08-20.json \
  --source WU > reports/inspections/wu_2025-08-20.compare.json
```

Look for:

- `coverage_pct` significantly < 100.
- Large `missing_metrics` set.

### 3. Generate Deterministic UNPIVOT SQL

Use raw table names you loaded to BigQuery (or external tables):

```bash
python scripts/generate_unpivot_sql.py \
  --manifest config/metrics_manifest.json \
  --date 2025-08-20 \
  --wu-table my_project.my_dataset.sensor_readings_wu_raw \
  --tsi-table my_project.my_dataset.sensor_readings_tsi_raw \
  --out bq_unpivot_2025-08-20.sql
```

Review the file to ensure all expected metrics appear in UNPIVOT IN (...) lists.

### 4. Diagnose Gaps

| Scenario | Raw Parquet Missing? | UNPIVOT SQL Missing? | Likely Cause | Action |
|----------|----------------------|----------------------|--------------|--------|
| Metrics absent in Parquet & compare script | Yes | N/A | Collection / API / rename mapping | Re-run collection; verify mapping in `clean_and_transform_data` |
| Metrics present in Parquet but absent post-UNPIVOT | No | Yes | Manifest outdated or SQL generator omission | Update manifest and regenerate SQL |
| Metrics present in Parquet and UNPIVOT but absent in fact table | No | No | Join / deployment mapping issue | Check deployments table & sensor type mapping |
| Only one source impacted | Source-specific | Depends | Source ingestion pipeline issue | Isolate source client logs |

### 5. Validate Deployment Mapping

If metrics vanish only after merge/upsert:

- Confirm `native_sensor_id` values in raw align with `sensors_master.native_sensor_id` for the sensor type.
- Ensure `deployments.end_date` is NULL for active sensors (string 'NULL' vs actual NULL mismatch can filter out rows).

### 6. Reprocess a Date (Optional Sandbox)

1. DROP or isolate staging / temp tables for the date.
2. Re-run UNPIVOT SQL (generated) into a temp table.
3. Perform MERGE with explicit date predicate.

### 7. Update Manifest When Adding Metrics

- Add new field under the correct source metrics object.
- Commit & regenerate any SQL using `generate_unpivot_sql.py`.

## Design Principles

- Determinism: Manifest drives a single source of truth for expected metrics.
- Separation: Raw ingestion (wide tables) vs transformation (UNPIVOT) decoupled.
- Diff-Friendly: JSON manifest; generated SQL reproducible.

## Future Enhancements (Suggested)

- CI check: Run comparison on a sample recent Parquet and fail if coverage < threshold.
- Automated BigQuery INFORMATION_SCHEMA introspection to compare fact table metric distribution vs manifest over last N days.
- Add metric lineage comments/labels to BigQuery schema for governance.

## Troubleshooting Checklist

1. Are raw Parquet files present for the date? (List with `gsutil ls` or via console.)
2. Do inspection JSONs show the expected columns? (If not, start at API client.)
3. Does compare script show high coverage? (If not, adjust mapping or manifest.)
4. Does generated UNPIVOT SQL contain all metrics? (Search for a missing metric name.)
5. Are there deployment mapping mismatches filtering rows? (`SELECT native_sensor_id FROM sensors_master WHERE sensor_type='TSI';`)
6. Any recent schema changes (renamed columns) not reflected in the manifest?

## File Locations

- Manifest: `config/metrics_manifest.json`
- Scripts: `scripts/inspect_gcs_parquet.py`, `scripts/compare_metrics.py`, `scripts/generate_unpivot_sql.py`
- Docs: `docs/Metric-Diagnostics.md`

---

Maintained as part of the ingestion reliability toolchain.
