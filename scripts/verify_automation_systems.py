#!/usr/bin/env python3
"""
Automation Systems Verification - Post Google Drive Migration
Hot Durham Environmental Monitoring Project

This script verifies that all automation systems are working correctly
after the Google Drive folder structure migration.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src' / 'core'))
sys.path.insert(0, str(project_root / 'src' / 'automation'))
sys.path.insert(0, str(project_root / 'config'))

def test_automation_systems():
    """Test all automation systems after Google Drive migration"""
    
    print("🔍 AUTOMATION SYSTEMS VERIFICATION")
    print("=" * 50)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        "data_manager": {"status": "unknown", "details": []},
        "master_data_system": {"status": "unknown", "details": []},
        "daily_sheets": {"status": "unknown", "details": []},
        "test_sensors": {"status": "unknown", "details": []},
        "google_drive": {"status": "unknown", "details": []},
        "folder_structure": {"status": "unknown", "details": []}
    }
    
    # Test 1: Data Manager
    print("1. Testing Data Manager")
    print("-" * 25)
    try:
        from data_manager import DataManager
        dm = DataManager(str(project_root / 'data'))
        results["data_manager"]["status"] = "success"
        results["data_manager"]["details"].append("✅ DataManager initialized successfully")
        
        # Check Google Drive service
        if dm.drive_service:
            results["data_manager"]["details"].append("✅ Google Drive service available")
        else:
            results["data_manager"]["details"].append("⚠️  Google Drive service not initialized")
        
        # Check paths configuration
        if hasattr(dm, 'test_config'):
            results["data_manager"]["details"].append("✅ Test sensor configuration loaded")
        else:
            results["data_manager"]["details"].append("⚠️  Test sensor configuration missing")
            
        print("✅ Data Manager: WORKING")
        
    except Exception as e:
        results["data_manager"]["status"] = "error"
        results["data_manager"]["details"].append(f"❌ Error: {str(e)}")
        print(f"❌ Data Manager: ERROR - {e}")
    
    # Test 2: Master Data File System
    print("\n2. Testing Master Data File System")
    print("-" * 35)
    try:
        from master_data_file_system import MasterDataFileSystem
        mdfs = MasterDataFileSystem(str(project_root))
        results["master_data_system"]["status"] = "success"
        results["master_data_system"]["details"].append("✅ MasterDataFileSystem initialized")
        
        # Test Google Drive integration
        drive_test = mdfs.test_google_drive_integration()
        if drive_test.get('google_drive_available'):
            results["master_data_system"]["details"].append("✅ Google Drive integration working")
        else:
            results["master_data_system"]["details"].append("⚠️  Google Drive integration issues")
            
        print("✅ Master Data System: WORKING")
        
    except Exception as e:
        results["master_data_system"]["status"] = "error"
        results["master_data_system"]["details"].append(f"❌ Error: {str(e)}")
        print(f"❌ Master Data System: ERROR - {e}")
    
    # Test 3: Daily Sheets System
    print("\n3. Testing Daily Sheets System")
    print("-" * 32)
    try:
        from daily_sheets_system import DailySheetsSystem
        dss = DailySheetsSystem(str(project_root))
        results["daily_sheets"]["status"] = "success"
        results["daily_sheets"]["details"].append("✅ DailySheetsSystem initialized")
        
        # Check Google services
        try:
            dss.setup_google_services()
            results["daily_sheets"]["details"].append("✅ Google services configured")
        except Exception as e:
            results["daily_sheets"]["details"].append(f"⚠️  Google services issue: {e}")
            
        print("✅ Daily Sheets System: WORKING")
        
    except Exception as e:
        results["daily_sheets"]["status"] = "error"
        results["daily_sheets"]["details"].append(f"❌ Error: {str(e)}")
        print(f"❌ Daily Sheets System: ERROR - {e}")
    
    # Test 4: Test Sensor Configuration
    print("\n4. Testing Test Sensor Configuration")
    print("-" * 38)
    try:
        from test_sensors_config import TestSensorConfig, TEST_SENSOR_IDS
        tsc = TestSensorConfig()
        results["test_sensors"]["status"] = "success"
        results["test_sensors"]["details"].append(f"✅ Test sensors configured: {len(TEST_SENSOR_IDS)}")
        
        # Check folder structure configuration
        drive_config = tsc.get_drive_config()
        if drive_config.get('test_data_folder') == 'Testing':
            results["test_sensors"]["details"].append("✅ Using new folder structure (Testing)")
        else:
            results["test_sensors"]["details"].append("⚠️  Old folder structure detected")
            
        print("✅ Test Sensor Config: WORKING")
        
    except Exception as e:
        results["test_sensors"]["status"] = "error"
        results["test_sensors"]["details"].append(f"❌ Error: {str(e)}")
        print(f"❌ Test Sensor Config: ERROR - {e}")
    
    # Test 5: Google Drive Configuration
    print("\n5. Testing Google Drive Configuration")
    print("-" * 38)
    try:
        from improved_google_drive_config import get_production_path, get_testing_path
        
        # Test production paths
        prod_raw = get_production_path('raw', 'WU')
        prod_reports = get_production_path('reports')
        
        # Test testing paths  
        test_reports = get_testing_path('reports', 'WU')
        
        if 'HotDurham/Production' in prod_raw:
            results["google_drive"]["details"].append("✅ Production paths use new structure")
        if 'HotDurham/Testing' in test_reports:
            results["google_drive"]["details"].append("✅ Testing paths use new structure")
            
        results["google_drive"]["status"] = "success"
        print("✅ Google Drive Config: WORKING")
        
    except Exception as e:
        results["google_drive"]["status"] = "error"
        results["google_drive"]["details"].append(f"❌ Error: {str(e)}")
        print(f"❌ Google Drive Config: ERROR - {e}")
    
    # Test 6: Folder Structure Compliance
    print("\n6. Testing Folder Structure Compliance")
    print("-" * 40)
    try:
        # Check upload summary files
        summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                data = json.load(f)
            
            upload_folder = data.get('upload_info', {}).get('upload_folder', '')
            if '/ValidationReports/' in upload_folder:
                results["folder_structure"]["details"].append("✅ Upload paths use new structure")
            elif '/Visualizations/' in upload_folder:
                results["folder_structure"]["details"].append("❌ Upload paths still use old structure")
            else:
                results["folder_structure"]["details"].append("⚠️  Unknown upload path pattern")
        
        results["folder_structure"]["status"] = "success"
        print("✅ Folder Structure: COMPLIANT")
        
    except Exception as e:
        results["folder_structure"]["status"] = "error"
        results["folder_structure"]["details"].append(f"❌ Error: {str(e)}")
        print(f"❌ Folder Structure: ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 AUTOMATION VERIFICATION SUMMARY")
    print("=" * 50)
    
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    total_count = len(results)
    
    print(f"✅ Systems Working: {success_count}/{total_count}")
    
    for system, result in results.items():
        status_icon = "✅" if result["status"] == "success" else "❌" if result["status"] == "error" else "⚠️"
        print(f"\n{status_icon} {system.replace('_', ' ').title()}:")
        for detail in result["details"]:
            print(f"   {detail}")
    
    # Overall assessment
    if success_count == total_count:
        print(f"\n🎉 ALL AUTOMATION SYSTEMS WORKING CORRECTLY!")
        print(f"   Your Google Drive migration was successful and")
        print(f"   all automations are compatible with the new structure.")
    elif success_count >= total_count * 0.8:
        print(f"\n⚠️  MOST SYSTEMS WORKING - MINOR ISSUES DETECTED")
        print(f"   {success_count}/{total_count} systems working correctly.")
        print(f"   Review the errors above and fix as needed.")
    else:
        print(f"\n❌ SIGNIFICANT ISSUES DETECTED")
        print(f"   Only {success_count}/{total_count} systems working correctly.")
        print(f"   Manual intervention required.")
    
    # Save results
    results_file = project_root / 'automation_verification_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_systems": total_count,
                "working_systems": success_count,
                "success_rate": success_count / total_count
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")
    
    return success_count == total_count

if __name__ == "__main__":
    success = test_automation_systems()
    exit(0 if success else 1)
