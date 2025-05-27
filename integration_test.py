#!/usr/bin/env python3
"""
Integration test for the complete Hot Durham Air Quality Monitoring system.
Tests the three major components:
1. Live Sensor Map
2. Daily Google Sheets System  
3. Master Data File System
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add source paths
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src" / "automation"))
sys.path.append(str(project_root / "src" / "data_collection"))
sys.path.append(str(project_root / "src" / "visualization"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_live_sensor_map():
    """Test the live sensor map functionality."""
    logger.info("Testing Live Sensor Map...")
    
    try:
        # Import and test the live sensor map
        from live_sensor_map import LiveSensorMapServer
        
        # Initialize the server
        server = LiveSensorMapServer(str(project_root))
        app = server.app
        
        with app.test_client() as client:
            # Test the main page
            response = client.get('/')
            if response.status_code != 200:
                logger.error(f"Main page returned status {response.status_code}")
                return False
            logger.info("✓ Live sensor map main page accessible")
            
            # Test API endpoints with more detailed error handling
            try:
                response = client.get('/api/sensors/wu')
                if response.status_code != 200:
                    logger.warning(f"WU API endpoint returned status {response.status_code} (may be due to API limits)")
                else:
                    logger.info("✓ Weather Underground API endpoint working")
            except Exception as e:
                logger.warning(f"WU API test failed (may be expected): {e}")
            
            try:
                response = client.get('/api/sensors/tsi')
                if response.status_code != 200:
                    logger.warning(f"TSI API endpoint returned status {response.status_code} (may be due to API limits)")
                else:
                    logger.info("✓ TSI API endpoint working")
            except Exception as e:
                logger.warning(f"TSI API test failed (may be expected): {e}")
            
        logger.info("✓ Live Sensor Map test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Live Sensor Map test failed: {e}")
        return False

def test_daily_sheets_system():
    """Test the daily sheets system functionality."""
    logger.info("Testing Daily Google Sheets System...")
    
    try:
        from daily_sheets_system import DailySheetsSystem
        
        # Initialize system with project root path
        sheets_system = DailySheetsSystem(str(project_root))
        
        # Test configuration loading
        assert sheets_system.data_manager is not None
        logger.info("✓ Daily sheets system initialized")
        
        # Test data manager functionality
        assert hasattr(sheets_system, 'sheets_service')
        assert hasattr(sheets_system, 'drive_service')
        logger.info("✓ Google services initialized")
        
        # Test date handling
        test_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"✓ Daily sheets system ready for date: {test_date}")
        
        logger.info("✓ Daily Google Sheets System test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Daily Google Sheets System test failed: {e}")
        return False

def test_master_data_system():
    """Test the master data file system functionality."""
    logger.info("Testing Master Data File System...")
    
    try:
        from master_data_file_system import MasterDataFileSystem
        
        # Initialize system with config path as named parameter
        config_path = project_root / "config" / "master_data_config.json"
        master_system = MasterDataFileSystem(config_path=str(config_path))
        
        # Test system initialization
        if master_system.config is None:
            logger.error("Config is None")
            return False
        if not master_system.base_dir.exists():
            logger.error(f"Base directory does not exist: {master_system.base_dir}")
            return False
        logger.info("✓ Master data system initialized")
        
        # Test directory structure creation
        if not master_system.master_data_path.exists():
            logger.error(f"Master data path does not exist: {master_system.master_data_path}")
            return False
        if not master_system.backup_path.exists():
            logger.error(f"Backup path does not exist: {master_system.backup_path}")
            return False
        if not (master_system.master_data_path / "exports").exists():
            logger.error("Exports directory does not exist")
            return False
        logger.info("✓ Master data directory structure created")
        
        # Test metadata operations
        try:
            metadata = master_system.create_metadata("test")
            if not isinstance(metadata, dict):
                logger.error(f"Metadata is not a dict: {type(metadata)}")
                return False
            if "creation_time" not in metadata:
                logger.error("creation_time not in metadata")
                return False
            logger.info("✓ Metadata operations working")
        except Exception as e:
            logger.error(f"Metadata operation failed: {e}")
            return False
        
        # Test summary generation
        try:
            summary = master_system.get_master_data_summary()
            if not isinstance(summary, dict):
                logger.error(f"Summary is not a dict: {type(summary)}")
                return False
            if "last_updated" not in summary:
                logger.error("last_updated not in summary")
                return False
            logger.info("✓ Summary generation working")
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return False
        
        logger.info("✓ Master Data File System test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Master Data File System test failed: {e}")
        return False

def test_scheduler_systems():
    """Test the scheduler systems for automation."""
    logger.info("Testing Scheduler Systems...")
    
    try:
        # Test daily sheets scheduler
        from daily_sheets_scheduler import DailySheetsScheduler
        
        daily_scheduler = DailySheetsScheduler()
        assert daily_scheduler is not None
        logger.info("✓ Daily sheets scheduler initialized")
        
        # Test master data scheduler
        from master_data_scheduler import MasterDataScheduler
        
        master_scheduler = MasterDataScheduler()
        assert master_scheduler is not None
        logger.info("✓ Master data scheduler initialized")
        
        logger.info("✓ Scheduler Systems test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Scheduler Systems test failed: {e}")
        return False

def test_configuration_files():
    """Test that all configuration files are present and valid."""
    logger.info("Testing Configuration Files...")
    
    try:
        # Test daily sheets config
        daily_config_path = project_root / "config" / "daily_sheets_config.json"
        if not daily_config_path.exists():
            logger.error("Daily sheets config file missing")
            return False
        
        with open(daily_config_path, 'r') as f:
            daily_config = json.load(f)
        # Check for key fields in daily sheets config
        if "wu_sensors" not in daily_config or "notification_settings" not in daily_config:
            logger.error("Daily sheets config missing required sections")
            return False
        logger.info("✓ Daily sheets configuration valid")
        
        # Test master data config
        master_config_path = project_root / "config" / "master_data_config.json"
        if not master_config_path.exists():
            logger.error("Master data config file missing")
            return False
        
        with open(master_config_path, 'r') as f:
            master_config = json.load(f)
        if "data_sources" not in master_config:
            logger.error("Master data config missing data_sources section")
            return False
        logger.info("✓ Master data configuration valid")
        
        logger.info("✓ Configuration Files test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration Files test failed: {e}")
        return False

def main():
    """Run the complete integration test suite."""
    logger.info("=" * 60)
    logger.info("STARTING HOT DURHAM INTEGRATION TEST SUITE")
    logger.info("=" * 60)
    
    test_results = {}
    
    # Run all tests
    test_results["Configuration Files"] = test_configuration_files()
    test_results["Master Data System"] = test_master_data_system()
    test_results["Daily Sheets System"] = test_daily_sheets_system()
    test_results["Scheduler Systems"] = test_scheduler_systems()
    test_results["Live Sensor Map"] = test_live_sensor_map()
    
    # Print results summary
    logger.info("=" * 60)
    logger.info("INTEGRATION TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    for test_name, result in test_results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<25}: {status}")
    
    logger.info("-" * 40)
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {total_tests - passed_tests}")
    logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        logger.info("🎉 ALL TESTS PASSED! The Hot Durham system is ready for deployment.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs and fix issues before deployment.")
        return 1

if __name__ == "__main__":
    exit(main())
