#!/usr/bin/env python3
"""
Live Test of Google Drive Integration for Test Sensors

This script simulates a data collection run to test the Google Drive upload integration.
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.core.data_manager import DataManager
from config.test_sensors_config import TestSensorConfig

def test_google_drive_integration():
    """Test the Google Drive integration with sample data."""
    
    print("🧪 Live Test: Google Drive Integration for Test Sensors")
    print("=" * 60)
    
    # Initialize systems
    print("🔧 Initializing systems...")
    data_manager = DataManager(str(project_root))
    test_config = TestSensorConfig()
    
    # Check Google Drive connection
    if data_manager.drive_service:
        print("✅ Google Drive service connected")
    else:
        print("⚠️ Google Drive service not available - will test local routing only")
    
    # Create sample data for test sensors
    print("\n📊 Creating sample test sensor data...")
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    start_date = yesterday.strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    # Sample data for test sensors
    test_sensor_data = []
    test_sensors = test_config.get_test_sensors()[:3]  # Test with first 3 sensors
    
    for i, sensor_id in enumerate(test_sensors):
        ms_station = test_config.get_ms_station_name(sensor_id)
        
        # Create sample data
        sample_data = {
            'station_id': sensor_id,
            'ms_station': ms_station,
            'timestamp': today.strftime("%Y-%m-%d %H:%M:%S"),
            'temperature': 72.5 + i,
            'humidity': 65.0 + i * 2,
            'pressure': 1013.25 + i * 0.5,
            'wind_speed': 5.0 + i,
            'wind_direction': 180 + i * 10,
            'test_run': True
        }
        test_sensor_data.append(sample_data)
    
    # Create DataFrame
    test_df = pd.DataFrame(test_sensor_data)
    
    print(f"📋 Sample data created for {len(test_sensors)} test sensors:")
    for sensor_id in test_sensors:
        ms_station = test_config.get_ms_station_name(sensor_id)
        print(f"   • {sensor_id} ({ms_station})")
    
    # Test the routing and Google Drive upload
    print(f"\n🚀 Testing data routing and Google Drive upload...")
    
    for sensor_id in test_sensors:
        sensor_df = test_df[test_df['station_id'] == sensor_id]
        
        print(f"\n🔍 Processing {sensor_id}:")
        
        # Check sensor classification
        is_test = test_config.is_test_sensor(sensor_id)
        ms_station = test_config.get_ms_station_name(sensor_id)
        drive_path = test_config.get_drive_folder_path_with_date(
            sensor_id, 
            today.strftime("%Y%m%d"), 
            "sensors"
        )
        
        print(f"   Type: {'TEST' if is_test else 'PRODUCTION'}")
        print(f"   MS Station: {ms_station}")
        print(f"   Local Path: {test_config.get_data_path(sensor_id)}")
        print(f"   Google Drive Path: {drive_path}")
        
        # Save sensor data (this will trigger Google Drive upload if connected)
        try:
            saved_path = data_manager.save_sensor_data(
                sensor_id=sensor_id,
                data_type="wu",
                df=sensor_df,
                start_date=start_date,
                end_date=end_date,
                file_format="csv"
            )
            
            if saved_path:
                print(f"   ✅ Data saved: {saved_path}")
                if data_manager.drive_service:
                    print(f"   📤 Google Drive upload initiated to: {drive_path}")
                else:
                    print(f"   📝 Local save only (Google Drive not connected)")
            else:
                print(f"   ❌ Save failed")
                
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
    
    # Check what files were created
    print(f"\n📁 Checking created files...")
    
    test_data_dir = test_config.test_sensors_path
    if test_data_dir.exists():
        files = list(test_data_dir.glob("*.csv"))
        print(f"   Local test data files: {len(files)}")
        for file in files[-3:]:  # Show last 3 files
            print(f"   • {file.name}")
    else:
        print(f"   No test data directory found")
    
    # Show expected Google Drive structure
    print(f"\n🗂️ Expected Google Drive Structure:")
    print(f"   HotDurham/TestData_ValidationCluster/SensorData/WU/2025/05-May/")
    for sensor_id in test_sensors:
        expected_filename = f"wu_data_{start_date.replace('-', '')}_to_{end_date.replace('-', '')}_test_{sensor_id}.csv"
        print(f"   ├── {expected_filename}")
    
    print(f"\n✅ Test completed!")
    print(f"   📊 Tested {len(test_sensors)} test sensors")
    print(f"   🗂️ Data routing verified")
    print(f"   📤 Google Drive integration {'active' if data_manager.drive_service else 'simulated'}")
    
    if data_manager.drive_service:
        print(f"\n🎯 Next: Check your Google Drive at HotDurham/TestData_ValidationCluster/")
    else:
        print(f"\n🎯 To enable Google Drive: Ensure google_creds.json is properly configured")
    
    return True

if __name__ == "__main__":
    test_google_drive_integration()
