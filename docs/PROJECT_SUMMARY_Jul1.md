# Hot Durham Weather Data Collection & Analysis Project
## Comprehensive Project Summary

### Project Overview
The "Hot Durham" project is a comprehensive weather data collection, processing, and analysis system focused on Durham, North Carolina. It aggregates data from multiple sources, processes it through automated pipelines, and stores results in Google Drive/Sheets for accessibility and sharing.

### Core Mission
Monitor and analyze weather patterns in Durham, NC by collecting real-time data from multiple weather stations and services, processing it for insights, and making it accessible through automated reports and potential web interfaces.

---

## Data Sources & Collection

### Primary Data Sources
1. **TSI (Temperature Sensor Initiative) Weather Stations**
   - Multiple weather stations in Durham area
   - Real-time temperature, humidity, pressure data
   - API-based data collection
   - High-resolution data collection (multiple readings per hour)

2. **Weather Underground (WU) API**
   - Historical and current weather data
   - Complementary data source for validation
   - Broader geographical coverage

### Data Collection Infrastructure
- **Automated Data Pull System**: Python-based scripts with scheduling
- **Rate Limiting**: Respects API limits and implements intelligent throttling
- **Error Handling**: Robust retry mechanisms and logging
- **Data Validation**: Anomaly detection and outlier removal
- **Backup Systems**: Multiple storage locations for data redundancy

---

## Technical Architecture

### Core Technologies
- **Python 3.11+**: Primary programming language
- **PostgreSQL**: Primary database for storing sensor readings.
- **Google Drive API**: Cloud storage and file sharing
- **Google Sheets API**: Data presentation and sharing
- **Pandas**: Data manipulation and analysis
- **JSON/CSV**: Data format standards

### System Components

#### 1. Data Collection Layer
Located in `src/data_collection/`
- `daily_data_collector.py`: Main data collection orchestrator.
- `clients/`: Contains API clients for WU and TSI.

#### 2. Configuration Management
All configuration is centralized in `src/config/`.
- `app_config.py`: Main configuration loader (handles secrets, env vars).
- `logging.json`: Logging configuration.
- `production_sensors.json`: List of production sensor IDs.

#### 3. Data Processing & Storage
- **PostgreSQL Database**: Stores all sensor readings, metadata, and logs.
- **Google Drive**: Used for backups and sharing reports.

processed/
├── annual_summaries/               # Yearly aggregations
├── monthly_summaries/             # Monthly reports
└── weekly_summaries/              # Weekly analysis
```

#### 4. Alert & Monitoring System
- **SMTP Email Alerts**: Real-time notifications for system issues
- **Anomaly Detection**: Automated identification of unusual readings
- **System Health Monitoring**: Service uptime and data quality checks
- **Production Monitoring**: Deployment status and error tracking

---

## Data Flow & Processing Pipeline

### 1. Data Ingestion
```
External APIs → Rate-Limited Collectors → Validation Layer → Local Storage
```

### 2. Data Processing
```
Raw Data → Cleaning & Validation → Anomaly Detection → Aggregation → Analysis
```

### 3. Data Distribution
```
Processed Data → Google Sheets → PDF Reports → Alert System → Archive Storage
```

### Key Features
- **High-Resolution Data**: Multiple readings per hour for detailed analysis
- **Historical Analysis**: Long-term trend identification
- **Anomaly Detection**: Automatic flagging of unusual weather patterns
- **Multi-Format Output**: CSV, JSON, PDF reports, Google Sheets
- **Automated Scheduling**: Cron-based execution with intelligent retry logic

---

## Current Infrastructure Status

### Google Drive Integration
- **Service Account**: `hotdurhamnewdatasender@hot-durham-data.iam.gserviceaccount.com`
- **Shared Access**: All data accessible to `hotdurham@gmail.com`
- **Folder Structure**:
  - `TSI/` - TSI weather station data
  - `WU/` - Weather Underground data
  - `Production/` - Production environment files
  - `RawData/` - Unprocessed data storage
  - `HotDurham/` - Main project folder

### Alert System
- **SMTP Configuration**: Gmail-based alert system
- **Real-time Monitoring**: System health and data quality alerts
- **Error Notifications**: Automatic failure detection and reporting

---

## Historical Challenges & Solutions

### Recent Infrastructure Issues
1. **Service Account Flagging**: Previous Google service account was flagged, requiring migration
2. **Data Access Recovery**: Implemented comprehensive folder sharing restoration
3. **Missing Historical Data**: Some analysis folders from old service account are inaccessible
4. **Permission Management**: Established robust sharing protocols

### Implemented Solutions
- **New Service Account**: Migrated to clean, unflagged service account
- **Automated Sharing**: Scripts to ensure proper folder permissions
- **Backup Strategies**: Multiple data storage locations
- **Recovery Tools**: Scripts for data migration and folder restoration

---

## Current Capabilities

### Data Analysis Features
- **Trend Analysis**: Long-term weather pattern identification
- **Comparative Analysis**: Multi-station data comparison
- **Anomaly Detection**: Automated unusual reading identification
- **Report Generation**: Automated PDF and spreadsheet reports
- **Data Visualization**: Chart generation and analysis plots

### Automation Features
- **Scheduled Collection**: Automated data pulls every few hours
- **Error Recovery**: Automatic retry mechanisms
- **Health Monitoring**: System status tracking
- **Alert Management**: Real-time notification system

### Data Access
- **Google Sheets Integration**: Live data accessible via spreadsheets
- **CSV Export**: Standard format data export
- **API-Ready**: Structured data suitable for web service integration
- **Historical Archives**: Long-term data storage and retrieval

---

## Potential Web Implementation Areas

### Mapping & Visualization Opportunities
1. **Interactive Weather Map**: Real-time weather station locations and readings
2. **Historical Data Visualization**: Time-series charts and trend analysis
3. **Comparative Analysis Dashboard**: Multi-station comparison tools
4. **Alert Dashboard**: Real-time system status and weather alerts

### Data Serving Capabilities
- **RESTful API**: The system can easily be extended to provide JSON APIs
- **Real-time Updates**: Data is collected frequently enough for live web updates
- **Historical Queries**: Rich historical data suitable for time-based queries
- **Geospatial Data**: Weather station locations suitable for mapping

### Current Data Structure Example
```json
{
  "timestamp": "2025-07-01T10:30:00Z",
  "station_id": "TSI_DURHAM_001",
  "location": {"lat": 35.9940, "lng": -78.8986},
  "readings": {
    "temperature": 78.5,
    "humidity": 65.2,
    "pressure": 30.15,
    "wind_speed": 5.2
  },
  "quality_flags": ["validated", "no_anomalies"]
}
```

---

## Infrastructure & Hosting Considerations

### Current Setup
- **Local Processing**: Python scripts run on local infrastructure
- **Cloud Storage**: Google Drive for file storage and sharing
- **Email Alerts**: Gmail SMTP for notifications
- **Database**: PostgreSQL for storing all sensor data and metadata.

### Scaling Considerations
- **Data Volume**: Currently processing hundreds of readings per day
- **API Limits**: Working within TSI and Weather Underground rate limits
- **Storage Growth**: Approximately 1-2GB of data per year
- **Processing Requirements**: Moderate computational needs for analysis

### Security & Access
- **Service Account Security**: Google Cloud IAM for API access
- **Data Privacy**: Weather data is generally public domain
- **Access Control**: Controlled sharing via Google Drive permissions
- **Backup Security**: Multiple secure storage locations

---

## Potential Questions for Web Implementation

Consider Googling:

### 1. Hosting & Infrastructure
- **Cloud Platform Recommendations**: AWS, Google Cloud, Azure for weather data hosting
- **Database Solutions**: PostgreSQL, MongoDB, or cloud databases for time-series data
- **CDN Solutions**: For serving map tiles and static weather data
- **Auto-scaling**: Handling variable traffic to weather dashboards

### 2. Mapping & Visualization
- **Mapping Libraries**: Leaflet, Mapbox, Google Maps for weather station locations
- **Real-time Data Visualization**: D3.js, Chart.js for live weather charts
- **Time-series Visualization**: Specialized libraries for historical weather data
- **Mobile-responsive Design**: Cross-platform weather dashboard design

### 3. API & Data Services
- **REST API Design**: Best practices for weather data APIs
- **WebSocket Implementation**: Real-time weather update streaming
- **Caching Strategies**: Redis, Memcached for weather data caching
- **Rate Limiting**: API protection for public weather services

### 4. Integration Possibilities
- **Third-party Weather APIs**: Integration with additional weather services
- **Government Data Sources**: NOAA, NWS integration possibilities
- **Social Media Integration**: Weather alerts and updates
- **Mobile App Development**: Native or progressive web app strategies

---

## Project Files & Structure Reference

### Key Directories
```
.
├── src/                     # Main application source code
│   ├── config/              # Centralized configuration
│   ├── data_collection/     # Data collection scripts and API clients
│   └── ...
├── web-app/                 # Self-contained web application (map visualization)
├── docs/                    # Project documentation
├── tests/                   # Automated tests
└── ...                      # Other project files (e.g., Dockerfile)
```

### Important Files
- `pyproject.toml`: Project metadata and dependencies (replaces setup.py).
- `requirements.txt`: Pinned production dependencies.
- `requirements-dev.txt`: Pinned development dependencies.
- `.env`: Used for local development environment variables.
- `README.md`: Main project overview and setup instructions.

---

## Summary

This is a mature, production-ready weather data collection and analysis system that:

1. **Collects real-time weather data** from multiple sources in Durham, NC
2. **Processes and validates data** through automated pipelines
3. **Stores data in multiple formats** (PostgreSQL, CSV, Google Sheets)
4. **Provides automated reporting** and alert capabilities
5. **Has robust error handling** and recovery mechanisms
6. **Operates with cloud integration** via Google Drive/Sheets APIs
7. **Maintains historical data** for trend analysis
8. **Is ready for web service extension** with structured data and APIs

The system is currently local/cloud hybrid but has all the components necessary for full web deployment, including APIs, structured data, real-time capabilities, and geographical information suitable for mapping applications.

**New goals**: Extend this system to include public-facing web interfaces for weather data visualization, interactive maps, and public API access while maintaining the existing automated data collection and processing capabilities.
