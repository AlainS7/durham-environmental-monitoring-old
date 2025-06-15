#!/usr/bin/env python3
"""
Enhanced Data Manager for Hot Durham Project
Handles automated data pulls, organization, and Google Drive synchronization.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import logging
from typing import Optional, Tuple, Dict, Any
import time

# Import test sensor configuration
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'config'))
from test_sensors_config import TestSensorConfig, is_test_sensor, get_data_path, get_log_path

# Optional imports
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("Warning: schedule module not available. Install with: pip install schedule")

# Google Drive integration
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.oauth2.service_account import Credentials
    import io
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Warning: Google Drive integration not available. Install google-api-python-client")

# Note: Removed circular import of data fetching functions
# The fetch_wu_data and fetch_tsi_data functions are now accessed dynamically
# to avoid circular import issues

class DataManager:
    """Manages automated data pulls, storage, and Google Drive synchronization."""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent / "data"
        
        # Initialize test sensor configuration
        self.test_config = TestSensorConfig()
        
        self.setup_directories()
        self.setup_logging()
        self.drive_service = self.setup_google_drive()
        
        # Set up common paths
        self.raw_data_path = self.base_dir / "raw_pulls"
        self.processed_path = self.base_dir / "processed"
        self.backup_path = self.base_dir / "backup"
        self.temp_path = self.base_dir / "temp"
        self.logs_path = self.base_dir
        
    def setup_directories(self):
        """Create the complete directory structure if it doesn't exist."""
        directories = [
            "raw_pulls/wu/2024", "raw_pulls/wu/2025",
            "raw_pulls/tsi/2024", "raw_pulls/tsi/2025", 
            "processed/weekly_summaries",
            "processed/monthly_summaries",
            "processed/annual_summaries",
            "backup/google_drive_sync",
            "backup/local_archive",
            "temp"
        ]
        
        for directory in directories:
            (self.base_dir / directory).mkdir(parents=True, exist_ok=True)
            
    def setup_logging(self):
        """Configure logging for data management operations."""
        log_file = self.base_dir / "data_management.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_google_drive(self) -> Optional[Any]:
        """Initialize Google Drive service if credentials are available."""
        if not GOOGLE_DRIVE_AVAILABLE:
            self.logger.warning("Google Drive integration not available")
            return None
            
        creds_path = Path(__file__).parent.parent.parent / "creds" / "google_creds.json"
        if not creds_path.exists():
            self.logger.warning(f"Google credentials not found at {creds_path}")
            return None
            
        try:
            credentials = Credentials.from_service_account_file(
                str(creds_path),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            service = build('drive', 'v3', credentials=credentials)
            self.logger.info("Google Drive service initialized successfully")
            return service
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive service: {e}")
            return None
    
    def get_week_info(self, date: datetime = None) -> Tuple[int, int, str]:
        """Get ISO week number, year, and formatted string for a given date."""
        if date is None:
            date = datetime.now()
        year, week, _ = date.isocalendar()
        week_str = f"{year}-{week:02d}"
        return year, week, week_str
    
    def get_file_paths(self, data_type: str, start_date: str, end_date: str, 
                      file_format: str = "csv") -> Dict[str, Path]:
        """Generate file paths for different storage locations."""
        # Parse start_date - support both YYYY-MM-DD and YYYYMMDD formats
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            try:
                start_dt = datetime.strptime(start_date, "%Y%m%d")
            except ValueError:
                raise ValueError(f"Date format not supported: {start_date}. Use YYYY-MM-DD or YYYYMMDD")
        
        year, week, week_str = self.get_week_info(start_dt)
        
        # Create week subfolder if it doesn't exist
        week_folder = self.base_dir / "raw_pulls" / data_type / str(year) / f"week_{week:02d}"
        week_folder.mkdir(parents=True, exist_ok=True)
        
        filename = f"{data_type}_data_{start_date}_to_{end_date}.{file_format}"
        weekly_filename = f"{data_type}_week_{week_str}.{file_format}"
        
        return {
            "raw": week_folder / filename,
            "weekly": self.base_dir / "processed" / "weekly_summaries" / weekly_filename,
            "backup": self.base_dir / "backup" / "local_archive" / filename,
            "temp": self.base_dir / "temp" / filename
        }
    
    def pull_and_store_data(self, data_type: str, start_date: str, end_date: str, 
                           file_format: str = "csv") -> Optional[Path]:
        """Pull data from API and store in organized structure."""
        self.logger.info(f"Starting {data_type.upper()} data pull for {start_date} to {end_date}")
        
        try:
            # Dynamically import data fetching functions to avoid circular imports
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent / "data_collection"))
            
            # Fetch data based on type
            if data_type == "wu":
                from faster_wu_tsi_to_sheets_async import fetch_wu_data
                df = fetch_wu_data(start_date, end_date)
            elif data_type == "tsi":
                from faster_wu_tsi_to_sheets_async import fetch_tsi_data
                df, _ = fetch_tsi_data(start_date, end_date)
            else:
                self.logger.error(f"Unknown data type: {data_type}")
                return None
            
            if df is None or df.empty:
                self.logger.warning(f"No {data_type.upper()} data retrieved")
                return None
            
            # Get file paths
            paths = self.get_file_paths(data_type, start_date, end_date, file_format)
            
            # Save data to various locations
            if file_format == "excel":
                df.to_excel(paths["raw"], index=False)
                df.to_excel(paths["backup"], index=False)
            else:
                df.to_csv(paths["raw"], index=False)
                df.to_csv(paths["backup"], index=False)
            
            self.logger.info(f"Data saved to {paths['raw']}")
            
            # Upload to Google Drive if available using improved folder structure
            if self.drive_service:
                try:
                    from config.improved_google_drive_config import get_production_path
                    # Use improved folder structure
                    drive_folder = get_production_path('raw', data_type.upper())
                    self.upload_to_drive(paths["raw"], drive_folder, priority=1)  # High priority for production data
                except ImportError:
                    # Fallback to legacy folder structure
                    self.upload_to_drive(paths["raw"], f"HotDurham/Production/RawData/{data_type.upper()}")
            
            return paths["raw"]
            
        except Exception as e:
            self.logger.error(f"Error during {data_type} data pull: {e}")
            return None
    
    def upload_to_drive(self, local_path: Path, drive_folder: str, priority: int = 2) -> bool:
        """Upload a file to Google Drive using enhanced manager with rate limiting."""
        # Try to use enhanced manager first
        try:
            from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
            enhanced_manager = get_enhanced_drive_manager(str(self.base_dir.parent))
            
            if enhanced_manager and enhanced_manager.drive_service:
                # Use enhanced manager with queue system
                return enhanced_manager.queue_upload(local_path, drive_folder, priority)
        except ImportError:
            self.logger.warning("Enhanced Google Drive manager not available, using legacy upload")
        
        # Fallback to legacy upload method
        if not self.drive_service:
            return False
            
        try:
            # Create folder structure if it doesn't exist
            folder_id = self.get_or_create_drive_folder(drive_folder)
            if not folder_id:
                return False
            
            # Upload file
            media = MediaFileUpload(str(local_path))
            file_metadata = {
                'name': local_path.name,
                'parents': [folder_id]
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            self.logger.info(f"File uploaded to Google Drive: {local_path.name} (ID: {file.get('id')})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to upload {local_path.name} to Google Drive: {e}")
            return False
    
    def get_or_create_drive_folder(self, folder_path: str) -> Optional[str]:
        """Get or create a folder in Google Drive, handling nested paths."""
        if not self.drive_service:
            return None
            
        try:
            folder_names = folder_path.strip('/').split('/')
            parent_id = 'root'
            
            for folder_name in folder_names:
                # Search for existing folder
                query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
                results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
                items = results.get('files', [])
                
                if items:
                    parent_id = items[0]['id']
                else:
                    # Create new folder
                    folder_metadata = {
                        'name': folder_name,
                        'parents': [parent_id],
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
                    parent_id = folder.get('id')
            
            return parent_id
            
        except Exception as e:
            self.logger.error(f"Failed to create/access folder {folder_path}: {e}")
            return None
    
    def weekly_data_pull(self):
        """Perform weekly data pull for both WU and TSI."""
        self.logger.info("Starting scheduled weekly data pull")
        
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        # Pull WU data
        wu_path = self.pull_and_store_data("wu", start_str, end_str)
        
        # Pull TSI data
        tsi_path = self.pull_and_store_data("tsi", start_str, end_str)
        
        # Clean up old temp files
        self.cleanup_temp_files()
        
        self.logger.info("Weekly data pull completed")
        
        return wu_path, tsi_path
    
    def bi_weekly_backup_pull(self):
        """Perform bi-weekly backup pull with extended date range."""
        self.logger.info("Starting bi-weekly backup data pull")
        
        # Calculate date range (last 14 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        # Pull data with backup suffix
        for data_type in ["wu", "tsi"]:
            try:
                paths = self.get_file_paths(data_type, start_str, end_str)
                backup_path = paths["backup"].parent / f"backup_{paths['backup'].name}"
                
                if data_type == "wu":
                    df = fetch_wu_data(start_str, end_str)
                else:
                    df, _ = fetch_tsi_data(start_str, end_str)
                
                if df is not None and not df.empty:
                    df.to_csv(backup_path, index=False)
                    self.logger.info(f"Backup {data_type} data saved to {backup_path}")
                    
                    # Upload backup to Drive
                    if self.drive_service:
                        self.upload_to_drive(backup_path, f"HotDurham/Backups/{data_type.upper()}")
                        
            except Exception as e:
                self.logger.error(f"Error during {data_type} backup pull: {e}")
    
    def cleanup_temp_files(self, days_old: int = 7):
        """Clean up temporary files older than specified days."""
        temp_dir = self.base_dir / "temp"
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for file_path in temp_dir.glob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    self.logger.info(f"Cleaned up temp file: {file_path.name}")
    
    def sync_to_google_drive(self):
        """Sync all important data to Google Drive using improved folder structure."""
        if not self.drive_service:
            self.logger.warning("Google Drive service not available for sync")
            return
        
        self.logger.info("Starting Google Drive sync with improved folder structure")
        
        try:
            from config.improved_google_drive_config import get_production_path, get_archive_path
            use_improved_structure = True
        except ImportError:
            self.logger.warning("Improved folder structure not available, using legacy structure")
            use_improved_structure = False
        
        # Sync recent raw data
        for data_type in ["wu", "tsi"]:
            for year_folder in (self.base_dir / "raw_pulls" / data_type).glob("*"):
                if year_folder.is_dir():
                    for week_folder in year_folder.glob("week_*"):
                        for file_path in week_folder.glob("*.csv"):
                            # Only sync files from last month
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if (datetime.now() - file_time).days <= 30:
                                if use_improved_structure:
                                    drive_folder = get_production_path('raw', data_type.upper())
                                else:
                                    drive_folder = f"HotDurham/Production/RawData/{data_type.upper()}/{year_folder.name}"
                                self.upload_to_drive(file_path, drive_folder, priority=2)
        
        # Sync processed data
        for summary_type in ["weekly_summaries", "monthly_summaries", "annual_summaries"]:
            summary_dir = self.base_dir / "processed" / summary_type
            for file_path in summary_dir.glob("*.csv"):
                if use_improved_structure:
                    drive_folder = get_production_path('processed')
                else:
                    drive_folder = f"HotDurham/Production/Processed/{summary_type}"
                self.upload_to_drive(file_path, drive_folder, priority=3)
        
        self.logger.info("Google Drive sync completed")
    
    def schedule_automatic_pulls(self):
        """Set up scheduled automatic data pulls."""
        if not SCHEDULE_AVAILABLE:
            self.logger.error("Schedule module not available. Cannot set up automatic pulls.")
            print("Please install the schedule module: pip install schedule")
            return
            
        self.logger.info("Setting up automatic data pull schedule")
        
        # Weekly pulls every Sunday at midnight
        schedule.every().sunday.at("00:00").do(self.weekly_data_pull)
        
        # Bi-weekly backup pulls every other Wednesday at 2 AM
        schedule.every(2).weeks.at("02:00").do(self.bi_weekly_backup_pull)
        
        # Daily Google Drive sync at 3 AM
        schedule.every().day.at("03:00").do(self.sync_to_google_drive)
        
        # Weekly temp cleanup on Saturdays
        schedule.every().saturday.at("23:00").do(lambda: self.cleanup_temp_files(7))
        
        self.logger.info("Automatic schedule configured")
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def manual_pull(self, data_types: list, start_date: str, end_date: str, 
                   file_format: str = "csv") -> Dict[str, Path]:
        """Perform manual data pull for specific date range."""
        results = {}
        
        for data_type in data_types:
            if data_type.lower() in ["wu", "tsi"]:
                path = self.pull_and_store_data(data_type.lower(), start_date, end_date, file_format)
                results[data_type] = path
            else:
                self.logger.warning(f"Unknown data type: {data_type}")
        
        return results
    
    def load_recent_data(self, source, days=7):
        """
        Load recent data from the specified source
        
        Args:
            source (str): 'wu' or 'tsi'
            days (int): Number of days back to look for data
            
        Returns:
            pd.DataFrame: Combined dataframe of recent data
        """
        import pandas as pd
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        source_folder = os.path.join(self.raw_data_path, source, str(end_date.year))
        if not os.path.exists(source_folder):
            self.logger.warning(f"No data folder found for {source} in {end_date.year}")
            return pd.DataFrame()
        
        # Find files within the date range
        data_files = []
        for file in os.listdir(source_folder):
            if file.endswith(('.csv', '.xlsx')):
                file_path = os.path.join(source_folder, file)
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                if start_date <= file_date <= end_date:
                    data_files.append(file_path)
        
        if not data_files:
            self.logger.info(f"No recent {source} data found in last {days} days")
            return pd.DataFrame()
        
        # Load and combine files
        dataframes = []
        for file_path in data_files:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                dataframes.append(df)
                self.logger.info(f"Loaded {len(df)} records from {os.path.basename(file_path)}")
            except Exception as e:
                self.logger.error(f"Error loading {file_path}: {e}")
        
        if dataframes:
            combined_df = pd.concat(dataframes, ignore_index=True)
            self.logger.info(f"Combined {len(combined_df)} total records from {len(dataframes)} files")
            return combined_df
        else:
            return pd.DataFrame()
    
    def cleanup_temp_files(self, days_old=7):
        """
        Clean up temporary files older than specified days
        
        Args:
            days_old (int): Remove temp files older than this many days
        """
        from datetime import datetime, timedelta
        
        if not os.path.exists(self.temp_path):
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned_count = 0
        
        for file in os.listdir(self.temp_path):
            file_path = os.path.join(self.temp_path, file)
            if os.path.isfile(file_path):
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_date < cutoff_date:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up temp file: {file}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up {file}: {e}")
        
        self.logger.info(f"Cleaned up {cleaned_count} temporary files")
    
    def verify_data_integrity(self):
        """
        Verify data integrity and report on data availability
        
        Returns:
            dict: Report on data integrity and availability
        """
        report = {
            'total_files': 0,
            'total_size_mb': 0,
            'sources': {},
            'date_range': {},
            'issues': []
        }
        
        for source in ['wu', 'tsi']:
            source_path = os.path.join(self.raw_data_path, source)
            if not os.path.exists(source_path):
                report['issues'].append(f"Missing source folder: {source}")
                continue
            
            source_info = {
                'files': 0,
                'size_mb': 0,
                'years': [],
                'earliest_date': None,
                'latest_date': None
            }
            
            for year_folder in os.listdir(source_path):
                year_path = os.path.join(source_path, year_folder)
                if os.path.isdir(year_path) and year_folder.isdigit():
                    source_info['years'].append(year_folder)
                    
                    for file in os.listdir(year_path):
                        file_path = os.path.join(year_path, file)
                        if os.path.isfile(file_path) and file.endswith(('.csv', '.xlsx')):
                            source_info['files'] += 1
                            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                            source_info['size_mb'] += file_size
                            
                            # Track date range from file modification times
                            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if source_info['earliest_date'] is None or file_date < source_info['earliest_date']:
                                source_info['earliest_date'] = file_date
                            if source_info['latest_date'] is None or file_date > source_info['latest_date']:
                                source_info['latest_date'] = file_date
            
            report['sources'][source] = source_info
            report['total_files'] += source_info['files']
            report['total_size_mb'] += source_info['size_mb']
        
        # Overall date range
        all_earliest = [info['earliest_date'] for info in report['sources'].values() if info['earliest_date']]
        all_latest = [info['latest_date'] for info in report['sources'].values() if info['latest_date']]
        
        if all_earliest and all_latest:
            report['date_range'] = {
                'earliest': min(all_earliest),
                'latest': max(all_latest),
                'span_days': (max(all_latest) - min(all_earliest)).days
            }
        
        self.logger.info(f"Data integrity check completed: {report['total_files']} files, {report['total_size_mb']:.2f} MB")
        return report
    
    def get_data_summary(self, days_back=30):
        """
        Get a summary of recent data pulls and activity
        
        Args:
            days_back (int): Number of days to look back
            
        Returns:
            dict: Summary of recent data activity
        """
        from datetime import datetime, timedelta
        
        summary = {
            'period': f"Last {days_back} days",
            'wu_pulls': 0,
            'tsi_pulls': 0,
            'total_records': 0,
            'sheets_created': 0,
            'drive_syncs': 0,
            'last_pull': None,
            'data_sources_active': []
        }
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Check automation log
        automation_log_path = os.path.join(self.logs_path, 'automation_runs.json')
        if os.path.exists(automation_log_path):
            try:
                with open(automation_log_path, 'r') as f:
                    runs = [json.loads(line) for line in f if line.strip()]
                
                recent_runs = [
                    run for run in runs 
                    if datetime.strptime(run['timestamp'], '%Y-%m-%d %H:%M:%S') > cutoff_date
                ]
                
                for run in recent_runs:
                    if run.get('wu_records', 0) > 0:
                        summary['wu_pulls'] += 1
                        summary['total_records'] += run['wu_records']
                    if run.get('tsi_records', 0) > 0:
                        summary['tsi_pulls'] += 1
                        summary['total_records'] += run['tsi_records']
                    if run.get('sheet_created'):
                        summary['sheets_created'] += 1
                
                if recent_runs:
                    summary['last_pull'] = max(run['timestamp'] for run in recent_runs)
                    
            except Exception as e:
                self.logger.error(f"Error reading automation log: {e}")
        
        # Determine active data sources
        if summary['wu_pulls'] > 0:
            summary['data_sources_active'].append('Weather Underground')
        if summary['tsi_pulls'] > 0:
            summary['data_sources_active'].append('TSI')
        
        return summary

    def save_raw_data(self, data: pd.DataFrame, source: str, start_date: str, end_date: str, 
                     pull_type: str, file_format: str = 'csv') -> str:
        """
        Save raw data to organized folder structure.
        
        Args:
            data: DataFrame to save
            source: 'wu' or 'tsi'
            start_date: Start date string
            end_date: End date string
            pull_type: Type of pull (weekly, bi-weekly, manual, etc.)
            file_format: File format ('csv', 'excel')
            
        Returns:
            Path to saved file
        """
        try:
            # Get current date info for folder organization
            current_date = datetime.now()
            year = current_date.year
            week_num = current_date.isocalendar()[1]
            
            # Create year-specific folder if needed
            year_folder = self.raw_data_path / source / str(year)
            year_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp and type
            timestamp = current_date.strftime('%Y%m%d_%H%M%S')
            filename = f"{source.upper()}_{start_date}_to_{end_date}_{pull_type}_{timestamp}.{file_format}"
            
            file_path = year_folder / filename
            
            # Save the data
            if file_format.lower() == 'csv':
                data.to_csv(file_path, index=False)
            elif file_format.lower() == 'excel':
                data.to_excel(file_path, index=False, engine='openpyxl')
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            # Log the operation
            self.logger.info(f"Saved {source.upper()} raw data to {file_path}")
            
            # Save metadata
            metadata = {
                'source': source,
                'start_date': start_date,
                'end_date': end_date,
                'pull_type': pull_type,
                'file_format': file_format,
                'rows': len(data),
                'columns': list(data.columns),
                'created_date': timestamp,
                'file_size_bytes': file_path.stat().st_size if file_path.exists() else 0
            }
            
            metadata_path = file_path.with_suffix(f'.{file_format}.metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Error saving {source} raw data: {e}")
            return None
    
    def save_sheet_metadata(self, sheet_info: dict, start_date: str, end_date: str, pull_type: str):
        """
        Save Google Sheet metadata for tracking purposes.
        
        Args:
            sheet_info: Dictionary containing sheet information
            start_date: Start date string
            end_date: End date string
            pull_type: Type of pull
        """
        try:
            # Create metadata folder if needed
            metadata_folder = self.processed_path / "sheet_metadata"
            metadata_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate metadata filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sheet_metadata_{start_date}_to_{end_date}_{pull_type}_{timestamp}.json"
            
            metadata_path = metadata_folder / filename
            
            # Enhance sheet info with additional metadata
            enhanced_info = {
                **sheet_info,
                'metadata': {
                    'saved_date': timestamp,
                    'start_date': start_date,
                    'end_date': end_date,
                    'pull_type': pull_type,
                    'data_manager_version': '1.0'
                }
            }
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(enhanced_info, f, indent=2)
            
            self.logger.info(f"Saved sheet metadata to {metadata_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving sheet metadata: {e}")
    
    def sync_to_drive(self):
        """
        Sync recent data to Google Drive.
        This is a wrapper for sync_to_google_drive with simplified interface.
        """
        try:
            self.sync_to_google_drive()
        except Exception as e:
            self.logger.error(f"Error in sync_to_drive: {e}")
            raise

    def log_automation_run(self, log_entry):
        """Log automation run details."""
        try:
            logs_dir = self.base_dir / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            log_file = logs_dir / f"automation_log_{datetime.now().strftime('%Y%m')}.json"
            
            # Read existing logs
            logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            
            # Add new log entry
            logs.append(log_entry)
            
            # Write back logs
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2, default=str)
                
            self.logger.info(f"Logged automation run to {log_file}")
            
        except Exception as e:
            self.logger.error(f"Error logging automation run: {e}")

    def get_sensor_file_paths(self, sensor_id: str, data_type: str, start_date: str, 
                             end_date: str, file_format: str = "csv") -> Dict[str, Path]:
        """Generate file paths for sensor data based on test vs production status."""
        year, week, week_str = self.get_week_info(datetime.strptime(start_date, "%Y%m%d"))
        
        # Determine if this is a test sensor
        is_test = self.test_config.is_test_sensor(sensor_id)
        
        if is_test:
            # Use test data paths
            base_path = self.test_config.get_data_path(sensor_id)
            log_path = self.test_config.get_log_path(sensor_id)
            prefix = self.test_config.get_filename_prefix(sensor_id)
            
            # Create test-specific subdirectories
            week_folder = base_path / data_type / str(year) / f"week_{week:02d}"
            week_folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"{prefix}_{data_type}_data_{start_date}_to_{end_date}_{sensor_id}.{file_format}"
            
            return {
                "raw": week_folder / filename,
                "backup": base_path / "backup" / filename,
                "temp": base_path / "temp" / filename,
                "log": log_path / f"{prefix}_{data_type}_{datetime.now().strftime('%Y%m%d')}.log",
                "type": "test"
            }
        else:
            # Use production paths (existing logic)
            week_folder = self.base_dir / "raw_pulls" / data_type / str(year) / f"week_{week:02d}"
            week_folder.mkdir(parents=True, exist_ok=True)
            
            filename = f"{data_type}_data_{start_date}_to_{end_date}.{file_format}"
            
            return {
                "raw": week_folder / filename,
                "weekly": self.base_dir / "processed" / "weekly_summaries" / f"{data_type}_week_{week_str}.{file_format}",
                "backup": self.base_dir / "backup" / "local_archive" / filename,
                "temp": self.base_dir / "temp" / filename,
                "log": self.logs_path / f"{data_type}_{datetime.now().strftime('%Y%m%d')}.log",
                "type": "production"
            }
    
    def save_sensor_data(self, sensor_id: str, data_type: str, df: pd.DataFrame, 
                        start_date: str, end_date: str, file_format: str = "csv") -> Optional[Path]:
        """Save sensor data to appropriate location based on test vs production status."""
        if df is None or df.empty:
            self.logger.warning(f"No data to save for sensor {sensor_id}")
            return None
        
        try:
            # Get sensor-specific file paths
            paths = self.get_sensor_file_paths(sensor_id, data_type, start_date, end_date, file_format)
            
            # Log the routing decision
            sensor_type = "TEST" if paths["type"] == "test" else "PRODUCTION"
            self.logger.info(f"Routing {sensor_id} ({sensor_type}) data to: {paths['raw']}")
            
            # Ensure backup and temp directories exist for test sensors
            if paths["type"] == "test":
                paths["backup"].parent.mkdir(parents=True, exist_ok=True)
                paths["temp"].parent.mkdir(parents=True, exist_ok=True)
            
            # Save data based on format
            if file_format == "excel":
                df.to_excel(paths["raw"], index=False)
                df.to_excel(paths["backup"], index=False)
            else:
                df.to_csv(paths["raw"], index=False)
                df.to_csv(paths["backup"], index=False)
            
            # Log the save operation
            with open(paths["log"], 'a', encoding='utf-8') as log_file:
                log_file.write(f"{datetime.now().isoformat()} - Saved {len(df)} records for sensor {sensor_id} to {paths['raw']}\n")
            
            self.logger.info(f"Sensor data saved successfully: {paths['raw']}")
            
            # Upload to appropriate Google Drive folder
            if self.drive_service:
                if paths["type"] == "test":
                    # Use new organized test sensor folder structure
                    drive_folder = self.test_config.get_drive_folder_path_with_date(
                        sensor_id, 
                        start_date.replace('-', ''), 
                        "sensors"
                    )
                else:
                    # Use existing production folder structure
                    drive_folder = f"HotDurham/Production/RawData/{data_type.upper()}"
                
                self.logger.info(f"Uploading {sensor_id} data to Google Drive: {drive_folder}")
                self.upload_to_drive(paths["raw"], drive_folder)
            
            return paths["raw"]
            
        except Exception as e:
            self.logger.error(f"Error saving sensor data for {sensor_id}: {e}")
            return None

    def get_test_sensor_summary(self) -> Dict[str, Any]:
        """Get summary of test sensor configuration and data status."""
        summary = {
            "test_sensors_count": len(self.test_config.get_test_sensors()),
            "test_sensors": self.test_config.get_test_sensors(),
            "test_data_path": str(self.test_config.test_data_path),
            "test_logs_path": str(self.test_config.test_logs_path),
            "data_files": {},
            "log_files": {}
        }
        
        # Count data files in test directories
        if self.test_config.test_sensors_path.exists():
            for data_type in ['wu', 'tsi']:
                type_path = self.test_config.test_sensors_path / data_type
                if type_path.exists():
                    summary["data_files"][data_type] = len(list(type_path.rglob("*.csv"))) + len(list(type_path.rglob("*.xlsx")))
        
        # Count log files
        if self.test_config.test_logs_path.exists():
            summary["log_files"]["count"] = len(list(self.test_config.test_logs_path.glob("*.log")))
        
        return summary
    
    def get_data_inventory(self) -> Dict[str, Any]:
        """Get inventory of all data files"""
        inventory = {
            "total_files": 0,
            "total_size_mb": 0.0,
            "by_type": {},
            "last_updated": datetime.now().isoformat()
        }
        
        # Count files in data directories
        data_dirs = [self.base_dir / "data"]
        if hasattr(self, 'raw_data_path'):
            data_dirs.append(self.raw_data_path)
        if hasattr(self, 'processed_data_path'):
            data_dirs.append(self.processed_data_path)
        
        for data_dir in data_dirs:
            if data_dir.exists():
                for file_path in data_dir.rglob("*"):
                    if file_path.is_file():
                        inventory["total_files"] += 1
                        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                        inventory["total_size_mb"] += file_size
                        
                        # Count by file type
                        file_ext = file_path.suffix.lower()
                        if file_ext not in inventory["by_type"]:
                            inventory["by_type"][file_ext] = {"count": 0, "size_mb": 0.0}
                        inventory["by_type"][file_ext]["count"] += 1
                        inventory["by_type"][file_ext]["size_mb"] += file_size
        
        inventory["total_size_mb"] = round(inventory["total_size_mb"], 2)
        return inventory
