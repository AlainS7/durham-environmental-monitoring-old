#!/usr/bin/env python3
"""
Test Sensor Configuration for Hot Durham Project

This module handles configuration and data routing for test sensors that are
physically clustered together for validation testing.

The hardcoded approach is used to explicitly identify which sensors are in test mode,
making it clear which sensors should have their data stored separately from production.
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import os
import json

# Path to the JSON file that stores the list of test sensors
CONFIG_FILE_PATH = Path(__file__).parent.parent / 'test_data' / 'test_sensors.json'

# Global variable to hold the list of test sensors
TEST_SENSOR_IDS = []

def load_test_sensor_ids():
    """Loads the test sensor list from the JSON config file."""
    global TEST_SENSOR_IDS
    if CONFIG_FILE_PATH.exists():
        with open(CONFIG_FILE_PATH, 'r') as f:
            TEST_SENSOR_IDS = json.load(f)
    else:
        # Default list if the file doesn't exist
        TEST_SENSOR_IDS = [
            {'id': 'KNCDURHA634', 'active': True},
            {'id': 'KNCDURHA635', 'active': True},
        ]
        save_test_sensor_ids()

def save_test_sensor_ids():
    """Saves the current test sensor list to the JSON config file."""
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(TEST_SENSOR_IDS, f, indent=4)

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

# Google Drive folder configuration for test sensors (improved structure)
GOOGLE_DRIVE_CONFIG = {
    "main_folder": "HotDurham",
    "test_data_folder": "Testing",  # Renamed from Testing
    "structure": {
        "sensors": "SensorData",
        "reports": "ValidationReports", 
        "comparisons": "TestVsProduction",
        "logs": "Logs"
    }
}

class TestSensorConfig:
    """Configuration manager for test sensors."""
    
    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            # Get the project root (Hot Durham folder)
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)
            
        # Set up paths
        self.test_data_path = self.project_root / 'test_data'
        self.test_sensors_path = self.test_data_path / 'sensors'
        self.test_logs_path = self.test_data_path / 'logs'
        
        # Production paths
        self.prod_data_path = self.project_root / 'data'
        self.prod_logs_path = self.project_root / 'logs'
        
        # Ensure test directories exist
        self.test_sensors_path.mkdir(parents=True, exist_ok=True)
        self.test_logs_path.mkdir(parents=True, exist_ok=True)
    
    def is_test_sensor(self, sensor_id: str) -> bool:
        """
        Check if this sensor is one of the clustered test sensors.
        
        Args:
            sensor_id: The sensor identifier (device name, station ID, etc.)
            
        Returns:
            True if this is a test sensor, False otherwise
        """
        load_test_sensor_ids()
        return any(s['id'] == sensor_id for s in TEST_SENSOR_IDS)
    
    def get_data_path(self, sensor_id: str) -> Path:
        """
        Get the appropriate data storage path based on sensor type.
        
        Args:
            sensor_id: The sensor identifier
            
        Returns:
            Path object for where sensor data should be stored
        """
        if self.is_test_sensor(sensor_id):
            return self.test_sensors_path
        else:
            return self.prod_data_path / 'raw_pulls'
    
    def get_log_path(self, sensor_id: str) -> Path:
        """
        Get the appropriate log path based on sensor type.
        
        Args:
            sensor_id: The sensor identifier
            
        Returns:
            Path object for where sensor logs should be stored
        """
        if self.is_test_sensor(sensor_id):
            return self.test_logs_path
        else:
            return self.prod_logs_path
    
    def get_filename_prefix(self, sensor_id: str) -> str:
        """
        Get filename prefix for sensor data files.
        
        Args:
            sensor_id: The sensor identifier
            
        Returns:
            Prefix string to use in filenames
        """
        if self.is_test_sensor(sensor_id):
            return 'test_'
        else:
            return ''
    
    def add_test_sensor(self, sensor_id: str, active: bool = True) -> None:
        """
        Add a new sensor to the test list and save it to the config file.
        
        Args:
            sensor_id: The sensor identifier to add
            active: The active status of the sensor
        """
        load_test_sensor_ids()
        if not any(s['id'] == sensor_id for s in TEST_SENSOR_IDS):
            TEST_SENSOR_IDS.append({'id': sensor_id, 'active': active})
            save_test_sensor_ids()
            print(f"Sensor {sensor_id} added.")
        else:
            print(f"Sensor {sensor_id} already exists.")

    def remove_test_sensor(self, sensor_id: str) -> None:
        """
        Remove a sensor from the test list and save the updated list.
        
        Args:
            sensor_id: The sensor identifier to remove
        """
        load_test_sensor_ids()
        original_count = len(TEST_SENSOR_IDS)
        TEST_SENSOR_IDS[:] = [s for s in TEST_SENSOR_IDS if s['id'] != sensor_id]
        if len(TEST_SENSOR_IDS) < original_count:
            save_test_sensor_ids()
            print(f"Sensor {sensor_id} removed.")
        else:
            print(f"Sensor {sensor_id} not found.")

    def set_sensor_active_status(self, sensor_id: str, active=True) -> None:
        """
        Set the active status of a sensor.
        
        Args:
            sensor_id: The sensor identifier
            active: True to set as active, False to set as inactive
        """
        load_test_sensor_ids()
        sensor_found = False
        for sensor in TEST_SENSOR_IDS:
            if sensor['id'] == sensor_id:
                sensor['active'] = active
                sensor_found = True
                break
        if sensor_found:
            save_test_sensor_ids()
            status = "active" if active else "inactive"
            print(f"Sensor {sensor_id} set to {status}.")
        else:
            print(f"Sensor {sensor_id} not found.")

    def get_test_sensor_ids(self, active_only=True):
        """
        Retrieves the list of test sensor IDs from the configuration file.
        """
        load_test_sensor_ids()
        if active_only:
            return [sensor['id'] for sensor in TEST_SENSOR_IDS if sensor.get('active', True)]
        return [sensor['id'] for sensor in TEST_SENSOR_IDS]

    def get_test_sensors(self) -> List[Dict[str, Any]]:
        """Get list of all test sensor objects."""
        load_test_sensor_ids()
        return TEST_SENSOR_IDS.copy()
    
    def get_ms_station_name(self, wu_sensor_id: str) -> Optional[str]:
        """
        Get the MS station name for a Weather Underground sensor ID.
        
        Args:
            wu_sensor_id: The Weather Underground sensor identifier
            
        Returns:
            MS station name if found, None otherwise
        """
        return WU_TO_MS_MAPPING.get(wu_sensor_id)
    
    def get_drive_folder_path(self, sensor_id: str, data_type: str = "sensors") -> str:
        """
        Get the Google Drive folder path for a sensor using improved structure.
        
        Args:
            sensor_id: The sensor identifier
            data_type: Type of data ("sensors", "reports", "comparisons", "logs")
            
        Returns:
            Google Drive folder path
        """
        # Try to use improved configuration first
        try:
            from config.improved_google_drive_config import get_testing_path, get_production_path
            
            if self.is_test_sensor(sensor_id):
                # Determine sensor type (WU vs TSI)
                sensor_type = "WU" if sensor_id.startswith('KNCDURHA') else "TSI"
                return get_testing_path(data_type, sensor_type)
            else:
                # Production sensor path
                sensor_type = "WU" if sensor_id.startswith('KNCDURHA') else "TSI"
                return get_production_path('raw', sensor_type)
                
        except ImportError:
            # Fallback to legacy structure
            config = GOOGLE_DRIVE_CONFIG
            
            if self.is_test_sensor(sensor_id):
                # Test sensor path: HotDurham/Testing/SensorData/WU or TSI
                base_path = f"{config['main_folder']}/{config['test_data_folder']}/{config['structure'][data_type]}"
                
                # Determine sensor type (WU vs TSI)
                if sensor_id.startswith('KNCDURHA'):
                    sensor_type = "WU"
                else:
                    sensor_type = "TSI"
                    
                return f"{base_path}/{sensor_type}"
            else:
                # Production path (existing structure)
                sensor_type = "WU" if sensor_id.startswith('KNCDURHA') else "TSI" 
                return f"{config['main_folder']}/RawData/{sensor_type}"
    
    def get_drive_folder_path_with_date(self, sensor_id: str, date_str: str, data_type: str = "sensors") -> str:
        """
        Get Google Drive folder path with date organization using improved structure.
        
        Args:
            sensor_id: The sensor identifier
            date_str: Date string in YYYYMMDD format
            data_type: Type of data ("sensors", "reports", "comparisons", "logs")
            
        Returns:
            Google Drive folder path with date organization
        """
        # Try to use improved configuration first
        try:
            from config.improved_google_drive_config import get_testing_path, get_production_path
            
            if self.is_test_sensor(sensor_id):
                # Determine sensor type (WU vs TSI)
                sensor_type = "WU" if sensor_id.startswith('KNCDURHA') else "TSI"
                return get_testing_path(data_type, sensor_type, date_str)
            else:
                # Production sensors use base path without date organization
                sensor_type = "WU" if sensor_id.startswith('KNCDURHA') else "TSI"
                return get_production_path('raw', sensor_type)
                
        except ImportError:
            # Fallback to legacy method
            base_path = self.get_drive_folder_path(sensor_id, data_type)
            
            if self.is_test_sensor(sensor_id):
                # Add date organization for test sensors: .../2025/06-June/
                from datetime import datetime
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                year = date_obj.strftime("%Y")
                month = date_obj.strftime("%m-%B")
                return f"{base_path}/{year}/{month}"
            else:
                # Use existing production structure
                return base_path
    
    def get_drive_config(self) -> Dict[str, Any]:
        """
        Get the Google Drive configuration for this sensor configuration.
        
        Returns:
            Dictionary with Google Drive configuration
        """
        return GOOGLE_DRIVE_CONFIG.copy()
    
    def get_sensor_status(self, sensor_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status information for a sensor.
        
        Args:
            sensor_id: The sensor identifier
            
        Returns:
            Dictionary with sensor status information
        """
        is_test = self.is_test_sensor(sensor_id)
        ms_station = self.get_ms_station_name(sensor_id)
        
        status_dict = {
            'sensor_id': sensor_id,
            'is_test_sensor': is_test,
            'data_path': str(self.get_data_path(sensor_id)),
            'log_path': str(self.get_log_path(sensor_id)),
            'filename_prefix': self.get_filename_prefix(sensor_id),
            'status': 'TEST' if is_test else 'PRODUCTION',
            'drive_folder_path': self.get_drive_folder_path(sensor_id)
        }
        
        # Add MS station name if this is a WU sensor
        if ms_station:
            status_dict['ms_station'] = ms_station
            
        return status_dict
    
    def print_configuration(self) -> None:
        """Print current test sensor configuration."""
        print("\n=== Test Sensor Configuration ===")
        print(f"Project Root: {self.project_root}")
        print(f"Test Data Path: {self.test_sensors_path}")
        print(f"Test Logs Path: {self.test_logs_path}")
        print(f"Production Data Path: {self.prod_data_path}")
        print(f"\nTest Sensors ({len(TEST_SENSOR_IDS)}):")
        for sensor in TEST_SENSOR_IDS:
            ms_station = self.get_ms_station_name(sensor['id'])
            if ms_station:
                print(f"  - {sensor['id']} ({ms_station})")
            else:
                print(f"  - {sensor['id']}")
        print("=" * 40)
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the test sensor configuration and return validation results.
        
        Returns:
            Dictionary containing validation results and recommendations
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': [],
            'stats': {
                'total_test_sensors': len(TEST_SENSOR_IDS),
                'wu_test_sensors': 0,
                'tsi_test_sensors': 0,
                'unknown_type_sensors': 0
            }
        }
        
        print("🔍 Validating test sensor configuration...")
        
        # Check if any test sensors are configured
        if not TEST_SENSOR_IDS:
            validation['errors'].append("No test sensors configured in TEST_SENSOR_IDS")
            validation['is_valid'] = False
            return validation
        
        # Analyze sensor types and patterns
        wu_sensors = []
        tsi_sensors = []
        unknown_sensors = []
        
        for sensor in TEST_SENSOR_IDS:
            sensor_id = sensor['id']
            if sensor_id.startswith('KNCDURHA'):
                wu_sensors.append(sensor_id)
                validation['stats']['wu_test_sensors'] += 1
            elif any(pattern in sensor_id.upper() for pattern in ['BS-', 'TEST', 'AIR', 'QUALITY']):
                tsi_sensors.append(sensor_id)
                validation['stats']['tsi_test_sensors'] += 1
            else:
                unknown_sensors.append(sensor_id)
                validation['stats']['unknown_type_sensors'] += 1
        
        # Validate WU sensors
        if wu_sensors:
            print(f"   ✅ Found {len(wu_sensors)} Weather Underground test sensors")
            # Check WU sensor ID patterns
            for sensor_id in wu_sensors:
                if len(sensor_id) != 11 or not sensor_id.startswith('KNCDURHA'):
                    validation['warnings'].append(f"WU sensor ID '{sensor_id}' may have incorrect format (expected: KNCDURHA### pattern)")
        
        # Validate TSI sensors  
        if tsi_sensors:
            print(f"   ✅ Found {len(tsi_sensors)} TSI test sensors")
        else:
            validation['warnings'].append("No TSI test sensors configured - consider adding TSI test sensor IDs")
            validation['recommendations'].append("Add TSI test sensor IDs to TEST_SENSOR_IDS list for comprehensive testing")
        
        # Check for unknown sensor types
        if unknown_sensors:
            validation['warnings'].append(f"Found {len(unknown_sensors)} sensors with unrecognized ID patterns: {unknown_sensors}")
            validation['recommendations'].append("Review sensor IDs with unrecognized patterns and ensure they follow expected naming conventions")
        
        # Check directory structure
        try:
            if not self.test_sensors_path.exists():
                validation['warnings'].append(f"Test sensor data directory does not exist: {self.test_sensors_path}")
                validation['recommendations'].append("Test sensor data directory will be created automatically on first use")
            
            if not self.test_logs_path.exists():
                validation['warnings'].append(f"Test sensor logs directory does not exist: {self.test_logs_path}")
                validation['recommendations'].append("Test sensor logs directory will be created automatically on first use")
        except Exception as e:
            validation['errors'].append(f"Error checking directory structure: {e}")
            validation['is_valid'] = False
        
        # Check WU to MS mapping consistency
        unmapped_wu_sensors = []
        for sensor_id in wu_sensors:
            if sensor_id not in WU_TO_MS_MAPPING:
                unmapped_wu_sensors.append(sensor_id)
        
        if unmapped_wu_sensors:
            validation['warnings'].append(f"WU sensors missing MS station mapping: {unmapped_wu_sensors}")
            validation['recommendations'].append("Add missing WU sensor IDs to WU_TO_MS_MAPPING dictionary")
        
        # Generate final recommendations
        if validation['stats']['wu_test_sensors'] > 0 and validation['stats']['tsi_test_sensors'] == 0:
            validation['recommendations'].append("Consider adding TSI test sensors for comprehensive air quality testing")
        elif validation['stats']['tsi_test_sensors'] > 0 and validation['stats']['wu_test_sensors'] == 0:
            validation['recommendations'].append("Consider adding Weather Underground test sensors for comprehensive weather monitoring")
        
        # Print validation summary
        if validation['is_valid']:
            if not validation['warnings']:
                print("   ✅ Configuration validation passed with no issues")
            else:
                print(f"   ⚠️ Configuration validation passed with {len(validation['warnings'])} warnings")
        else:
            print(f"   ❌ Configuration validation failed with {len(validation['errors'])} errors")
        
        return validation


# Global instance for easy importing
test_config = TestSensorConfig()
# Load the initial sensor list at startup
load_test_sensor_ids()

# Convenience functions for easy importing
def is_test_sensor(sensor_id: str) -> bool:
    """Check if sensor is a test sensor."""
    return test_config.is_test_sensor(sensor_id)

def get_data_path(sensor_id: str) -> Path:
    """Get data path for sensor."""
    return test_config.get_data_path(sensor_id)

def get_log_path(sensor_id: str) -> Path:
    """Get log path for sensor."""
    return test_config.get_log_path(sensor_id)

def get_filename_prefix(sensor_id: str) -> str:
    """Get filename prefix for sensor."""
    return test_config.get_filename_prefix(sensor_id)

def get_ms_station_name(wu_sensor_id: str) -> Optional[str]:
    """Get MS station name for WU sensor."""
    return test_config.get_ms_station_name(wu_sensor_id)

def get_drive_folder_path(sensor_id: str, data_type: str = "sensors") -> str:
    """Get Google Drive folder path for sensor."""
    return test_config.get_drive_folder_path(sensor_id, data_type)

def get_drive_folder_path_with_date(sensor_id: str, date_str: str, data_type: str = "sensors") -> str:
    """Get Google Drive folder path with date organization."""
    return test_config.get_drive_folder_path_with_date(sensor_id, date_str, data_type)


if __name__ == "__main__":
    # Test the configuration
    test_config.print_configuration()
    
    # Test some example sensors
    print("\n=== Example Sensor Status ===")
    example_sensors = [
        'KNCDURHA209',  # Production WU sensor
        'KNCDURHA634',  # Test WU sensor (MS-09)
        'KNCDURHA648',  # Test WU sensor (MS-22)
        'BS-01',  # Production TSI sensor
        # 'BS-TEST-01'  # Test TSI sensor (uncomment when you have TSI test sensors)
    ]
    
    for sensor in example_sensors:
        status = test_config.get_sensor_status(sensor)
        ms_info = f" ({status['ms_station']})" if 'ms_station' in status else ""
        print(f"{sensor}{ms_info}: {status['status']} -> {status['data_path']}")
