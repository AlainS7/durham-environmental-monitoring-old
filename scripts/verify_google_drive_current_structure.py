#!/usr/bin/env python3
"""
Google Drive Folder Structure Verification Script
===============================================

This script checks the actual Google Drive folder structure being used
and can optionally create a test upload to verify the new paths work.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_current_upload_summary():
    """Check what the current upload summary shows."""
    print("🔍 CHECKING CURRENT UPLOAD SUMMARY")
    print("=" * 50)
    
    summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
    
    if not summary_file.exists():
        print("❌ No upload summary file found")
        return None
    
    try:
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        upload_info = data.get('upload_info', {})
        upload_folder = upload_info.get('upload_folder', 'Unknown')
        upload_timestamp = upload_info.get('upload_timestamp', 'Unknown')
        
        print(f"📁 Current Upload Folder: {upload_folder}")
        print(f"📅 Last Upload: {upload_timestamp}")
        
        # Check if it's using new or old structure
        if 'TestData_ValidationCluster' in upload_folder:
            print("⚠️  Status: Still using OLD structure!")
            return 'old'
        elif 'Testing/ValidationReports' in upload_folder:
            print("✅ Status: Using NEW structure correctly!")
            return 'new_correct'
        elif 'Testing/Visualizations' in upload_folder:
            print("🟡 Status: Partially migrated (Testing/ but wrong subfolder)")
            return 'partial'
        else:
            print(f"❓ Status: Unknown structure - {upload_folder}")
            return 'unknown'
            
    except Exception as e:
        print(f"❌ Error reading upload summary: {e}")
        return None

def check_enhanced_upload_summaries():
    """Check enhanced production upload summaries."""
    print("\n🔍 CHECKING ENHANCED PRODUCTION UPLOADS")
    print("=" * 50)
    
    enhanced_dir = project_root / 'sensor_visualizations' / 'enhanced_production_sensors'
    
    if not enhanced_dir.exists():
        print("❌ No enhanced production sensors directory found")
        return
    
    # Find the most recent enhanced upload summary
    summary_files = list(enhanced_dir.glob("ENHANCED_UPLOAD_SUMMARY_*.txt"))
    
    if not summary_files:
        print("❌ No enhanced upload summary files found")
        return
    
    # Get the most recent file
    latest_file = max(summary_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Latest Enhanced Upload: {latest_file.name}")
    
    try:
        with open(latest_file, 'r') as f:
            content = f.read()
        
        # Look for Google Drive location
        lines = content.split('\n')
        drive_location = None
        
        for line in lines:
            if 'HotDurham/' in line and 'Location:' in line:
                drive_location = line.strip()
                break
            elif 'Folder: HotDurham/' in line:
                drive_location = line.strip()
                break
        
        if drive_location:
            print(f"📁 Enhanced Upload Location: {drive_location}")
            
            if 'ProductionData_SensorAnalysis' in drive_location:
                print("⚠️  Enhanced Status: Still using OLD production structure!")
                return 'old'
            elif 'Production/Reports' in drive_location:
                print("✅ Enhanced Status: Using NEW production structure!")
                return 'new'
            else:
                print("❓ Enhanced Status: Unknown structure")
                return 'unknown'
        else:
            print("❓ Could not find drive location in enhanced summary")
            return None
            
    except Exception as e:
        print(f"❌ Error reading enhanced summary: {e}")
        return None

def get_current_google_drive_config():
    """Check what Google Drive configuration is being used."""
    print("\n🔍 CHECKING GOOGLE DRIVE CONFIGURATION")
    print("=" * 50)
    
    try:
        from config.improved_google_drive_config import get_testing_path, get_production_path
        
        # Test new configuration functions
        test_path = get_testing_path('reports', 'WU', '20250614')
        prod_path = get_production_path('reports')
        
        print(f"✅ Improved config available:")
        print(f"   Test reports path: {test_path}")
        print(f"   Production reports path: {prod_path}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Improved config not available: {e}")
        return False

def test_visualization_upload_path():
    """Test what path would be used for a new visualization upload."""
    print("\n🧪 TESTING VISUALIZATION UPLOAD PATH")
    print("=" * 50)
    
    try:
        # Try to determine what path would be used
        from config.improved_google_drive_config import get_testing_path
        
        # For test visualizations
        test_viz_path = get_testing_path('reports', 'WU', datetime.now().strftime('%Y%m%d'))
        print(f"📊 Test Visualization Path: {test_viz_path}")
        
        # For production reports
        from config.improved_google_drive_config import get_production_path
        prod_report_path = get_production_path('reports')
        print(f"📈 Production Report Path: {prod_report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing upload paths: {e}")
        return False

def create_test_upload_to_verify_structure():
    """Create a small test file and upload it to verify the new structure works."""
    print("\n🚀 CREATING TEST UPLOAD TO VERIFY NEW STRUCTURE")
    print("=" * 50)
    
    try:
        # Create a small test file
        test_content = f"""# Google Drive Structure Test
        
Test file created on: {datetime.now().isoformat()}
Purpose: Verify new Google Drive folder structure is working

This file was uploaded to test the migration from:
- OLD: HotDurham/TestData_ValidationCluster/Visualizations/
- NEW: HotDurham/Testing/ValidationReports/

If you see this file in the NEW location, the migration is working correctly!
"""
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_structure_test.md', delete=False) as f:
            f.write(test_content)
            temp_file_path = Path(f.name)
        
        print(f"📄 Created test file: {temp_file_path.name}")
        
        # Try to upload using the enhanced manager
        try:
            from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
            from config.improved_google_drive_config import get_testing_path
            
            manager = get_enhanced_drive_manager()
            test_folder = get_testing_path('reports', 'TEST', datetime.now().strftime('%Y%m%d'))
            
            print(f"🎯 Target folder: {test_folder}")
            
            if manager and manager.drive_service:
                success = manager.upload_file_sync(temp_file_path, test_folder)
                
                if success:
                    print("✅ Test upload SUCCESS! New structure is working!")
                    print(f"   File uploaded to: {test_folder}")
                    
                    # Update upload summary to reflect this test
                    summary_data = {
                        "upload_info": {
                            "upload_timestamp": datetime.now().isoformat(),
                            "upload_folder": f"{test_folder}/structure_test",
                            "total_files_uploaded": 1,
                            "project": "Hot Durham Structure Test"
                        },
                        "test_info": {
                            "purpose": "Verify new Google Drive structure",
                            "migration_status": "Testing new paths",
                            "old_structure": "HotDurham/TestData_ValidationCluster/Visualizations/",
                            "new_structure": f"{test_folder}/"
                        }
                    }
                    
                    summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
                    with open(summary_file, 'w') as f:
                        json.dump(summary_data, f, indent=2)
                    
                    print("📄 Updated upload summary with test results")
                    
                else:
                    print("❌ Test upload FAILED")
                    
            else:
                print("❌ Enhanced drive manager not available")
                
        except Exception as e:
            print(f"❌ Error during test upload: {e}")
        
        # Clean up temp file
        try:
            temp_file_path.unlink()
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error creating test upload: {e}")

def show_expected_vs_actual_structure():
    """Show what the structure should be vs what we're currently seeing."""
    print("\n📋 EXPECTED VS ACTUAL STRUCTURE")
    print("=" * 50)
    
    print("🎯 EXPECTED NEW STRUCTURE:")
    print("   HotDurham/")
    print("   ├── Production/")
    print("   │   ├── RawData/WU/")
    print("   │   ├── RawData/TSI/")
    print("   │   ├── Processed/")
    print("   │   └── Reports/           ← Production visualizations should go here")
    print("   ├── Testing/")
    print("   │   ├── SensorData/WU/")
    print("   │   ├── SensorData/TSI/")
    print("   │   ├── ValidationReports/ ← Test visualizations should go here")
    print("   │   └── Logs/")
    print("   └── Archives/")
    
    print("\n📊 CURRENT UPLOAD EVIDENCE:")
    
    # Check current upload summary
    summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
    if summary_file.exists():
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)
            upload_folder = data.get('upload_info', {}).get('upload_folder', 'Unknown')
            print(f"   Last upload went to: {upload_folder}")
        except:
            print("   Could not read upload summary")
    
    # Check enhanced summaries
    enhanced_dir = project_root / 'sensor_visualizations' / 'enhanced_production_sensors'
    if enhanced_dir.exists():
        summary_files = list(enhanced_dir.glob("ENHANCED_UPLOAD_SUMMARY_*.txt"))
        if summary_files:
            latest_file = max(summary_files, key=lambda x: x.stat().st_mtime)
            try:
                with open(latest_file, 'r') as f:
                    content = f.read()
                for line in content.split('\n'):
                    if 'HotDurham/' in line and ('Location:' in line or 'Folder:' in line):
                        print(f"   Enhanced uploads going to: {line.strip()}")
                        break
            except:
                print("   Could not read enhanced summary")

def main():
    """Main verification function."""
    print("🔍 Google Drive Folder Structure Verification")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Check current upload summary
    current_status = check_current_upload_summary()
    
    # Step 2: Check enhanced production uploads
    enhanced_status = check_enhanced_upload_summaries()
    
    # Step 3: Check configuration
    config_available = get_current_google_drive_config()
    
    # Step 4: Test upload paths
    if config_available:
        test_visualization_upload_path()
    
    # Step 5: Show expected vs actual
    show_expected_vs_actual_structure()
    
    # Step 6: Overall assessment
    print("\n🎯 OVERALL ASSESSMENT")
    print("=" * 50)
    
    if current_status == 'new_correct' and enhanced_status == 'new':
        print("✅ MIGRATION COMPLETE - All uploads using new structure!")
    elif current_status == 'partial' or enhanced_status == 'old':
        print("🟡 MIGRATION PARTIAL - Some components still using old paths")
        print("\n🔧 RECOMMENDED ACTION:")
        print("   1. Run a new visualization generation to test current paths")
        print("   2. If uploads still go to old structure, update the upload scripts")
        print("   3. Create test upload to verify new structure works")
        
        # Offer to create test upload
        response = input("\n❓ Create test upload to verify new structure? (y/n): ")
        if response.lower() == 'y':
            create_test_upload_to_verify_structure()
    else:
        print("❌ MIGRATION STATUS UNCLEAR - Manual investigation needed")

if __name__ == "__main__":
    main()
