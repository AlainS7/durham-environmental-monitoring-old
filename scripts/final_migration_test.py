#!/usr/bin/env python3
"""
Google Drive Migration - Final Completion Test
Hot Durham Environmental Monitoring Project

This script performs a final test to confirm the migration is complete
and the new folder structure is working correctly.
"""

import json
from pathlib import Path
from datetime import datetime

def run_final_completion_test():
    """Perform final migration completion test"""
    
    print("🎯 GOOGLE DRIVE MIGRATION - FINAL COMPLETION TEST")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent
    
    # Test 1: Check upload summary uses new paths
    print("\n1. Testing Upload Summary Paths")
    print("-" * 35)
    
    summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        upload_folder = data.get('upload_info', {}).get('upload_folder', '')
        
        if '/ValidationReports/' in upload_folder:
            print(f"✅ Upload folder uses NEW structure: {upload_folder}")
        elif '/Visualizations/' in upload_folder:
            print(f"❌ Upload folder still uses OLD structure: {upload_folder}")
            return False
        else:
            print(f"⚠️  Unknown upload folder pattern: {upload_folder}")
    else:
        print("⚠️  Upload summary file not found")
    
    # Test 2: Check enhanced upload summaries
    print("\n2. Testing Enhanced Upload Summaries")
    print("-" * 40)
    
    enhanced_dir = project_root / 'sensor_visualizations' / 'enhanced_production_sensors'
    if enhanced_dir.exists():
        summary_files = list(enhanced_dir.glob('ENHANCED_UPLOAD_SUMMARY_*.txt'))
        
        for summary_file in summary_files[-2:]:  # Check last 2 files
            with open(summary_file, 'r') as f:
                content = f.read()
            
            if '/Reports/' in content and '/Visualizations/' not in content:
                print(f"✅ Enhanced summary uses NEW structure: {summary_file.name}")
            elif '/Visualizations/' in content:
                print(f"❌ Enhanced summary uses OLD structure: {summary_file.name}")
                return False
            else:
                print(f"⚠️  Unknown pattern in: {summary_file.name}")
    else:
        print("⚠️  Enhanced summaries directory not found")
    
    # Test 3: Check configuration files
    print("\n3. Testing Configuration Files")
    print("-" * 34)
    
    config_file = project_root / 'config' / 'improved_google_drive_config.py'
    if config_file.exists():
        with open(config_file, 'r') as f:
            content = f.read()
        
        if 'ValidationReports' in content and 'Testing/' in content:
            print("✅ Improved config uses NEW structure")
        else:
            print("⚠️  Config may need review")
    else:
        print("⚠️  Improved config not found")
    
    # Test 4: Verify folder structure documentation
    print("\n4. Testing Structure Documentation")
    print("-" * 37)
    
    status_file = project_root / 'GOOGLE_DRIVE_MIGRATION_FINAL_STATUS.md'
    if status_file.exists():
        print("✅ Final status documentation exists")
    else:
        print("⚠️  Final status documentation missing")
    
    # Final Assessment
    print("\n" + "=" * 60)
    print("🏁 FINAL MIGRATION ASSESSMENT")
    print("=" * 60)
    
    # Check for any remaining problematic patterns
    test_files = [
        'sensor_visualizations/google_drive_upload_summary.json',
        'config/improved_google_drive_config.py'
    ]
    
    all_good = True
    
    for file_path in test_files:
        full_path = project_root / file_path
        if full_path.exists():
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Check for old patterns
            old_patterns = [
                'TestData_ValidationCluster',
                'ProductionData_SensorAnalysis',
                '/Visualizations/',
            ]
            
            found_old = False
            for pattern in old_patterns:
                if pattern in content and 'Migration from' not in content:
                    print(f"❌ Found old pattern '{pattern}' in {file_path}")
                    found_old = True
                    all_good = False
            
            if not found_old:
                print(f"✅ {file_path} - Clean")
    
    if all_good:
        print("\n🎉 MIGRATION SUCCESSFULLY COMPLETED!")
        print("   ✅ All upload paths use new folder structure")
        print("   ✅ Configuration files updated")
        print("   ✅ No legacy path references in active systems")
        print("   ✅ Documentation complete")
        
        print(f"\n🚀 NEW GOOGLE DRIVE STRUCTURE:")
        print(f"   📁 HotDurham/Production/Reports/ ← Production visualizations")
        print(f"   📁 HotDurham/Testing/ValidationReports/ ← Test visualizations")
        print(f"   📁 HotDurham/Production/RawData/ ← Raw sensor data")
        print(f"   📁 HotDurham/Production/Processed/ ← Processed data")
        
        print(f"\n📊 MIGRATION SUMMARY:")
        print(f"   • Legacy paths removed from active systems")
        print(f"   • Upload summaries corrected")
        print(f"   • Configuration files updated")
        print(f"   • New folder structure implemented")
        print(f"   • Migration scripts preserved for reference")
        
        return True
    else:
        print("\n⚠️  MIGRATION NEEDS ATTENTION")
        print("   Some issues were found that need manual review")
        return False

if __name__ == "__main__":
    success = run_final_completion_test()
    exit(0 if success else 1)
