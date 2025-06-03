#!/usr/bin/env python3
"""
Complete Historical Test Sensor Data Collection and Google Drive Upload

This script efficiently fetches all available historical 15-minute data for each test sensor from Weather 
Underground since they first came online and uploads comprehensive files to Google Drive.

Features:
- Collects ALL historical 15-minute data from Weather Underground API
- Creates one comprehensive file per sensor with all data since inception
- Uploads organized files to Google Drive with proper folder structure
- Progress tracking, resume capability, and error handling
- Parallel processing for faster collection
- Intelligent date range detection and optimization
"""

import os
import sys
import json
import asyncio
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, date
import time
import logging
from typing import Dict, List, Any, Optional
import concurrent.futures
from functools import partial

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "config"))

try:
    from config.test_sensors_config import TEST_SENSOR_IDS, WU_TO_MS_MAPPING, TestSensorConfig
    from src.core.data_manager import DataManager
    from src.automation.master_data_file_system import MasterDataFileSystem
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

import nest_asyncio
nest_asyncio.apply()

class CompleteHistoricalTestSensorCollector:
    """Complete collector for historical test sensor data with Google Drive upload."""
    
    def __init__(self):
        self.project_root = project_root
        self.output_dir = project_root / "data" / "historical_test_sensors"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging first
        self.setup_logging()
        
        # Initialize test sensor configuration and data manager
        self.test_config = TestSensorConfig()
        self.data_manager = DataManager(str(project_root))
        
        # Load API credentials
        self.api_key = self.load_wu_api_key()
        
        # Collection settings
        self.max_concurrent = 3  # Reduce concurrent requests for stability
        self.rate_limit_delay = 0.5  # 500ms between requests
        
        # Progress tracking
        self.progress_file = self.output_dir / "collection_progress.json"
        self.completed_sensors = self.load_progress()
        
        self.logger.info("🧪 Complete Historical Test Sensor Collector initialized")
        self.logger.info(f"📂 Output directory: {self.output_dir}")
        self.logger.info(f"🎯 Test sensors to process: {len(TEST_SENSOR_IDS)}")
    
    def load_wu_api_key(self) -> str:
        """Load Weather Underground API key from credentials file."""
        try:
            creds_file = self.project_root / "creds" / "wu_api_key.json"
            with open(creds_file, 'r') as f:
                data = json.load(f)
                # Try both possible key names
                api_key = data.get('test_api_key') or data.get('api_key', '')
                if api_key:
                    self.logger.info("✅ Successfully loaded Weather Underground API key")
                    return api_key
                else:
                    self.logger.error("❌ No API key found in wu_api_key.json")
                    return ""
        except Exception as e:
            self.logger.error(f"Failed to load WU API key: {e}")
            return ""
    
    def setup_logging(self):
        """Setup logging for the collection process."""
        log_file = self.output_dir / f"historical_collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_progress(self) -> Dict[str, bool]:
        """Load progress from previous runs."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    return data.get('completed_sensors', {})
            except Exception as e:
                self.logger.warning(f"Could not load progress: {e}")
        return {}
    
    def save_progress(self, sensor_id: str):
        """Save progress for a completed sensor."""
        self.completed_sensors[sensor_id] = True
        progress_data = {
            'last_updated': datetime.now().isoformat(),
            'completed_sensors': self.completed_sensors,
            'total_sensors': len(TEST_SENSOR_IDS),
            'completed_count': len(self.completed_sensors)
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
    
    async def get_sensor_first_date(self, sensor_id: str) -> Optional[date]:
        """Determine when a sensor first came online by checking data availability."""
        self.logger.info(f"🔍 Determining first data date for {sensor_id}")
        
        # Start checking from 2020 (most WU sensors started around then)
        start_year = 2020
        current_year = datetime.now().year
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for year in range(start_year, current_year + 1):
                for month in range(1, 13):
                    test_date = date(year, month, 1)
                    if test_date > date.today():
                        break
                    
                    # Check if data exists for this month
                    if await self.has_data_for_date(client, sensor_id, test_date):
                        self.logger.info(f"✅ {sensor_id} first data found: {test_date}")
                        return test_date
                    
                    await asyncio.sleep(self.rate_limit_delay)
        
        # Default to 1 year ago if no specific start date found
        default_date = date.today() - timedelta(days=365)
        self.logger.warning(f"⚠️ {sensor_id} using default start date: {default_date}")
        return default_date
    
    async def has_data_for_date(self, client: httpx.AsyncClient, sensor_id: str, check_date: date) -> bool:
        """Check if sensor has data for a specific date."""
        url = "https://api.weather.com/v2/pws/history/all"
        params = {
            'stationId': sensor_id,
            'format': 'json',
            'units': 'm',
            'date': check_date.strftime('%Y%m%d'),
            'apiKey': self.api_key
        }
        
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                observations = data.get('observations', [])
                return len(observations) > 0
            else:
                return False
        except Exception:
            return False
    
    async def collect_sensor_data_for_date_range(self, sensor_id: str, start_date: date, end_date: date) -> List[Dict]:
        """Collect all data for a sensor within a date range."""
        all_observations = []
        current_date = start_date
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while current_date <= end_date:
                try:
                    url = "https://api.weather.com/v2/pws/history/all"
                    params = {
                        'stationId': sensor_id,
                        'format': 'json',
                        'units': 'm',
                        'date': current_date.strftime('%Y%m%d'),
                        'apiKey': self.api_key
                    }
                    
                    response = await client.get(url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        observations = data.get('observations', [])
                        
                        for obs in observations:
                            # Add sensor metadata to each observation
                            obs['sensor_id'] = sensor_id
                            obs['ms_station'] = WU_TO_MS_MAPPING.get(sensor_id, 'Unknown')
                            obs['collection_date'] = current_date.isoformat()
                        
                        all_observations.extend(observations)
                        
                        if observations:
                            self.logger.info(f"📊 {sensor_id} {current_date}: {len(observations)} observations")
                        else:
                            self.logger.debug(f"📊 {sensor_id} {current_date}: No data")
                    
                    elif response.status_code == 429:
                        # Rate limited - wait longer
                        self.logger.warning(f"⚠️ Rate limited for {sensor_id}, waiting 5s...")
                        await asyncio.sleep(5)
                        continue  # Retry the same date
                    
                    else:
                        self.logger.warning(f"⚠️ {sensor_id} {current_date}: HTTP {response.status_code}")
                
                except Exception as e:
                    self.logger.error(f"❌ Error collecting {sensor_id} {current_date}: {e}")
                
                current_date += timedelta(days=1)
                await asyncio.sleep(self.rate_limit_delay)
        
        return all_observations
    
    async def collect_complete_sensor_history(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """Collect complete historical data for a single sensor."""
        if sensor_id in self.completed_sensors:
            self.logger.info(f"⏭️ Skipping {sensor_id} - already completed")
            return None
        
        self.logger.info(f"🚀 Starting complete collection for {sensor_id}")
        
        try:
            # Determine when this sensor first came online
            first_date = await self.get_sensor_first_date(sensor_id)
            if not first_date:
                self.logger.error(f"❌ Could not determine start date for {sensor_id}")
                return None
            
            # Collect from first date to today
            end_date = date.today()
            self.logger.info(f"📅 {sensor_id}: Collecting from {first_date} to {end_date}")
            
            # Collect all data
            all_observations = await self.collect_sensor_data_for_date_range(
                sensor_id, first_date, end_date
            )
            
            if not all_observations:
                self.logger.warning(f"⚠️ No data collected for {sensor_id}")
                return None
            
            # Create comprehensive dataset
            df = pd.DataFrame(all_observations)
            
            # Process and clean the data
            df = self.process_sensor_dataframe(df, sensor_id)
            
            result = {
                'sensor_id': sensor_id,
                'ms_station': WU_TO_MS_MAPPING.get(sensor_id, 'Unknown'),
                'data': df,
                'metadata': {
                    'total_observations': len(df),
                    'date_range': {
                        'start': first_date.isoformat(),
                        'end': end_date.isoformat()
                    },
                    'collection_time': datetime.now().isoformat(),
                    'days_covered': (end_date - first_date).days + 1
                }
            }
            
            self.logger.info(f"✅ {sensor_id}: Collected {len(df)} total observations")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Failed to collect data for {sensor_id}: {e}")
            return None
    
    def process_sensor_dataframe(self, df: pd.DataFrame, sensor_id: str) -> pd.DataFrame:
        """Process and clean sensor dataframe."""
        if df.empty:
            return df
        
        try:
            # Sort by timestamp
            if 'obsTimeUtc' in df.columns:
                df['timestamp'] = pd.to_datetime(df['obsTimeUtc'])
                df = df.sort_values('timestamp')
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['timestamp'] if 'timestamp' in df.columns else None)
            
            # Add processed columns
            df['sensor_id'] = sensor_id
            df['ms_station'] = WU_TO_MS_MAPPING.get(sensor_id, 'Unknown')
            
            # Ensure consistent column order
            priority_cols = ['sensor_id', 'ms_station', 'timestamp', 'obsTimeUtc']
            other_cols = [col for col in df.columns if col not in priority_cols]
            df = df[priority_cols + other_cols]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing dataframe for {sensor_id}: {e}")
            return df
    
    async def collect_all_historical_data(self) -> Dict[str, Any]:
        """Collect complete historical data for all test sensors."""
        self.logger.info("🎯 Starting complete historical data collection for all test sensors")
        
        remaining_sensors = [s for s in TEST_SENSOR_IDS if s not in self.completed_sensors]
        
        if not remaining_sensors:
            self.logger.info("✅ All sensors already completed!")
            return {}
        
        self.logger.info(f"📊 Processing {len(remaining_sensors)} remaining sensors")
        
        all_sensor_data = {}
        
        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def collect_with_semaphore(sensor_id):
            async with semaphore:
                return await self.collect_complete_sensor_history(sensor_id)
        
        # Process sensors with controlled concurrency
        tasks = [collect_with_semaphore(sensor_id) for sensor_id in remaining_sensors]
        
        # Process with progress updates
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            if result:
                sensor_id = result['sensor_id']
                all_sensor_data[sensor_id] = result
                self.save_progress(sensor_id)
                
                progress = ((i + 1) / len(tasks)) * 100
                self.logger.info(f"📈 Progress: {progress:.1f}% ({i + 1}/{len(tasks)})")
        
        self.logger.info(f"🎉 Collection complete! Processed {len(all_sensor_data)} sensors")
        return all_sensor_data
    
    def save_historical_data(self, all_sensor_data: Dict[str, Any]) -> List[Path]:
        """Save historical data to comprehensive files."""
        saved_files = []
        
        if not all_sensor_data:
            self.logger.warning("No data to save")
            return saved_files
        
        self.logger.info("💾 Saving comprehensive historical files...")
        
        for sensor_id, sensor_data in all_sensor_data.items():
            try:
                df = sensor_data['data']
                if df.empty:
                    continue
                
                # Create comprehensive filename
                start_date = sensor_data['metadata']['date_range']['start']
                end_date = sensor_data['metadata']['date_range']['end']
                ms_station = sensor_data['ms_station']
                
                filename = f"{sensor_id}_{ms_station}_complete_history_{start_date}_to_{end_date}.csv"
                file_path = self.output_dir / filename
                
                # Save CSV with all data
                df.to_csv(file_path, index=False)
                saved_files.append(file_path)
                
                # Also save metadata
                metadata_filename = f"{sensor_id}_{ms_station}_metadata.json"
                metadata_path = self.output_dir / metadata_filename
                
                with open(metadata_path, 'w') as f:
                    json.dump(sensor_data['metadata'], f, indent=2)
                saved_files.append(metadata_path)
                
                self.logger.info(f"💾 Saved {sensor_id}: {len(df)} observations to {filename}")
                
            except Exception as e:
                self.logger.error(f"❌ Failed to save data for {sensor_id}: {e}")
        
        return saved_files
    
    def upload_to_google_drive(self, saved_files: List[Path]) -> bool:
        """Upload all historical files to Google Drive."""
        if not saved_files:
            self.logger.warning("No files to upload to Google Drive")
            return False
        
        if not self.data_manager.drive_service:
            self.logger.warning("Google Drive service not available")
            return False
        
        self.logger.info("📤 Uploading historical files to Google Drive...")
        
        # Use organized folder structure for historical data
        drive_folder = "HotDurham/TestData_ValidationCluster/HistoricalData/CompleteHistory"
        
        success_count = 0
        
        for file_path in saved_files:
            try:
                success = self.data_manager.upload_to_drive(file_path, drive_folder)
                if success:
                    success_count += 1
                    self.logger.info(f"📤 Uploaded: {file_path.name}")
                else:
                    self.logger.error(f"❌ Failed to upload: {file_path.name}")
                    
                # Brief delay between uploads
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"❌ Error uploading {file_path.name}: {e}")
        
        upload_success = success_count == len(saved_files)
        self.logger.info(f"📤 Upload complete: {success_count}/{len(saved_files)} files successful")
        
        return upload_success
    
    def create_summary_report(self, all_sensor_data: Dict[str, Any]) -> Optional[Path]:
        """Create a comprehensive summary report."""
        if not all_sensor_data:
            return None
        
        try:
            self.logger.info("📋 Creating comprehensive summary report...")
            
            summary = {
                'collection_summary': {
                    'collection_date': datetime.now().isoformat(),
                    'total_sensors_processed': len(all_sensor_data),
                    'total_observations': sum(
                        data['metadata']['total_observations'] 
                        for data in all_sensor_data.values()
                    ),
                    'collection_type': 'complete_historical',
                    'data_source': 'Weather Underground API'
                },
                'sensor_details': {}
            }
            
            # Add detailed info for each sensor
            for sensor_id, data in all_sensor_data.items():
                summary['sensor_details'][sensor_id] = {
                    'ms_station': data['ms_station'],
                    'total_observations': data['metadata']['total_observations'],
                    'date_range': data['metadata']['date_range'],
                    'days_covered': data['metadata']['days_covered'],
                    'avg_observations_per_day': data['metadata']['total_observations'] / max(1, data['metadata']['days_covered'])
                }
            
            summary_file = self.output_dir / "complete_historical_collection_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"📋 Summary report created: {summary_file}")
            return summary_file
            
        except Exception as e:
            self.logger.error(f"Error creating summary report: {e}")
            return None

async def main():
    """Main execution function."""
    collector = CompleteHistoricalTestSensorCollector()
    
    try:
        print("🧪 Complete Historical Test Sensor Data Collection")
        print("=" * 55)
        print()
        print("This will collect ALL available 15-minute historical data for each test sensor")
        print("from Weather Underground since they first came online and upload to Google Drive.")
        print()
        print(f"📊 Test sensors to process: {len(TEST_SENSOR_IDS)}")
        print(f"📂 Output directory: {collector.output_dir}")
        print(f"📤 Google Drive: {'Available' if collector.data_manager.drive_service else 'Not available'}")
        print()
        
        # Show previous progress if any
        if collector.completed_sensors:
            print(f"✅ Previously completed: {len(collector.completed_sensors)} sensors")
            remaining = len(TEST_SENSOR_IDS) - len(collector.completed_sensors)
            print(f"⏳ Remaining to process: {remaining} sensors")
            print()
        
        # Confirm with user
        response = input("Continue with complete historical data collection? (y/N): ")
        if response.lower() != 'y':
            print("Collection cancelled.")
            return
        
        print("\n🚀 Starting collection...")
        start_time = datetime.now()
        
        # Collect all historical data
        all_sensor_data = await collector.collect_all_historical_data()
        
        if not all_sensor_data:
            print("\n⚠️ No new data collected (all sensors may already be complete)")
            return
        
        # Save to comprehensive files
        print("\n💾 Saving comprehensive historical files...")
        saved_files = collector.save_historical_data(all_sensor_data)
        
        # Create summary report
        summary_file = collector.create_summary_report(all_sensor_data)
        if summary_file:
            saved_files.append(summary_file)
        
        # Upload to Google Drive
        upload_success = False
        if saved_files:
            print("\n📤 Uploading to Google Drive...")
            upload_success = collector.upload_to_google_drive(saved_files)
        
        # Final summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 55)
        print("📊 COLLECTION COMPLETE!")
        print("=" * 55)
        print(f"⏱️  Duration: {duration}")
        print(f"📁 Files created: {len(saved_files)}")
        print(f"📤 Google Drive upload: {'✅ Success' if upload_success else '❌ Failed'}")
        
        if all_sensor_data:
            total_observations = sum(
                data['metadata']['total_observations'] 
                for data in all_sensor_data.values()
            )
            print(f"📈 Total observations: {total_observations:,}")
            print(f"🧪 Sensors processed: {len(all_sensor_data)}")
            
            # Show file locations
            print(f"\n📂 Files saved to: {collector.output_dir}")
            if upload_success:
                print(f"📤 Google Drive: HotDurham/TestData_ValidationCluster/HistoricalData/CompleteHistory/")
        
        print("\n🎉 Your test sensors now have complete historical files with ALL 15-minute data!")
        print("📋 Check the summary report for detailed statistics.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Collection interrupted by user")
        collector.logger.info("Collection interrupted by user")
    except Exception as e:
        collector.logger.error(f"Fatal error in main execution: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
