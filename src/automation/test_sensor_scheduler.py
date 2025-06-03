#!/usr/bin/env python3
"""
Test Sensor 15-Minute Scheduler for Hot Durham Air Quality Monitoring

This scheduler implements automated data recording for test sensors to collect 
data every 15 minutes throughout each day. It targets the 14 Weather Underground 
test sensors (KNCDURHA634-648) that are clustered for validation testing.

Features:
- 15-minute data collection intervals for test sensors
- Integration with existing data management infrastructure
- Separate storage for test sensor data
- Error handling and recovery
- Logging and monitoring
- Google Drive integration for test data
"""

import os
import sys
import schedule
import time
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import json
import traceback
from typing import Dict, Any, List

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "config"))

try:
    from src.core.data_manager import DataManager
    from config.test_sensors_config import TEST_SENSOR_IDS, WU_TO_MS_MAPPING
    from src.automation.master_data_file_system import MasterDataFileSystem
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

import nest_asyncio
import httpx
import requests
import pandas as pd

nest_asyncio.apply()

class TestSensorScheduler:
    """Scheduler for automated 15-minute test sensor data collection."""
    
    def __init__(self, config_path: str = None):
        self.project_root = project_root
        self.config_path = Path(config_path) if config_path else project_root / "config" / "test_sensor_scheduler_config.json"
        self.log_file = project_root / "logs" / "test_sensor_scheduler.log"
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.config = self.load_or_create_config()
        
        # Initialize data manager
        self.data_manager = DataManager(str(project_root))
        
        # Initialize master data system for Google Drive integration
        self.master_system = MasterDataFileSystem()
        
        # Setup test sensor data storage
        self.test_data_dir = project_root / "data" / "test_sensors"
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Track last successful collection time
        self.last_collection_file = self.test_data_dir / "last_collection.json"
        
        # API credentials
        self.load_api_credentials()
        
    def setup_logging(self):
        """Configure logging for scheduler operations."""
        # Ensure logs directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_or_create_config(self) -> Dict[str, Any]:
        """Load existing configuration or create default one."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.logger.info("Loaded existing test sensor scheduler configuration")
                    return config
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")
        
        # Create default configuration
        default_config = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "description": "15-minute test sensor data collection configuration",
            
            "collection_settings": {
                "interval_minutes": 15,
                "max_retry_attempts": 3,
                "retry_delay_seconds": 30,
                "collection_timeout_seconds": 300,
                "batch_size": 5  # Number of sensors to query simultaneously
            },
            
            "test_sensors": {
                "wu_sensors": TEST_SENSOR_IDS,
                "ms_mapping": WU_TO_MS_MAPPING,
                "data_types": ["temperature", "humidity", "pressure", "windSpeed", "windGust", "precipRate", "solarRadiation", "uv"]
            },
            
            "storage_settings": {
                "local_storage": True,
                "google_drive_upload": True,
                "data_retention_days": 90,
                "backup_retention_days": 30
            },
            
            "automation": {
                "enabled": True,
                "start_hour": 0,  # 24-hour format
                "end_hour": 23,
                "skip_weekends": False,
                "pause_during_maintenance": True
            },
            
            "monitoring": {
                "log_level": "INFO",
                "health_check_interval_minutes": 60,
                "alert_on_failures": True,
                "max_consecutive_failures": 3
            }
        }
        
        # Save default configuration
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            self.logger.info(f"Created default configuration at {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error saving default config: {e}")
            
        return default_config
    
    def load_api_credentials(self):
        """Load Weather Underground API credentials."""
        try:
            wu_api_key_path = self.project_root / "creds" / "wu_api_key.json"
            if wu_api_key_path.exists():
                with open(wu_api_key_path, 'r') as f:
                    creds = json.load(f)
                    self.wu_api_key = creds.get('test_api_key') or creds.get('api_key')
                    if not self.wu_api_key:
                        raise ValueError("No API key found in wu_api_key.json")
                    self.logger.info("Successfully loaded Weather Underground API credentials")
            else:
                raise FileNotFoundError(f"API credentials not found at {wu_api_key_path}")
        except Exception as e:
            self.logger.error(f"Error loading API credentials: {e}")
            self.wu_api_key = None
    
    def setup_schedules(self):
        """Setup automated schedules for 15-minute data collection."""
        if not self.config.get("automation", {}).get("enabled", True):
            self.logger.info("Automation is disabled in configuration")
            return
        
        # Schedule data collection every 15 minutes
        interval_minutes = self.config.get("collection_settings", {}).get("interval_minutes", 15)
        
        # Set up 15-minute intervals throughout the day
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                time_str = f"{hour:02d}:{minute:02d}"
                schedule.every().day.at(time_str).do(self.collection_job)
        
        # Setup health check every hour
        schedule.every().hour.do(self.health_check_job)
        
        # Setup daily cleanup at 1:00 AM
        schedule.every().day.at("01:00").do(self.daily_cleanup_job)
        
        self.logger.info(f"Scheduled test sensor data collection every {interval_minutes} minutes")
        self.logger.info("Scheduled hourly health checks")
        self.logger.info("Scheduled daily cleanup at 01:00")
    
    async def collect_wu_sensor_data(self, sensor_id: str, collection_time: datetime = None) -> Dict[str, Any]:
        """Collect data from a single Weather Underground sensor."""
        if collection_time is None:
            collection_time = datetime.now()
        
        if not self.wu_api_key:
            return {"error": "No API key available", "sensor_id": sensor_id}
        
        try:
            # Use current conditions API for real-time data
            base_url = "https://api.weather.com/v2/pws/observations/current"
            params = {
                "stationId": sensor_id,
                "format": "json",
                "apiKey": self.wu_api_key,
                "units": "m",
                "numericPrecision": "decimal"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if "observations" in data and data["observations"]:
                    obs = data["observations"][0]
                    
                    # Extract relevant data fields
                    result = {
                        "sensor_id": sensor_id,
                        "ms_station": WU_TO_MS_MAPPING.get(sensor_id, "Unknown"),
                        "collection_time": collection_time.isoformat(),
                        "timestamp": obs.get("obsTimeUtc", collection_time.isoformat()),
                        "temperature": obs.get("metric", {}).get("temp"),
                        "humidity": obs.get("humidity"),
                        "pressure": obs.get("metric", {}).get("pressure"),
                        "wind_speed": obs.get("metric", {}).get("windSpeed"),
                        "wind_gust": obs.get("metric", {}).get("windGust"),
                        "wind_direction": obs.get("winddir"),
                        "precip_rate": obs.get("metric", {}).get("precipRate"),
                        "precip_total": obs.get("metric", {}).get("precipTotal"),
                        "solar_radiation": obs.get("solarRadiation"),
                        "uv": obs.get("uv"),
                        "dewpoint": obs.get("metric", {}).get("dewpt"),
                        "heat_index": obs.get("metric", {}).get("heatIndex"),
                        "wind_chill": obs.get("metric", {}).get("windChill")
                    }
                    
                    return result
                else:
                    return {"error": "No observation data available", "sensor_id": sensor_id}
                    
        except Exception as e:
            self.logger.error(f"Error collecting data from sensor {sensor_id}: {e}")
            return {"error": str(e), "sensor_id": sensor_id}
    
    async def collect_all_test_sensors(self) -> List[Dict[str, Any]]:
        """Collect data from all test sensors concurrently."""
        collection_time = datetime.now()
        
        # Get batch size from configuration
        batch_size = self.config.get("collection_settings", {}).get("batch_size", 5)
        
        results = []
        sensor_list = self.config.get("test_sensors", {}).get("wu_sensors", TEST_SENSOR_IDS)
        
        # Process sensors in batches to avoid overwhelming the API
        for i in range(0, len(sensor_list), batch_size):
            batch = sensor_list[i:i + batch_size]
            
            # Collect data for this batch
            tasks = [self.collect_wu_sensor_data(sensor_id, collection_time) for sensor_id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Exception in batch collection: {result}")
                    results.append({"error": str(result), "sensor_id": "unknown"})
                else:
                    results.append(result)
            
            # Add delay between batches to be respectful to the API
            if i + batch_size < len(sensor_list):
                await asyncio.sleep(2)
        
        return results
    
    def save_test_sensor_data(self, data: List[Dict[str, Any]]) -> bool:
        """Save collected test sensor data to individual daily files per sensor."""
        try:
            if not data:
                self.logger.warning("No data to save")
                return False
            
            timestamp = datetime.now()
            date_str = timestamp.strftime('%Y%m%d')
            successful_data = [d for d in data if "error" not in d]
            
            if not successful_data:
                self.logger.warning("No successful sensor readings to save")
                return False
            
            # Create individual daily files for each sensor
            saved_files = []
            for sensor_data in successful_data:
                sensor_id = sensor_data.get("sensor_id")
                if not sensor_id:
                    continue
                
                # Create individual sensor daily file
                sensor_filename = f"{sensor_id}_daily_{date_str}.json"
                sensor_filepath = self.test_data_dir / sensor_filename
                
                # Load existing data if file exists
                if sensor_filepath.exists():
                    try:
                        with open(sensor_filepath, 'r') as f:
                            existing_data = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Could not load existing data for {sensor_id}: {e}")
                        existing_data = self._create_new_sensor_file_structure(sensor_id, date_str)
                else:
                    existing_data = self._create_new_sensor_file_structure(sensor_id, date_str)
                
                # Add new reading to sensor's daily data
                existing_data["readings"].append(sensor_data)
                existing_data["last_updated"] = timestamp.isoformat()
                existing_data["reading_count"] = len(existing_data["readings"])
                
                # Sort readings by collection time
                existing_data["readings"].sort(key=lambda x: x.get("collection_time", ""))
                
                # Save updated sensor file
                with open(sensor_filepath, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                
                saved_files.append(sensor_filepath)
            
            self.logger.info(f"Updated daily files for {len(saved_files)} sensors")
            
            # Update last collection timestamp
            self.update_last_collection_time(timestamp)
            
            # Also create/update combined daily CSV for easier analysis
            self.update_daily_csv(successful_data, timestamp)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving test sensor data: {e}")
            return False
    
    def _create_new_sensor_file_structure(self, sensor_id: str, date_str: str) -> Dict[str, Any]:
        """Create the structure for a new daily sensor file."""
        return {
            "sensor_id": sensor_id,
            "ms_station": WU_TO_MS_MAPPING.get(sensor_id, "Unknown"),
            "date": date_str,
            "date_readable": datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'),
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "reading_count": 0,
            "readings": []
        }
    
    def update_daily_csv(self, data: List[Dict[str, Any]], timestamp: datetime):
        """Update daily CSV file with new data."""
        try:
            # Create daily CSV filename
            date_str = timestamp.strftime('%Y%m%d')
            csv_filename = f"test_sensors_daily_{date_str}.csv"
            csv_filepath = self.test_data_dir / csv_filename
            
            # Convert data to DataFrame
            successful_data = [d for d in data if "error" not in d]
            if not successful_data:
                return
            
            new_df = pd.DataFrame(successful_data)
            
            # Append to existing CSV or create new one
            if csv_filepath.exists():
                existing_df = pd.read_csv(csv_filepath)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df
            
            # Sort by collection time
            if 'collection_time' in combined_df.columns:
                combined_df = combined_df.sort_values('collection_time')
            
            # Save updated CSV
            combined_df.to_csv(csv_filepath, index=False)
            
        except Exception as e:
            self.logger.error(f"Error updating daily CSV: {e}")
    
    def update_last_collection_time(self, timestamp: datetime):
        """Update the last successful collection timestamp."""
        try:
            data = {
                "last_collection": timestamp.isoformat(),
                "last_collection_readable": timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.last_collection_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error updating last collection time: {e}")
    
    def upload_to_google_drive(self, local_files: List[Path]) -> bool:
        """Upload test sensor data files to Google Drive."""
        try:
            if not self.config.get("storage_settings", {}).get("google_drive_upload", True):
                return True
            
            # Use master data system's Google Drive integration
            success_count = 0
            for file_path in local_files:
                try:
                    # Upload to test sensors folder in Google Drive
                    folder_name = "test_sensors_15min_data"
                    result = self.master_system.upload_to_drive(
                        file_path, 
                        folder_name
                    )
                    if result:
                        success_count += 1
                        self.logger.info(f"Uploaded {file_path.name} to Google Drive")
                    else:
                        self.logger.error(f"Failed to upload {file_path.name} to Google Drive")
                except Exception as e:
                    self.logger.error(f"Error uploading {file_path.name}: {e}")
            
            return success_count == len(local_files)
            
        except Exception as e:
            self.logger.error(f"Error in Google Drive upload: {e}")
            return False
    
    def collection_job(self):
        """Main data collection job that runs every 15 minutes."""
        self.logger.info("🔄 Starting 15-minute test sensor data collection")
        
        try:
            start_time = datetime.now()
            
            # Check if we're within operating hours
            current_hour = start_time.hour
            automation_config = self.config.get("automation", {})
            start_hour = automation_config.get("start_hour", 0)
            end_hour = automation_config.get("end_hour", 23)
            
            if not (start_hour <= current_hour <= end_hour):
                self.logger.info(f"Outside operating hours ({start_hour}:00-{end_hour}:00), skipping collection")
                return
            
            # Collect data from all test sensors
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(self.collect_all_test_sensors())
            finally:
                loop.close()
            
            # Save data locally
            if self.save_test_sensor_data(data):
                # Count successful collections
                success_count = len([d for d in data if "error" not in d])
                error_count = len([d for d in data if "error" in d])
                
                # Log results
                execution_time = (datetime.now() - start_time).total_seconds()
                self.logger.info(f"✅ Collection completed in {execution_time:.1f}s")
                self.logger.info(f"📊 Results: {success_count} successful, {error_count} errors")
                
                # Upload to Google Drive if enabled (upload all today's sensor files)
                today_sensor_files = self.get_latest_data_files(0)  # Get all sensor files from today
                if today_sensor_files:
                    self.upload_to_google_drive(today_sensor_files)
                
                # Log execution metadata
                self.log_execution_metadata("15min_collection", {
                    "start_time": start_time.isoformat(),
                    "execution_time_seconds": execution_time,
                    "sensors_attempted": len(data),
                    "sensors_successful": success_count,
                    "sensors_failed": error_count,
                    "data_saved": True
                })
            else:
                self.logger.error("❌ Failed to save collected data")
                
        except Exception as e:
            self.logger.error(f"❌ Error in collection job: {e}")
            self.logger.error(traceback.format_exc())
    
    def health_check_job(self):
        """Hourly health check to monitor system status."""
        self.logger.info("🔍 Running test sensor scheduler health check")
        
        try:
            issues = []
            
            # Check last collection time
            if self.last_collection_file.exists():
                with open(self.last_collection_file, 'r') as f:
                    last_data = json.load(f)
                    last_collection = datetime.fromisoformat(last_data["last_collection"])
                    
                    # Check if last collection was more than 30 minutes ago
                    if datetime.now() - last_collection > timedelta(minutes=30):
                        issues.append(f"Last collection was {datetime.now() - last_collection} ago")
            else:
                issues.append("No collection history found")
            
            # Check API credentials
            if not self.wu_api_key:
                issues.append("Weather Underground API key not available")
            
            # Check storage space and recent activity
            if self.test_data_dir.exists():
                # Count sensor files from today
                now = datetime.now()
                today_str = now.strftime('%Y%m%d')
                today_sensor_files = list(self.test_data_dir.glob(f"*_daily_{today_str}.json"))
                
                # Check if we have files for most sensors (should have 14 files for 14 sensors)
                expected_sensors = len(self.config.get("test_sensors", {}).get("wu_sensors", TEST_SENSOR_IDS))
                if len(today_sensor_files) < expected_sensors * 0.8:  # Allow for some sensors to be offline
                    issues.append(f"Only {len(today_sensor_files)} sensor files today (expected ~{expected_sensors})")
                
                # Check if sensor files have recent readings
                for sensor_file in today_sensor_files:
                    try:
                        with open(sensor_file, 'r') as f:
                            sensor_data = json.load(f)
                            reading_count = sensor_data.get("reading_count", 0)
                            
                            # Expected readings per day: 96 (every 15 minutes)
                            # Check proportionally based on time of day
                            expected_readings = min(96, int((now.hour * 60 + now.minute) / 15))
                            if reading_count < expected_readings * 0.7:  # Allow 30% tolerance
                                sensor_id = sensor_data.get("sensor_id", "Unknown")
                                issues.append(f"Sensor {sensor_id} has only {reading_count} readings (expected ~{expected_readings})")
                    except Exception as e:
                        issues.append(f"Could not check sensor file {sensor_file.name}: {e}")
                
                # Clean up old timestamped files that shouldn't exist anymore
                old_files = list(self.test_data_dir.glob("test_sensors_*.json"))
                if old_files:
                    self.logger.info(f"Found {len(old_files)} old timestamped files to clean up")
                    for old_file in old_files:
                        try:
                            old_file.unlink()
                            self.logger.info(f"Cleaned up old file: {old_file.name}")
                        except Exception as e:
                            self.logger.warning(f"Could not remove old file {old_file.name}: {e}")
            
            # Log health status
            if issues:
                self.logger.warning(f"⚠️ Health check found {len(issues)} issues:")
                for issue in issues:
                    self.logger.warning(f"  - {issue}")
            else:
                self.logger.info("✅ Health check passed - test sensor system operational")
            
            # Log health metadata
            self.log_execution_metadata("health_check", {
                "timestamp": datetime.now().isoformat(),
                "issues_count": len(issues),
                "issues": issues
            })
            
        except Exception as e:
            self.logger.error(f"❌ Error during health check: {e}")
    
    def daily_cleanup_job(self):
        """Daily cleanup of old data files."""
        self.logger.info("🧹 Running daily test sensor data cleanup")
        
        try:
            retention_days = self.config.get("storage_settings", {}).get("data_retention_days", 90)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Clean up old sensor daily files
            sensor_files = list(self.test_data_dir.glob("*_daily_*.json"))
            removed_count = 0
            
            for file_path in sensor_files:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
            
            # Clean up old timestamped files (legacy format)
            old_format_files = list(self.test_data_dir.glob("test_sensors_*.json"))
            for file_path in old_format_files:
                # These files are from the old format and can be removed
                file_path.unlink()
                removed_count += 1
            
            # Clean up old CSV files
            csv_files = list(self.test_data_dir.glob("test_sensors_daily_*.csv"))
            for file_path in csv_files:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
            
            self.logger.info(f"✅ Cleanup completed: removed {removed_count} old files")
            
        except Exception as e:
            self.logger.error(f"❌ Error during daily cleanup: {e}")
    
    def get_latest_data_files(self, count: int = 1) -> List[Path]:
        """Get the most recent sensor data files."""
        try:
            # Get all sensor daily files from today
            today_str = datetime.now().strftime('%Y%m%d')
            sensor_files = list(self.test_data_dir.glob(f"*_daily_{today_str}.json"))
            sensor_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return sensor_files[:count] if count > 0 else sensor_files
        except Exception:
            return []
    
    def log_execution_metadata(self, job_type: str, metadata: Dict[str, Any]):
        """Log execution metadata for monitoring and debugging."""
        metadata_file = project_root / "logs" / "test_sensor_execution.jsonl"
        
        try:
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "job_type": job_type,
                **metadata
            }
            
            with open(metadata_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Error logging execution metadata: {e}")
    
    def run_test_collection(self):
        """Run a test collection to verify everything works."""
        self.logger.info("🧪 Running test collection for test sensors")
        
        try:
            # Run a single collection cycle
            self.collection_job()
            
            # Check if data was saved by looking at today's sensor files
            today_str = datetime.now().strftime('%Y%m%d')
            today_sensor_files = list(self.test_data_dir.glob(f"*_daily_{today_str}.json"))
            
            if today_sensor_files:
                self.logger.info(f"✅ Test collection successful: Updated {len(today_sensor_files)} sensor files")
                
                # Display summary from one of the sensor files
                sample_file = today_sensor_files[0]
                with open(sample_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"📊 Sample sensor {data['sensor_id']}: {data['reading_count']} total readings today")
                
                return True
            else:
                self.logger.error("❌ Test collection failed: no data files created")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Test collection error: {e}")
            return False
    
    def get_schedule_info(self):
        """Get information about scheduled jobs."""
        jobs_info = []
        for job in schedule.jobs:
            jobs_info.append({
                "job": str(job.job_func.__name__),
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval),
                "unit": job.unit if hasattr(job, 'unit') else 'unknown'
            })
        return jobs_info
    
    def run_scheduler(self):
        """Run the scheduler continuously."""
        self.logger.info("🚀 Starting Test Sensor 15-Minute Scheduler")
        self.setup_schedules()
        
        # Log schedule information
        self.logger.info("📅 Scheduled jobs:")
        for job_info in self.get_schedule_info():
            if job_info['job'] == 'collection_job':
                # Don't log all 96 collection jobs, just summarize
                continue
            self.logger.info(f"  - {job_info['job']}: {job_info.get('interval', 'varies')} {job_info.get('unit', '')}")
        
        collection_jobs = [j for j in self.get_schedule_info() if j['job'] == 'collection_job']
        self.logger.info(f"  - collection_job: {len(collection_jobs)} times per day (every 15 minutes)")
        
        self.logger.info("⏰ Test sensor scheduler is running. Press Ctrl+C to stop.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("🛑 Test sensor scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Scheduler error: {e}")
            self.logger.error(traceback.format_exc())


def main():
    """Main entry point for the test sensor scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Test Sensor 15-Minute Scheduler')
    parser.add_argument('--run', action='store_true', help='Run the scheduler continuously')
    parser.add_argument('--test', action='store_true', help='Run a test collection and exit')
    parser.add_argument('--health-check', action='store_true', help='Run health check and exit')
    parser.add_argument('--schedule-info', action='store_true', help='Show scheduled jobs info')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Initialize scheduler
    scheduler = TestSensorScheduler(config_path=args.config)
    
    if args.run:
        scheduler.run_scheduler()
    elif args.test:
        success = scheduler.run_test_collection()
        sys.exit(0 if success else 1)
    elif args.health_check:
        scheduler.health_check_job()
    elif args.schedule_info:
        print("📅 Test Sensor Scheduled Jobs:")
        for job_info in scheduler.get_schedule_info():
            if job_info['job'] == 'collection_job':
                continue  # Skip individual collection jobs
            print(f"  - {job_info['job']}: {job_info.get('interval', 'varies')} {job_info.get('unit', '')}")
            if job_info['next_run']:
                print(f"    Next run: {job_info['next_run']}")
        
        collection_jobs = [j for j in scheduler.get_schedule_info() if j['job'] == 'collection_job']
        print(f"  - collection_job: {len(collection_jobs)} times per day (every 15 minutes)")
        if collection_jobs:
            print(f"    Next collection: {collection_jobs[0]['next_run']}")
    else:
        print("ℹ️  Test Sensor 15-Minute Scheduler")
        print("💡 Use --run to start the scheduler")
        print("🧪 Use --test to run a test collection")
        print("🔍 Use --health-check to check system health")
        print("📅 Use --schedule-info to see scheduled jobs")


if __name__ == "__main__":
    main()
