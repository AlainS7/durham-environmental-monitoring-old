#!/usr/bin/env python3
"""
Integration Test for Hot Durham New Features

This script tests the integration of all new features to ensure they work
together correctly with the existing system.

Tests:
- Anomaly detection system functionality
- Prioritized data pull manager
- Backup system operations
- Production data pull executor
- Complete analysis suite integration
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src" / "core"))
sys.path.append(str(project_root / "src" / "analysis"))
sys.path.append(str(project_root / "src" / "data_collection"))
sys.path.append(str(project_root / "src" / "automation"))
sys.path.append(str(project_root / "src" / "gui"))
sys.path.append(str(project_root / "src" / "utils"))

def test_imports():
    """Test that all new modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from anomaly_detection_and_trend_analysis import AnomalyDetectionSystem
        print("  ✅ Anomaly detection system imported")
    except ImportError as e:
        print(f"  ❌ Failed to import anomaly detection: {e}")
        return False
    
    try:
        from prioritized_data_pull_manager import PrioritizedDataPullManager
        print("  ✅ Prioritized data pull manager imported")
    except ImportError as e:
        print(f"  ❌ Failed to import priority manager: {e}")
        return False
    
    try:
        from backup_system import BackupSystem
        print("  ✅ Backup system imported")
    except ImportError as e:
        print(f"  ❌ Failed to import backup system: {e}")
        return False
    
    try:
        from production_data_pull_executor import ProductionDataPullExecutor
        print("  ✅ Production data pull executor imported")
    except ImportError as e:
        print(f"  ❌ Failed to import production executor: {e}")
        return False
    
    try:
        from complete_analysis_suite import CompleteAnalysisSuite
        print("  ✅ Complete analysis suite imported")
    except ImportError as e:
        print(f"  ❌ Failed to import analysis suite: {e}")
        return False
    
    try:
        # Import from data_fetching_functions in scripts if available
        from data_fetching_functions import fetch_tsi_data, fetch_wu_data
        print("  ✅ Data fetching functions imported")
    except ImportError:
        print("Warning: Could not import data fetching functions")
    
    return True

def test_anomaly_detection():
    """Test anomaly detection system initialization and basic functionality"""
    print("\n🔍 Testing anomaly detection system...")
    
    try:
        from anomaly_detection_and_trend_analysis import AnomalyDetectionSystem
        
        # Test initialization
        detector = AnomalyDetectionSystem(str(project_root))
        print("  ✅ Anomaly detection system initialized")
        
        # Test configuration loading
        config = detector.load_configuration()
        if config and 'analysis_parameters' in config:
            print("  ✅ Configuration loaded successfully")
        else:
            print("  ⚠️ Configuration created (first run)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Anomaly detection test failed: {e}")
        return False

def test_priority_manager():
    """Test prioritized data pull manager"""
    print("\n🔍 Testing prioritized data pull manager...")
    
    try:
        from prioritized_data_pull_manager import PrioritizedDataPullManager
        
        # Test initialization
        priority_manager = PrioritizedDataPullManager(str(project_root))
        print("  ✅ Priority manager initialized")
        
        # Test schedule generation
        schedule = priority_manager.generate_pull_schedule()
        if (schedule and 'priority_queues' in schedule and 
            all(priority in schedule['priority_queues'] for priority in ['critical', 'high', 'standard'])):
            print("  ✅ Pull schedule generated successfully")
        else:
            print("  ❌ Pull schedule generation failed")
            return False
        
        # Test sensor classification
        test_sensors = [
            {'device_name': 'Indoor Air Quality Monitor', 'location': 'Office'},
            {'device_name': 'Outdoor Weather Station', 'location': 'Ambient'}
        ]
        
        # Test classification of individual sensors
        classification1 = priority_manager.classify_sensor_priority('tsi', test_sensors[0])
        classification2 = priority_manager.classify_sensor_priority('wu', test_sensors[1])
        if classification1 and classification2:
            print("  ✅ Sensor classification working")
        else:
            print("  ❌ Sensor classification failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Priority manager test failed: {e}")
        return False

def test_backup_system():
    """Test backup system functionality"""
    print("\n🔍 Testing backup system...")
    
    try:
        from backup_system import BackupSystem
        
        # Test initialization
        backup_system = BackupSystem(str(project_root))
        print("  ✅ Backup system initialized")
        
        # Test status check
        status = backup_system.get_backup_status()
        if status and 'backup_root' in status:
            print("  ✅ Backup status check working")
        else:
            print("  ❌ Backup status check failed")
            return False
        
        # Test configuration backup (safe test)
        success = backup_system.backup_configurations()
        if success:
            print("  ✅ Configuration backup test successful")
        else:
            print("  ❌ Configuration backup test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backup system test failed: {e}")
        return False

def test_production_executor():
    """Test production data pull executor"""
    print("\n🔍 Testing production data pull executor...")
    
    try:
        from production_data_pull_executor import ProductionDataPullExecutor
        
        # Test initialization (without actually executing pulls)
        executor = ProductionDataPullExecutor(str(project_root))
        print("  ✅ Production executor initialized")
        
        # Test schedule generation
        schedule = executor.get_optimal_pull_schedule()
        if schedule:
            print("  ✅ Optimal pull schedule generated")
        else:
            print("  ❌ Schedule generation failed")
            return False
        
        # Test status check
        status = executor.get_execution_status()
        if status is not None:
            print("  ✅ Execution status check working")
        else:
            print("  ❌ Execution status check failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Production executor test failed: {e}")
        return False

def test_analysis_suite():
    """Test complete analysis suite"""
    print("\n🔍 Testing complete analysis suite...")
    
    try:
        from complete_analysis_suite import CompleteAnalysisSuite
        
        # Test initialization
        suite = CompleteAnalysisSuite(str(project_root))
        print("  ✅ Analysis suite initialized")
        
        # Test component checking
        components = suite.check_available_components()
        if components:
            print(f"  ✅ Component check successful ({len(components)} components available)")
        else:
            print("  ❌ Component check failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Analysis suite test failed: {e}")
        return False

def test_integration():
    """Test integration between components"""
    print("\n🔍 Testing component integration...")
    
    try:
        # Test that data manager can be accessed by new components
        from data_manager import DataManager
        from prioritized_data_pull_manager import PrioritizedDataPullManager
        
        data_manager = DataManager(str(project_root))
        priority_manager = PrioritizedDataPullManager(str(project_root))
        
        # Test that they can work together
        if hasattr(priority_manager, 'base_dir') and hasattr(data_manager, 'base_dir'):
            print("  ✅ Base directory configuration consistent")
        else:
            print("  ❌ Base directory configuration inconsistent")
            return False
        
        # Test configuration compatibility
        from backup_system import BackupSystem
        backup_system = BackupSystem(str(project_root))
        
        if backup_system.base_dir == priority_manager.base_dir:
            print("  ✅ Component path consistency verified")
        else:
            print("  ❌ Component path inconsistency detected")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False

def test_requirements_availability():
    """Test that all new requirements are available"""
    print("\n🔍 Testing new requirements availability...")
    
    required_packages = [
        'matplotlib',
        'seaborn', 
        'scipy',
        'sklearn',  # Note: scikit-learn is imported as sklearn
        'plotly',
        'kaleido'
    ]
    
    available_packages = []
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            available_packages.append(package)
            print(f"  ✅ {package} available")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package} missing")
    
    if missing_packages:
        print(f"  ⚠️ Missing packages: {', '.join(missing_packages)}")
        print("  💡 Run: pip install -r requirements.txt")
        return False
    else:
        print(f"  ✅ All {len(available_packages)} required packages available")
        return True

def main():
    """Run all integration tests"""
    print("🧪 Hot Durham New Features Integration Test")
    print("=" * 50)
    print(f"📅 Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Project root: {project_root}")
    print()
    
    test_results = []
    
    # Run all tests
    test_results.append(("Requirements", test_requirements_availability()))
    test_results.append(("Imports", test_imports()))
    test_results.append(("Anomaly Detection", test_anomaly_detection()))
    test_results.append(("Priority Manager", test_priority_manager()))
    test_results.append(("Backup System", test_backup_system()))
    test_results.append(("Production Executor", test_production_executor()))
    test_results.append(("Analysis Suite", test_analysis_suite()))
    test_results.append(("Integration", test_integration()))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status_icon = "✅" if result else "❌"
        print(f"{status_icon} {test_name}")
        if result:
            passed_tests += 1
    
    print()
    print(f"Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All integration tests passed! New features ready for production.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review and fix issues before production use.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
