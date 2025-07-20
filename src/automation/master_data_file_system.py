#!/usr/bin/env python3
"""
Master Data File System for Hot Durham Air Quality Monitoring

This system creates and maintains comprehensive historical data files that:
1. Accumulate all sensor data since inception
2. Add new weekly data automatically
3. Provide master datasets for analysis and reporting

Features:
- Master CSV files for WU and TSI data combined since inception
- Weekly automated data collection and appending
- Data deduplication and quality validation
- Historical data gap detection and filling
- Backup and versioning of master files
- Integration with existing data management infrastructure
- Automatic Google Drive synchronization for master files
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Optional, Dict, List, Tuple, Any
import sqlite3
import shutil
import hashlib
import asyncio

# Google Drive integration
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.service_account import Credentials
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    print("Warning: Google Drive integration not available. Install google-api-python-client")

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

try:
    from src.core.data_manager import DataManager
    from src.data_collection.faster_wu_tsi_to_sheets_async import fetch_wu_data, fetch_tsi_data_async
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")

class MasterDataFileSystem:
    """Manages master historical data files with automated weekly updates."""
    
    def __init__(self, base_dir: Optional[str] = None, config_path: Optional[str] = None):
        self.project_root = project_root  # Add project_root as instance attribute
        self.base_dir = Path(base_dir) if base_dir else project_root / "data"
        self.config_path = Path(config_path) if config_path else project_root / "config" / "master_data_config.json"
        
        # Initialize paths
        self.master_data_path = self.base_dir / "master_data"
        self.backup_path = self.base_dir / "backup" / "master_data_backup"
        self.raw_pulls_path = project_root / "raw_pulls"  # Fixed: Point to actual raw_pulls location
        self.metadata_path = self.base_dir / "master_data_metadata"
        
        # Setup system
        self.setup_directories()
        self.setup_logging()
        self.config = self.load_configuration()
        self.data_manager = DataManager(str(self.base_dir))
        
        # Google Drive integration
        self.drive_service = self.setup_google_drive()
        
        # Master file paths
        self.wu_master_file = self.master_data_path / "wu_master_historical_data.csv"
        self.tsi_master_file = self.master_data_path / "tsi_master_historical_data.csv"
        self.combined_master_file = self.master_data_path / "combined_master_historical_data.csv"
        self.master_db_file = self.master_data_path / "master_data.db"
        
        # Initialize database
        self.init_database()
        
    def setup_directories(self):
        """Create required directory structure."""
        directories = [
            self.master_data_path,
            self.backup_path,
            self.metadata_path,
            self.master_data_path / "versions",
            self.master_data_path / "exports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
    def setup_logging(self):
        """Configure logging for master data operations."""
        log_file = self.base_dir / "master_data_system.log"
        
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
        """Initialize Google Drive service for master data uploads."""
        if not GOOGLE_DRIVE_AVAILABLE:
            self.logger.warning("Google Drive integration not available")
            return None
            
        creds_path = self.project_root / "creds" / "google_creds.json"
        if not creds_path.exists():
            self.logger.warning(f"Google credentials not found at {creds_path}")
            return None
            
        try:
            credentials = Credentials.from_service_account_file(
                str(creds_path),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            service = build('drive', 'v3', credentials=credentials)
            self.logger.info("Google Drive service initialized successfully for master data")
            return service
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive service: {e}")
            return None
            
    def upload_to_drive(self, local_path: Path, drive_folder: str) -> bool:
        """Upload a master data file to Google Drive using enhanced manager."""
        # Try to use enhanced manager first
        try:
            from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
            enhanced_manager = get_enhanced_drive_manager(str(self.project_root))
            
            if enhanced_manager and enhanced_manager.drive_service:
                # Use enhanced manager with high priority for master data
                return enhanced_manager.upload_file_sync(local_path, drive_folder)
        except ImportError:
            self.logger.warning("Enhanced Google Drive manager not available, using legacy upload")
        
        # Fallback to legacy upload
        if not self.drive_service:
            self.logger.info(f"Google Drive not available, skipping upload of {local_path.name}")
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
            
            self.logger.info(f"Master data file uploaded to Google Drive: {local_path.name} (ID: {file.get('id')})")
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
    def load_configuration(self) -> Dict[str, Any]:
        """Load or create master data system configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                self.logger.info("Loaded existing master data configuration")
                return config
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")
        
        # Create default configuration
        default_config = {
            "data_sources": {
                "wu": {
                    "enabled": True,
                    "stations": ["KNCDURHA209", "KNCDURHA284", "KNCDURHA590", "KNCDURHA548", "KNCDURHA549"],
                    "metrics": ["timestamp", "tempf", "humidity", "precipRate", "windspeedAvg", "winddir", "solarRadiationHigh", "pressure"],
                    "collection_start_date": "2023-01-01"
                },
                "tsi": {
                    "enabled": True,
                    "devices": "auto_discover",
                    "metrics": ["timestamp", "PM 2.5", "T (C)", "RH (%)", "PM 1", "PM 4", "PM 10", "PM 2.5 AQI"],
                    "collection_start_date": "2023-01-01"
                }
            },
            "master_file_settings": {
                "update_frequency": "weekly",
                "max_file_size_mb": 500,
                "backup_retention_days": 365,
                "enable_versioning": True,
                "enable_sqlite_db": True
            },
            "data_quality": {
                "enable_deduplication": True,
                "enable_gap_detection": True,
                "enable_outlier_detection": False,
                "duplicate_tolerance_minutes": 5
            },
            "automation": {
                "auto_weekly_update": True,
                "update_day_of_week": "sunday",
                "update_time": "02:00",
                "enable_notifications": False
            },
            "export_settings": {
                "enable_monthly_exports": True,
                "enable_annual_exports": True,
                "export_formats": ["csv", "excel", "json"]
            },
            "google_drive": {
                "enabled": True,
                "upload_master_files": True,
                "upload_backups": True,
                "upload_exports": True,
                "master_folder": "HotDurham/Production/Processed/MasterData",
                "backup_folder": "HotDurham/Backups/MasterData",
                "export_folder": "HotDurham/Production/Processed/MasterData/Exports"
            }
        }
        
        # Save default configuration
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        self.logger.info("Created default master data configuration")
        return default_config
        
    def init_database(self):
        """Initialize SQLite database for master data."""
        if not self.config.get("master_file_settings", {}).get("enable_sqlite_db", True):
            return
            
        try:
            conn = sqlite3.connect(self.master_db_file)
            cursor = conn.cursor()
            
            # Create WU data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wu_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    station_id TEXT,
                    tempf REAL,
                    humidity REAL,
                    precipRate REAL,
                    windspeedAvg REAL,
                    winddir REAL,
                    solarRadiationHigh REAL,
                    pressure REAL,
                    data_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_file TEXT
                )
            ''')
            
            # Create TSI data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tsi_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    device_id TEXT,
                    device_name TEXT,
                    pm25 REAL,
                    temp_c REAL,
                    rh_percent REAL,
                    pm1 REAL,
                    pm4 REAL,
                    pm10 REAL,
                    pm25_aqi REAL,
                    data_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_file TEXT
                )
            ''')
            
            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT,
                    last_update DATETIME,
                    total_records INTEGER,
                    date_range_start DATETIME,
                    date_range_end DATETIME,
                    file_version INTEGER DEFAULT 1,
                    notes TEXT
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_wu_timestamp ON wu_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_wu_station ON wu_data(station_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tsi_timestamp ON tsi_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tsi_device ON tsi_data(device_id)')
            
            conn.commit()
            conn.close()
            
            self.logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            
    def create_data_hash(self, row: pd.Series) -> str:
        """Create a hash for data row to enable deduplication."""
        # Create a string representation of key data fields
        hash_data = ""
        if 'timestamp' in row and pd.notna(row['timestamp']):
            hash_data += str(row['timestamp'])
        if 'station_id' in row or 'device_id' in row:
            hash_data += str(row.get('station_id', row.get('device_id', '')))
        
        # Add key metric values
        for col in row.index:
            if col not in ['timestamp', 'station_id', 'device_id', 'device_name']:
                hash_data += str(row[col])
                
        return hashlib.md5(hash_data.encode()).hexdigest()
        
    def scan_historical_data(self, data_type: str) -> List[Path]:
        """Scan for all historical data files of a given type."""
        self.logger.info(f"Scanning for historical {data_type.upper()} data files")
        
        data_files = []
        data_dir = self.raw_pulls_path / data_type
        
        if not data_dir.exists():
            self.logger.warning(f"Data directory not found: {data_dir}")
            return data_files
            
        # Scan all year folders
        for year_folder in data_dir.iterdir():
            if year_folder.is_dir() and year_folder.name.isdigit():
                # Scan all files in year folder and subfolders
                for file_path in year_folder.rglob("*.csv"):
                    if data_type in file_path.name.lower():
                        data_files.append(file_path)
                        
        # Also check processed folder for additional data
        processed_dir = self.base_dir / "processed"
        if processed_dir.exists():
            for summary_folder in processed_dir.iterdir():
                if summary_folder.is_dir():
                    for file_path in summary_folder.rglob("*.csv"):
                        if data_type in file_path.name.lower():
                            data_files.append(file_path)
                            
        data_files.sort()
        self.logger.info(f"Found {len(data_files)} historical {data_type.upper()} files")
        return data_files
        
    def load_and_combine_historical_data(self, data_type: str) -> Optional[pd.DataFrame]:
        """Load and combine all historical data for a given type."""
        self.logger.info(f"Loading and combining historical {data_type.upper()} data")
        
        data_files = self.scan_historical_data(data_type)
        if not data_files:
            self.logger.warning(f"No historical {data_type.upper()} files found")
            return None
            
        all_data = []
        
        for file_path in data_files:
            try:
                df = pd.read_csv(file_path)
                if df.empty:
                    continue
                    
                # Add source file information
                df['source_file'] = file_path.name
                
                # Standardize timestamp column
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                
                all_data.append(df)
                self.logger.debug(f"Loaded {len(df)} records from {file_path.name}")
                
            except Exception as e:
                self.logger.error(f"Error loading file {file_path}: {e}")
                continue
                
        if not all_data:
            self.logger.error(f"No valid {data_type.upper()} data could be loaded")
            return None
            
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        self.logger.info(f"Combined {len(combined_df)} total {data_type.upper()} records")
        
        # Remove duplicates if enabled
        if self.config.get("data_quality", {}).get("enable_deduplication", True):
            combined_df = self.deduplicate_data(combined_df, data_type)
            
        # Sort by timestamp
        if 'timestamp' in combined_df.columns:
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            
        return combined_df
        
    def deduplicate_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Remove duplicate records from the dataset."""
        initial_count = len(df)
        
        # Add data hash for deduplication
        df['data_hash'] = df.apply(self.create_data_hash, axis=1)
        
        # Remove exact duplicates by hash
        df = df.drop_duplicates('data_hash')
        
        # For time-based deduplication
        tolerance = self.config.get("data_quality", {}).get("duplicate_tolerance_minutes", 5)
        
        if 'timestamp' in df.columns and tolerance > 0:
            # Group by device/station and remove records too close in time
            if data_type == "wu" and 'station_id' in df.columns:
                group_col = 'station_id'
            elif data_type == "tsi" and 'device_id' in df.columns:
                group_col = 'device_id'
            else:
                group_col = None
                
            if group_col:
                def remove_close_duplicates(group):
                    group = group.sort_values('timestamp')
                    mask = pd.Series([True] * len(group), index=group.index)
                    
                    for i in range(1, len(group)):
                        prev_time = group['timestamp'].iloc[i-1]
                        curr_time = group['timestamp'].iloc[i]
                        
                        if pd.notna(prev_time) and pd.notna(curr_time):
                            time_diff = (curr_time - prev_time).total_seconds() / 60
                            if time_diff < tolerance:
                                mask.iloc[i] = False
                                
                    return group[mask]
                
                df = df.groupby(group_col).apply(remove_close_duplicates).reset_index(drop=True) # type: ignore
        
        duplicates_removed = initial_count - len(df)
        if duplicates_removed > 0:
            self.logger.info(f"Removed {duplicates_removed} duplicate {data_type.upper()} records")
            
        return df.drop(columns=['data_hash'])
        
    def create_master_file(self, data_type: str, force_rebuild: bool = False) -> bool:
        """Create or update the master data file for a given type."""
        self.logger.info(f"Creating master {data_type.upper()} file (force_rebuild={force_rebuild})")
        
        master_file = self.wu_master_file if data_type == "wu" else self.tsi_master_file
        
        # Check if master file exists and force_rebuild is False
        if master_file.exists() and not force_rebuild:
            self.logger.info(f"Master {data_type.upper()} file already exists. Use force_rebuild=True to recreate.")
            return True
            
        # Create backup of existing file if it exists
        if master_file.exists():
            backup_name = f"{master_file.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            backup_path = self.backup_path / backup_name
            shutil.copy2(master_file, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            # Upload backup to Google Drive if enabled
            if self.config.get("google_drive", {}).get("upload_backups", True):
                backup_folder = self.config.get("google_drive", {}).get("backup_folder", "HotDurham/Backups/MasterData")
                self.upload_to_drive(backup_path, backup_folder)
            
        # Load and combine all historical data
        combined_df = self.load_and_combine_historical_data(data_type)
        
        if combined_df is None or combined_df.empty:
            self.logger.error(f"No data available to create master {data_type.upper()} file")
            return False
            
        try:
            # Save master file
            combined_df.to_csv(master_file, index=False)
            
            # Save to database if enabled
            if self.config.get("master_file_settings", {}).get("enable_sqlite_db", True):
                # Fix timestamp column mapping for existing database
                if data_type == "wu" and 'timestamp' in combined_df.columns and 'obsTimeUtc' not in combined_df.columns:
                    # Database expects obsTimeUtc for wu_data table
                    combined_df['obsTimeUtc'] = combined_df['timestamp']
                self.save_to_database(combined_df, data_type)
                
            # Update metadata
            self.update_metadata(data_type, combined_df)
            
            # Create version if enabled
            if self.config.get("master_file_settings", {}).get("enable_versioning", True):
                self.create_version(data_type, combined_df)
                
            # Upload to Google Drive if enabled
            if self.config.get("google_drive", {}).get("upload_master_files", True):
                master_folder = self.config.get("google_drive", {}).get("master_folder", "HotDurham/Production/Processed/MasterData")
                self.upload_to_drive(master_file, master_folder)
                
            self.logger.info(f"Successfully created master {data_type.upper()} file with {len(combined_df)} records")
            self.logger.info(f"Date range: {combined_df['timestamp'].min()} to {combined_df['timestamp'].max()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating master {data_type.upper()} file: {e}")
            return False
            
    def save_to_database(self, df: pd.DataFrame, data_type: str):
        """Save data to SQLite database."""
        try:
            conn = sqlite3.connect(self.master_db_file)
            
            table_name = f"{data_type}_data"
            
            # Prepare data for database
            db_df = df.copy()
            
            # Add data hash for deduplication
            db_df['data_hash'] = db_df.apply(self.create_data_hash, axis=1)
            
            # Rename columns to match database schema
            if data_type == "wu":
                column_mapping = {
                    'PM 2.5': 'pm25',
                    'T (C)': 'temp_c', 
                    'RH (%)': 'rh_percent'
                }
            else:  # tsi
                column_mapping = {
                    'PM 2.5': 'pm25',
                    'T (C)': 'temp_c',
                    'RH (%)': 'rh_percent',
                    'PM 1': 'pm1',
                    'PM 4': 'pm4', 
                    'PM 10': 'pm10',
                    'PM 2.5 AQI': 'pm25_aqi'
                }
                
            for old_col, new_col in column_mapping.items():
                if old_col in db_df.columns:
                    db_df.rename(columns={old_col: new_col}, inplace=True)
            
            # Save to database using replace to handle duplicates
            db_df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            conn.close()
            self.logger.info(f"Saved {len(db_df)} records to database table {table_name}")
            
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            
    def update_metadata(self, data_type: str, df: pd.DataFrame):
        """Update metadata for the master file."""
        metadata = {
            "data_type": data_type,
            "last_update": datetime.now().isoformat(),
            "total_records": len(df),
            "date_range_start": df['timestamp'].min().isoformat() if 'timestamp' in df.columns else None,
            "date_range_end": df['timestamp'].max().isoformat() if 'timestamp' in df.columns else None,
            "file_size_mb": round((self.wu_master_file if data_type == "wu" else self.tsi_master_file).stat().st_size / 1024 / 1024, 2),
            "source_files_count": df['source_file'].nunique() if 'source_file' in df.columns else 0
        }
        
        metadata_file = self.metadata_path / f"{data_type}_master_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        self.logger.info(f"Updated {data_type.upper()} metadata: {metadata}")
        
    def create_version(self, data_type: str, df: pd.DataFrame):
        """Create a versioned copy of the master file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version_file = self.master_data_path / "versions" / f"{data_type}_master_v{timestamp}.csv"
        
        df.to_csv(version_file, index=False)
        self.logger.info(f"Created version: {version_file}")
        
    def fetch_new_weekly_data(self, data_type: str) -> Optional[pd.DataFrame]:
        """Fetch new data for the past week."""
        self.logger.info(f"Fetching new weekly {data_type.upper()} data")
        
        # Calculate date range for the past week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        try:
            if data_type == "wu":
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                df = fetch_wu_data(start_str, end_str)
            elif data_type == "tsi":
                start_str = start_date.strftime("%Y%m%d")
                end_str = end_date.strftime("%Y%m%d")
                df, _ = asyncio.run(fetch_tsi_data_async(start_str, end_str))
            else:
                self.logger.error(f"Unknown data type: {data_type}")
                return None
                
            if df is not None and not df.empty:
                # Standardize timestamp
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    
                # Add source information
                df['source_file'] = f"weekly_fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                self.logger.info(f"Fetched {len(df)} new {data_type.upper()} records")
                return df
            else:
                self.logger.warning(f"No new {data_type.upper()} data retrieved")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching new {data_type.upper()} data: {e}")
            return None
            
    def append_new_data(self, data_type: str, new_df: pd.DataFrame) -> bool:
        """Append new data to the master file."""
        master_file = self.wu_master_file if data_type == "wu" else self.tsi_master_file
        
        if not master_file.exists():
            self.logger.error(f"Master {data_type.upper()} file does not exist. Create it first.")
            return False
            
        try:
            # Load existing master data
            existing_df = pd.read_csv(master_file)
            
            # Standardize timestamps
            if 'timestamp' in existing_df.columns:
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'], errors='coerce')
            if 'timestamp' in new_df.columns:
                new_df['timestamp'] = pd.to_datetime(new_df['timestamp'], errors='coerce')
                
            # Combine data
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Remove duplicates
            if self.config.get("data_quality", {}).get("enable_deduplication", True):
                combined_df = self.deduplicate_data(combined_df, data_type)
                
            # Sort by timestamp
            if 'timestamp' in combined_df.columns:
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
                
            # Create backup before updating
            backup_name = f"{master_file.stem}_pre_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            backup_path = self.backup_path / backup_name
            shutil.copy2(master_file, backup_path)
            
            # Upload backup to Google Drive if enabled
            if self.config.get("google_drive", {}).get("upload_backups", True):
                backup_folder = self.config.get("google_drive", {}).get("backup_folder", "HotDurham/Backups/MasterData")
                self.upload_to_drive(backup_path, backup_folder)
            
            # Save updated master file
            combined_df.to_csv(master_file, index=False)
            
            # Update database if enabled
            if self.config.get("master_file_settings", {}).get("enable_sqlite_db", True):
                # Fix timestamp column mapping for existing database
                if data_type == "wu" and 'timestamp' in combined_df.columns and 'obsTimeUtc' not in combined_df.columns:
                    # Database expects obsTimeUtc for wu_data table
                    combined_df['obsTimeUtc'] = combined_df['timestamp']
                self.save_to_database(combined_df, data_type)
                
            # Update metadata
            self.update_metadata(data_type, combined_df)
            
            # Upload updated file to Google Drive if enabled
            if self.config.get("google_drive", {}).get("upload_master_files", True):
                master_folder = self.config.get("google_drive", {}).get("master_folder", "HotDurham/Production/Processed/MasterData")
                self.upload_to_drive(master_file, master_folder)
            
            new_records = len(combined_df) - len(existing_df)
            self.logger.info(f"Successfully appended {new_records} new {data_type.upper()} records to master file")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error appending new {data_type.upper()} data: {e}")
            return False
            
    def weekly_update(self) -> Dict[str, bool]:
        """Perform weekly update of master files with new data."""
        self.logger.info("Starting weekly master data update")
        
        results = {"wu": False, "tsi": False}
        
        for data_type in ["wu", "tsi"]:
            if not self.config.get("data_sources", {}).get(data_type, {}).get("enabled", True):
                self.logger.info(f"Skipping {data_type.upper()} update (disabled in config)")
                continue
                
            try:
                # Fetch new weekly data
                new_df = self.fetch_new_weekly_data(data_type)
                
                if new_df is not None and not new_df.empty:
                    # Append to master file
                    success = self.append_new_data(data_type, new_df)
                    results[data_type] = success
                else:
                    self.logger.warning(f"No new {data_type.upper()} data to append")
                    results[data_type] = True  # Consider success if no data needed
                    
            except Exception as e:
                self.logger.error(f"Error during {data_type.upper()} weekly update: {e}")
                results[data_type] = False
                
        # Create combined master file
        if results["wu"] or results["tsi"]:
            self.create_combined_master_file()
            
        self.logger.info(f"Weekly update completed. Results: {results}")
        return results
        
    def create_combined_master_file(self) -> bool:
        """Create a combined master file with both WU and TSI data."""
        self.logger.info("Creating combined master data file")
        
        try:
            combined_data = []
            
            # Load WU data if available
            if self.wu_master_file.exists():
                wu_df = pd.read_csv(self.wu_master_file)
                if not wu_df.empty:
                    wu_df['data_source'] = 'Weather Underground'
                    combined_data.append(wu_df)
                    self.logger.info(f"Added {len(wu_df)} WU records to combined file")
                    
            # Load TSI data if available
            if self.tsi_master_file.exists():
                tsi_df = pd.read_csv(self.tsi_master_file)
                if not tsi_df.empty:
                    tsi_df['data_source'] = 'TSI Air Quality'
                    combined_data.append(tsi_df)
                    self.logger.info(f"Added {len(tsi_df)} TSI records to combined file")
                    
            if not combined_data:
                self.logger.warning("No data available for combined master file")
                return False
                
            # Combine all data
            combined_df = pd.concat(combined_data, ignore_index=True, sort=False)
            
            # Sort by timestamp if available
            if 'timestamp' in combined_df.columns:
                combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], errors='coerce')
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
                
            # Save combined master file
            combined_df.to_csv(self.combined_master_file, index=False)
            
            # Update metadata for combined file
            self.update_metadata("combined", combined_df)
            
            # Upload combined file to Google Drive if enabled
            if self.config.get("google_drive", {}).get("upload_master_files", True):
                master_folder = self.config.get("google_drive", {}).get("master_folder", "HotDurham/Production/Processed/MasterData")
                self.upload_to_drive(self.combined_master_file, master_folder)
            
            self.logger.info(f"Successfully created combined master file with {len(combined_df)} total records")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating combined master file: {e}")
            return False
            
    def export_data(self, data_type: str = "all", format: str = "csv", 
                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Path]:
        """Export master data in various formats."""
        self.logger.info(f"Exporting {data_type} data in {format} format")
        
        exported_files = []
        
        # Determine which files to export
        if data_type == "all":
            export_types = ["wu", "tsi", "combined"]
        else:
            export_types = [data_type]
            
        for export_type in export_types:
            if export_type == "wu" and not self.wu_master_file.exists():
                continue
            elif export_type == "tsi" and not self.tsi_master_file.exists():
                continue
            elif export_type == "combined" and not self.combined_master_file.exists():
                continue
                
            try:
                # Load data
                if export_type == "wu":
                    df = pd.read_csv(self.wu_master_file)
                elif export_type == "tsi":
                    df = pd.read_csv(self.tsi_master_file)
                else:  # combined
                    df = pd.read_csv(self.combined_master_file)
                    
                # Filter by date range if specified
                if start_date or end_date:
                    if 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                        
                        if start_date:
                            start_dt = pd.to_datetime(start_date)
                            df = df[df['timestamp'] >= start_dt]
                            
                        if end_date:
                            end_dt = pd.to_datetime(end_date)
                            df = df[df['timestamp'] <= end_dt]
                            
                # Create export filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                date_suffix = ""
                if start_date or end_date:
                    date_suffix = f"_filtered_{start_date or 'start'}_to_{end_date or 'end'}"
                
                # Map format to file extension
                extension_map = {
                    "csv": "csv",
                    "excel": "xlsx",
                    "json": "json"
                }
                file_extension = extension_map.get(format, format)
                    
                export_filename = f"{export_type}_master_export{date_suffix}_{timestamp}.{file_extension}"
                export_path = self.master_data_path / "exports" / export_filename
                
                # Export in specified format
                if format == "csv":
                    df.to_csv(export_path, index=False)
                elif format == "excel":
                    df.to_excel(export_path, index=False)
                elif format == "json":
                    df.to_json(export_path, orient='records', date_format='iso')
                else:
                    self.logger.error(f"Unsupported export format: {format}")
                    continue
                    
                exported_files.append(export_path)
                self.logger.info(f"Exported {len(df)} records to {export_path}")
                
                # Upload export to Google Drive if enabled
                if self.config.get("google_drive", {}).get("upload_exports", True):
                    export_folder = self.config.get("google_drive", {}).get("export_folder", "HotDurham/Production/Processed/MasterData/Exports")
                    self.upload_to_drive(export_path, export_folder)
                
            except Exception as e:
                self.logger.error(f"Error exporting {export_type} data: {e}")
                
        return exported_files
        
    def get_master_data_summary(self) -> Dict[str, Any]:
        """Get summary information about master data files."""
        summary = {
            "last_updated": datetime.now().isoformat(),
            "wu_data": {},
            "tsi_data": {},
            "combined_data": {},
            "system_status": "operational"
        }
        
        # WU data summary
        if self.wu_master_file.exists():
            try:
                wu_df = pd.read_csv(self.wu_master_file)
                wu_df['timestamp'] = pd.to_datetime(wu_df['timestamp'], errors='coerce')
                
                summary["wu_data"] = {
                    "file_exists": True,
                    "total_records": len(wu_df),
                    "date_range_start": wu_df['timestamp'].min().isoformat() if 'timestamp' in wu_df.columns else None,
                    "date_range_end": wu_df['timestamp'].max().isoformat() if 'timestamp' in wu_df.columns else None,
                    "file_size_mb": round(self.wu_master_file.stat().st_size / 1024 / 1024, 2),
                    "unique_stations": wu_df['station_id'].nunique() if 'station_id' in wu_df.columns else 0
                }
            except Exception as e:
                summary["wu_data"] = {"file_exists": True, "error": str(e)}
        else:
            summary["wu_data"] = {"file_exists": False}
            
        # TSI data summary
        if self.tsi_master_file.exists():
            try:
                tsi_df = pd.read_csv(self.tsi_master_file)
                tsi_df['timestamp'] = pd.to_datetime(tsi_df['timestamp'], errors='coerce')
                
                summary["tsi_data"] = {
                    "file_exists": True,
                    "total_records": len(tsi_df),
                    "date_range_start": tsi_df['timestamp'].min().isoformat() if 'timestamp' in tsi_df.columns else None,
                    "date_range_end": tsi_df['timestamp'].max().isoformat() if 'timestamp' in tsi_df.columns else None,
                    "file_size_mb": round(self.tsi_master_file.stat().st_size / 1024 / 1024, 2),
                    "unique_devices": tsi_df['device_id'].nunique() if 'device_id' in tsi_df.columns else 0
                }
            except Exception as e:
                summary["tsi_data"] = {"file_exists": True, "error": str(e)}
        else:
            summary["tsi_data"] = {"file_exists": False}
            
        # Combined data summary
        if self.combined_master_file.exists():
            try:
                combined_df = pd.read_csv(self.combined_master_file)
                combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], errors='coerce');
                
                summary["combined_data"] = {
                    "file_exists": True,
                    "total_records": len(combined_df),
                    "date_range_start": combined_df['timestamp'].min().isoformat() if 'timestamp' in combined_df.columns else None,
                    "date_range_end": combined_df['timestamp'].max().isoformat() if 'timestamp' in combined_df.columns else None,
                    "file_size_mb": round(self.combined_master_file.stat().st_size / 1024 / 1024, 2),
                    "data_sources": combined_df['data_source'].unique().tolist() if 'data_source' in combined_df.columns else []
                }
            except Exception as e:
                summary["combined_data"] = {"file_exists": True, "error": str(e)}
        else:
            summary["combined_data"] = {"file_exists": False}
            
        return summary
        
    def cleanup_old_backups(self, retention_days: Optional[int] = None):
        """Clean up old backup files."""
        if retention_days is None:
            retention_days = self.config.get("master_file_settings", {}).get("backup_retention_days", 365)
            
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        for backup_file in self.backup_path.rglob("*"):
            if backup_file.is_file():
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        cleaned_count += 1
                except Exception as e:
                    self.logger.error(f"Error cleaning backup file {backup_file}: {e}")
                    
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old backup files")
            
    def test_google_drive_integration(self) -> Dict[str, bool]:
        """Test Google Drive integration for master data files."""
        self.logger.info("🔍 Testing Google Drive integration for master data files...")
        
        results = {
            "google_drive_available": False,
            "credentials_valid": False,
            "folder_creation": False,
            "file_upload": False
        }
        
        # Check Google Drive availability
        results["google_drive_available"] = GOOGLE_DRIVE_AVAILABLE and self.drive_service is not None
        
        if not results["google_drive_available"]:
            self.logger.warning("❌ Google Drive service not available")
            return results
            
        # Test credentials
        try:
            # Try to access drive
            if self.drive_service:
                self.drive_service.files().list(pageSize=1).execute()
                results["credentials_valid"] = True
                self.logger.info("✅ Google Drive credentials valid")
            else:
                results["credentials_valid"] = False
        except Exception as e:
            self.logger.error(f"❌ Google Drive credentials invalid: {e}")
            return results
            
        # Test folder creation
        try:
            test_folder = "HotDurham/Production/Processed/MasterData/Test"
            folder_id = self.get_or_create_drive_folder(test_folder)
            if folder_id:
                results["folder_creation"] = True
                self.logger.info("✅ Google Drive folder creation successful")
                
                # Clean up test folder
                if self.drive_service:
                    self.drive_service.files().delete(fileId=folder_id).execute()
            else:
                self.logger.error("❌ Google Drive folder creation failed")
                return results
        except Exception as e:
            self.logger.error(f"❌ Google Drive folder creation error: {e}")
            return results
            
        # Test file upload with a small test file
        try:
            test_file_path = self.master_data_path / "test_upload.txt"
            test_file_path.write_text("Test file for Google Drive integration")
            
            upload_success = self.upload_to_drive(test_file_path, "HotDurham/Production/Processed/MasterData")
            if upload_success:
                results["file_upload"] = True
                self.logger.info("✅ Google Drive file upload successful")
            else:
                self.logger.error("❌ Google Drive file upload failed")
                
            # Clean up test file
            test_file_path.unlink()
            
        except Exception as e:
            self.logger.error(f"❌ Google Drive file upload error: {e}")
            
        return results
        
    def sync_existing_master_files_to_drive(self) -> Dict[str, bool]:
        """Sync existing master data files to Google Drive."""
        self.logger.info("📤 Syncing existing master data files to Google Drive...")
        
        results = {}
        master_folder = self.config.get("google_drive", {}).get("master_folder", "HotDurham/Production/Processed/MasterData")
        
        # Sync master files
        master_files = [
            ("wu", self.wu_master_file),
            ("tsi", self.tsi_master_file), 
            ("combined", self.combined_master_file),
            ("database", self.master_db_file)
        ]
        
        for file_type, file_path in master_files:
            if file_path.exists():
                success = self.upload_to_drive(file_path, master_folder)
                results[f"{file_type}_master"] = success
                if success:
                    self.logger.info(f"✅ Uploaded {file_type} master file to Google Drive")
                else:
                    self.logger.error(f"❌ Failed to upload {file_type} master file")
            else:
                results[f"{file_type}_master"] = False
                self.logger.warning(f"⚠️ {file_type} master file does not exist: {file_path}")
                
        # Sync metadata files
        if self.metadata_path.exists():
            for metadata_file in self.metadata_path.glob("*.json"):
                success = self.upload_to_drive(metadata_file, f"{master_folder}/Metadata")
                metadata_name = metadata_file.stem
                results[f"metadata_{metadata_name}"] = success
                
        return results
def main():
    """Main entry point for master data file system operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Master Data File System')
    parser.add_argument('--create-master', action='store_true', help='Create initial master files')
    parser.add_argument('--update-weekly', action='store_true', help='Perform weekly update')
    parser.add_argument('--force-rebuild', action='store_true', help='Force rebuild of master files')
    parser.add_argument('--export', choices=['wu', 'tsi', 'combined', 'all'], help='Export data')
    parser.add_argument('--format', choices=['csv', 'excel', 'json'], default='csv', help='Export format')
    parser.add_argument('--summary', action='store_true', help='Show master data summary')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')
    parser.add_argument('--test-drive', action='store_true', help='Test Google Drive integration')
    parser.add_argument('--sync-to-drive', action='store_true', help='Sync existing master files to Google Drive')
    
    args = parser.parse_args()
    
    # Initialize master data system
    master_system = MasterDataFileSystem()
    
    if args.create_master:
        print("🔄 Creating master data files...")
        master_system.create_master_file("wu", force_rebuild=args.force_rebuild)
        master_system.create_master_file("tsi", force_rebuild=args.force_rebuild)
        master_system.create_combined_master_file()
        
    elif args.update_weekly:
        print("📅 Performing weekly update...")
        results = master_system.weekly_update()
        print(f"Update results: {results}")
        
    elif args.export:
        print(f"📤 Exporting {args.export} data in {args.format} format...")
        exported_files = master_system.export_data(args.export, args.format)
        print(f"Exported files: {[str(f) for f in exported_files]}")
        
    elif args.summary:
        print("📊 Master Data Summary:")
        summary = master_system.get_master_data_summary()
        print(json.dumps(summary, indent=2, default=str))
        
    elif args.cleanup:
        print("🧹 Cleaning up old backups...")
        master_system.cleanup_old_backups()
        
    elif args.test_drive:
        print("🔧 Testing Google Drive integration...")
        results = master_system.test_google_drive_integration()
        print("Test Results:")
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test}: {status}")
            
    elif args.sync_to_drive:
        print("☁️ Syncing existing master files to Google Drive...")
        results = master_system.sync_existing_master_files_to_drive()
        print("Sync Results:")
        for file_type, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"  {file_type}: {status}")
        
    else:
        print("ℹ️  No action specified. Use --help for options.")
        print("💡 Quick start: python master_data_file_system.py --create-master")

if __name__ == "__main__":
    main()
