#!/usr/bin/env python3
"""
Production Sensor Visualization Google Drive Upload System
=========================================================

This script uploads the production sensor visualizations to Google Drive
in an organized folder structure separate from test sensor data.

Author: Hot Durham Project  
Date: June 2025
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionSensorDriveUploader:
    """Upload production sensor visualizations to Google Drive."""
    
    def __init__(self, credentials_file: str = "creds/google_creds.json"):
        """Initialize the Google Drive uploader."""
        self.credentials_file = credentials_file
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.service = None
        
        # Production sensor visualization path
        self.viz_dir = Path("sensor_visualizations/production_sensors")
        
        # Google Drive folder structure for production sensors
        self.base_folder_name = "HotDurham"
        self.production_folder_name = "ProductionData_SensorAnalysis"
        self.viz_subfolder_name = "Visualizations"
        self.multi_sensor_folder_name = "MultiSensorAnalysis"
        
        # Current session timestamp
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API using service account."""
        try:
            # Check if we have a service account credentials file
            if os.path.exists(self.credentials_file):
                # Use service account authentication
                creds = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_file, scopes=self.scopes)
                self.service = build('drive', 'v3', credentials=creds)
                logger.info("Successfully authenticated with Google Drive using service account")
                return True
            else:
                logger.error(f"Credentials file not found: {self.credentials_file}")
                return False
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Find existing folder or create new one."""
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            response = self.service.files().list(q=query).execute()
            folders = response.get('files', [])
            
            if folders:
                logger.info(f"Found existing folder: {folder_name}")
                return folders[0]['id']
            
            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(body=folder_metadata).execute()
            logger.info(f"Created new folder: {folder_name}")
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error with folder {folder_name}: {e}")
            return None
    
    def setup_folder_structure(self) -> Optional[str]:
        """Setup the complete folder structure for production sensor data."""
        try:
            # 1. Find or create base HotDurham folder
            base_folder_id = self.find_or_create_folder(self.base_folder_name)
            if not base_folder_id:
                return None
            
            # 2. Find or create ProductionData_SensorAnalysis folder
            production_folder_id = self.find_or_create_folder(
                self.production_folder_name, base_folder_id)
            if not production_folder_id:
                return None
            
            # 3. Find or create Visualizations folder
            viz_folder_id = self.find_or_create_folder(
                self.viz_subfolder_name, production_folder_id)
            if not viz_folder_id:
                return None
            
            # 4. Find or create MultiSensorAnalysis folder
            multi_sensor_folder_id = self.find_or_create_folder(
                self.multi_sensor_folder_name, viz_folder_id)
            if not multi_sensor_folder_id:
                return None
            
            # 5. Create session-specific folder with timestamp
            session_folder_name = f"Analysis_{self.timestamp}"
            session_folder_id = self.find_or_create_folder(
                session_folder_name, multi_sensor_folder_id)
            
            if session_folder_id:
                logger.info(f"Setup complete folder structure: {self.base_folder_name}/{self.production_folder_name}/{self.viz_subfolder_name}/{self.multi_sensor_folder_name}/{session_folder_name}")
            
            return session_folder_id
            
        except Exception as e:
            logger.error(f"Error setting up folder structure: {e}")
            return None
    
    def upload_file(self, file_path: Path, folder_id: str, description: str = "") -> bool:
        """Upload a single file to Google Drive."""
        try:
            # Determine MIME type based on file extension
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.pdf': 'application/pdf',
                '.html': 'text/html',
                '.txt': 'text/plain',
                '.csv': 'text/csv'
            }
            
            file_extension = file_path.suffix.lower()
            mime_type = mime_types.get(file_extension, 'application/octet-stream')
            
            # File metadata
            file_metadata = {
                'name': file_path.name,
                'parents': [folder_id],
                'description': description
            }
            
            # Upload file
            media = MediaFileUpload(str(file_path), mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            logger.info(f"Uploaded: {file_path.name} -> {file.get('webViewLink')}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading {file_path.name}: {e}")
            return False
    
    def get_production_visualization_files(self) -> List[Dict[str, str]]:
        """Get list of production visualization files to upload."""
        files_to_upload = []
        
        if not self.viz_dir.exists():
            logger.warning(f"Visualization directory not found: {self.viz_dir}")
            return files_to_upload
        
        # Define file patterns and descriptions
        file_patterns = {
            'production_temperature_overlay_*.png': 'Multi-sensor temperature comparison overlay showing all production sensors (WU + TSI)',
            'production_humidity_overlay_*.png': 'Multi-sensor humidity comparison overlay showing all production sensors (WU + TSI)',
            'production_air_quality_analysis_*.png': 'Comprehensive air quality analysis for TSI sensors (PM 2.5, PM 10, AQI)',
            'production_weather_parameters_*.png': 'Weather parameters grid analysis for Weather Underground sensors',
            'production_correlation_matrix_*.png': 'Cross-sensor correlation analysis between all production sensors',
            'production_interactive_dashboard_*.html': 'Interactive multi-parameter dashboard (HTML) for all production sensors',
            'production_sensor_report_*.txt': 'Comprehensive analysis summary report for all production sensors'
        }
        
        # Find matching files
        for pattern, description in file_patterns.items():
            matching_files = list(self.viz_dir.glob(pattern))
            for file_path in matching_files:
                files_to_upload.append({
                    'path': file_path,
                    'description': description
                })
        
        # Sort by filename for consistent ordering
        files_to_upload.sort(key=lambda x: x['path'].name)
        
        logger.info(f"Found {len(files_to_upload)} production visualization files to upload")
        return files_to_upload
    
    def create_upload_summary(self, uploaded_files: List[Dict], folder_id: str) -> bool:
        """Create and upload a summary file of the upload session."""
        try:
            summary_lines = [
                "PRODUCTION SENSOR VISUALIZATION UPLOAD SUMMARY",
                "=" * 55,
                f"Upload Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Session ID: {self.timestamp}",
                f"Total Files Uploaded: {len(uploaded_files)}",
                "",
                "PRODUCTION SENSOR INVENTORY:",
                "-" * 30,
                "Weather Underground Sensors:",
                "  • KNCDURHA209: Duke-MS-03",
                "  • KNCDURHA590: Duke-Kestrel-01",
                "",
                "TSI Air Quality Sensors:",
                "  • curp44dveott0jmp5aig: BS-05 (El Futuro Greenspace)",
                "  • curp5a72jtt5l9q4rkd0: BS-7",
                "  • curp4k5veott0jmp5aj0: BS-01 (Eno)",
                "  • cv884m3ne4ath43m7hu0: BS-11",
                "  • d0930cvoovhpfm35n49g: BS-13",
                "  • curp515veott0jmp5ajg: BS-3 (Golden Belt)",
                "",
                "UPLOADED VISUALIZATIONS:",
                "-" * 25
            ]
            
            for i, file_info in enumerate(uploaded_files, 1):
                summary_lines.append(f"{i}. {file_info['file_name']}")
                summary_lines.append(f"   Description: {file_info['description']}")
                summary_lines.append(f"   Google Drive Link: {file_info['link']}")
                summary_lines.append("")
            
            summary_lines.extend([
                "VISUALIZATION TYPES GENERATED:",
                "-" * 30,
                "1. Multi-Sensor Temperature Overlay",
                "   - Shows temperature trends from all WU and TSI sensors",
                "   - Compares sensor readings over time",
                "",
                "2. Multi-Sensor Humidity Overlay", 
                "   - Shows humidity trends from all WU and TSI sensors",
                "   - Identifies patterns and correlations",
                "",
                "3. Air Quality Analysis (TSI Sensors)",
                "   - PM 2.5 AQI trends over time",
                "   - PM 10 concentration analysis",
                "   - Average AQI by sensor location",
                "   - PM 2.5 vs PM 10 correlation plots",
                "",
                "4. Weather Parameters Grid (WU Sensors)",
                "   - Temperature, humidity, solar radiation",
                "   - Wind speed, pressure, precipitation",
                "   - Comprehensive weather monitoring",
                "",
                "5. Cross-Sensor Correlation Matrix",
                "   - Temperature correlations between all sensors",
                "   - Humidity correlations between all sensors",
                "   - Statistical relationship analysis",
                "",
                "6. Interactive Dashboard (HTML)",
                "   - Multi-parameter interactive plots",
                "   - Zoom, pan, and filter capabilities",
                "   - Real-time data exploration",
                "",
                "7. Analysis Summary Report",
                "   - Comprehensive sensor inventory",
                "   - Statistical summaries",
                "   - Data quality metrics",
                "",
                "FOLDER STRUCTURE:",
                "-" * 17,
                "HotDurham/",
                "  └── ProductionData_SensorAnalysis/",
                "      └── Visualizations/",
                "          └── MultiSensorAnalysis/",
                f"              └── Analysis_{self.timestamp}/",
                "                  ├── Temperature & Humidity Overlays",
                "                  ├── Air Quality Analysis",
                "                  ├── Weather Parameters Grid",
                "                  ├── Correlation Matrix",
                "                  ├── Interactive Dashboard",
                "                  └── Summary Report",
                "",
                "ANALYSIS NOTES:",
                "-" * 15,
                "• Production sensors are distinct from test sensors",
                "• Test sensors (KNCDURHA634-648) are used for validation",
                "• Production sensors provide operational monitoring data",
                "• Weather Underground sensors provide meteorological data",
                "• TSI sensors provide air quality measurements",
                "• All visualizations use consistent color coding",
                "• Interactive dashboard allows detailed exploration",
                "",
                "END OF SUMMARY"
            ])
            
            # Save summary file
            summary_filename = f"UPLOAD_SUMMARY_{self.timestamp}.txt"
            summary_path = self.viz_dir / summary_filename
            
            with open(summary_path, 'w') as f:
                f.write('\n'.join(summary_lines))
            
            # Upload summary to Google Drive
            success = self.upload_file(
                summary_path, 
                folder_id, 
                f"Upload summary for production sensor visualization session {self.timestamp}"
            )
            
            if success:
                logger.info(f"Created and uploaded summary file: {summary_filename}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating upload summary: {e}")
            return False
    
    def upload_production_visualizations(self) -> Dict[str, str]:
        """Upload all production sensor visualizations to Google Drive."""
        logger.info("Starting production sensor visualization upload to Google Drive...")
        
        # Authenticate
        if not self.authenticate():
            return {}
        
        # Setup folder structure
        upload_folder_id = self.setup_folder_structure()
        if not upload_folder_id:
            logger.error("Failed to setup folder structure")
            return {}
        
        # Get files to upload
        files_to_upload = self.get_production_visualization_files()
        if not files_to_upload:
            logger.warning("No visualization files found to upload")
            return {}
        
        # Upload files
        uploaded_files = []
        upload_results = {}
        
        for file_info in files_to_upload:
            file_path = file_info['path']
            description = file_info['description']
            
            success = self.upload_file(file_path, upload_folder_id, description)
            
            if success:
                # Get the file link (simplified)
                file_link = f"https://drive.google.com/drive/folders/{upload_folder_id}"
                uploaded_files.append({
                    'file_name': file_path.name,
                    'description': description,
                    'link': file_link
                })
                upload_results[file_path.name] = file_link
            else:
                logger.error(f"Failed to upload: {file_path.name}")
        
        # Create upload summary
        if uploaded_files:
            self.create_upload_summary(uploaded_files, upload_folder_id)
        
        # Print results
        print(f"\n{'='*70}")
        print("PRODUCTION SENSOR VISUALIZATION UPLOAD COMPLETE")
        print(f"{'='*70}")
        print(f"Upload session: {self.timestamp}")
        print(f"Files uploaded: {len(uploaded_files)}")
        print(f"Google Drive folder: HotDurham/ProductionData_SensorAnalysis/Visualizations/MultiSensorAnalysis/Analysis_{self.timestamp}")
        print(f"Folder link: https://drive.google.com/drive/folders/{upload_folder_id}")
        print(f"{'='*70}")
        
        if uploaded_files:
            print("\nUploaded files:")
            for file_info in uploaded_files:
                print(f"  ✓ {file_info['file_name']}")
        
        return upload_results


def main():
    """Main function to upload production sensor visualizations."""
    uploader = ProductionSensorDriveUploader()
    results = uploader.upload_production_visualizations()
    
    if results:
        print(f"\nSuccessfully uploaded {len(results)} files to Google Drive!")
    else:
        print("\nNo files were uploaded.")


if __name__ == "__main__":
    main()
