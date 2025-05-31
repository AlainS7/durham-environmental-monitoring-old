# Test Sensor Implementation - Complete Guide

## 🎯 What We've Implemented

The Hot Durham project now has a comprehensive test sensor routing system that automatically separates data from test sensors (physically clustered for validation) from production sensors deployed in the field.

## 🏗️ System Architecture

### 1. Test Sensor Configuration (`config/test_sensors_config.py`)
- **Hardcoded approach**: Test sensor IDs are explicitly listed for clear identification
- **Flexible routing**: Automatically routes data to separate storage paths
- **Easy management**: Simple list-based configuration that's easy to update

### 2. Enhanced DataManager (`src/core/data_manager.py`)
- **Sensor-aware storage**: Routes data based on sensor type (test vs production)
- **Separate paths**: Test data goes to `test_data/` directory structure
- **Automatic logging**: Separate logs for test vs production operations

### 3. Updated Data Collection (`src/data_collection/faster_wu_tsi_to_sheets_async.py`)
- **Automatic separation**: Identifies test sensors during data collection
- **Dual storage**: Saves test and production data to appropriate locations
- **Status reporting**: Clear feedback on which sensors are routed where

## 📁 Directory Structure Created

```
Hot Durham/
├── test_data/                    # Test sensor data (NEW)
│   ├── sensors/                  # Test sensor readings
│   │   ├── wu/                   # Weather Underground test sensors
│   │   └── tsi/                  # TSI test sensors
│   ├── logs/                     # Test sensor operation logs
│   ├── backup/                   # Test data backups
│   └── temp/                     # Temporary test files
└── data/                         # Production sensor data (EXISTING)
    ├── raw_pulls/                # Production sensor readings
    ├── processed/                # Processed production data
    └── backup/                   # Production data backups
```

## 🔧 Configuration

### Adding Test Sensors

Edit `config/test_sensors_config.py`:

```python
TEST_SENSOR_IDS = [
    # Weather Underground test sensors (clustered for validation testing)
    # Format: WU_SENSOR_ID -> MS_STATION_NAME
    'KNCDURHA634',  # MS-09
    'KNCDURHA635',  # MS-10
    'KNCDURHA636',  # MS-11
    'KNCDURHA638',  # MS-12
    'KNCDURHA639',  # MS-13
    'KNCDURHA640',  # MS-14
    'KNCDURHA641',  # MS-15
    'KNCDURHA642',  # MS-16
    'KNCDURHA643',  # MS-17
    'KNCDURHA644',  # MS-18
    'KNCDURHA645',  # MS-19
    'KNCDURHA646',  # MS-20
    'KNCDURHA647',  # MS-21
    'KNCDURHA648',  # MS-22
    
    # TSI test sensors (device names or IDs) - add your TSI test sensor IDs here
    # 'test_sensor_1',
    # 'test_sensor_2', 
    # 'test_sensor_3',
    # 'BS-TEST-01',
    # 'BS-TEST-02',
    
    # Add additional test sensor IDs here as you deploy them
]

# Mapping of WU sensor IDs to MS station names for reference
WU_TO_MS_MAPPING = {
    'KNCDURHA634': 'MS-09',
    'KNCDURHA635': 'MS-10',
    'KNCDURHA636': 'MS-11',
    'KNCDURHA638': 'MS-12',
    'KNCDURHA639': 'MS-13',
    'KNCDURHA640': 'MS-14',
    'KNCDURHA641': 'MS-15',
    'KNCDURHA642': 'MS-16',
    'KNCDURHA643': 'MS-17',
    'KNCDURHA644': 'MS-18',
    'KNCDURHA645': 'MS-19',
    'KNCDURHA646': 'MS-20',
    'KNCDURHA647': 'MS-21',
    'KNCDURHA648': 'MS-22',
}
```

## 🚀 How to Use

### 1. Configuration Complete
The test sensor configuration is now set up with your 14 Weather Underground sensors (KNCDURHA634-648) corresponding to MS stations MS-09 through MS-22.

### 2. Run Data Collection
The existing data collection script now automatically routes data:

```bash
python src/data_collection/faster_wu_tsi_to_sheets_async.py
```

### 3. Monitor Data Routing
During data collection, you'll see output like:
```
🧪 Found 3 WU test sensor records
🏭 Found 5 WU production sensor records
🧪 Found 2 TSI test sensor records
🏭 Found 8 TSI production sensor records
```

### 4. Verify File Locations
- **Test data**: Check `test_data/sensors/` for clustered sensor data
- **Production data**: Check `data/raw_pulls/` for field sensor data
- **Logs**: Separate logs in `test_data/logs/` and `logs/`

## 🧪 Testing

Run the verification script:
```bash
python test_sensor_routing.py
```

This will:
- Verify configuration is loaded correctly
- Test sensor classification logic
- Show sample data routing
- Display directory structure

## 📊 Data Analysis Benefits

### Validation Capabilities
- **Accuracy testing**: Compare readings from clustered test sensors
- **Quality validation**: Identify sensor drift or calibration issues
- **Environmental testing**: Test sensor performance under controlled conditions

### Production Confidence
- **Proven sensors**: Deploy only validated sensors to field locations
- **Quality baseline**: Use test cluster data as quality reference
- **Troubleshooting**: Compare field issues against test cluster behavior

## 🔄 Workflow Integration

### 1. Data Collection Phase
- Test sensors automatically identified and routed to `test_data/`
- Production sensors continue using existing `data/` structure
- Google Sheets created with both test and production data marked

### 2. Validation Phase
- Analyze test sensor data for consistency
- Compare readings between clustered sensors
- Validate sensor performance before field deployment

### 3. Production Deployment
- Move validated sensors from test cluster to field locations
- Update `TEST_SENSOR_IDS` to remove deployed sensors
- Add new sensors to test cluster for validation

## 🛠️ Maintenance

### Adding New Test Sensors
1. Add sensor ID to `TEST_SENSOR_IDS` list
2. Restart data collection
3. New sensor data automatically routes to test directories

### Deploying Test Sensors to Production
1. Remove sensor ID from `TEST_SENSOR_IDS` list
2. Physically move sensor to field location
3. Future data automatically routes to production directories

### Monitoring
- Check `test_data/logs/` for test sensor operation logs
- Monitor file counts in test vs production directories
- Use `get_test_sensor_summary()` for status reports

## 🎉 Implementation Complete

The test sensor routing system is now fully integrated and ready for use. The hardcoded approach provides clear, explicit control over which sensors are treated as test vs production, making data validation workflows straightforward and reliable.

### Key Benefits Achieved:
✅ **Separate storage** for test validation data  
✅ **Automatic routing** based on sensor identification  
✅ **Production safety** - no risk of mixing test and field data  
✅ **Easy configuration** - simple list-based sensor management  
✅ **Comprehensive logging** - full audit trail of data routing decisions  

Your clustered test sensors can now be used for validation while keeping their data completely separate from production field sensors!
