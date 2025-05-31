#!/usr/bin/env python3
"""
Test Google Drive Organization Demo for Hot Durham Test Sensors

This script demonstrates how test sensor data will be organized in Google Drive
with the new folder structure and validation reports.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config.test_sensors_config import TestSensorConfig, get_drive_folder_path, get_drive_folder_path_with_date

def demo_google_drive_organization():
    """Demonstrate how test sensor data will be organized in Google Drive."""
    
    print("🚗 Hot Durham Test Sensor Google Drive Organization Demo")
    print("=" * 65)
    
    # Initialize test configuration
    test_config = TestSensorConfig()
    
    # Example dates for demonstration
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    # Show current test sensors
    test_sensors = test_config.get_test_sensors()
    print(f"\n📊 Test Sensors Configured: {len(test_sensors)}")
    for sensor_id in test_sensors[:3]:  # Show first 3 for brevity
        ms_station = test_config.get_ms_station_name(sensor_id)
        print(f"   • {sensor_id} ({ms_station})")
    print(f"   ... and {len(test_sensors) - 3} more sensors")
    
    print(f"\n🗂️  Google Drive Folder Structure:")
    print(f"   Root: HotDurham/")
    
    # Production structure (existing)
    print(f"\n   📁 Production Data (Existing Structure):")
    print(f"      HotDurham/RawData/WU/")
    print(f"      HotDurham/RawData/TSI/")
    
    # Test sensor structure (new)
    print(f"\n   🧪 Test Data (New Organized Structure):")
    print(f"      HotDurham/TestData_ValidationCluster/")
    print(f"      ├── SensorData/")
    print(f"      │   ├── WU/")
    print(f"      │   │   ├── 2025/")
    print(f"      │   │   │   ├── 05-May/")
    print(f"      │   │   │   ├── 06-June/")
    print(f"      │   │   │   └── ...")
    print(f"      │   │   └── 2024/...")
    print(f"      │   └── TSI/")
    print(f"      │       └── (similar structure)")
    print(f"      ├── ValidationReports/")
    print(f"      │   ├── WU/2025/05-May/")
    print(f"      │   └── TSI/2025/05-May/")
    print(f"      ├── TestVsProduction/")
    print(f"      │   └── (comparison reports)")
    print(f"      └── Logs/")
    print(f"          └── (test sensor operation logs)")
    
    # Example folder paths for different scenarios
    print(f"\n🎯 Example Google Drive Paths:")
    
    # Test sensor data paths
    example_sensor = "KNCDURHA634"  # MS-09
    date_str = today.strftime("%Y%m%d")
    
    sensor_path = get_drive_folder_path_with_date(example_sensor, date_str, "sensors")
    reports_path = get_drive_folder_path_with_date(example_sensor, date_str, "reports")
    comparisons_path = get_drive_folder_path_with_date(example_sensor, date_str, "comparisons")
    logs_path = get_drive_folder_path_with_date(example_sensor, date_str, "logs")
    
    print(f"   📂 Test Sensor Data: {sensor_path}")
    print(f"   📋 Validation Reports: {reports_path}")
    print(f"   📊 Comparison Reports: {comparisons_path}")
    print(f"   📝 Operation Logs: {logs_path}")
    
    # Production sensor comparison
    production_sensor = "KNCDURHA209"  # Example production sensor
    prod_path = get_drive_folder_path(production_sensor, "sensors")
    print(f"   🏭 Production Data: {prod_path}")
    
    print(f"\n🔄 Data Flow Example:")
    print(f"   1. Data collection runs automatically")
    print(f"   2. Test sensors (KNCDURHA634-648) → {sensor_path}")
    print(f"   3. Production sensors → {prod_path}")
    print(f"   4. Validation reports → {reports_path}")
    print(f"   5. All files organized by date automatically")
    
    # Demonstrate status information with Google Drive paths
    print(f"\n🔍 Test Sensor Status with Google Drive Integration:")
    
    for sensor_id in test_sensors[:2]:  # Show first 2 for demonstration
        status = test_config.get_sensor_status(sensor_id)
        ms_info = f" ({status['ms_station']})" if 'ms_station' in status else ""
        
        print(f"\n   Sensor: {sensor_id}{ms_info}")
        print(f"   Status: {status['status']}")
        print(f"   Local Path: {status['data_path']}")
        print(f"   Drive Path: {status['drive_folder_path']}")
        print(f"   Today's Upload: {get_drive_folder_path_with_date(sensor_id, date_str)}")
    
    print(f"\n💡 Key Benefits:")
    print(f"   ✅ Automatic separation of test vs production data")
    print(f"   ✅ Organized by date for easy tracking")
    print(f"   ✅ MS station mapping for clear identification")
    print(f"   ✅ Validation reports for data quality monitoring")
    print(f"   ✅ Seamless integration with existing workflow")
    
    print(f"\n🎛️  Configuration:")
    print(f"   • Test sensors: {len(test_sensors)} configured")
    print(f"   • Local test data: test_data/sensors/")
    print(f"   • Google Drive root: HotDurham/TestData_ValidationCluster/")
    print(f"   • Auto-upload: Enabled with organized folder structure")
    
    print(f"\n🚀 Ready for deployment!")
    print(f"   Your test sensors will automatically upload to the organized")
    print(f"   Google Drive structure starting with the next data collection run.")

if __name__ == "__main__":
    demo_google_drive_organization()
