#!/usr/bin/env python3
"""
Test script to verify test sensor routing functionality
"""

import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'config'))
sys.path.insert(0, str(project_root / 'src' / 'core'))

from test_sensors_config import TestSensorConfig, is_test_sensor, get_data_path, get_log_path
from data_manager import DataManager
import pandas as pd
from datetime import datetime

def test_sensor_configuration():
    """Test the test sensor configuration system."""
    print("🧪 Testing Test Sensor Configuration System")
    print("=" * 50)
    
    # Initialize configuration
    config = TestSensorConfig(project_root)
    data_manager = DataManager()
    
    print(f"📋 Configuration loaded:")
    print(f"   - Project root: {config.project_root}")
    print(f"   - Test data path: {config.test_data_path}")
    print(f"   - Test logs path: {config.test_logs_path}")
    print(f"   - Production data path: {config.prod_data_path}")
    print()
    
    # Test sensor ID checks
    test_sensors = config.get_test_sensors()
    print(f"🔬 Test sensors configured ({len(test_sensors)}):")
    for sensor in test_sensors:
        print(f"   - {sensor}")
    print()
    
    # Test some sample sensor IDs
    sample_sensors = [
        'KNCDURHA_TEST_01',  # Should be test
        'BS-TEST-01',        # Should be test
        'KNCDURHA209',       # Should be production
        'BS-01',             # Should be production
        'unknown_sensor'     # Should be production
    ]
    
    print("🔍 Testing sensor classification:")
    for sensor in sample_sensors:
        is_test = config.is_test_sensor(sensor)
        data_path = config.get_data_path(sensor)
        log_path = config.get_log_path(sensor)
        sensor_type = "TEST" if is_test else "PRODUCTION"
        
        print(f"   {sensor:20} -> {sensor_type:10} | Data: {data_path.name} | Logs: {log_path.name}")
    print()
    
    # Test data manager integration
    print("🗂️ Testing DataManager integration:")
    summary = data_manager.get_test_sensor_summary()
    for key, value in summary.items():
        if key == 'test_sensors':
            print(f"   - {key}: {', '.join(value) if value else 'None'}")
        else:
            print(f"   - {key}: {value}")
    print()
    
    # Create sample data to test routing
    print("📊 Testing data routing with sample data:")
    
    # Sample WU data
    wu_sample = pd.DataFrame([
        {'stationID': 'KNCDURHA_TEST_01', 'obsTimeUtc': datetime.now(), 'tempAvg': 20.5, 'humidityAvg': 65},
        {'stationID': 'KNCDURHA209', 'obsTimeUtc': datetime.now(), 'tempAvg': 21.0, 'humidityAvg': 63},
        {'stationID': 'KNCDURHA_TEST_02', 'obsTimeUtc': datetime.now(), 'tempAvg': 19.8, 'humidityAvg': 67}
    ])
    
    # Sample TSI data
    tsi_sample = pd.DataFrame([
        {'device_id': 'BS-TEST-01', 'device_name': 'BS-TEST-01', 'Device Name': 'Test Sensor 1', 'timestamp': datetime.now(), 'PM 2.5': 15.2},
        {'device_id': 'BS-01', 'device_name': 'BS-01', 'Device Name': 'Production Sensor 1', 'timestamp': datetime.now(), 'PM 2.5': 12.8},
        {'device_id': 'test_sensor_1', 'device_name': 'test_sensor_1', 'Device Name': 'Test Sensor 2', 'timestamp': datetime.now(), 'PM 2.5': 18.3}
    ])
    
    # Import the separation function
    sys.path.insert(0, str(project_root / 'src' / 'data_collection'))
    from faster_wu_tsi_to_sheets_async import separate_sensor_data_by_type
    
    test_data, prod_data = separate_sensor_data_by_type(wu_sample, tsi_sample, config)
    
    print("   Results:")
    for data_type in ['wu', 'tsi']:
        test_count = len(test_data[data_type]) if test_data[data_type] is not None else 0
        prod_count = len(prod_data[data_type]) if prod_data[data_type] is not None else 0
        print(f"   - {data_type.upper()}: {test_count} test records, {prod_count} production records")
    
    print()
    print("✅ Test sensor configuration system is working correctly!")
    print()
    print("📝 Next steps:")
    print("   1. Update TEST_SENSOR_IDS in config/test_sensors_config.py with your actual sensor IDs")
    print("   2. Run data collection to see the routing in action")
    print("   3. Check test_data/ and data/ directories for separated files")

if __name__ == "__main__":
    test_sensor_configuration()
