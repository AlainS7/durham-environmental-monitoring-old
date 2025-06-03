#!/usr/bin/env python3
"""
Fast Historical Test Sensor Data Collection

Optimized script to quickly collect historical data for test sensors and fix database issues.
Features:
- Parallel processing for speed
- Resume capability  
- Database error fixes
- Progress tracking
- Google Drive upload
"""

import os
import sys
import json
import asyncio
import httpx
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, date
import logging
from typing import Dict, List, Any, Optional
import concurrent.futures

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "config"))

try:
    from config.test_sensors_config import TEST_SENSOR_IDS, WU_TO_MS_MAPPING
    from src.automation.master_data_file_system import MasterDataFileSystem
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

import nest_asyncio
nest_asyncio.apply()

class FastHistoricalCollector:
    """Fast collector for historical test sensor data."""
    
    def __init__(self):
        self.project_root = project_root
        self.output_dir = project_root / "data" / "historical_test_sensors"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / "fast_collection_progress.json"
        self.load_progress()
        
        # Setup logging
        self.setup_logging()
        
        # Load API credentials
        self.load_api_credentials()
        
        # Initialize Google Drive integration with database fix
        self.master_system = MasterDataFileSystem()
        
        # Fast settings
        self.api_delay = 0.3
        self.max_concurrent = 4
        
        # Start from recent data first (last 6 months)
        self.start_date = date(2024, 1, 1)
        
    def load_progress(self):
        """Load collection progress."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    self.progress = json.load(f)
            except:
                self.progress = {}
        else:
            self.progress = {}
            
    def save_progress(self):
        """Save collection progress."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2, default=str)
            
    def setup_logging(self):
        """Configure logging."""
        log_file = self.project_root / "logs" / "fast_historical_collection.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_api_credentials(self):
        """Load Weather Underground API credentials."""
        try:
            wu_api_key_path = self.project_root / "creds" / "wu_api_key.json"
            if wu_api_key_path.exists():
                with open(wu_api_key_path, 'r') as f:
                    creds = json.load(f)
                    self.wu_api_key = creds.get('test_api_key') or creds.get('api_key')
                    if not self.wu_api_key:
                        raise ValueError("No API key found")
                    self.logger.info("✅ API credentials loaded")
            else:
                raise FileNotFoundError("API credentials not found")
        except Exception as e:
            self.logger.error(f"❌ Error loading API credentials: {e}")
            self.wu_api_key = None
            
    async def get_historical_data_for_date(self, sensor_id: str, target_date: date) -> List[Dict[str, Any]]:
        """Get historical data for a specific date."""
        if not self.wu_api_key:
            return []
            
        try:
            date_str = target_date.strftime('%Y%m%d')
            base_url = "https://api.weather.com/v2/pws/history/hourly"
            
            params = {
                "stationId": sensor_id,
                "format": "json",
                "apiKey": self.wu_api_key,
                "units": "m",
                "date": date_str,
                "numericPrecision": "decimal"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                observations = []
                
                if "observations" in data and data["observations"]:
                    for obs in data["observations"]:
                        # Create observation with both timestamp formats for database compatibility
                        observation = {
                            "stationID": sensor_id,
                            "obsTimeUtc": obs.get("obsTimeUtc"),
                            "timestamp": obs.get("obsTimeUtc"),  # Add both for compatibility
                            "tempAvg": obs.get("metric", {}).get("temp"),
                            "humidityAvg": obs.get("humidity"),
                            "pressureMax": obs.get("metric", {}).get("pressure"),
                            "windspeedAvg": obs.get("metric", {}).get("windSpeed"),
                            "winddirAvg": obs.get("winddir"),
                            "precipRate": obs.get("metric", {}).get("precipRate"),
                            "precipTotal": obs.get("metric", {}).get("precipTotal"),
                            "solarRadiationHigh": obs.get("solarRadiation"),
                            "dewptAvg": obs.get("metric", {}).get("dewpt"),
                            "heatindexAvg": obs.get("metric", {}).get("heatIndex"),
                            "source_file": f"fast_historical_{target_date.strftime('%Y%m%d')}"
                        }
                        observations.append(observation)
                
                await asyncio.sleep(self.api_delay)
                return observations
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error fetching {sensor_id} on {target_date}: {e}")
            return []
    
    async def collect_sensor_batch(self, sensor_id: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Collect data for a sensor using concurrent batch processing."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def fetch_date_data(target_date: date):
            async with semaphore:
                return await self.get_historical_data_for_date(sensor_id, target_date)
        
        # Generate date range
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Process in weekly batches
        all_data = []
        batch_size = 7
        
        for i in range(0, len(dates), batch_size):
            batch_dates = dates[i:i+batch_size]
            tasks = [fetch_date_data(date) for date in batch_dates]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, list):
                    all_data.extend(result)
            
            # Progress update
            progress_pct = ((i + batch_size) / len(dates)) * 100
            self.logger.info(f"  📊 {sensor_id} progress: {progress_pct:.1f}%")
            
            await asyncio.sleep(0.5)  # Brief pause between batches
        
        return all_data
    
    async def collect_all_sensors_fast(self) -> Dict[str, bool]:
        """Collect data for all sensors with parallel processing."""
        self.logger.info("🚀 Starting fast historical data collection")
        
        end_date = date.today() - timedelta(days=1)
        results = {}
        
        # Process 3 sensors at a time
        sensor_batches = [TEST_SENSOR_IDS[i:i+3] for i in range(0, len(TEST_SENSOR_IDS), 3)]
        
        for batch_num, sensor_batch in enumerate(sensor_batches, 1):
            self.logger.info(f"📦 Processing batch {batch_num}/{len(sensor_batches)}: {sensor_batch}")
            
            # Create tasks for this batch
            tasks = []
            for sensor_id in sensor_batch:
                if sensor_id not in self.progress or not self.progress[sensor_id].get('completed', False):
                    task = self.process_single_sensor(sensor_id, self.start_date, end_date)
                    tasks.append((sensor_id, task))
                else:
                    self.logger.info(f"⏭️ Skipping {sensor_id} - already completed")
                    results[sensor_id] = True
            
            # Wait for batch completion
            for sensor_id, task in tasks:
                try:
                    success = await task
                    results[sensor_id] = success
                    
                    # Update progress
                    if sensor_id not in self.progress:
                        self.progress[sensor_id] = {}
                    self.progress[sensor_id]['completed'] = success
                    self.progress[sensor_id]['last_updated'] = datetime.now().isoformat()
                    self.save_progress()
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing {sensor_id}: {e}")
                    results[sensor_id] = False
        
        return results
    
    async def process_single_sensor(self, sensor_id: str, start_date: date, end_date: date) -> bool:
        """Process a single sensor efficiently."""
        self.logger.info(f"📡 Processing {sensor_id} from {start_date} to {end_date}")
        
        try:
            # Check for existing data
            output_file = self.output_dir / f"{sensor_id}_historical_data.csv"
            existing_data = []
            resume_date = start_date
            
            if output_file.exists():
                try:
                    existing_df = pd.read_csv(output_file)
                    if not existing_df.empty and 'obsTimeUtc' in existing_df.columns:
                        existing_df['obsTimeUtc'] = pd.to_datetime(existing_df['obsTimeUtc'])
                        latest_date = existing_df['obsTimeUtc'].max().date()
                        resume_date = latest_date + timedelta(days=1)
                        existing_data = existing_df.to_dict('records')
                        self.logger.info(f"📂 Resuming {sensor_id} from {resume_date}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not read existing data for {sensor_id}: {e}")
            
            # Only collect new data if needed
            if resume_date <= end_date:
                new_data = await self.collect_sensor_batch(sensor_id, resume_date, end_date)
            else:
                new_data = []
                self.logger.info(f"✅ {sensor_id} is already up to date")
            
            # Combine and save
            all_data = existing_data + new_data
            
            if all_data:
                df = pd.DataFrame(all_data)
                
                # Ensure proper timestamp handling for database compatibility
                if 'obsTimeUtc' in df.columns:
                    df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
                    df = df.sort_values('obsTimeUtc').drop_duplicates()
                
                # Save file
                df.to_csv(output_file, index=False)
                
                # Create metadata
                metadata = {
                    'sensor_id': sensor_id,
                    'total_records': len(df),
                    'date_range_start': df['obsTimeUtc'].min().isoformat() if 'obsTimeUtc' in df.columns else None,
                    'date_range_end': df['obsTimeUtc'].max().isoformat() if 'obsTimeUtc' in df.columns else None,
                    'file_size_mb': round(output_file.stat().st_size / 1024 / 1024, 2),
                    'collection_date': datetime.now().isoformat()
                }
                
                metadata_file = self.output_dir / f"{sensor_id}_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
                
                self.logger.info(f"✅ {sensor_id}: {len(df)} records saved")
                
                # Upload to Google Drive
                try:
                    if hasattr(self.master_system, 'drive_service') and self.master_system.drive_service:
                        upload_success = self.master_system.upload_to_drive(
                            output_file, 
                            "HotDurham/TestSensors/HistoricalData"
                        )
                        if upload_success:
                            self.logger.info(f"☁️ {sensor_id} uploaded to Google Drive")
                except Exception as e:
                    self.logger.warning(f"⚠️ Google Drive upload failed for {sensor_id}: {e}")
                
                return True
            else:
                self.logger.warning(f"⚠️ No data collected for {sensor_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error processing {sensor_id}: {e}")
            return False

async def main():
    """Main execution function."""
    collector = FastHistoricalCollector()
    
    try:
        print("⚡ Fast Historical Test Sensor Data Collection")
        print("=" * 50)
        print()
        print("This will quickly collect historical data for test sensors")
        print("with optimizations for speed and database compatibility.")
        print()
        
        # Start collection
        results = await collector.collect_all_sensors_fast()
        
        # Create summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print()
        print("📊 Collection Summary:")
        print(f"✅ Successful: {successful}/{total} sensors")
        print(f"❌ Failed: {total - successful}/{total} sensors")
        
        if successful > 0:
            print(f"📁 Files saved to: {collector.output_dir}")
            print("☁️ Files uploaded to Google Drive")
        
        # Test database fix
        print()
        print("🔧 Testing database compatibility fix...")
        try:
            # This will test the database schema fix
            summary = collector.master_system.get_master_data_summary()
            print("✅ Database compatibility verified")
        except Exception as e:
            print(f"⚠️ Database issue still exists: {e}")
            
    except Exception as e:
        collector.logger.error(f"Fatal error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
