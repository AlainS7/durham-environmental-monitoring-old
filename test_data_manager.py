#!/usr/bin/env python3
"""
Test script for the data management system
"""

import sys
import os
from pathlib import Path

# Add the scripts directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

def test_data_manager_imports():
    """Test that all imports work correctly"""
    try:
        from data_manager import DataManager
        print("✅ DataManager import successful")
        return True
    except ImportError as e:
        print(f"❌ DataManager import failed: {e}")
        return False

def test_data_manager_initialization():
    """Test that DataManager can be initialized"""
    try:
        from data_manager import DataManager
        
        # Initialize with a test directory
        test_dir = Path(__file__).parent / "test_data"
        dm = DataManager(str(test_dir))
        print("✅ DataManager initialization successful")
        print(f"   Base directory: {dm.base_dir}")
        
        # Check if directories were created
        expected_dirs = [
            "raw_pulls/wu/2024", "raw_pulls/wu/2025",
            "raw_pulls/tsi/2024", "raw_pulls/tsi/2025", 
            "processed/weekly_summaries",
            "processed/monthly_summaries",
            "processed/annual_summaries",
            "backup/google_drive_sync",
            "backup/local_archive",
            "temp"
        ]
        
        all_exist = True
        for dir_path in expected_dirs:
            full_path = dm.base_dir / dir_path
            if not full_path.exists():
                print(f"❌ Missing directory: {dir_path}")
                all_exist = False
            else:
                print(f"✅ Directory exists: {dir_path}")
        
        return all_exist
        
    except Exception as e:
        print(f"❌ DataManager initialization failed: {e}")
        return False

def test_google_drive_integration():
    """Test Google Drive integration setup"""
    try:
        from data_manager import DataManager, GOOGLE_DRIVE_AVAILABLE
        
        print(f"Google Drive integration available: {GOOGLE_DRIVE_AVAILABLE}")
        
        if not GOOGLE_DRIVE_AVAILABLE:
            print("⚠️ Google Drive integration not available (install google-api-python-client)")
        else:
            print("✅ Google Drive integration libraries available")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Drive integration test failed: {e}")
        return False

def test_schedule_integration():
    """Test schedule integration"""
    try:
        from data_manager import DataManager, SCHEDULE_AVAILABLE
        
        print(f"Schedule module available: {SCHEDULE_AVAILABLE}")
        
        if not SCHEDULE_AVAILABLE:
            print("⚠️ Schedule module not available")
        else:
            print("✅ Schedule module available")
        
        return True
        
    except Exception as e:
        print(f"❌ Schedule integration test failed: {e}")
        return False

def test_data_manager_methods():
    """Test key DataManager methods"""
    try:
        from data_manager import DataManager
        
        test_dir = Path(__file__).parent / "test_data"
        dm = DataManager(str(test_dir))
        
        # Test week info
        year, week, week_str = dm.get_week_info()
        print(f"✅ Week info: Year {year}, Week {week}, String {week_str}")
        
        # Test file paths generation
        paths = dm.get_file_paths("wu", "20241201", "20241207", "csv")
        print(f"✅ File paths generated: {len(paths)} paths")
        for key, path in paths.items():
            print(f"   {key}: {path}")
        
        # Test data integrity check
        report = dm.verify_data_integrity()
        print(f"✅ Data integrity check completed")
        print(f"   Total files: {report['total_files']}")
        print(f"   Total size: {report['total_size_mb']:.2f} MB")
        print(f"   Sources: {list(report['sources'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ DataManager methods test failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data directory"""
    try:
        import shutil
        test_dir = Path(__file__).parent / "test_data"
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("✅ Test data cleaned up")
        return True
    except Exception as e:
        print(f"⚠️ Failed to clean up test data: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Hot Durham Data Management System")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_data_manager_imports),
        ("Initialization Tests", test_data_manager_initialization),
        ("Google Drive Integration", test_google_drive_integration),
        ("Schedule Integration", test_schedule_integration),
        ("Method Tests", test_data_manager_methods),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Data management system is ready.")
    else:
        print("⚠️ Some tests failed. Please check the output above.")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    cleanup_test_data()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
