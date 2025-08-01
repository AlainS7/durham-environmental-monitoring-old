# Hot Durham Environmental Monitoring System

A comprehensive environmental monitoring system for Durham, NC, featuring **high-resolution 15-minute interval** data collection from Weather Underground and TSI air quality sensors for accurate research and analysis.

## 🌟 Features

- **High-Resolution Data Collection**: 15-minute interval data from Weather Underground and TSI sensors
- **Daily Data Processing**: Daily summaries instead of weekly for increased accuracy
- **Research-Grade Data**: Credible, high-granularity data suitable for academic research
- **Enhanced Test Sensor Separation**: Advanced separation of test vs production data with robust error handling
- **Automated Reporting**: Daily, weekly, and monthly automated reports
- **Google Drive Integration**: Seamless cloud storage and sharing
- **Data Visualization**: Interactive charts and analysis tools with 15-minute resolution
- **Master Data Management**: Historical data aggregation and management
- **Test Sensor Management**: Dedicated testing infrastructure with comprehensive validation
- **Configuration Validation**: Automatic validation of sensor configurations before data collection
- **Advanced Error Handling**: Robust error handling and graceful failure recovery

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
