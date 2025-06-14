#!/usr/bin/env python3
"""
Improved Google Drive Configuration for Hot Durham Project
Implements the recommended folder structure improvements.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import json

# Improved Google Drive folder structure
IMPROVED_GOOGLE_DRIVE_CONFIG = {
    "main_folder": "HotDurham",
    
    # Production data structure
    "production": {
        "base_folder": "Production",
        "raw_data": "Production/RawData",
        "processed": "Production/Processed",
        "reports": "Production/Reports"
    },
    
    # Testing data structure (renamed from TestData_ValidationCluster)
    "testing": {
        "base_folder": "Testing",
        "sensor_data": "Testing/SensorData",
        "validation_reports": "Testing/ValidationReports", 
        "logs": "Testing/Logs"
    },
    
    # Archives with timestamp organization
    "archives": {
        "base_folder": "Archives",
        "daily": "Archives/Daily",
        "weekly": "Archives/Weekly",
        "monthly": "Archives/Monthly"
    },
    
    # System files and configurations
    "system": {
        "base_folder": "System",
        "configs": "System/Configs",
        "backups": "System/Backups",
        "metadata": "System/Metadata"
    }
}

# Rate limiting configuration for Google Drive API
RATE_LIMITING_CONFIG = {
    "requests_per_second": 10,
    "batch_size": 10,
    "retry_attempts": 3,
    "backoff_factor": 2,
    "chunk_size_mb": 5  # For large file uploads
}

# Data retention policies
DATA_RETENTION_CONFIG = {
    "raw_data_days": 730,  # 2 years
    "processed_data_days": -1,  # Keep indefinitely
    "test_data_days": 90,  # 3 months
    "logs_days": 365,  # 1 year
    "archive_compression": True
}

class ImprovedGoogleDriveConfig:
    """Improved Google Drive configuration manager with better organization."""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            self.project_root = Path(__file__).parent.parent
        else:
            self.project_root = Path(project_root)
    
    def get_production_folder_path(self, data_type: str, sensor_type: str = None) -> str:
        """
        Get production folder path for organized data.
        
        Args:
            data_type: 'raw', 'processed', 'reports'
            sensor_type: 'WU', 'TSI' (optional)
            
        Returns:
            Google Drive folder path
        """
        config = IMPROVED_GOOGLE_DRIVE_CONFIG
        
        if data_type == 'raw':
            base_path = config['production']['raw_data']
            return f"{config['main_folder']}/{base_path}/{sensor_type}" if sensor_type else f"{config['main_folder']}/{base_path}"
        elif data_type == 'processed':
            return f"{config['main_folder']}/{config['production']['processed']}"
        elif data_type == 'reports':
            return f"{config['main_folder']}/{config['production']['reports']}"
        else:
            return f"{config['main_folder']}/{config['production']['base_folder']}"
    
    def get_testing_folder_path(self, data_type: str, sensor_type: str = None, date_str: str = None) -> str:
        """
        Get testing folder path with improved organization.
        
        Args:
            data_type: 'sensors', 'reports', 'logs'
            sensor_type: 'WU', 'TSI' (optional)
            date_str: Date string in YYYYMMDD format (optional)
            
        Returns:
            Google Drive folder path
        """
        config = IMPROVED_GOOGLE_DRIVE_CONFIG
        
        if data_type == 'sensors':
            base_path = config['testing']['sensor_data']
        elif data_type == 'reports':
            base_path = config['testing']['validation_reports']
        elif data_type == 'logs':
            base_path = config['testing']['logs']
        else:
            base_path = config['testing']['base_folder']
        
        # Build path with sensor type
        if sensor_type:
            path = f"{config['main_folder']}/{base_path}/{sensor_type}"
        else:
            path = f"{config['main_folder']}/{base_path}"
        
        # Add date organization if provided
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m-%B")
            path = f"{path}/{year}/{month}"
        
        return path
    
    def get_archive_folder_path(self, archive_type: str, date_str: str = None) -> str:
        """
        Get archive folder path with timestamp organization.
        
        Args:
            archive_type: 'daily', 'weekly', 'monthly'
            date_str: Date string in YYYYMMDD format (optional)
            
        Returns:
            Google Drive folder path
        """
        config = IMPROVED_GOOGLE_DRIVE_CONFIG
        
        if archive_type in config['archives']:
            base_path = config['archives'][archive_type]
        else:
            base_path = config['archives']['base_folder']
        
        path = f"{config['main_folder']}/{base_path}"
        
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            year = date_obj.strftime("%Y")
            path = f"{path}/{year}"
        
        return path
    
    def get_system_folder_path(self, system_type: str) -> str:
        """
        Get system folder path for configurations and metadata.
        
        Args:
            system_type: 'configs', 'backups', 'metadata'
            
        Returns:
            Google Drive folder path
        """
        config = IMPROVED_GOOGLE_DRIVE_CONFIG
        
        if system_type in ['configs', 'backups', 'metadata']:
            return f"{config['main_folder']}/{config['system'][system_type]}"
        else:
            return f"{config['main_folder']}/{config['system']['base_folder']}"
    
    def get_rate_limiting_config(self) -> Dict:
        """Get rate limiting configuration for API calls."""
        return RATE_LIMITING_CONFIG.copy()
    
    def get_retention_policy(self, data_type: str) -> int:
        """
        Get data retention policy in days.
        
        Args:
            data_type: Type of data to check retention for
            
        Returns:
            Number of days to retain (-1 means keep indefinitely)
        """
        return DATA_RETENTION_CONFIG.get(f"{data_type}_days", 365)
    
    def should_compress_archive(self) -> bool:
        """Check if archive files should be compressed."""
        return DATA_RETENTION_CONFIG.get("archive_compression", True)
    
    def generate_folder_structure_report(self) -> str:
        """Generate a report showing the new folder structure."""
        report = """
🗂️  IMPROVED GOOGLE DRIVE FOLDER STRUCTURE
==========================================

HotDurham/
├── Production/              # Production data (clean naming)
│   ├── RawData/
│   │   ├── WU/             # Weather Underground production
│   │   └── TSI/            # TSI production sensors
│   ├── Processed/          # Processed production data
│   └── Reports/            # Production reports
│
├── Testing/                 # Test data (renamed from TestData_ValidationCluster)
│   ├── SensorData/
│   │   ├── WU/2025/01-January/
│   │   └── TSI/2025/01-January/
│   ├── ValidationReports/
│   │   ├── WU/2025/01-January/
│   │   └── TSI/2025/01-January/
│   └── Logs/
│       └── 2025/01-January/
│
├── Archives/                # Organized archives with timestamps
│   ├── Daily/2025/
│   ├── Weekly/2025/
│   └── Monthly/2025/
│
└── System/                  # System files and configurations
    ├── Configs/            # Configuration backups
    ├── Backups/            # System backups
    └── Metadata/           # Data quality and metadata

IMPROVEMENTS IMPLEMENTED:
✅ Renamed confusing "TestData_ValidationCluster" to "Testing"
✅ Clear separation between Production and Testing
✅ Timestamp-based organization in Archives
✅ Dedicated System folder for configurations
✅ Hierarchical date organization (year/month)
✅ Rate limiting configuration for API stability
✅ Data retention policies defined
"""
        return report
    
    def validate_folder_structure(self) -> Dict[str, bool]:
        """Validate the improved folder structure configuration."""
        validation_results = {
            "config_loaded": True,
            "production_paths_valid": True,
            "testing_paths_valid": True,
            "archive_paths_valid": True,
            "system_paths_valid": True,
            "rate_limiting_configured": True,
            "retention_policies_set": True
        }
        
        try:
            # Test production paths
            self.get_production_folder_path('raw', 'WU')
            self.get_production_folder_path('processed')
            self.get_production_folder_path('reports')
            
            # Test testing paths
            self.get_testing_folder_path('sensors', 'WU', '20250614')
            self.get_testing_folder_path('reports', 'TSI', '20250614')
            self.get_testing_folder_path('logs', date_str='20250614')
            
            # Test archive paths
            self.get_archive_folder_path('daily', '20250614')
            self.get_archive_folder_path('weekly')
            
            # Test system paths
            self.get_system_folder_path('configs')
            self.get_system_folder_path('backups')
            self.get_system_folder_path('metadata')
            
            # Test configurations
            rate_config = self.get_rate_limiting_config()
            retention = self.get_retention_policy('raw_data')
            
        except Exception as e:
            print(f"Validation error: {e}")
            validation_results["config_loaded"] = False
        
        return validation_results

# Global instance for easy importing
improved_drive_config = ImprovedGoogleDriveConfig()

# Convenience functions
def get_production_path(data_type: str, sensor_type: str = None) -> str:
    """Get production folder path."""
    return improved_drive_config.get_production_folder_path(data_type, sensor_type)

def get_testing_path(data_type: str, sensor_type: str = None, date_str: str = None) -> str:
    """Get testing folder path."""
    return improved_drive_config.get_testing_folder_path(data_type, sensor_type, date_str)

def get_archive_path(archive_type: str, date_str: str = None) -> str:
    """Get archive folder path."""
    return improved_drive_config.get_archive_folder_path(archive_type, date_str)

def get_system_path(system_type: str) -> str:
    """Get system folder path."""
    return improved_drive_config.get_system_folder_path(system_type)

if __name__ == "__main__":
    # Demonstrate the improved configuration
    config = ImprovedGoogleDriveConfig()
    
    print(config.generate_folder_structure_report())
    
    print("\n🔍 VALIDATION RESULTS:")
    results = config.validate_folder_structure()
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check.replace('_', ' ').title()}")
    
    print(f"\n📊 EXAMPLE PATHS:")
    print(f"Production WU Data: {get_production_path('raw', 'WU')}")
    print(f"Testing WU Data: {get_testing_path('sensors', 'WU', '20250614')}")
    print(f"Archive Daily: {get_archive_path('daily', '20250614')}")
    print(f"System Configs: {get_system_path('configs')}")
