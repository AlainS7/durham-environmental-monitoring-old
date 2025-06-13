# Hot Durham Environmental Monitoring 🌍

**Comprehensive air quality and weather monitoring system for Durham, NC**

[![Status](https://img.shields.io/badge/status-fully%20operational-brightgreen)](#system-status)
[![PDF Reports](https://img.shields.io/badge/PDF%20reports-automated-blue)](PRODUCTION_PDF_SYSTEM_README.md)
[![Temperature Format](https://img.shields.io/badge/temperature-1%20decimal-green)](#features)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](requirements.txt)
[![Web Apps](https://img.shields.io/badge/web%20apps-3%20running-success)](#web-applications)
[![Last Updated](https://img.shields.io/badge/updated-June%202025-blue)](docs/MISSION_COMPLETE.md)

## 🚀 Quick Start

```bash
# Start all applications
./quick_start.sh start

# Generate test PDF report  
./quick_start.sh test-pdf

# Check system status
./quick_start.sh status

# Run automated data collection
python src/data_collection/production_data_pull_executor.py
```

## 🌟 System Status (June 2025)

### ✅ **Fully Operational**
- **Production PDF Reports**: 16MB automated weekly generation
- **Temperature Formatting**: Consistent 1 decimal precision across all interfaces  
- **Data Collection**: 8 production sensors (WU + TSI) actively monitored
- **Project Structure**: Clean, organized codebase with archived legacy files
- **Testing Framework**: Comprehensive validation and monitoring

### 🌐 **Web Applications**
- **📊 Public Dashboard**: http://localhost:5001 - Durham resident interface
- **🗺️ Live Sensor Map**: http://localhost:5003 - Interactive real-time sensor map  
- **📈 Streamlit GUI**: http://localhost:8502 - Enhanced monitoring dashboard

### 🚀 **Ready for Next Phase**
- Mobile-responsive public interface
- RESTful API for developer access
- Predictive analytics & AI forecasting
- IoT sensor network expansion

## 📚 Documentation

- [🎉 Mission Complete](docs/MISSION_COMPLETE.md) - Current system status
- [🚀 New Features Roadmap](docs/NEW_FEATURES_ROADMAP.md) - Planned enhancements
- [🧪 System Testing Report](docs/SYSTEM_TESTING_REPORT.md) - Verification results
- [📊 Production PDF System](PRODUCTION_PDF_SYSTEM_README.md) - Automated reporting
- [🧹 Cleanup Summary](CLEANUP_SUMMARY.md) - Project organization details

## 🏗️ Project Structure

```
Hot Durham/
├── src/                    # 🐍 Source code
│   ├── core/              # Core system components
│   │   ├── data_manager.py         # Data management system
│   │   └── backup_system.py        # Backup and recovery
│   ├── analysis/          # 📊 Data analysis modules
│   │   ├── anomaly_detection_and_trend_analysis.py
│   │   ├── complete_analysis_suite.py
│   │   ├── enhanced_data_analysis.py
│   │   ├── multi_category_visualization.py
│   │   └── generate_summary_reports.py
│   ├── data_collection/   # 📡 Data collection systems
│   │   ├── prioritized_data_pull_manager.py
│   │   ├── production_data_pull_executor.py
│   │   ├── automated_data_pull.py
│   │   └── faster_wu_tsi_to_sheets_async.py
│   ├── gui/               # 🖥️ User interfaces
│   │   └── enhanced_streamlit_gui.py
│   ├── automation/        # 🤖 Automation scripts
│   │   ├── automated_reporting.py
│   │   └── status_check.py
│   └── utils/             # 🛠️ Utility functions
│       └── google_drive_sync.py
├── tests/                  # 🧪 Test suites
│   ├── integration_test.py
│   └── test_data_manager.py
├── docs/                   # 📚 Documentation
├── config/                 # ⚙️ Configuration files
├── data/                   # 💾 Data storage
├── backup/                 # 🔐 Backup storage
├── logs/                   # 📝 Log files
├── reports/                # 📈 Generated reports
└── archive/                # 📦 Archived files
```

## 💡 Features

### 🔍 **Advanced Monitoring**
- ✅ Real-time air quality monitoring (TSI devices)
- ✅ Weather data integration (Weather Underground)
- ✅ Automated anomaly detection
- ✅ Trend analysis and forecasting

### 🎯 **Intelligent Data Collection**
- ✅ Prioritized sensor scheduling (Critical/High/Standard)
- ✅ Time-based frequency adjustments
- ✅ Gap detection and recovery
- ✅ Production-ready execution framework

### 📊 **Comprehensive Analysis**
- ✅ Statistical outlier detection
- ✅ Multi-sensor correlation analysis
- ✅ Interactive visualization dashboard
- ✅ Automated report generation

### 🔐 **Robust Data Protection**
- ✅ Multi-layer backup system
- ✅ Google Drive cloud sync
- ✅ Credential encryption
- ✅ Disaster recovery capabilities

## 🔧 Installation

### Prerequisites
- Python 3.8+
- Google Drive API credentials
- TSI and Weather Underground API keys

### Setup
```bash
# Clone and navigate to project
cd "Hot Durham"

# Install dependencies
pip install -r requirements.txt

# Set up credentials (see docs/DATA_MANAGEMENT_README.md)
cp creds/example_config.json creds/your_config.json

# Run tests to verify installation
python tests/integration_test.py
```

## 🚀 Usage

### Data Collection
```bash
# Start prioritized data collection
python src/data_collection/production_data_pull_executor.py

# Manual data pull
python src/data_collection/automated_data_pull.py
```

### Analysis & Visualization
```bash
# Launch interactive dashboard
streamlit run src/gui/enhanced_streamlit_gui.py

# Generate analysis reports
python src/analysis/complete_analysis_suite.py

# Run anomaly detection
python src/analysis/anomaly_detection_and_trend_analysis.py
```

### System Management
```bash
# Create backup
python src/core/backup_system.py --full

# Check system status
python src/automation/status_check.py

# Generate automated reports
python src/automation/automated_reporting.py
```

## 📈 Monitoring Capabilities

### Air Quality Metrics
- **PM2.5 Levels**: Real-time particulate matter monitoring
- **Temperature**: Ambient temperature tracking
- **Humidity**: Relative humidity measurements
- **Air Pressure**: Barometric pressure data

### Data Sources
- **TSI Devices**: Indoor/outdoor air quality sensors
- **Weather Underground**: Meteorological data
- **Historical Data**: Up to 90-day rolling archive

## 🎯 Production Status

| Component | Status | Tests | Documentation |
|-----------|--------|-------|---------------|
| Data Collection | ✅ Ready | 8/8 Passing | ✅ Complete |
| Analysis Suite | ✅ Ready | 8/8 Passing | ✅ Complete |
| Backup System | ✅ Ready | 8/8 Passing | ✅ Complete |
| GUI Dashboard | ✅ Ready | 8/8 Passing | ✅ Complete |
| Automation | ✅ Ready | 8/8 Passing | ✅ Complete |
| **Project Structure** | ✅ **Reorganized** | ✅ **Complete** | ✅ **Updated** |

## 🌟 Recent Updates

**v2.1 (May 2025)**
- ✨ **Complete project reorganization completed**
- ✨ Professional Python package structure implemented
- ✨ All import paths updated and tested
- ✨ Package installation with setup.py ready
- ✨ 8/8 integration tests passing
- ✨ Production deployment ready

**v2.0 (May 2025)**
- ✨ Added intelligent anomaly detection
- ✨ Implemented prioritized data collection
- ✨ Enhanced backup and recovery system
- ✨ Complete project reorganization
- ✨ Production-ready deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`python tests/integration_test.py`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is for environmental monitoring and research purposes.

## 📞 Support

- 📧 Documentation: [docs/](docs/)
- 🐛 Issues: Create an issue in the repository
- 💬 Questions: Check existing documentation first

---

**Ready for production deployment** 🎉

*Monitoring Durham's air quality with advanced analytics and intelligent automation.*
