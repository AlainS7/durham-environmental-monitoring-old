A daily GitHub Actions workflow (`daily-verify.yml`) runs the cloud pipeline verifier against the previous day's partition. It enforces:

* GCS round-trip write/read
* BigQuery dataset & table presence
* Adaptive row counts per table
* Schema normalization (canonical `ts` TIMESTAMP + float latitude/longitude copies)
* Epoch diagnostics (detects seconds/millis/micros/nanos integer time columns)

# Hot Durham Environmental Monitoring System

A comprehensive environmental monitoring system for Durham, NC, featuring **high-resolution 15-minute interval** data collection from Weather Underground and TSI air quality sensors for accurate research and analysis.

## 🌟 Features


### Continuous Verification

A daily GitHub Actions workflow (`daily-verify.yml`) runs the cloud pipeline verifier against the previous day's partition. It enforces:
* GCS round-trip write/read
* BigQuery dataset & table presence
* Adaptive row counts per table
* Schema normalization (canonical `ts` TIMESTAMP + float latitude/longitude copies)
* Epoch diagnostics (detects seconds/millis/micros/nanos integer time columns)

Failures surface directly in the Actions tab and block unnoticed schema drift.

### IAM Hardening

See `docs/IAM_HARDENING.md` for least-privilege roles, service account layout, and Workload Identity Federation (GitHub → GCP) guidance.
## � Data Collection Specifications

### High-Resolution Research-Grade Data

- **Temporal Resolution**: 15-minute intervals
- **Data Processing**: Daily aggregations (no weekly averaging)
- **Quality Standards**: Research-grade accuracy and credibility
- **Collection Frequency**: Automated daily pulls at 6:00 AM
- **Data Preservation**: All 15-minute measurements retained for analysis

### Sensor Coverage

- **TSI Air Quality Sensors**: PM2.5, PM10, Temperature, Humidity
- **Weather Underground Stations**: Temperature, Humidity, Wind, Solar Radiation
- **Update Frequency**: Every 15 minutes for all sensors
- **Data Validation**: Continuous quality monitoring and anomaly detection

## 🚀 Quick Start (with uv)

1. **Install uv** (if not already):

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.cargo/bin:$PATH"
   ```

2. **Create a virtual environment** (recommended):

   ```sh
   uv venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:

   ```sh
   uv pip sync requirements.txt
   uv pip sync requirements-dev.txt
   ```

4. **Configure Credentials**:
   - Add Google API credentials to `creds/google_creds.json`
   - Add Weather Underground API key to `creds/wu_api_key.json`
   - Add TSI credentials to `creds/tsi_creds.json`

5. **Run Data Collection**:

   ```sh
   python src/data_collection/faster_wu_tsi_to_sheets_async.py
   ```

6. **System Management**:

   ```sh
   # Lint
   uv run ruff check .

   # Test
   uv run pytest

   # Check system health
   python tests/comprehensive_test_suite.py

   # Production deployment
   python scripts/production_manager.py deploy

   # Monitor system
   python scripts/production_manager.py monitor
   ```

**Note:** The CI/CD pipeline and Docker build use `uv` for all dependency management. For more info, see: [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)

## 📁 Project Structure

```text
├── config/                 # Configuration files
├── src/                   # Source code
│   ├── core/              # Core functionality
│   ├── data_collection/   # Data collection scripts
│   └── automation/        # Automation systems
├── data/                  # Data storage
├── docs/                  # Documentation
├── tests/                 # Test files
└── scripts/               # Utility scripts
```

## 🛠️ System Components

### Data Collection

- **Weather Underground**: Meteorological data collection
- **TSI Sensors**: Air quality monitoring
- **Automated Scheduling**: Configurable data collection intervals

### Data Management

- **Master Data System**: Historical data aggregation
- **Google Drive Sync**: Cloud backup and sharing
- **Test Data Isolation**: Separate handling of test vs production data

### Automation

- **Daily Sheets**: Automated daily reports
- **Master Data Updates**: Weekly data consolidation
- **Alert System**: Anomaly detection and notifications

## 📊 Data Flow

1. **Collection**: Sensors → Raw Data
2. **Processing**: Raw Data → Processed Data
3. **Storage**: Processed Data → Master Files
4. **Reporting**: Master Files → Visualizations & Reports
5. **Distribution**: Reports → Google Drive & Dashboard

## �️ Troubleshooting

### If Test Sensors Appear in Google Sheets

The system is designed to exclude test sensors from Google Sheets. If test sensors appear:

1. **Check Sheet Date**: Ensure you're looking at recently created sheets
2. **Verify Configuration**: Confirm test sensor IDs are in `config/test_sensors_config.py`
3. **Generate Fresh Sheet**: Run data collection to create new clean sheets
4. **Review Data Sources**: Check if additional sensors should be classified as test sensors

### Common Issues

- **KeyError: 'Device Name'**: Fixed in current version with proper column handling
- **Mixed Test/Production Data**: Resolved with enhanced separation logic
- **Chart Data Issues**: Now uses production-only data sources

### Validation

Run the system with recent date ranges to verify clean separation:

```bash
python src/data_collection/faster_wu_tsi_to_sheets_async.py
# Select date range within last 7 days for best results
```

## �🔧 Configuration

Main configuration files:

- `config/improved_google_drive_config.py` - Google Drive paths
- `config/test_sensors_config.py` - Test sensor management
- `config/master_data_config.json` - Master data system settings

## 📋 Maintenance

- **Daily**: Automated data collection and basic reporting
- **Weekly**: Master data updates and system health checks
- **Monthly**: Comprehensive system verification and cleanup

## 🧪 Test Sensor Management

### Current Configuration

- **27 Test Sensors Configured**: 14 WU + 13 TSI test sensors

### Quick Raw Sample Fetch (Diagnostics)

Use `scripts/fetch_sample_raw.py` to pull a single day's raw data directly from a source API and inspect non-null coverage before it enters the pipeline.

Examples:

```sh
WU_API_KEY=yourkey \
python scripts/fetch_sample_raw.py --source WU --date 2025-08-20 --stations STATIONID123 --verbose --validated-out /tmp/wu_20250820.parquet
```

## Maintainability Refactors (2025-08-28)

Internal improvements to reduce complexity and long argument lists (CodeScene flags):

- Added `RunConfig` to `daily_data_collector` (legacy params still accepted).
- Introduced `UploadSpec` plus compatibility shim for `GCSUploader` path building & uploads.
- Added `PartitionSpec` and `LoadSpec` in `load_to_bigquery`; retained `build_gcs_uri` shim for existing tests.
- Decomposed `bq_normalize_day` into smaller functions (`parse`, `list_target_tables`, `build_plans`, `execute_plan`).
- Modularized `verify_cloud_pipeline` into focused helpers (`perform_gcs_check`, `gather_row_related`, etc.).
- All changes keep CLI behavior stable; tests and lint pass.


```sh
TSI_CLIENT_ID=cid TSI_CLIENT_SECRET=secret TSI_AUTH_URL=https://auth.example/token \
python scripts/fetch_sample_raw.py --source TSI --date 2025-08-20 --devices DEVICE123 --validated-out /tmp/tsi_20250820.parquet
```

Output includes a JSON summary with row counts and per-column non-null counts for fast gap analysis.

- **Production Data Only**: Google Sheets contain only production sensor data
- **Separate Storage**: Test data isolated for internal analysis

### Test Sensor IDs

**Weather Underground Test Sensors:**

- KNCDURHA634 through KNCDURHA648 (MS-09 through MS-22)

**TSI Test Sensors:**

- AA-2 (Burch) through AA-14 (clustered test deployment)

### Data Separation

```text
🧪 TEST SENSORS → Local storage (/test_data/)
🏭 PRODUCTION SENSORS → Google Sheets & reporting
```

## 🎯 System Status (June 2025)

### ✅ Production Ready Features

- **Clean Google Sheets**: Production sensor data only
- **Test Sensor Exclusion**: All test sensors properly filtered from external reports
- **Data Integrity**: Robust separation logic with comprehensive validation
- **Professional Output**: Production-ready visualizations and reports

### Key Technical Implementations

- **Enhanced Separation Logic**: `separate_sensor_data_by_type()` with comprehensive error handling
- **Google Sheets Integration**: Production-only data flow with proper column handling
- **Configuration Validation**: Pre-collection validation prevents common errors
- **Smart TSI Detection**: Automatic detection of available sensor ID fields

## Cloud storage and BigQuery

This project defaults to writing raw sensor data to Google Cloud Storage (GCS) as Parquet, organized for efficient BigQuery batch loads.

- GCS layout: `gs://$GCS_BUCKET/$GCS_PREFIX/source=<WU|TSI>/agg=<raw|interval>/dt=YYYY-MM-DD/*.parquet`
- BigQuery tables: partitioned by `timestamp`, clustered by `native_sensor_id`.

Environment variables:

- GCS_BUCKET: Target GCS bucket (required for GCS uploads)
- GCS_PREFIX: Prefix within the bucket (default: sensor_readings)
- BQ_PROJECT: BigQuery project (optional; defaults to ADC project)
- BQ_DATASET: BigQuery dataset (required by the loader)
- BQ_LOCATION: BigQuery location (default: US)
- GOOGLE_APPLICATION_CREDENTIALS: Path to a service account key (if not using ADC)

Example (zsh):

```sh
export GCS_BUCKET="my-bucket"
export GCS_PREFIX="sensor_readings"
export BQ_PROJECT="my-project"
export BQ_DATASET="env_readings"
export BQ_LOCATION="US"
# export GOOGLE_APPLICATION_CREDENTIALS="$PWD/sa.json"  # if needed
```

## Scripts overview

- src/data_collection/daily_data_collector.py
  - Purpose: Fetch Weather Underground (WU) and TSI data and write to sinks.
  - Defaults: raw (no aggregation), sink=gcs.
  - Flags:
    - --aggregate/--no-aggregate (default: no-aggregate)
    - --agg-interval [pandas offset alias] (e.g., h, 15min) when aggregating
    - --sink [gcs|db|both]
    - --source [WU|TSI|all]
  - Example:
    - python -m src.data_collection.daily_data_collector --no-aggregate --sink gcs --source all --start-date 2025-01-01 --end-date 2025-01-02

- scripts/load_to_bigquery.py
  - Purpose: Batch load the partitioned Parquet files from GCS into BigQuery.
  - Table naming: sensor_readings_{source}_{agg} (e.g., sensor_readings_wu_raw)
  - Partitioning: by `timestamp`; clustering: `native_sensor_id` by default.
  - Requirements: BQ_DATASET and GCS_BUCKET (env or flags), ADC credentials.

### Quick usage: BigQuery loader

With env vars:

```sh
export GCS_BUCKET="my-bucket"
export GCS_PREFIX="sensor_readings"
export BQ_PROJECT="my-project"
export BQ_DATASET="env_readings"
export BQ_LOCATION="US"

python scripts/load_to_bigquery.py \
  --date 2025-01-01 \
  --source all \
  --agg raw
```

Via flags:

```sh
python scripts/load_to_bigquery.py \
  --project my-project \
  --dataset env_readings \
  --location US \
  --bucket my-bucket \
  --prefix sensor_readings \
  --date 2025-01-01 \
  --source WU \
  --agg raw \
  --table-prefix sensor_readings \
  --partition-field timestamp \
  --cluster-by native_sensor_id
```

Notes:

- Authenticate locally first: `gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS.
- The loader creates the dataset if needed and appends rows by default (WRITE_APPEND).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions or support, please check the documentation in the `docs/` directory or create an issue in the repository.

---

### Last updated: June 2025
