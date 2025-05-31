# Google Drive Integration for Test Sensors

## 📁 **Organized Folder Structure**

Your test sensor data will be automatically uploaded to Google Drive in a well-organized structure separate from production data:

```
HotDurham/
├── RawData/                          # 🏭 Production Data (Existing)
│   ├── WU/                           # Weather Underground production sensors
│   └── TSI/                          # TSI production sensors
│
└── TestData_ValidationCluster/       # 🧪 Test Data (New Organized Structure)
    ├── SensorData/                   # Raw test sensor data
    │   ├── WU/                       # Weather Underground test sensors
    │   │   ├── 2025/
    │   │   │   ├── 05-May/           # Data from May 2025
    │   │   │   ├── 06-June/          # Data from June 2025
    │   │   │   └── ...
    │   │   └── 2024/
    │   │       └── ...
    │   └── TSI/                      # TSI test sensors (when added)
    │       └── (same date structure)
    │
    ├── ValidationReports/            # 📋 Daily/weekly validation reports
    │   ├── WU/2025/05-May/          # Validation reports for WU test sensors
    │   └── TSI/2025/05-May/         # Validation reports for TSI test sensors
    │
    ├── TestVsProduction/            # 📊 Comparison analysis reports
    │   ├── WU/2025/05-May/          # Test vs production comparisons
    │   └── TSI/2025/05-May/
    │
    └── Logs/                        # 📝 Test sensor operation logs
        ├── WU/2025/05-May/          # Logs for WU test operations
        └── TSI/2025/05-May/         # Logs for TSI test operations
```

## 🧪 **Your Test Sensors**

**14 Weather Underground Test Sensors** (Clustered for Validation):
- KNCDURHA634 → MS-09
- KNCDURHA635 → MS-10
- KNCDURHA636 → MS-11
- KNCDURHA638 → MS-12
- KNCDURHA639 → MS-13
- KNCDURHA640 → MS-14
- KNCDURHA641 → MS-15
- KNCDURHA642 → MS-16
- KNCDURHA643 → MS-17
- KNCDURHA644 → MS-18
- KNCDURHA645 → MS-19
- KNCDURHA646 → MS-20
- KNCDURHA647 → MS-21
- KNCDURHA648 → MS-22

## 🚀 **Automatic Data Flow**

### Daily Data Collection
1. **Data Collection Script Runs** → `src/data_collection/faster_wu_tsi_to_sheets_async.py`
2. **Automatic Sensor Classification** → Test vs Production sensors identified
3. **Local Storage**:
   - Test sensors → `test_data/sensors/`
   - Production sensors → `data/raw_pulls/`
4. **Google Drive Upload**:
   - Test sensors → `HotDurham/TestData_ValidationCluster/SensorData/WU/2025/05-May/`
   - Production sensors → `HotDurham/RawData/WU/`

### Validation Reports
1. **Daily Validation Reports** → Compare test vs production sensor performance
2. **Weekly Summaries** → Aggregate performance metrics
3. **Upload to Drive** → `HotDurham/TestData_ValidationCluster/ValidationReports/`

## 📋 **Example Google Drive Paths**

For today's data collection (May 31, 2025):

**Test Sensor Data:**
- `HotDurham/TestData_ValidationCluster/SensorData/WU/2025/05-May/wu_data_20250531_test_KNCDURHA634.csv`
- `HotDurham/TestData_ValidationCluster/SensorData/WU/2025/05-May/wu_data_20250531_test_KNCDURHA635.csv`
- ... (for all 14 test sensors)

**Validation Reports:**
- `HotDurham/TestData_ValidationCluster/ValidationReports/WU/2025/05-May/test_validation_report_20250531.csv`
- `HotDurham/TestData_ValidationCluster/ValidationReports/WU/2025/05-May/weekly_test_summary_2025_week_22.csv`

**Operation Logs:**
- `HotDurham/TestData_ValidationCluster/Logs/WU/2025/05-May/test_wu_20250531.log`

## 🔧 **Configuration Complete**

### Files Updated:
1. **`config/test_sensors_config.py`**
   - Added Google Drive folder configuration
   - Added MS station mappings
   - Added date-organized folder path methods

2. **`src/core/data_manager.py`**
   - Enhanced to use organized test sensor Google Drive paths
   - Automatic routing based on sensor type

3. **`src/validation/test_sensor_reports.py`** (New)
   - Daily validation report generation
   - Weekly performance summaries
   - Automatic Google Drive upload

## 🎯 **Key Benefits**

✅ **Automatic Separation**: Test and production data stored separately  
✅ **Date Organization**: Files organized by year/month for easy browsing  
✅ **MS Station Mapping**: Clear identification of test sensor locations  
✅ **Validation Reports**: Automated quality monitoring and comparisons  
✅ **Seamless Integration**: Works with existing data collection workflow  
✅ **Google Drive Sync**: Automatic cloud backup with organized structure  

## 🚦 **Status: Ready for Production**

Your test sensor system is now fully configured with Google Drive integration:

- ✅ 14 test sensors configured with MS station mappings
- ✅ Automatic data routing (test vs production)
- ✅ Organized Google Drive folder structure
- ✅ Validation reporting system
- ✅ Date-based organization
- ✅ Seamless integration with existing workflow

**Next Steps:**
1. Run your regular data collection - test sensors will automatically upload to the organized Google Drive structure
2. Check the `HotDurham/TestData_ValidationCluster/` folder in Google Drive after the first run
3. Review validation reports for data quality monitoring
4. Add TSI test sensor IDs when you have clustered TSI sensors for testing

## 🔍 **Monitoring Your Test Data**

### Check Local Test Data:
```bash
ls -la test_data/sensors/
ls -la test_data/logs/
```

### Check Google Drive:
Navigate to: `HotDurham/TestData_ValidationCluster/SensorData/WU/2025/05-May/`

### Generate Validation Reports:
```bash
python src/validation/test_sensor_reports.py
```

### View Current Configuration:
```bash
python config/test_sensors_config.py
```

---

**🎉 Your test sensor validation cluster is ready for data collection with organized Google Drive storage!**
