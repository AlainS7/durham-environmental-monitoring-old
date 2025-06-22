# Hot Durham Project: New Features Documentation

## Overview
This document provides comprehensive documentation for the new features and enhancements implemented in the Hot Durham weather monitoring system. These improvements significantly enhance data analysis capabilities, system reliability, and operational efficiency.

## Table of Contents
1. [Anomaly Detection and Trend Analysis](#anomaly-detection-and-trend-analysis)
2. [Prioritized Data Pull Manager](#prioritized-data-pull-manager)
3. [Complete Analysis Suite](#complete-analysis-suite)
4. [Backup System](#backup-system)
5. [Updated Requirements](#updated-requirements)
6. [Integration with Existing System](#integration-with-existing-system)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)

---

## Anomaly Detection and Trend Analysis

### Overview
The anomaly detection system (`anomaly_detection_and_trend_analysis.py`) provides comprehensive analysis of sensor data to identify outliers, trends, and potential equipment malfunctions.

### Key Features

#### Statistical Outlier Detection
- Uses Interquartile Range (IQR) method to identify statistical outliers
- Configurable sensitivity levels (conservative, moderate, aggressive)
- Separate analysis for different sensor types (PM2.5, temperature, humidity)

#### Trend Analysis
- Linear regression analysis to detect significant trends
- Statistical significance testing (p-value < 0.05)
- Trend direction and magnitude quantification

#### Sensor Health Monitoring
- Stuck value detection (consecutive identical readings)
- Impossible reading detection (values outside physically possible ranges)
- Data completeness scoring

#### Comprehensive Reporting
- HTML reports with visualizations and recommendations
- JSON reports for programmatic analysis
- Automated plot generation for anomaly visualization

### Configuration

```python
# Example configuration in anomaly_detection_and_trend_analysis.py
ANOMALY_THRESHOLDS = {
    'PM2.5 (µg/m³)': {'min': 0, 'max': 1000},
    'Temperature (°C)': {'min': -40, 'max': 60},
    'Humidity (%)': {'min': 0, 'max': 100}
}

IQR_MULTIPLIERS = {
    'conservative': 3.0,    # Fewer outliers detected
    'moderate': 1.5,        # Standard detection
    'aggressive': 1.0       # More outliers detected
}
```

### Usage

```bash
# Run anomaly detection on recent data
python scripts/anomaly_detection_and_trend_analysis.py

# Run with specific parameters
python scripts/anomaly_detection_and_trend_analysis.py --days-back 14 --sensitivity aggressive

# Generate report for specific time period
python scripts/anomaly_detection_and_trend_analysis.py --start-date 20240101 --end-date 20240131
```

---

## Prioritized Data Pull Manager

### Overview
The prioritized data pull manager (`prioritized_data_pull_manager.py`) implements intelligent scheduling for sensor data collection based on location importance and operational requirements.

### Priority System

#### Three-Tier Classification
1. **Critical (15-minute intervals)**
   - Indoor sensors in occupied spaces
   - Critical monitoring points
   - High-traffic areas

2. **High (60-minute intervals)**
   - Semi-indoor or transitional spaces
   - Important but less critical sensors
   - Secondary monitoring points

3. **Standard (240-minute intervals)**
   - Outdoor sensors
   - Background monitoring
   - Less critical data points

#### Time-Based Adjustments
- **Business Hours (8 AM - 6 PM)**: Normal frequencies
- **After Hours (6 PM - 11 PM)**: 50% reduction in frequency
- **Night/Weekend**: 75% reduction in frequency

### Sensor Classification Logic

The system automatically classifies sensors based on:
- **Location keywords**: "Indoor", "Office", "Lab", "Room" → Higher priority
- **Device names**: Air quality monitors → Higher priority
- **Data types**: PM2.5 sensors → Higher priority for indoor locations

### Configuration Management

```json
{
  "priority_settings": {
    "critical": {
      "base_frequency_minutes": 15,
      "business_hours_multiplier": 1.0,
      "after_hours_multiplier": 1.5,
      "night_weekend_multiplier": 2.0
    }
  },
  "classification_keywords": {
    "indoor_indicators": ["indoor", "office", "lab", "room", "building"],
    "outdoor_indicators": ["outdoor", "ambient", "external", "weather"]
  }
}
```

### Usage

```bash
# Generate prioritized pull schedule
python scripts/prioritized_data_pull_manager.py

# Update sensor classifications
python scripts/prioritized_data_pull_manager.py --update-classifications

# Run prioritized data collection
python scripts/prioritized_data_pull_manager.py --execute-pulls
```

---

## Complete Analysis Suite

### Overview
The complete analysis suite (`complete_analysis_suite.py`) integrates all analysis components into a unified framework for comprehensive system monitoring and reporting.

### Integrated Components

1. **Data Availability Assessment**
   - Checks for recent data from all sources
   - Validates data completeness and quality
   - Identifies gaps in data collection

2. **Anomaly Detection Integration**
   - Runs comprehensive anomaly analysis
   - Generates consolidated anomaly reports
   - Provides actionable recommendations

3. **Prioritized Data Management**
   - Implements intelligent pull scheduling
   - Optimizes data collection efficiency
   - Monitors sensor health and performance

4. **System Health Monitoring**
   - Overall system status assessment
   - Component health checks
   - Performance metrics tracking

### Unified Reporting

The suite generates comprehensive JSON reports containing:
- System status overview
- Data quality assessments
- Anomaly detection results
- Prioritization recommendations
- Performance metrics

### Usage

```bash
# Run complete analysis suite
python scripts/complete_analysis_suite.py

# Run with progress tracking
python scripts/complete_analysis_suite.py --verbose

# Generate specific analysis type
python scripts/complete_analysis_suite.py --analysis-type anomaly
```

---

## Backup System

### Overview
The new backup system (`backup_system.py`) provides comprehensive data protection and disaster recovery capabilities for the Hot Durham project.

### Backup Types

#### 1. Credential Backup
- Backs up all API keys and authentication files
- Optional encryption using GPG
- Secure storage with integrity verification

#### 2. Critical Data Backup
- Recent sensor data (configurable time period)
- Processed summaries and reports
- System logs and automation records

#### 3. Configuration Backup
- Project configuration files
- Documentation and README files
- Automation scripts and settings

### Security Features

- **File Integrity Verification**: SHA256 hashing for all backed up files
- **Encryption Support**: Optional GPG encryption for sensitive data
- **Manifest Files**: Detailed backup contents and verification data
- **Automated Cleanup**: Configurable retention periods

### Google Drive Integration

When available, backups are automatically uploaded to Google Drive:
- Organized folder structure
- Automatic synchronization
- Remote disaster recovery capability

### Usage

```bash
# Create full system backup
python scripts/backup_system.py --full

# Backup only credentials (with encryption)
python scripts/backup_system.py --credentials --encrypt

# Check backup status
python scripts/backup_system.py --status

# Clean up old backups (keep 90 days)
python scripts/backup_system.py --cleanup 90

# Verify backup integrity
python scripts/backup_system.py --verify /path/to/backup.tar.gz
```

---

## Updated Requirements

### New Dependencies

The following packages have been added to `requirements.txt`:

```
# Enhanced data analysis capabilities
matplotlib~=3.8.4
seaborn~=0.13.2
scipy~=1.12.0
scikit-learn~=1.4.2

# Interactive visualizations
plotly~=5.20.0
kaleido~=0.2.1
```

### Installation

```bash
# Update environment with new requirements
pip install -r requirements.txt

# Or install specific packages
pip install matplotlib seaborn scipy scikit-learn plotly kaleido
```

---

## Integration with Existing System

### Compatibility

All new features are designed to integrate seamlessly with existing components:

- **Data Manager Integration**: New scripts work with existing data management system
- **Google Drive Sync**: Leverages existing Google Drive integration
- **Logging System**: Uses established logging framework
- **File Structure**: Maintains existing project organization

### Automation Integration

New features can be integrated into existing cron jobs:

```bash
# Add to existing daily automation
0 6 * * * cd /path/to/project && python scripts/complete_analysis_suite.py >> logs/analysis.log 2>&1

# Daily backup automation
0 2 * * * cd /path/to/project && python scripts/backup_system.py --full >> logs/backup.log 2>&1
```

---

## Usage Examples

### Daily Operations

```bash
# Morning routine: Check system status and run analysis
python scripts/status_check.py --detailed
python scripts/complete_analysis_suite.py

# Daily routine: Automated backup and comprehensive analysis
python scripts/backup_system.py --full --encrypt
python scripts/anomaly_detection_and_trend_analysis.py --days-back 7
```

### Problem Investigation

```bash
# Investigate data quality issues
python scripts/anomaly_detection_and_trend_analysis.py --sensitivity aggressive

# Check for sensor malfunctions
python scripts/prioritized_data_pull_manager.py --health-check

# Verify data integrity
python scripts/complete_analysis_suite.py --analysis-type data-quality
```

### Maintenance Tasks

```bash
# Monthly backup cleanup
python scripts/backup_system.py --cleanup 90

# Update sensor prioritization
python scripts/prioritized_data_pull_manager.py --update-classifications

# System health assessment
python scripts/status_check.py --days 30
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors
If you encounter import errors with new dependencies:
```bash
# Reinstall requirements
pip install -r requirements.txt --upgrade

# Check virtual environment activation
source .venv/bin/activate  # On macOS/Linux
```

#### 2. Google Drive Integration Issues
If Google Drive sync fails:
```bash
# Check credentials
ls -la creds/google_creds.json

# Test data manager integration
python -c "from scripts.data_manager import DataManager; dm = DataManager(); print(dm.drive_service is not None)"
```

#### 3. Backup System Issues
If backups fail:
```bash
# Check backup directory permissions
ls -la backup/

# Verify available disk space
df -h

# Test backup creation
python scripts/backup_system.py --config
```

### Error Recovery

#### Data Analysis Failures
```bash
# Check data availability
python scripts/status_check.py

# Verify data files
ls -la raw_pulls/*/

# Run with verbose logging
python scripts/anomaly_detection_and_trend_analysis.py --verbose
```

#### Backup Recovery
```bash
# List available backups
python scripts/backup_system.py --status

# Verify backup integrity
python scripts/backup_system.py --verify backup/critical_data/backup_20240101_120000.tar.gz

# Restore from backup (manual process)
tar -xzf backup/critical_data/backup_20240101_120000.tar.gz
```

---

## Configuration Reference

### Environment Variables

```bash
# Optional: Set custom base directory
export HOT_DURHAM_BASE_DIR="/custom/path/to/project"

# Optional: Configure backup encryption
export HOT_DURHAM_ENCRYPT_BACKUPS="true"
```

### Configuration Files

- `config/automation_config.json`: Automation settings
- `config/analysis_config.json`: Analysis parameters (auto-generated)
- `config/backup_config.json`: Backup preferences (auto-generated)

### Log Files

- `logs/anomaly_detection_YYYYMMDD.log`: Anomaly detection logs
- `logs/prioritized_pulls_YYYYMMDD.log`: Priority system logs
- `backup/verification_logs/backup_YYYYMMDD.log`: Backup operation logs

---

## Future Enhancements

### Planned Features

1. **Machine Learning Integration**
   - Predictive anomaly detection
   - Automated sensor health scoring
   - Smart prioritization based on historical patterns

2. **Advanced Visualization**
   - Interactive dashboard development
   - Real-time monitoring displays
   - Mobile-friendly interfaces

3. **Enhanced Automation**
   - Self-healing data collection
   - Intelligent retry mechanisms
   - Adaptive scheduling algorithms

### Contributing

To contribute to these features:
1. Follow existing code patterns and documentation standards
2. Include comprehensive logging and error handling
3. Add appropriate tests and validation
4. Update documentation for any new functionality

---

This documentation provides a comprehensive guide to the new features in the Hot Durham project. For specific implementation details, refer to the individual script files and their inline documentation.
