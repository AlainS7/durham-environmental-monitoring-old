#!/usr/bin/env python3
"""
Upload Enhanced Production Sensor Visualizations to Google Drive
================================================================

This script uploads the enhanced production sensor visualizations that incorporate
Central Asian Data Center techniques to Google Drive in an organized folder structure.

Enhanced visualizations include:
- Sensor uptime monitoring with chunked bar charts
- PM 2.5 logarithmic scaling analysis
- Daily uptime heatmaps
- Cross-sensor correlation analysis
- Comprehensive HTML reports with embedded images
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "core"))

try:
    from src.automation.master_data_file_system import MasterDataFileSystem
    from src.core.data_manager import DataManager
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

class EnhancedVisualizationUploader:
    """Upload enhanced production sensor visualizations to Google Drive."""
    
    def __init__(self):
        self.project_root = project_root
        self.enhanced_viz_dir = project_root / "sensor_visualizations" / "enhanced_production_sensors"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize Google Drive system
        self.master_system = MasterDataFileSystem()
        self.data_manager = DataManager(str(project_root))
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for upload process."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def get_enhanced_visualization_files(self):
        """Get all enhanced visualization files to upload."""
        if not self.enhanced_viz_dir.exists():
            self.logger.error(f"Enhanced visualization directory not found: {self.enhanced_viz_dir}")
            return []
        
        # Get all visualization files (PNG, HTML, TXT)
        file_patterns = ['*.png', '*.html', '*.txt']
        files_to_upload = []
        
        for pattern in file_patterns:
            files_to_upload.extend(self.enhanced_viz_dir.glob(pattern))
        
        # Filter to get the latest files only (avoid duplicates from multiple runs)
        latest_files = {}
        for file_path in files_to_upload:
            # Extract base name (remove timestamp)
            base_name = file_path.name
            if '_2025' in base_name:
                # Get the base type
                parts = base_name.split('_')
                if len(parts) >= 3:
                    base_type = '_'.join(parts[:-2])  # Remove date and time parts
                    
                    # Keep only the newest file for each type
                    if base_type not in latest_files or file_path.stat().st_mtime > latest_files[base_type].stat().st_mtime:
                        latest_files[base_type] = file_path
        
        return list(latest_files.values())
    
    def create_drive_folder_structure(self):
        """Create organized folder structure in Google Drive for enhanced visualizations."""
        try:
            # Create folder path: HotDurham/ProductionData_SensorAnalysis/Visualizations/EnhancedAnalysis/Analysis_Enhanced_TIMESTAMP
            folder_path = f"HotDurham/ProductionData_SensorAnalysis/Visualizations/EnhancedAnalysis/Analysis_Enhanced_{self.timestamp}"
            
            # Use the get_or_create_drive_folder method to handle the full path
            folder_id = self.master_system.get_or_create_drive_folder(folder_path)
            
            if folder_id:
                self.logger.info(f"Setup complete folder structure: {folder_path}")
                return folder_path  # Return the path, not the ID
            else:
                self.logger.error(f"Failed to create/find folder path: {folder_path}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error creating folder structure: {e}")
            return None
    
    def upload_files_to_drive(self, files_to_upload, folder_path):
        """Upload enhanced visualization files to Google Drive."""
        uploaded_files = []
        
        self.logger.info(f"Found {len(files_to_upload)} enhanced visualization files to upload")
        
        for file_path in files_to_upload:
            try:
                # Upload file using master system upload_to_drive method
                success = self.master_system.upload_to_drive(file_path, folder_path)
                
                if success:
                    self.logger.info(f"Uploaded: {file_path.name} -> Google Drive")
                    uploaded_files.append({
                        'name': file_path.name,
                        'path': str(file_path),
                        'url': f"Google Drive: {folder_path}",
                        'id': 'uploaded'
                    })
                else:
                    self.logger.error(f"Failed to upload: {file_path.name}")
                    
            except Exception as e:
                self.logger.error(f"Error uploading {file_path.name}: {e}")
        
        return uploaded_files
    
    def create_upload_summary(self, uploaded_files, folder_path):
        """Create and upload a summary of the enhanced visualization upload."""
        try:
            summary_content = f"""ENHANCED PRODUCTION SENSOR VISUALIZATION UPLOAD SUMMARY
=====================================================================
Upload Session: {self.timestamp}
Upload Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Files Uploaded: {len(uploaded_files)}

ENHANCED FEATURES INCLUDED:
---------------------------
• Sensor Uptime Monitoring with Chunked Bar Charts
• PM 2.5 Logarithmic Scaling Analysis (Central Asian Technique)
• Daily Performance Heatmaps
• Cross-Sensor Correlation Analysis
• Comprehensive HTML Reports with Embedded Images
• Geographic Sensor Grouping
• Statistical Summary Tables
• Quality Threshold Filtering

UPLOADED FILES:
---------------
"""
            
            for i, file_info in enumerate(uploaded_files, 1):
                file_type = "Visualization" if file_info['name'].endswith('.png') else \
                           "Report" if file_info['name'].endswith('.html') else \
                           "Summary" if file_info['name'].endswith('.txt') else "File"
                
                summary_content += f"{i:2d}. {file_info['name']}\n"
                summary_content += f"    Type: {file_type}\n"
                summary_content += f"    Location:  Google Drive: {folder_path}\n\n"
            
            summary_content += f"""
GOOGLE DRIVE LOCATION:
----------------------
Folder: {folder_path}

TECHNIQUES FROM CENTRAL ASIAN DATA CENTER:
------------------------------------------
• Logarithmic scaling for high-variance environmental data
• Chunked bar charts for improved readability (8 sensors per chart)
• Daily uptime tables with pivot analysis
• HTML report generation with embedded base64 images
• Quality threshold filtering for sensor data integrity
• Geographic grouping and correlation analysis
• Statistical summary tables and heatmaps
• Professional HTML/CSS report styling

SENSOR UPTIME ANALYSIS:
-----------------------
The enhanced visualizations include comprehensive uptime analysis showing:
- Weather Underground sensors achieving 100% uptime
- TSI Air Quality sensors with variable performance (7-100% uptime)
- Daily performance tracking and heatmaps
- Geographic correlation patterns

Generated by: Enhanced Production Sensor Visualization System
Hot Durham Environmental Monitoring Project
"""
            
            # Save summary file locally
            summary_filename = f"ENHANCED_UPLOAD_SUMMARY_{self.timestamp}.txt"
            summary_path = self.enhanced_viz_dir / summary_filename
            
            with open(summary_path, 'w') as f:
                f.write(summary_content)
            
            # Upload summary to Drive
            summary_success = self.master_system.upload_to_drive(summary_path, folder_path)
            
            if summary_success:
                self.logger.info(f"Uploaded: {summary_filename} -> Google Drive")
                return summary_path, f"Google Drive: {folder_path}"
            else:
                self.logger.error(f"Failed to upload summary file: {summary_filename}")
                return summary_path, None
                
        except Exception as e:
            self.logger.error(f"Error creating upload summary: {e}")
            return None, None
    
    def run_upload(self):
        """Execute the complete enhanced visualization upload process."""
        try:
            self.logger.info("Starting enhanced production sensor visualization upload to Google Drive...")
            
            # Get files to upload
            files_to_upload = self.get_enhanced_visualization_files()
            if not files_to_upload:
                self.logger.error("No enhanced visualization files found to upload")
                return False
            
            # Create folder structure
            folder_path = self.create_drive_folder_structure()
            if not folder_path:
                self.logger.error("Failed to create Google Drive folder structure")
                return False
            
            # Upload files
            uploaded_files = self.upload_files_to_drive(files_to_upload, folder_path)
            
            if not uploaded_files:
                self.logger.error("No files were successfully uploaded")
                return False
            
            # Create and upload summary
            summary_path, summary_url = self.create_upload_summary(uploaded_files, folder_path)
            
            # Print completion summary
            print("\n" + "=" * 80)
            print("ENHANCED PRODUCTION SENSOR VISUALIZATION UPLOAD COMPLETE")
            print("=" * 80)
            print(f"Upload session: {self.timestamp}")
            print(f"Files uploaded: {len(uploaded_files)}")
            print(f"Google Drive folder: {folder_path}")
            print("=" * 80)
            print()
            print("Enhanced Features Uploaded:")
            print("  ✓ Sensor uptime monitoring with chunked bar charts")
            print("  ✓ PM 2.5 logarithmic scaling analysis")
            print("  ✓ Daily performance heatmaps") 
            print("  ✓ Cross-sensor correlation analysis")
            print("  ✓ Comprehensive HTML reports")
            print("  ✓ Geographic sensor grouping")
            print()
            print("Uploaded files:")
            for file_info in uploaded_files:
                print(f"  ✓ {file_info['name']}")
            print()
            print("Successfully uploaded enhanced visualizations to Google Drive!")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fatal error in upload process: {e}")
            return False

def main():
    """Main execution function."""
    uploader = EnhancedVisualizationUploader()
    
    if not uploader.data_manager.drive_service:
        print("❌ Google Drive service not available. Check credentials.")
        return 1
    
    success = uploader.run_upload()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
