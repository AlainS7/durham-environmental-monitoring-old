#!/usr/bin/env python3
"""
Test Script for Daily Sheets System
Comprehensive testing of the automated daily Google Sheets generation.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.automation.daily_sheets_system import DailySheetsSystem

class TestDailySheetsSystem(unittest.TestCase):
    """Test cases for the Daily Sheets System"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.daily_system = DailySheetsSystem(project_root)
        cls.test_date = datetime.now() - timedelta(days=1)  # Yesterday
    
    def test_01_credentials_loading(self):
        """Test that all required credentials are loaded"""
        print("\n=== Testing Credentials Loading ===")
        
        # Check if credential files exist
        self.assertTrue(self.daily_system.google_creds_path.exists(), 
                       "Google credentials file not found")
        self.assertTrue(self.daily_system.tsi_creds_path.exists(), 
                       "TSI credentials file not found")
        self.assertTrue(self.daily_system.wu_api_key_path.exists(), 
                       "WU API key file not found")
        
        # Check if Google services are initialized
        self.assertIsNotNone(self.daily_system.sheets_service, 
                           "Sheets service not initialized")
        self.assertIsNotNone(self.daily_system.drive_service, 
                           "Drive service not initialized")
        self.assertIsNotNone(self.daily_system.gspread_client, 
                           "gspread client not initialized")
        
        print("✅ All credentials loaded successfully")
    
    def test_02_configuration_loading(self):
        """Test configuration loading and validation"""
        print("\n=== Testing Configuration Loading ===")
        
        config = self.daily_system.config
        
        # Check required configuration fields
        required_fields = [
            'share_email', 'drive_folder_name', 'sheet_retention_days',
            'auto_cleanup', 'wu_sensors', 'data_pull_hours'
        ]
        
        for field in required_fields:
            self.assertIn(field, config, f"Required config field missing: {field}")
        
        # Validate specific configurations
        self.assertTrue(len(config['wu_sensors']) > 0, "No WU sensors configured")
        self.assertIsInstance(config['sheet_retention_days'], int, 
                            "sheet_retention_days should be integer")
        self.assertGreater(config['data_pull_hours'], 0, 
                         "data_pull_hours should be positive")
        
        print(f"✅ Configuration loaded with {len(config['wu_sensors'])} WU sensors")
        print(f"✅ Retention period: {config['sheet_retention_days']} days")
    
    def test_03_data_fetching(self):
        """Test data fetching capabilities"""
        print("\n=== Testing Data Fetching ===")
        
        # Test getting daily data
        data = self.daily_system.get_daily_data(self.test_date)
        
        self.assertIsNotNone(data, "Data fetch returned None")
        self.assertIn('wu', data, "WU data key missing")
        self.assertIn('tsi', data, "TSI data key missing")
        self.assertIn('date_range', data, "Date range key missing")
        
        # Log data availability
        wu_available = data['wu'] is not None and not data['wu'].empty
        tsi_available = data['tsi'] is not None and not data['tsi'].empty
        
        print(f"✅ Data fetch completed")
        print(f"  - WU data available: {wu_available}")
        print(f"  - TSI data available: {tsi_available}")
        
        if wu_available:
            print(f"  - WU records: {len(data['wu'])}")
        if tsi_available:
            print(f"  - TSI records: {len(data['tsi'])}")
        
        # At least one data source should be available
        self.assertTrue(wu_available or tsi_available, 
                       "No data available from either source")
    
    def test_04_summary_creation(self):
        """Test daily summary creation"""
        print("\n=== Testing Summary Creation ===")
        
        # Get data for summary
        data = self.daily_system.get_daily_data(self.test_date)
        wu_df = data.get('wu')
        tsi_df = data.get('tsi')
        
        # Create summary
        summary = self.daily_system.create_daily_summary(wu_df, tsi_df)
        
        self.assertIsNotNone(summary, "Summary creation returned None")
        self.assertIn('date', summary, "Summary missing date")
        self.assertIn('wu_summary', summary, "Summary missing WU summary")
        self.assertIn('tsi_summary', summary, "Summary missing TSI summary")
        self.assertIn('overall_summary', summary, "Summary missing overall summary")
        
        overall = summary['overall_summary']
        self.assertIn('data_sources_active', overall, "Missing active data sources")
        
        print("✅ Summary creation successful")
        print(f"  - Date: {summary['date']}")
        print(f"  - Active sources: {overall['data_sources_active']}")
        print(f"  - WU stations: {overall['wu_stations_count']}")
        print(f"  - TSI devices: {overall['tsi_devices_count']}")
    
    def test_05_drive_folder_creation(self):
        """Test Google Drive folder creation"""
        print("\n=== Testing Drive Folder Creation ===")
        
        # Test creating a test folder
        test_folder_name = f"HotDurham_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        folder_id = self.daily_system.create_drive_folder(test_folder_name)
        
        self.assertIsNotNone(folder_id, "Drive folder creation failed")
        
        print(f"✅ Test folder created: {test_folder_name}")
        print(f"  - Folder ID: {folder_id}")
        
        # Clean up - delete test folder
        try:
            self.daily_system.drive_service.files().delete(fileId=folder_id).execute()
            print("✅ Test folder cleaned up successfully")
        except Exception as e:
            print(f"⚠️ Failed to clean up test folder: {e}")
    
    def test_06_sheet_metadata_handling(self):
        """Test sheet metadata saving and loading"""
        print("\n=== Testing Sheet Metadata Handling ===")
        
        # Create test metadata
        test_metadata = {
            'sheet_id': 'test_sheet_id_123',
            'sheet_url': 'https://docs.google.com/spreadsheets/test',
            'date': self.test_date.strftime('%Y-%m-%d'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_sources': ['Weather Underground', 'TSI Air Quality']
        }
        
        # Test saving metadata
        try:
            self.daily_system.save_daily_sheet_metadata(test_metadata)
            print("✅ Metadata saving successful")
        except Exception as e:
            self.fail(f"Metadata saving failed: {e}")
        
        # Verify metadata file exists
        metadata_dir = Path(self.daily_system.project_root) / "data" / "daily_sheets_metadata"
        self.assertTrue(metadata_dir.exists(), "Metadata directory not created")
        
        metadata_file = metadata_dir / f"daily_sheets_{datetime.now().strftime('%Y_%m')}.json"
        self.assertTrue(metadata_file.exists(), "Metadata file not created")
        
        # Load and verify metadata
        with open(metadata_file, 'r') as f:
            saved_metadata = json.load(f)
        
        self.assertIsInstance(saved_metadata, list, "Metadata should be a list")
        self.assertGreater(len(saved_metadata), 0, "No metadata entries found")
        
        # Find our test entry
        test_entry = None
        for entry in saved_metadata:
            if entry.get('sheet_id') == 'test_sheet_id_123':
                test_entry = entry
                break
        
        self.assertIsNotNone(test_entry, "Test metadata entry not found")
        self.assertEqual(test_entry['sheet_url'], test_metadata['sheet_url'])
        
        print("✅ Metadata loading and verification successful")

class TestRunner:
    """Test runner with enhanced reporting"""
    
    def __init__(self):
        self.project_root = project_root
    
    def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("🧪 Hot Durham Daily Sheets System - Comprehensive Test Suite")
        print("=" * 70)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("❌ Prerequisites check failed. Cannot run tests.")
            return False
        
        # Run unit tests
        print("\n🧪 Running Unit Tests...")
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDailySheetsSystem)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)
        
        # Test summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        if result.wasSuccessful():
            print("✅ ALL TESTS PASSED!")
            print(f"   Tests run: {result.testsRun}")
            print(f"   Failures: {len(result.failures)}")
            print(f"   Errors: {len(result.errors)}")
            return True
        else:
            print("❌ SOME TESTS FAILED!")
            print(f"   Tests run: {result.testsRun}")
            print(f"   Failures: {len(result.failures)}")
            print(f"   Errors: {len(result.errors)}")
            
            if result.failures:
                print("\n🔍 FAILURES:")
                for test, traceback in result.failures:
                    print(f"   - {test}: {traceback}")
            
            if result.errors:
                print("\n🔍 ERRORS:")
                for test, traceback in result.errors:
                    print(f"   - {test}: {traceback}")
            
            return False
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        print("🔍 Checking Prerequisites...")
        
        prerequisites_met = True
        
        # Check credential files
        creds_dir = Path(self.project_root) / "creds"
        required_creds = [
            "google_creds.json",
            "tsi_creds.json", 
            "wu_api_key.json"
        ]
        
        for cred_file in required_creds:
            cred_path = creds_dir / cred_file
            if cred_path.exists():
                print(f"  ✅ {cred_file} found")
            else:
                print(f"  ❌ {cred_file} NOT found")
                prerequisites_met = False
        
        # Check Python dependencies
        required_packages = [
            'gspread', 'googleapiclient', 'pandas', 
            'requests', 'schedule'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✅ {package} available")
            except ImportError:
                print(f"  ❌ {package} NOT available")
                prerequisites_met = False
        
        # Check project structure
        required_dirs = [
            "src/core",
            "src/automation", 
            "src/data_collection",
            "config"
        ]
        
        for dir_path in required_dirs:
            full_path = Path(self.project_root) / dir_path
            if full_path.exists():
                print(f"  ✅ {dir_path} directory exists")
            else:
                print(f"  ❌ {dir_path} directory NOT found")
                prerequisites_met = False
        
        return prerequisites_met
    
    def run_integration_test(self):
        """Run integration test with actual sheet creation"""
        print("\n🔧 Running Integration Test...")
        print("This will create a real Google Sheet for testing purposes.")
        
        try:
            daily_system = DailySheetsSystem(self.project_root)
            
            # Create a test sheet for yesterday
            test_date = datetime.now() - timedelta(days=1)
            
            print(f"Creating test sheet for {test_date.strftime('%Y-%m-%d')}...")
            
            result = daily_system.create_daily_sheet(
                target_date=test_date,
                replace_existing=False  # Don't replace to avoid conflicts
            )
            
            if result:
                print("✅ Integration test PASSED!")
                print(f"   Test sheet created: {result['sheet_url']}")
                print(f"   Sheet ID: {result['sheet_id']}")
                print(f"   Data sources: {', '.join(result['data_sources'])}")
                
                # Ask user if they want to delete the test sheet
                response = input("\nDelete test sheet? (y/n): ").lower().strip()
                if response == 'y':
                    try:
                        daily_system.delete_sheet(result['sheet_id'])
                        print("✅ Test sheet deleted successfully")
                    except Exception as e:
                        print(f"⚠️ Failed to delete test sheet: {e}")
                
                return True
            else:
                print("❌ Integration test FAILED!")
                print("   Could not create test sheet")
                return False
                
        except Exception as e:
            print(f"❌ Integration test ERROR: {e}")
            return False

def main():
    """Main function for running tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Hot Durham Daily Sheets System')
    parser.add_argument('--unit-only', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration-only', action='store_true', help='Run integration test only')
    parser.add_argument('--full', action='store_true', help='Run full test suite including integration')
    
    args = parser.parse_args()
    
    test_runner = TestRunner()
    
    if args.integration_only:
        success = test_runner.run_integration_test()
    elif args.full:
        unit_success = test_runner.run_comprehensive_test()
        integration_success = test_runner.run_integration_test()
        success = unit_success and integration_success
    else:  # Default: unit tests only
        success = test_runner.run_comprehensive_test()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("The Daily Sheets System is ready for production use.")
    else:
        print("⚠️ TESTS FAILED!")
        print("Please resolve issues before using the system.")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
