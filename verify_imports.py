#!/usr/bin/env python3
"""
Import verification script for the reorganized Hot Durham project.

This script tests that all modules can be imported correctly with the new
project structure.
"""

import sys
from pathlib import Path

# Add all src directories to Python path
project_root = Path(__file__).parent
src_paths = [
    project_root / "src" / "core",
    project_root / "src" / "analysis", 
    project_root / "src" / "data_collection",
    project_root / "src" / "automation",
    project_root / "src" / "gui",
    project_root / "src" / "utils"
]

for path in src_paths:
    if path.exists():
        sys.path.append(str(path))

def test_imports():
    """Test all module imports"""
    
    modules_to_test = [
        ("data_manager", "DataManager"),
        ("backup_system", "BackupSystem"),
        ("anomaly_detection_and_trend_analysis", "AnomalyDetectionSystem"),
        ("prioritized_data_pull_manager", "PrioritizedDataPullManager"),
        ("production_data_pull_executor", "ProductionDataPullExecutor"),
        ("complete_analysis_suite", "CompleteAnalysisSuite"),
        ("enhanced_data_analysis", None),
        # Skip automated_data_pull as it imports modules that check for credentials
        # ("automated_data_pull", None),
        ("status_check", None),
    ]
    
    results = []
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name)
            if class_name:
                getattr(module, class_name)
            print(f"✅ {module_name}: Import successful")
            results.append(True)
        except Exception as e:
            print(f"❌ {module_name}: Import failed - {e}")
            results.append(False)
    
    total = len(results)
    passed = sum(results)
    print(f"\n📊 Import Summary: {passed}/{total} modules imported successfully")
    
    if passed == total:
        print("🎉 All imports working correctly!")
        return True
    else:
        print("⚠️ Some imports failed - check the errors above")
        return False

if __name__ == "__main__":
    print("🔍 Testing imports for reorganized Hot Durham project...")
    print(f"📁 Project root: {project_root}")
    print()
    
    success = test_imports()
    sys.exit(0 if success else 1)
