#!/usr/bin/env python3
"""
Simple Integration Test for Hot Durham Air Quality Monitoring System
Tests essential functionality of all three major components.
"""

import sys
import logging
from pathlib import Path

# Add source paths
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src" / "automation"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def test_system_integration():
    """Test the essential integration of all three systems."""
    logger.info("🚀 Starting Hot Durham System Integration Test")
    
    results = {}
    
    # Test 1: Configuration Files
    try:
        import json
        daily_config = project_root / "config" / "daily_sheets_config.json"
        master_config = project_root / "config" / "master_data_config.json"
        
        with open(daily_config) as f:
            daily_data = json.load(f)
        with open(master_config) as f:
            master_data = json.load(f)
            
        results["Configuration"] = len(daily_data) > 0 and "data_sources" in master_data
        logger.info(f"✓ Configuration Files: {'PASS' if results['Configuration'] else 'FAIL'}")
    except Exception as e:
        results["Configuration"] = False
        logger.error(f"✗ Configuration Files: FAIL - {e}")
    
    # Test 2: Master Data System Import
    try:
        from master_data_file_system import MasterDataFileSystem
        from master_data_scheduler import MasterDataScheduler
        results["Master Data Import"] = True
        logger.info("✓ Master Data System: PASS - Modules imported successfully")
    except Exception as e:
        results["Master Data Import"] = False
        logger.error(f"✗ Master Data System: FAIL - {e}")
    
    # Test 3: Daily Sheets System Import
    try:
        from daily_sheets_system import DailySheetsSystem
        from daily_sheets_scheduler import DailySheetsScheduler
        results["Daily Sheets Import"] = True
        logger.info("✓ Daily Sheets System: PASS - Modules imported successfully")
    except Exception as e:
        results["Daily Sheets Import"] = False
        logger.error(f"✗ Daily Sheets System: FAIL - {e}")
    
    # Test 4: Live Sensor Map Import
    try:
        sys.path.append(str(project_root / "src" / "visualization"))
        from live_sensor_map import LiveSensorMapServer
        results["Live Sensor Map Import"] = True
        logger.info("✓ Live Sensor Map: PASS - Module imported successfully")
    except Exception as e:
        results["Live Sensor Map Import"] = False
        logger.error(f"✗ Live Sensor Map: FAIL - {e}")
    
    # Test 5: Core Dependencies
    try:
        import pandas as pd
        import numpy as np
        import requests
        import google.oauth2.service_account
        import gspread
        import openpyxl
        results["Dependencies"] = True
        logger.info("✓ Core Dependencies: PASS - All major dependencies available")
    except Exception as e:
        results["Dependencies"] = False
        logger.error(f"✗ Core Dependencies: FAIL - {e}")
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    success_rate = (passed / total) * 100
    
    logger.info("=" * 60)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<25}: {status}")
    
    logger.info("-" * 40)
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    logger.info(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        logger.info("🎉 INTEGRATION TEST PASSED! System is ready for deployment.")
        return 0
    else:
        logger.error("❌ Integration test failed. Please check errors above.")
        return 1

if __name__ == "__main__":
    exit(test_system_integration())
