# Hot Durham Environmental Monitoring System

A comprehensive environmental monitoring system for Durham, NC, featuring real-time data collection from Weather Underground and TSI air quality sensors.

## 🌟 Features

- **Real-time Data Collection**: Weather Underground and TSI sensor integration
- **Automated Reporting**: Daily, weekly, and monthly automated reports
- **Google Drive Integration**: Seamless cloud storage and sharing
- **Data Visualization**: Interactive charts and analysis tools
- **Master Data Management**: Historical data aggregation and management
- **Test Sensor Management**: Dedicated testing infrastructure

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Credentials**:
   - Add Google API credentials to `creds/google_creds.json`
   - Add Weather Underground API key to `creds/wu_api_key.json`
   - Add TSI credentials to `creds/tsi_creds.json`

3. **Run Data Collection**:
   ```bash
   python src/data_collection/faster_wu_tsi_to_sheets_async.py
   ```

## 📁 Project Structure

```
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

## 🔧 Configuration

Main configuration files:
- `config/improved_google_drive_config.py` - Google Drive paths
- `config/test_sensors_config.py` - Test sensor management
- `config/master_data_config.json` - Master data system settings

## 📋 Maintenance

- **Daily**: Automated data collection and basic reporting
- **Weekly**: Master data updates and system health checks
- **Monthly**: Comprehensive system verification and cleanup

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

*Last updated: June 2025*
