#!/usr/bin/env python3
"""
Upload Multi-Sensor Visualization Graphs to Google Drive

This script uploads all the generated visualization graphs to Google Drive
within the test sensor folder structure for easy access and sharing.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "config"))

try:
    from data_manager import DataManager
    from test_sensors_config import TestSensorConfig
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

class VisualizationUploader:
    """Upload visualization graphs to Google Drive"""
    
    def __init__(self):
        self.project_root = project_root
        self.viz_dir = self.project_root / "sensor_visualizations"
        self.data_manager = None
        self.test_config = None
        
        print("🎨 Multi-Sensor Visualization Google Drive Uploader")
        print("=" * 55)
        
    def initialize_services(self):
        """Initialize Google Drive and test sensor services"""
        print("\n🔧 Initializing services...")
        
        try:
            # Initialize data manager for Google Drive access
            self.data_manager = DataManager(str(self.project_root))
            
            # Initialize test sensor config
            self.test_config = TestSensorConfig()
            
            if self.data_manager.drive_service:
                print("✅ Google Drive service connected")
            else:
                print("❌ Google Drive service not available")
                return False
                
            print("✅ Services initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing services: {e}")
            return False
    
    def check_visualization_files(self):
        """Check what visualization files are available for upload"""
        print(f"\n📊 Checking visualization files in {self.viz_dir}...")
        
        if not self.viz_dir.exists():
            print(f"❌ Visualization directory not found: {self.viz_dir}")
            return []
        
        # Look for PNG files (the visualizations)
        png_files = list(self.viz_dir.glob("*.png"))
        other_files = [f for f in self.viz_dir.glob("*") 
                      if f.is_file() and f.suffix not in ['.png']]
        
        print(f"\n📈 Found visualization files:")
        print(f"   PNG Graphs: {len(png_files)}")
        for png_file in png_files:
            file_size = png_file.stat().st_size / (1024 * 1024)  # MB
            print(f"   • {png_file.name} ({file_size:.1f} MB)")
        
        print(f"\n📄 Additional files:")
        for other_file in other_files:
            file_size = other_file.stat().st_size / 1024  # KB
            print(f"   • {other_file.name} ({file_size:.1f} KB)")
        
        all_files = png_files + other_files
        print(f"\n📊 Total files to upload: {len(all_files)}")
        
        return all_files
    
    def create_google_drive_folder_structure(self):
        """Create the Google Drive folder structure for visualizations"""
        print(f"\n📁 Creating Google Drive folder structure...")
        
        # Create a dedicated folder for sensor visualizations within the test data structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_folder = "HotDurham/TestData_ValidationCluster/Visualizations"
        viz_folder = f"{base_folder}/MultiSensorAnalysis/Analysis_{timestamp}"
        
        try:
            folder_id = self.data_manager.get_or_create_drive_folder(viz_folder)
            if folder_id:
                print(f"✅ Created Google Drive folder: {viz_folder}")
                return viz_folder
            else:
                print(f"❌ Failed to create Google Drive folder")
                return None
                
        except Exception as e:
            print(f"❌ Error creating Google Drive folder: {e}")
            return None
    
    def upload_visualization_files(self, files_to_upload, drive_folder):
        """Upload all visualization files to Google Drive"""
        print(f"\n📤 Uploading {len(files_to_upload)} files to Google Drive...")
        print(f"   Target folder: {drive_folder}")
        
        success_count = 0
        failed_files = []
        
        for i, file_path in enumerate(files_to_upload, 1):
            try:
                print(f"\n   📤 Uploading {i}/{len(files_to_upload)}: {file_path.name}")
                
                # Upload file to Google Drive
                success = self.data_manager.upload_to_drive(file_path, drive_folder)
                
                if success:
                    success_count += 1
                    file_size = file_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"      ✅ Uploaded successfully ({file_size:.1f} MB)")
                else:
                    failed_files.append(file_path.name)
                    print(f"      ❌ Upload failed")
                
                # Brief delay between uploads to avoid rate limiting
                if i < len(files_to_upload):
                    time.sleep(0.5)
                    
            except Exception as e:
                failed_files.append(file_path.name)
                print(f"      ❌ Error uploading {file_path.name}: {e}")
        
        # Upload summary
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Successful: {success_count}/{len(files_to_upload)} files")
        print(f"   📈 Graphs uploaded: {len([f for f in files_to_upload if f.suffix == '.png' and f.name not in failed_files])}")
        print(f"   📄 Documents uploaded: {len([f for f in files_to_upload if f.suffix != '.png' and f.name not in failed_files])}")
        
        if failed_files:
            print(f"   ❌ Failed uploads: {len(failed_files)}")
            for failed_file in failed_files:
                print(f"      • {failed_file}")
        
        return success_count == len(files_to_upload)
    
    def create_drive_summary_info(self, drive_folder, uploaded_files):
        """Create a summary information file for the uploaded visualizations"""
        try:
            summary_info = {
                "upload_info": {
                    "upload_timestamp": datetime.now().isoformat(),
                    "upload_folder": drive_folder,
                    "total_files_uploaded": len(uploaded_files),
                    "project": "Hot Durham Multi-Sensor Visualization Analysis"
                },
                "visualization_files": {
                    "graphs": [f.name for f in uploaded_files if f.suffix == '.png'],
                    "reports": [f.name for f in uploaded_files if f.suffix in ['.json', '.md']],
                    "other": [f.name for f in uploaded_files if f.suffix not in ['.png', '.json', '.md']]
                },
                "analysis_details": {
                    "sensors_analyzed": 14,
                    "data_points": 8113,
                    "analysis_period": "2025-06-01 to 2025-06-10",
                    "visualization_types": [
                        "Temperature Analysis",
                        "Humidity Analysis", 
                        "Pressure & Wind Analysis",
                        "Sensor Correlations",
                        "Data Quality Dashboard",
                        "Environmental Dashboard"
                    ]
                },
                "access_info": {
                    "google_drive_folder": drive_folder,
                    "recommended_viewing": "Download PNG files for best quality",
                    "report_file": "analysis_report.json",
                    "documentation": "README.md"
                }
            }
            
            # Save summary locally
            summary_file = self.viz_dir / "google_drive_upload_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary_info, f, indent=2)
            
            # Upload summary to Google Drive
            self.data_manager.upload_to_drive(summary_file, drive_folder)
            
            print(f"\n📋 Created and uploaded summary information")
            return summary_info
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create summary information: {e}")
            return None
    
    def run_upload(self):
        """Execute the complete upload process"""
        
        # Initialize services
        if not self.initialize_services():
            return False
        
        # Check visualization files
        files_to_upload = self.check_visualization_files()
        if not files_to_upload:
            print("❌ No visualization files found to upload")
            return False
        
        # Create Google Drive folder structure
        drive_folder = self.create_google_drive_folder_structure()
        if not drive_folder:
            return False
        
        # Upload files
        upload_success = self.upload_visualization_files(files_to_upload, drive_folder)
        
        # Create summary information
        self.create_drive_summary_info(drive_folder, files_to_upload)
        
        # Final status
        if upload_success:
            print(f"\n🎉 UPLOAD COMPLETE!")
            print(f"✅ All visualization files uploaded successfully")
            print(f"📁 Google Drive location: {drive_folder}")
            print(f"🔗 Access: Open Google Drive and navigate to the folder above")
            print(f"📊 Files available: Graphs, reports, and documentation")
            
            print(f"\n📋 Uploaded Visualizations:")
            graphs = [f for f in files_to_upload if f.suffix == '.png']
            for graph in graphs:
                print(f"   🎨 {graph.name}")
            
            print(f"\n💡 Usage Tips:")
            print(f"   • Download PNG files for best quality viewing")
            print(f"   • Check analysis_report.json for detailed statistics")
            print(f"   • Read README.md for complete documentation")
            
            return True
        else:
            print(f"\n⚠️ Upload completed with some failures")
            print(f"📁 Google Drive location: {drive_folder}")
            print(f"💡 Check the upload summary for details")
            return False

def main():
    """Main execution function"""
    uploader = VisualizationUploader()
    success = uploader.run_upload()
    
    if success:
        print(f"\n🚀 Your multi-sensor visualizations are now available in Google Drive!")
    else:
        print(f"\n❌ Upload process encountered issues. Check the output above for details.")
    
    return success

if __name__ == "__main__":
    main()
