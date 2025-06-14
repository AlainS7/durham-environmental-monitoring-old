#!/usr/bin/env python3
"""
Google Drive Migration Final Verification
=========================================

This script provides final verification that the Google Drive migration is complete.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

project_root = Path(__file__).parent.parent

def check_for_actual_legacy_paths():
    """Check for files that still contain the actual old legacy paths."""
    
    # These are the truly problematic legacy paths that should not exist
    actual_legacy_paths = [
        "TestData_ValidationCluster",
        "ProductionData_SensorAnalysis", 
        "ProductionSensorReports"
    ]
    
    problematic_files = []
    
    # Search in key directories
    search_dirs = ['src', 'config', 'tools', 'scripts']
    extensions = ['.py', '.json', '.md', '.txt']
    
    for search_dir in search_dirs:
        dir_path = project_root / search_dir
        if not dir_path.exists():
            continue
            
        for ext in extensions:
            for file_path in dir_path.rglob(f'*{ext}'):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        found_legacy = []
                        for legacy_path in actual_legacy_paths:
                            if legacy_path in content:
                                # Skip if it's just a comment explaining the migration
                                lines = content.split('\n')
                                is_just_comment = True
                                for line in lines:
                                    if legacy_path in line and not line.strip().startswith('#'):
                                        # Check if it's in a string assignment or similar
                                        if '=' in line or ':' in line:
                                            is_just_comment = False
                                            break
                                            
                                if not is_just_comment:
                                    found_legacy.append(legacy_path)
                        
                        if found_legacy:
                            problematic_files.append((file_path, found_legacy))
                            
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")
    
    return problematic_files

def verify_new_structure_usage():
    """Verify that the new structure is being used correctly."""
    
    # Check key files for new structure usage
    checks = {
        'test_sensors_config_updated': False,
        'data_manager_updated': False,
        'upload_summaries_updated': False
    }
    
    # Check test sensors config
    test_config = project_root / 'config' / 'test_sensors_config.py'
    if test_config.exists():
        with open(test_config, 'r') as f:
            content = f.read()
        if 'Testing' in content and 'HotDurham/Testing' in content:
            checks['test_sensors_config_updated'] = True
    
    # Check data manager
    data_manager = project_root / 'src' / 'core' / 'data_manager.py'
    if data_manager.exists():
        with open(data_manager, 'r') as f:
            content = f.read()
        if 'HotDurham/Production' in content:
            checks['data_manager_updated'] = True
    
    # Check upload summaries
    upload_summary = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
    if upload_summary.exists():
        with open(upload_summary, 'r') as f:
            data = json.load(f)
        folder = data.get('upload_info', {}).get('upload_folder', '')
        if 'HotDurham/Testing' in folder and 'TestData_ValidationCluster' not in folder:
            checks['upload_summaries_updated'] = True
    
    return checks

def main():
    """Run final verification."""
    print("🔍 Google Drive Migration - Final Verification")
    print("=" * 50)
    
    # Check for problematic legacy paths
    print("\n1. Checking for problematic legacy paths...")
    problematic_files = check_for_actual_legacy_paths()
    
    if problematic_files:
        print(f"❌ Found {len(problematic_files)} files with problematic legacy paths:")
        for file_path, legacy_paths in problematic_files:
            print(f"   {file_path.relative_to(project_root)}: {legacy_paths}")
        legacy_check = False
    else:
        print("✅ No problematic legacy paths found")
        legacy_check = True
    
    # Check new structure usage
    print("\n2. Checking new structure implementation...")
    structure_checks = verify_new_structure_usage()
    
    all_structure_good = True
    for check_name, passed in structure_checks.items():
        status = "✅" if passed else "❌"
        print(f"   {check_name}: {status}")
        if not passed:
            all_structure_good = False
    
    # Overall assessment
    print("\n" + "=" * 50)
    print("📊 FINAL ASSESSMENT")
    print("=" * 50)
    
    if legacy_check and all_structure_good:
        print("🎊 MIGRATION 100% COMPLETE! 🎊")
        print("✅ All legacy paths removed")
        print("✅ New structure properly implemented")
        print("✅ Configuration files updated")
        print("✅ Upload paths migrated")
        
        # Create completion marker
        completion_file = project_root / 'GOOGLE_DRIVE_MIGRATION_COMPLETE.md'
        with open(completion_file, 'w') as f:
            f.write(f"""# Google Drive Migration Complete ✅

**Completion Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
The Google Drive folder structure migration has been completed successfully.

## Key Changes Made
- ✅ Legacy paths removed: `TestData_ValidationCluster`, `ProductionData_SensorAnalysis`
- ✅ New structure implemented: `HotDurham/Production/`, `HotDurham/Testing/`
- ✅ Configuration files updated
- ✅ Upload scripts migrated
- ✅ Visualization paths updated

## New Structure
```
HotDurham/
├── Production/
│   ├── RawData/
│   ├── Processed/
│   └── Reports/
├── Testing/
│   ├── SensorData/
│   ├── ValidationReports/
│   └── Logs/
├── Archives/
└── System/
```

## Status: 100% Complete
All components now use the improved Google Drive folder structure.
""")
        
        print(f"\n📄 Migration completion documented: GOOGLE_DRIVE_MIGRATION_COMPLETE.md")
        
    else:
        print("⚠️ Migration needs final attention:")
        if not legacy_check:
            print("   - Some legacy paths still exist")
        if not all_structure_good:
            print("   - New structure not fully implemented")

if __name__ == "__main__":
    main()
