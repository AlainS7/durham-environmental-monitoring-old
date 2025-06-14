#!/usr/bin/env python3
"""
Test Sensor Configuration for Hot Durham Project

This module handles configuration and data routing for test sensors that are
physically clustered together for validation testing.

The hardcoded approach is used to explicitly identify which sensors are in test mode,
making it clear which sensors should have their data stored separately from production.
"""

from pathlib import Path
from typing import List, Dict, Optional
import os

# List your test sensor IDs here - update this list with your actual test sensor identifiers
TEST_SENSOR_IDS = [
    # Weather Underground test sensors (clustered for validation testing)
    # Format: WU_ID (MS Station Name)
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
    # Uncomment and replace with your actual TSI test sensor IDs:
    # 'test_sensor_1',
    # 'test_sensor_2', 
    # 'test_sensor_3',
    # 'BS-TEST-01',
    # 'BS-TEST-02',
    
    # Example: If you have TSI sensors for testing, add their device IDs here:
    # 'your_tsi_test_device_id_1',
    # 'your_tsi_test_device_id_2',
    
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
    
    def __init__(self, project_root: str = None):
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
        return sensor_id in TEST_SENSOR_IDS
    
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
    
    def add_test_sensor(self, sensor_id: str) -> None:
        """
        Add a new sensor to the test list.
        
        Note: This modifies the in-memory list but doesn't persist changes.
        To permanently add sensors, update the TEST_SENSOR_IDS list in this file.
        
        Args:
            sensor_id: The sensor identifier to add
        """
        global TEST_SENSOR_IDS
        if sensor_id not in TEST_SENSOR_IDS:
            TEST_SENSOR_IDS.append(sensor_id)
            print(f"Added {sensor_id} to test sensors list (in-memory only)")
    
    def remove_test_sensor(self, sensor_id: str) -> None:
        """
        Remove a sensor from the test list (promote to production).
        
        Note: This modifies the in-memory list but doesn't persist changes.
        To permanently remove sensors, update the TEST_SENSOR_IDS list in this file.
        
        Args:
            sensor_id: The sensor identifier to remove
        """
        global TEST_SENSOR_IDS
        if sensor_id in TEST_SENSOR_IDS:
            TEST_SENSOR_IDS.remove(sensor_id)
            print(f"Removed {sensor_id} from test sensors list (in-memory only)")
    
    def get_test_sensors(self) -> List[str]:
        """Get list of all test sensor IDs."""
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
    
    def get_drive_config(self) -> Dict[str, any]:
        """
        Get the Google Drive configuration for this sensor configuration.
        
        Returns:
            Dictionary with Google Drive configuration
        """
        return GOOGLE_DRIVE_CONFIG.copy()
    
    def get_sensor_status(self, sensor_id: str) -> Dict[str, any]:
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
        for sensor_id in TEST_SENSOR_IDS:
            ms_station = self.get_ms_station_name(sensor_id)
            if ms_station:
                print(f"  - {sensor_id} ({ms_station})")
            else:
                print(f"  - {sensor_id}")
        print("=" * 40)


# Global instance for easy importing
test_config = TestSensorConfig()

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
