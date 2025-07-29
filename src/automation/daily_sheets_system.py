



#!/usr/bin/env python3
"""
Daily Google Sheets System for Hot Durham Air Quality Monitoring
Creates automated daily sheets with all sensor data, uploads to Google Drive,
and manages sheet lifecycle with overwrite/replacement logic.
"""
import os
import sys
import json
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials as GCreds
from googleapiclient.discovery import build
from src.core.data_manager import DataManager

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)


class DailySheetsSystem:
    """
    Automated Daily Google Sheets System for Hot Durham Air Quality Monitoring
    
    Features:
    - Creates daily Google Sheets with all sensor data (WU + TSI)
    - Uploads sheets to Google Drive in organized folders
    - Handles sheet overwrite/replacement logic
    - Integrates with existing data management system
    - Supports scheduling and automation
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.setup_logging()
        self.load_credentials()
        self.data_manager = DataManager(project_root)
        
        # Google Sheets/Drive services
        self.sheets_service = None
        self.drive_service = None
        self.gspread_client = None
        self.setup_google_services()
        
        # Configuration
        self.config = self.load_config()
        
    def setup_logging(self):
        """Setup logging for the daily sheets system"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("DailySheetsSystem")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = log_dir / "daily_sheets_system.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def load_credentials(self):
        """Load API credentials"""
        self.creds_dir = self.project_root / "creds"
        
        # Google credentials
        self.google_creds_path = self.creds_dir / "google_creds.json"
        if not self.google_creds_path.exists():
            raise FileNotFoundError(f"Google credentials not found: {self.google_creds_path}")
        
        # TSI credentials
        self.tsi_creds_path = self.creds_dir / "tsi_creds.json"
        if not self.tsi_creds_path.exists():
            raise FileNotFoundError(f"TSI credentials not found: {self.tsi_creds_path}")
        
        # WU API key
        self.wu_api_key_path = self.creds_dir / "wu_api_key.json"
        if not self.wu_api_key_path.exists():
            raise FileNotFoundError(f"WU API key not found: {self.wu_api_key_path}")
    
    def setup_google_services(self):
        """Setup Google Sheets and Drive services"""
        try:
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = GCreds.from_service_account_file(self.google_creds_path, scopes=scope)
            
            # Initialize services
            self.sheets_service = build('sheets', 'v4', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            self.gspread_client = gspread.authorize(creds)
            
            self.logger.info("Google services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Google services: {e}")
            raise
    
    def load_config(self):
        """Load system configuration"""
        config_path = self.project_root / "config" / "daily_sheets_config.json"
        
        # Default configuration
        default_config = {
            "share_email": "hotdurham@gmail.com",
            "drive_folder_name": "HotDurham_Daily_Sheets",
            "sheet_retention_days": 30,
            "auto_cleanup": True,
            "include_charts": True,
            "include_summary": True,
            "timezone": "US/Eastern",
            "wu_sensors": [
                "KNCDURHA556",  # Duke-MS-07
                "KNCDURHA590",  # Duke-Kestrel-01
                "KNCDURHA485",  # Duke-MS-01
                "KNCDURHA486",  # Duke-MS-02
                "KNCDURHA487",  # Duke-MS-03
                "KNCDURHA488",  # Duke-MS-04
                "KNCDURHA489",  # Duke-MS-05
                "KNCDURHA490"   # Duke-MS-06
            ],
            "tsi_device_discovery": True,
            "data_pull_hours": 24  # Hours of data to include
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Failed to load config, using defaults: {e}")
        
        return default_config
    
    def create_drive_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """Create a folder in Google Drive"""
        try:
            # Check if Google Drive service is initialized
            if self.drive_service is None:
                self.logger.error("Google Drive service is not initialized.")
                return None

            # Check if folder already exists
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_folder_id:
                query += f" and parents in '{parent_folder_id}'"
            
            results = self.drive_service.files().list(q=query).execute()
            items = results.get('files', [])
            
            if items:
                self.logger.info(f"Using existing folder: {folder_name}")
                return items[0]['id']
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                folder_metadata['parents'] = parent_folder_id  # Should be a string, not a list
            
            folder = self.drive_service.files().create(body=folder_metadata).execute()
            self.logger.info(f"Created new folder: {folder_name}")
            return folder.get('id')
            
        except Exception as e:
            self.logger.error(f"Failed to create drive folder {folder_name}: {e}")
            return None
    
    def get_daily_data(self, target_date: Optional[datetime] = None) -> Dict[str, Optional[pd.DataFrame]]:
        """Fetch daily data from both WU and TSI sources"""
        if target_date is None:
            target_date = datetime.now()
        
        # Calculate date range (24 hours from midnight to midnight)
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        self.logger.info(f"Fetching daily data for {start_date_str}")
        
        data = {
            'wu': None,
            'tsi': None,
            'date_range': f"{start_date_str} to {end_date_str}",
            'target_date': target_date
        }
        
        try:
            # The following code is commented out because fetch_wu_data and fetch_tsi_data_async are not defined or used anymore.
            # try:
            #     from src.data_collection.daily_data_collector import fetch_wu_data, fetch_tsi_data_async
            # except ImportError:
            #     self.logger.error("Could not import fetch_wu_data or fetch_tsi_data_async. Returning empty data.")
            #     return data

            # # Fetch WU data
            # self.logger.info("Fetching Weather Underground data...")
            # wu_df = fetch_wu_data(start_date_str, end_date_str)  # type: ignore[name-defined]
            # if wu_df is not None and not wu_df.empty:
            #     data['wu'] = wu_df
            #     self.logger.info(f"Retrieved {len(wu_df)} WU records")
            # else:
            #     self.logger.warning("No WU data retrieved")

            # # Fetch TSI data
            # self.logger.info("Fetching TSI data...")
            # import asyncio
            # try:
            #     loop = asyncio.get_event_loop()
            # except RuntimeError:
            #     loop = asyncio.new_event_loop()
            #     asyncio.set_event_loop(loop)
            # if loop.is_running():
            #     # If already in an event loop (e.g., in Jupyter), use create_task
            #     try:
            #         import nest_asyncio
            #         nest_asyncio.apply()
            #     except ImportError:
            #         self.logger.warning("nest_asyncio not installed; event loop may fail in notebook environments.")
            #     future = asyncio.ensure_future(fetch_tsi_data_async(start_date_str, end_date_str))  # type: ignore[name-defined]
            #     tsi_df, tsi_per_device = loop.run_until_complete(future)
            # else:
            #     tsi_df, tsi_per_device = loop.run_until_complete(fetch_tsi_data_async(start_date_str, end_date_str))  # type: ignore[name-defined]
            # if tsi_df is not None and not tsi_df.empty:
            #     data['tsi'] = tsi_df
            #     data['tsi_per_device'] = tsi_per_device
            #     self.logger.info(f"Retrieved {len(tsi_df)} TSI records")
            # else:
            #     self.logger.warning("No TSI data retrieved")

            pass  # No data fetching performed; functions are not available.
        except Exception as e:
            self.logger.error(f"Error fetching daily data: {e}")

        return data
    
    def create_daily_summary(self, wu_df: Optional[pd.DataFrame], tsi_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Create daily summary statistics"""
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'wu_summary': {},
            'tsi_summary': {},
            'overall_summary': {}
        }
        
        # WU Summary
        if wu_df is not None and not wu_df.empty:
            try:
                # Convert obsTimeUtc to datetime
                wu_df['obsTimeUtc'] = pd.to_datetime(wu_df['obsTimeUtc'], errors='coerce')
                
                # Group by station for summary
                wu_summary = []
                for station_id in wu_df['stationId'].unique():
                    station_data = wu_df[wu_df['stationId'] == station_id]
                    
                    # Get station name mapping
                    station_name_map = {
                        'KNCDURHA485': 'Duke-MS-01',
                        'KNCDURHA486': 'Duke-MS-02', 
                        'KNCDURHA487': 'Duke-MS-03',
                        'KNCDURHA488': 'Duke-MS-04',
                        'KNCDURHA489': 'Duke-MS-05',
                        'KNCDURHA490': 'Duke-MS-06',
                        'KNCDURHA556': 'Duke-MS-07',
                        'KNCDURHA590': 'Duke-Kestrel-01'
                    }
                    station_name = station_name_map.get(station_id, station_id)
                    
                    # Calculate metrics
                    temp_avg = station_data['tempAvg'].mean() if 'tempAvg' in station_data.columns else None
                    humidity_avg = station_data['humidityAvg'].mean() if 'humidityAvg' in station_data.columns else None
                    wind_avg = station_data['windspeedAvg'].mean() if 'windspeedAvg' in station_data.columns else None
                    
                    wu_summary.append({
                        'station_id': station_id,
                        'station_name': station_name,
                        'records_count': len(station_data),
                        'temp_avg_c': round(temp_avg, 1) if temp_avg is not None else 'N/A',
                        'humidity_avg': round(humidity_avg, 1) if humidity_avg is not None else 'N/A',
                        'wind_avg_kmh': round(wind_avg, 1) if wind_avg is not None else 'N/A'
                    })
                
                summary['wu_summary'] = wu_summary
                
            except Exception as e:
                self.logger.error(f"Error creating WU summary: {e}")
        
        # TSI Summary
        if tsi_df is not None and not tsi_df.empty:
            try:
                # Convert timestamp to datetime
                tsi_df['timestamp'] = pd.to_datetime(tsi_df['timestamp'], errors='coerce')
                
                # Group by device for summary
                tsi_summary = []
                for device_name in tsi_df['Device Name'].unique():
                    device_data = tsi_df[tsi_df['Device Name'] == device_name]
                    
                    # Calculate metrics
                    pm25_avg = device_data['PM 2.5'].mean() if 'PM 2.5' in device_data.columns else None
                    temp_avg = device_data['T (C)'].mean() if 'T (C)' in device_data.columns else None
                    humidity_avg = device_data['RH (%)'].mean() if 'RH (%)' in device_data.columns else None
                    pm10_avg = device_data['PM 10'].mean() if 'PM 10' in device_data.columns else None
                    
                    tsi_summary.append({
                        'device_name': device_name,
                        'records_count': len(device_data),
                        'pm25_avg': round(pm25_avg, 2) if pm25_avg is not None else 'N/A',
                        'pm10_avg': round(pm10_avg, 2) if pm10_avg is not None else 'N/A',
                        'temp_avg_c': round(temp_avg, 2) if temp_avg is not None else 'N/A',
                        'humidity_avg': round(humidity_avg, 2) if humidity_avg is not None else 'N/A'
                    })
                
                summary['tsi_summary'] = tsi_summary
                
            except Exception as e:
                self.logger.error(f"Error creating TSI summary: {e}")
        
        # Overall summary
        summary['overall_summary'] = {
            'wu_stations_count': len(summary['wu_summary']) if summary['wu_summary'] else 0,
            'wu_total_records': sum(s['records_count'] for s in summary['wu_summary']) if summary['wu_summary'] else 0,
            'tsi_devices_count': len(summary['tsi_summary']) if summary['tsi_summary'] else 0,
            'tsi_total_records': sum(s['records_count'] for s in summary['tsi_summary']) if summary['tsi_summary'] else 0,
            'data_sources_active': []
        }
        
        if summary['wu_summary']:
            summary['overall_summary']['data_sources_active'].append('Weather Underground')
        if summary['tsi_summary']:
            summary['overall_summary']['data_sources_active'].append('TSI Air Quality')
        
        return summary
    
    def create_daily_sheet(self, target_date: Optional[datetime] = None, replace_existing: bool = True) -> Optional[Dict[str, str]]:
        """Create a comprehensive daily Google Sheet with all sensor data"""
        if target_date is None:
            target_date = datetime.now()
        
        date_str = target_date.strftime('%Y-%m-%d')
        self.logger.info(f"Creating daily sheet for {date_str}")
        
        try:
            # Get daily data
            data = self.get_daily_data(target_date)
            wu_df: Optional[pd.DataFrame] = data.get('wu')
            tsi_df: Optional[pd.DataFrame] = data.get('tsi')

            if (wu_df is None or wu_df.empty) and (tsi_df is None or tsi_df.empty):
                self.logger.warning(f"No data available for {date_str}")
                return None
            
            # Create sheet name
            sheet_name = f"HotDurham_Daily_{date_str}_{datetime.now().strftime('%H%M%S')}"
            
            # Check for existing sheet and handle replacement
            if replace_existing:
                existing_sheet_id = self.find_existing_daily_sheet(date_str)
                if existing_sheet_id:
                    self.logger.info(f"Replacing existing sheet for {date_str}")
                    self.delete_sheet(existing_sheet_id)
            
            # Create new spreadsheet
            if self.gspread_client is None:
                self.logger.error("gspread_client is not initialized.")
                return None
            spreadsheet = self.gspread_client.create(sheet_name)  # type: ignore[union-attr]
            sheet_id = spreadsheet.id
            sheet_url = spreadsheet.url
            
            self.logger.info(f"Created new sheet: {sheet_name}")
            self.logger.info(f"Sheet URL: {sheet_url}")
            
            # Share with configured email
            try:
                spreadsheet.share(self.config['share_email'], perm_type='user', role='writer')
                self.logger.info(f"Shared with {self.config['share_email']}")
            except Exception as e:
                self.logger.warning(f"Failed to share sheet: {e}")
            
            # Add data to sheets
            sheet_info = {
                'sheet_id': sheet_id,
                'sheet_url': sheet_url,
                'date': date_str,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_sources': []
            }
            
            # Add WU data sheet
            if wu_df is not None and not wu_df.empty:
                self.add_wu_data_sheet(spreadsheet, wu_df)
                sheet_info['data_sources'].append('Weather Underground')
                self.logger.info("Added Weather Underground data sheet")

            # Add TSI data sheet
            if tsi_df is not None and not tsi_df.empty:
                self.add_tsi_data_sheet(spreadsheet, tsi_df)
                sheet_info['data_sources'].append('TSI Air Quality')
                self.logger.info("Added TSI air quality data sheet")

            # Add daily summary sheet
            if self.config.get('include_summary', True):
                summary = self.create_daily_summary(wu_df, tsi_df)
                self.add_summary_sheet(spreadsheet, summary)
                self.logger.info("Added daily summary sheet")

            # Add charts if enabled
            if self.config.get('include_charts', True):
                self.add_daily_charts(spreadsheet, wu_df, tsi_df)
                self.logger.info("Added daily charts")
            
            # Move to organized folder in Drive
            drive_folder_id = self.organize_sheet_in_drive(sheet_id, target_date)
            if drive_folder_id:
                sheet_info['drive_folder_id'] = drive_folder_id
            
            # Save metadata
            self.save_daily_sheet_metadata(sheet_info)
            
            self.logger.info(f"Daily sheet creation completed successfully for {date_str}")
            return sheet_info
            
        except Exception as e:
            self.logger.error(f"Failed to create daily sheet for {date_str}: {e}")
            return None
    
    def add_wu_data_sheet(self, spreadsheet, wu_df: pd.DataFrame) -> None:
        """Add Weather Underground data to the spreadsheet"""
        try:
            # Use first sheet or create new one
            if hasattr(spreadsheet, 'sheet1'):
                wu_ws = spreadsheet.sheet1
                wu_ws.update_title("Weather Underground Data")
            else:
                wu_ws = spreadsheet.add_worksheet(title="Weather Underground Data", 
                                                rows=len(wu_df)+1, cols=len(wu_df.columns))
            
            # Prepare data
            wu_headers = wu_df.columns.tolist()
            wu_data = wu_df.fillna('').values.tolist()
            
            # Update sheet
            wu_ws.update([wu_headers] + wu_data)
            
        except Exception as e:
            self.logger.error(f"Error adding WU data sheet: {e}")
    
    def add_tsi_data_sheet(self, spreadsheet, tsi_df: pd.DataFrame) -> None:
        """Add TSI air quality data to the spreadsheet"""
        try:
            tsi_ws = spreadsheet.add_worksheet(title="TSI Air Quality Data", 
                                             rows=len(tsi_df)+1, cols=len(tsi_df.columns))
            
            # Prepare data
            tsi_headers = tsi_df.columns.tolist()
            tsi_data = tsi_df.fillna('').values.tolist()
            
            # Update sheet
            tsi_ws.update([tsi_headers] + tsi_data)
            
        except Exception as e:
            self.logger.error(f"Error adding TSI data sheet: {e}")
    
    def add_summary_sheet(self, spreadsheet, summary: Dict[str, Any]) -> None:
        """Add daily summary sheet"""
        try:
            summary_ws = spreadsheet.add_worksheet(title="Daily Summary", rows=100, cols=10)
            
            # Build summary data
            summary_data = [
                ["Hot Durham Daily Air Quality Summary"],
                ["Date", summary['date']],
                ["Generated", datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                [""],
                ["=== OVERALL SUMMARY ==="],
                ["Active Data Sources", ", ".join(summary['overall_summary']['data_sources_active'])],
                ["WU Stations Count", summary['overall_summary']['wu_stations_count']],
                ["WU Total Records", summary['overall_summary']['wu_total_records']],
                ["TSI Devices Count", summary['overall_summary']['tsi_devices_count']],
                ["TSI Total Records", summary['overall_summary']['tsi_total_records']],
                [""]
            ]
            
            # Add WU summary
            if summary['wu_summary']:
                summary_data.extend([
                    ["=== WEATHER UNDERGROUND SUMMARY ==="],
                    ["Station ID", "Station Name", "Records", "Avg Temp (°C)", "Avg Humidity (%)", "Avg Wind (km/h)"]
                ])
                for station in summary['wu_summary']:
                    summary_data.append([
                        station['station_id'],
                        station['station_name'],
                        station['records_count'],
                        station['temp_avg_c'],
                        station['humidity_avg'],
                        station['wind_avg_kmh']
                    ])
                summary_data.append([""])
            
            # Add TSI summary
            if summary['tsi_summary']:
                summary_data.extend([
                    ["=== TSI AIR QUALITY SUMMARY ==="],
                    ["Device Name", "Records", "Avg PM2.5 (µg/m³)", "Avg PM10 (µg/m³)", "Avg Temp (°C)", "Avg Humidity (%)"]
                ])
                for device in summary['tsi_summary']:
                    summary_data.append([
                        device['device_name'],
                        device['records_count'],
                        device['pm25_avg'],
                        device['pm10_avg'],
                        device['temp_avg_c'],
                        device['humidity_avg']
                    ])
            
            # Update sheet
            summary_ws.update(summary_data)
            
        except Exception as e:
            self.logger.error(f"Error adding summary sheet: {e}")
    
    def add_daily_charts(self, spreadsheet, wu_df: Optional[pd.DataFrame], tsi_df: Optional[pd.DataFrame]) -> None:
        """Add charts for daily data visualization"""
        try:
            # This would implement chart creation similar to the existing chart systems
            # For now, we'll add a placeholder sheet
            charts_ws = spreadsheet.add_worksheet(title="Daily Charts", rows=100, cols=20)
            
            charts_info = [
                ["Daily Data Visualization Charts"],
                [""],
                ["Charts will be implemented here including:"],
                ["- PM2.5 trends by device"],
                ["- Temperature trends by station"],
                ["- Humidity comparison"],
                ["- Air quality index trends"],
                ["- 15-minute interval data visualization"],
                [""],
                ["This feature uses the existing chart generation"],
                ["system from the Hot Durham project."]
            ]
            
            charts_ws.update(charts_info)
            
        except Exception as e:
            self.logger.error(f"Error adding daily charts: {e}")
    
    def find_existing_daily_sheet(self, date_str: str) -> Optional[str]:
        """Find existing daily sheet for a given date"""
        try:
            # Search for sheets with the date in the name
            query = f"name contains 'HotDurham_Daily_{date_str}'"
            if self.drive_service is None:
                self.logger.error("drive_service is not initialized.")
                return None
            results = self.drive_service.files().list(
                q=query,
                mimeType='application/vnd.google-apps.spreadsheet'  # type: ignore[arg-type]
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']  # Return the first match
            
        except Exception as e:
            self.logger.error(f"Error finding existing sheet for {date_str}: {e}")
        
        return None
    
    def delete_sheet(self, sheet_id: str) -> None:
        """Delete a Google Sheet"""
        try:
            if self.drive_service is None:
                self.logger.error("drive_service is not initialized.")
                return
            self.drive_service.files().delete(fileId=sheet_id).execute()
            self.logger.info(f"Deleted sheet: {sheet_id}")
        except Exception as e:
            self.logger.error(f"Error deleting sheet {sheet_id}: {e}")
    
    def organize_sheet_in_drive(self, sheet_id: str, target_date: datetime) -> Optional[str]:
        """Organize sheet in Drive folder structure"""
        try:
            # Create main folder
            if self.drive_service is None:
                self.logger.error("drive_service is not initialized.")
                return None
            main_folder_id = self.create_drive_folder(self.config['drive_folder_name'])
            if not main_folder_id:
                return None

            # Create year folder
            year_folder_id = self.create_drive_folder(
                str(target_date.year), 
                main_folder_id
            )
            if not year_folder_id:
                return None

            # Create month folder
            month_name = target_date.strftime('%m-%B')
            month_folder_id = self.create_drive_folder(
                month_name,
                year_folder_id
            )
            if not month_folder_id:
                return None

            # Move sheet to month folder
            self.drive_service.files().update(
                fileId=sheet_id,
                addParents=month_folder_id,
                removeParents='root'  # type: ignore[arg-type]
            ).execute()

            self.logger.info(f"Organized sheet in Drive: {self.config['drive_folder_name']}/{target_date.year}/{month_name}")
            return month_folder_id
            
        except Exception as e:
            self.logger.error(f"Error organizing sheet in Drive: {e}")
        return None
    
    def save_daily_sheet_metadata(self, sheet_info: Dict[str, Any]) -> None:
        """Save metadata about created daily sheets"""
        try:
            metadata_dir = self.project_root / "data" / "daily_sheets_metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            metadata_file = metadata_dir / f"daily_sheets_{datetime.now().strftime('%Y_%m')}.json"
            
            # Load existing metadata
            metadata = []
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            # Add new entry
            metadata.append(sheet_info)
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Saved sheet metadata: {sheet_info['sheet_id']}")
            
        except Exception as e:
            self.logger.error(f"Error saving sheet metadata: {e}")
    
    def cleanup_old_sheets(self, retention_days: Optional[int] = None) -> None:
        """Clean up old daily sheets based on retention policy"""
        if retention_days is None:
            retention_days = int(self.config.get('sheet_retention_days', 30))
        
        if not self.config.get('auto_cleanup', True):
            self.logger.info("Auto cleanup disabled")
            return
        
        try:
            cutoff_date = datetime.now() - timedelta(days=int(retention_days))
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            # Search for old daily sheets
            query = f"name contains 'HotDurham_Daily_' and createdTime < '{cutoff_str}'"
            if self.drive_service is None:
                self.logger.error("drive_service is not initialized.")
                return
            results = self.drive_service.files().list(
                q=query,
                mimeType='application/vnd.google-apps.spreadsheet'  # type: ignore[arg-type]
            ).execute()
            
            files = results.get('files', [])
            deleted_count = 0
            
            for file in files:
                try:
                    self.drive_service.files().delete(fileId=file['id']).execute()
                    deleted_count += 1
                    self.logger.info(f"Deleted old sheet: {file['name']}")
                except Exception as e:
                    self.logger.error(f"Error deleting {file['name']}: {e}")
            
            self.logger.info(f"Cleanup completed: {deleted_count} old sheets deleted")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def run_daily_generation(self, target_date: Optional[datetime] = None, replace_existing: bool = True) -> Optional[Dict[str, str]]:
        """Run the complete daily sheet generation process"""
        self.logger.info("=== Starting Daily Sheets Generation ===")
        
        try:
            # Create daily sheet
            sheet_info = self.create_daily_sheet(target_date, replace_existing)
            
            if sheet_info:
                self.logger.info("✅ Daily sheet created successfully!")
                self.logger.info(f"📊 Sheet ID: {sheet_info['sheet_id']}")
                self.logger.info(f"🔗 Sheet URL: {sheet_info['sheet_url']}")
                self.logger.info(f"📂 Data Sources: {', '.join(sheet_info['data_sources'])}")
            else:
                self.logger.warning("⚠️ Daily sheet creation failed or no data available")
            
            # Cleanup old sheets
            if self.config.get('auto_cleanup', True):
                self.logger.info("🧹 Running cleanup of old sheets...")
                self.cleanup_old_sheets()
            
            self.logger.info("=== Daily Sheets Generation Completed ===")
            return sheet_info
            
        except Exception as e:
            self.logger.error(f"Error in daily generation process: {e}")
            return None

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Daily Sheets System')
    parser.add_argument('--date', help='Target date (YYYY-MM-DD), default: today')
    parser.add_argument('--no-replace', action='store_true', help='Do not replace existing sheets')
    parser.add_argument('--cleanup-only', action='store_true', help='Only run cleanup, do not create new sheet')
    parser.add_argument('--config-check', action='store_true', help='Check configuration and exit')
    
    args = parser.parse_args()
    
    # Initialize system
    daily_system = DailySheetsSystem(project_root)
    
    if args.config_check:
        print("=== Daily Sheets System Configuration ===")
        print(json.dumps(daily_system.config, indent=2))
        return
    
    if args.cleanup_only:
        print("Running cleanup only...")
        daily_system.cleanup_old_sheets()
        return
    
    # Parse target date
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            return
    
    # Run daily generation
    replace_existing = not args.no_replace
    result = daily_system.run_daily_generation(target_date, replace_existing)
    
    if result:
        print("\n✅ Daily sheet generation completed successfully!")
        print(f"🔗 Sheet URL: {result['sheet_url']}")
    else:
        print("\n❌ Daily sheet generation failed")

if __name__ == "__main__":
    main()
