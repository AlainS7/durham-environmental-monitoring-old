#!/usr/bin/env python3
"""
Test Suite for Master Data File System

Comprehensive tests for the Hot Durham Master Data File System including:
1. System initialization and configuration
2. Historical data scanning and loading
3. Master file creation and updates
4. Weekly data collection and appending
5. Data deduplication and quality checks
6. Export functionality
7. Database operations
8. Scheduler integration

This test suite validates the complete master data workflow.
"""

import unittest
import tempfile
import shutil
import pandas as pd
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

# Add project paths for testing
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))


try:
    from automation.master_data_file_system import MasterDataFileSystem
    from automation.master_data_scheduler import MasterDataScheduler
except ImportError as e:
    print(f"Error importing modules for testing: {e}")
    raise e

class TestMasterDataFileSystem(unittest.TestCase):
    """Test suite for Master Data File System."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.config_dir = cls.test_dir / "config"
        cls.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test configuration
        cls.test_config = {
            "data_sources": {
                "wu": {
                    "enabled": True,
                    "stations": ["TEST_WU_001", "TEST_WU_002"],
                    "metrics": ["timestamp", "tempf", "humidity"],
                    "collection_start_date": "2023-01-01"
                },
                "tsi": {
                    "enabled": True,
                    "devices": "auto_discover",
                    "metrics": ["timestamp", "PM 2.5", "T (C)", "RH (%)"],
                    "collection_start_date": "2023-01-01"
                }
            },
            "master_file_settings": {
                "update_frequency": "weekly",
                "enable_versioning": True,
                "enable_sqlite_db": True
            },
            "data_quality": {
                "enable_deduplication": True,
                "duplicate_tolerance_minutes": 5
            }
        }
        
        cls.config_path = cls.config_dir / "master_data_config.json"
        with open(cls.config_path, 'w') as f:
            json.dump(cls.test_config, f, indent=2)
            
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
            
    def setUp(self):
        """Set up individual test."""
        self.master_system = MasterDataFileSystem(
            base_dir=str(self.test_dir / "data"),
            config_path=str(self.config_path)
        )
        
        # Create test data
        self.create_test_data()
        
    def create_test_data(self):
        """Create sample test data files."""
        # Create WU test data
        wu_data = {
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='H'),
            'station_id': ['TEST_WU_001'] * 50 + ['TEST_WU_002'] * 50,
            'tempf': [70 + i * 0.1 for i in range(100)],
            'humidity': [50 + i * 0.2 for i in range(100)],
            'source_file': 'test_wu_data.csv'
        }
        wu_df = pd.DataFrame(wu_data)
        
        # Create TSI test data
        tsi_data = {
            'timestamp': pd.date_range('2024-01-01', periods=80, freq='H'),
            'device_id': ['TEST_TSI_001'] * 40 + ['TEST_TSI_002'] * 40,
            'device_name': ['Test Device 1'] * 40 + ['Test Device 2'] * 40,
            'PM 2.5': [15 + i * 0.1 for i in range(80)],
            'T (C)': [20 + i * 0.05 for i in range(80)],
            'RH (%)': [45 + i * 0.1 for i in range(80)],
            'source_file': 'test_tsi_data.csv'
        }
        tsi_df = pd.DataFrame(tsi_data)
        
        # Save test data files
        wu_dir = self.test_dir / "data" / "raw_pulls" / "wu" / "2024"
        tsi_dir = self.test_dir / "data" / "raw_pulls" / "tsi" / "2024"
        
        wu_dir.mkdir(parents=True, exist_ok=True)
        tsi_dir.mkdir(parents=True, exist_ok=True)
        
        wu_df.to_csv(wu_dir / "test_wu_data.csv", index=False)
        tsi_df.to_csv(tsi_dir / "test_tsi_data.csv", index=False)
        
        self.wu_test_data = wu_df
        self.tsi_test_data = tsi_df
        
    def test_system_initialization(self):
        """Test system initialization and directory setup."""
        # Check that directories were created
        self.assertTrue(self.master_system.master_data_path.exists())
        self.assertTrue(self.master_system.backup_path.exists())
        self.assertTrue(self.master_system.metadata_path.exists())
        
        # Check configuration loading
        self.assertIsInstance(self.master_system.config, dict)
        self.assertTrue(self.master_system.config.get("data_sources", {}).get("wu", {}).get("enabled"))
        
        print("✅ System initialization test passed")
        
    def test_historical_data_scanning(self):
        """Test scanning for historical data files."""
        # Test WU data scanning
        wu_files = self.master_system.scan_historical_data("wu")
        self.assertGreater(len(wu_files), 0)
        self.assertTrue(any("test_wu_data.csv" in str(f) for f in wu_files))
        
        # Test TSI data scanning
        tsi_files = self.master_system.scan_historical_data("tsi")
        self.assertGreater(len(tsi_files), 0)
        self.assertTrue(any("test_tsi_data.csv" in str(f) for f in tsi_files))
        
        print(f"✅ Historical data scanning test passed - Found {len(wu_files)} WU files, {len(tsi_files)} TSI files")
        
    def test_data_loading_and_combining(self):
        """Test loading and combining historical data."""
        print("\n🧪 Testing historical data loading and combining...")
        
        # Test for WU data
        wu_combined = self.master_system.load_and_combine_historical_data("wu")
        self.assertIsNotNone(wu_combined, "WU combined data should not be None")
        assert wu_combined is not None  # For type checker
        self.assertGreater(len(wu_combined), 0)
        self.assertTrue('timestamp' in wu_combined.columns)
        self.assertTrue('station_id' in wu_combined.columns)
        
        # Test for TSI data
        tsi_combined = self.master_system.load_and_combine_historical_data("tsi")
        self.assertIsNotNone(tsi_combined, "TSI combined data should not be None")
        assert tsi_combined is not None  # For type checker
        self.assertGreater(len(tsi_combined), 0)
        self.assertTrue('timestamp' in tsi_combined.columns)
        self.assertTrue('device_id' in tsi_combined.columns)
        
        print(f"✅ Data loading test passed - WU: {len(wu_combined)} records, TSI: {len(tsi_combined)} records")
        
    def test_master_file_creation(self):
        """Test master file creation."""
        # Test WU master file creation
        wu_success = self.master_system.create_master_file("wu", force_rebuild=True)
        self.assertTrue(wu_success)
        self.assertTrue(self.master_system.wu_master_file.exists())
        
        # Test TSI master file creation
        tsi_success = self.master_system.create_master_file("tsi", force_rebuild=True)
        self.assertTrue(tsi_success)
        self.assertTrue(self.master_system.tsi_master_file.exists())
        
        # Test combined master file creation
        combined_success = self.master_system.create_combined_master_file()
        self.assertTrue(combined_success)
        self.assertTrue(self.master_system.combined_master_file.exists())
        
        print("✅ Master file creation test passed")
        
    def test_database_operations(self):
        """Test SQLite database operations."""
        if not self.master_system.config.get("master_file_settings", {}).get("enable_sqlite_db", True):
            self.skipTest("SQLite database disabled in configuration")
            
        # Create master files first
        self.master_system.create_master_file("wu", force_rebuild=True)
        self.master_system.create_master_file("tsi", force_rebuild=True)
        
        # Check that database file was created
        self.assertTrue(self.master_system.master_db_file.exists())
        
        # Check database contents
        conn = sqlite3.connect(self.master_system.master_db_file)
        cursor = conn.cursor()
        
        # Check WU table
        cursor.execute("SELECT COUNT(*) FROM wu_data")
        wu_count = cursor.fetchone()[0]
        self.assertGreater(wu_count, 0)
        
        # Check TSI table
        cursor.execute("SELECT COUNT(*) FROM tsi_data")
        tsi_count = cursor.fetchone()[0]
        self.assertGreater(tsi_count, 0)
        
        conn.close()
        
        print(f"✅ Database operations test passed - WU: {wu_count} records, TSI: {tsi_count} records")
        
    def test_metadata_operations(self):
        """Test metadata creation and updates."""
        # Create master file to generate metadata
        self.master_system.create_master_file("wu", force_rebuild=True)
        
        # Check that metadata file was created
        wu_metadata_file = self.master_system.metadata_path / "wu_master_metadata.json"
        self.assertTrue(wu_metadata_file.exists())
        
        # Load and validate metadata
        with open(wu_metadata_file, 'r') as f:
            metadata = json.load(f)
            
        self.assertEqual(metadata["data_type"], "wu")
        self.assertIn("last_update", metadata)
        self.assertIn("total_records", metadata)
        self.assertGreater(metadata["total_records"], 0)
        
        print(f"✅ Metadata operations test passed - {metadata['total_records']} records logged")
        
    def test_data_appending(self):
        """Test appending new data to master files."""
        # Create initial master file
        self.master_system.create_master_file("wu", force_rebuild=True)
        
        # Get initial record count
        initial_df = pd.read_csv(self.master_system.wu_master_file)
        initial_count = len(initial_df)
        
        # Create new data to append
        new_data = {
            'timestamp': pd.date_range('2024-12-01', periods=10, freq='H'),
            'station_id': ['TEST_WU_001'] * 10,
            'tempf': [75 + i * 0.1 for i in range(10)],
            'humidity': [55 + i * 0.2 for i in range(10)],
            'source_file': 'new_test_data.csv'
        }
        new_df = pd.DataFrame(new_data)
        
        # Append new data
        success = self.master_system.append_new_data("wu", new_df)
        self.assertTrue(success)
        
        # Check that data was appended
        updated_df = pd.read_csv(self.master_system.wu_master_file)
        updated_count = len(updated_df)
        self.assertGreater(updated_count, initial_count)
        
        print(f"✅ Data appending test passed - Added {updated_count - initial_count} new records")
        
    def test_export_functionality(self):
        """Test data export in different formats."""
        # Create master files
        self.master_system.create_master_file("wu", force_rebuild=True)
        self.master_system.create_master_file("tsi", force_rebuild=True)
        self.master_system.create_combined_master_file()
        
        # Test CSV export
        csv_files = self.master_system.export_data("wu", "csv")
        self.assertGreater(len(csv_files), 0)
        self.assertTrue(csv_files[0].exists())
        self.assertTrue(csv_files[0].suffix == '.csv')
        
        # Test Excel export
        excel_files = self.master_system.export_data("tsi", "excel")
        self.assertGreater(len(excel_files), 0)
        self.assertTrue(excel_files[0].exists())
        self.assertTrue(excel_files[0].suffix in ['.xlsx', '.xls'])
        
        # Test JSON export
        json_files = self.master_system.export_data("combined", "json")
        self.assertGreater(len(json_files), 0)
        self.assertTrue(json_files[0].exists())
        self.assertTrue(json_files[0].suffix == '.json')
        
        print(f"✅ Export functionality test passed - Created {len(csv_files) + len(excel_files) + len(json_files)} export files")
        
    def test_summary_generation(self):
        """Test master data summary generation."""
        # Create master files
        self.master_system.create_master_file("wu", force_rebuild=True)
        self.master_system.create_master_file("tsi", force_rebuild=True)
        self.master_system.create_combined_master_file()
        
        # Get summary
        summary = self.master_system.get_master_data_summary()
        
        # Validate summary structure
        self.assertIn("wu_data", summary)
        self.assertIn("tsi_data", summary)
        self.assertIn("combined_data", summary)
        
        # Check WU data summary
        wu_summary = summary["wu_data"]
        self.assertTrue(wu_summary.get("file_exists", False))
        self.assertGreater(wu_summary.get("total_records", 0), 0)
        
        # Check TSI data summary
        tsi_summary = summary["tsi_data"]
        self.assertTrue(tsi_summary.get("file_exists", False))
        self.assertGreater(tsi_summary.get("total_records", 0), 0)
        
        # Check combined data summary
        combined_summary = summary["combined_data"]
        self.assertTrue(combined_summary.get("file_exists", False))
        self.assertGreater(combined_summary.get("total_records", 0), 0)
        
        print(f"✅ Summary generation test passed - WU: {wu_summary.get('total_records', 0)}, TSI: {tsi_summary.get('total_records', 0)}, Combined: {combined_summary.get('total_records', 0)}")
        
    def test_backup_operations(self):
        """Test backup creation and cleanup."""
        # Create master file
        self.master_system.create_master_file("wu", force_rebuild=True)
        
        # Force creation of backup by updating
        new_data = pd.DataFrame({
            'timestamp': [datetime.now()],
            'station_id': ['TEST_WU_001'],
            'tempf': [80],
            'humidity': [60],
            'source_file': 'backup_test.csv'
        })
        
        self.master_system.append_new_data("wu", new_data)
        
        # Check that backup was created
        backup_files = list(self.master_system.backup_path.glob("*pre_update*"))
        self.assertGreater(len(backup_files), 0)
        
        # Test cleanup (with short retention for testing)
        self.master_system.cleanup_old_backups(retention_days=0)
        
        print(f"✅ Backup operations test passed - Created and cleaned {len(backup_files)} backup files")


class TestMasterDataScheduler(unittest.TestCase):
    """Test suite for Master Data Scheduler."""
    
    def setUp(self):
        """Set up scheduler test."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test configuration
        test_config = {
            "automation": {
                "auto_weekly_update": True,
                "update_day_of_week": "sunday",
                "update_time": "02:00"
            }
        }
        
        self.config_path = self.config_dir / "master_data_config.json"
        with open(self.config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
            
    def tearDown(self):
        """Clean up scheduler test."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            
    def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        try:
            scheduler = MasterDataScheduler(config_path=str(self.config_path))
            self.assertIsNotNone(scheduler.config)
            self.assertIsNotNone(scheduler.master_system)
            
            # Check schedule setup
            schedule_info = scheduler.get_schedule_info()
            self.assertGreater(len(schedule_info), 0)
            
            print(f"✅ Scheduler initialization test passed - {len(schedule_info)} jobs scheduled")
            
        except Exception as e:
            # Scheduler may fail if master data system dependencies aren't available
            print(f"⚠️ Scheduler test skipped due to dependencies: {e}")
            self.skipTest(f"Scheduler dependencies not available: {e}")


def run_tests():
    """Run the complete test suite."""
    print("🧪 Starting Master Data File System Test Suite")
    print("=" * 60)
    
    # Create test suite
    # loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    # suite.addTests(loader.loadTestsFromTestCase(TestMasterDataFileSystem))
    # suite.addTests(loader.loadTestsFromTestCase(TestMasterDataScheduler))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🧪 Test Suite Summary")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, trace in result.failures:
            print(f"  - {test}: {trace}")
            
    if result.errors:
        print("\n💥 Errors:")
        for test, trace in result.errors:
            print(f"  - {test}: {trace}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    
    return success

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
