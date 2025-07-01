#!/usr/bin/env python3
"""
🏗️ Create New Folders for Missing Analysis Data
==================================================
This script helps create replacement folders for the missing ones
and automatically shares them with hotdurham@gmail.com
"""

import os
import sys
from datetime import datetime

# Add the parent directory to sys.path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("📦 Please install: pip install google-api-python-client google-auth")
    sys.exit(1)

class FolderCreator:
    def __init__(self):
        self.creds_path = "creds/google_creds.json"
        self.main_user_email = "hotdurham@gmail.com"
        self.service = None
        
        # Define the folders to create
        self.folders_to_create = [
            {
                "name": "TestDataClusters_2025",
                "description": "Replacement for old testdataclusters folder"
            },
            {
                "name": "GeneratedReports_2025",
                "description": "Replacement for old PDF/report folders"
            },
            {
                "name": "AnalysisOutput_2025", 
                "description": "General analysis output folder"
            },
            {
                "name": "ExperimentalData_2025",
                "description": "For experimental analysis and testing"
            },
            {
                "name": "SensorAnalysis_2025",
                "description": "Sensor-specific analysis results"
            },
            {
                "name": "WeatherAnalysis_2025",
                "description": "Weather data analysis results"
            }
        ]
        
    def authenticate(self):
        """Authenticate with Google Drive API using service account."""
        try:
            if not os.path.exists(self.creds_path):
                print(f"❌ Credentials file not found: {self.creds_path}")
                return False
                
            credentials = service_account.Credentials.from_service_account_file(
                self.creds_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.service = build('drive', 'v3', credentials=credentials)
            print("✅ Successfully authenticated with Google Drive API")
            return True
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def create_folder(self, name: str, description: str = "") -> str:
        """Create a new folder and return its ID."""
        if not self.service:
            print("❌ Service not authenticated")
            return ""
            
        try:
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'description': description
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name, webViewLink'
            ).execute()
            
            folder_id = folder.get('id')
            folder_link = folder.get('webViewLink')
            
            print(f"✅ Created folder: {name}")
            print(f"   📁 ID: {folder_id}")
            print(f"   🔗 Link: {folder_link}")
            
            return folder_id
            
        except HttpError as e:
            print(f"❌ Failed to create folder '{name}': {e}")
            return ""
    
    def share_folder(self, folder_id: str, folder_name: str) -> bool:
        """Share folder with the main user."""
        if not self.service:
            print("❌ Service not authenticated")
            return False
            
        try:
            permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': self.main_user_email
            }
            
            self.service.permissions().create(
                fileId=folder_id,
                body=permission,
                sendNotificationEmail=False
            ).execute()
            
            print(f"   📧 Shared with {self.main_user_email}")
            return True
            
        except HttpError as e:
            print(f"   ❌ Failed to share '{folder_name}': {e}")
            return False
    
    def create_all_folders(self):
        """Create all replacement folders."""
        print("🏗️ Creating replacement folders...")
        print("="*50)
        
        created_folders = []
        
        for folder_info in self.folders_to_create:
            name = folder_info["name"]
            description = folder_info["description"]
            
            print(f"\n📂 Creating: {name}")
            print(f"   📋 Purpose: {description}")
            
            folder_id = self.create_folder(name, description)
            
            if folder_id:
                if self.share_folder(folder_id, name):
                    created_folders.append({
                        "name": name,
                        "id": folder_id,
                        "description": description
                    })
                    print("   ✅ Complete")
                else:
                    print("   ⚠️  Created but sharing failed")
            else:
                print("   ❌ Failed to create")
        
        return created_folders
    
    def generate_config_update(self, created_folders):
        """Generate configuration update suggestions."""
        print("\n" + "="*60)
        print("🔧 CONFIGURATION UPDATE GUIDE")
        print("="*60)
        
        if not created_folders:
            print("❌ No folders were created successfully")
            return
        
        print("📋 **New Folder IDs to use in your configuration:**")
        print()
        
        for folder in created_folders:
            print(f"📂 {folder['name']}:")
            print(f"   ID: {folder['id']}")
            print(f"   Purpose: {folder['description']}")
            print(f"   Link: https://drive.google.com/drive/folders/{folder['id']}")
            print()
        
        print("🔄 **Files to update:**")
        config_files = [
            "config/automated_data_pull_config.py",
            "config/daily_sheets_config.json",
            "scripts/automated_data_pull.py"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                print(f"   ✅ {config_file}")
            else:
                print(f"   📁 {config_file} (if it exists)")
        
        print("\n💾 **Save this information:**")
        
        # Generate a simple config file
        config_content = "# New Folder Configuration\n"
        config_content += f"# Generated: {datetime.now().isoformat()}\n\n"
        
        for folder in created_folders:
            var_name = folder['name'].upper().replace(' ', '_').replace('-', '_')
            config_content += f"{var_name}_FOLDER_ID = '{folder['id']}'\n"
        
        config_filename = f"new_folder_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        
        with open(config_filename, 'w') as f:
            f.write(config_content)
        
        print(f"   📄 Saved to: {config_filename}")
        
        print("\n🎯 **Next Steps:**")
        print("   1. Update your scripts to use these new folder IDs")
        print("   2. Test all automated processes")
        print("   3. Re-run any analysis that was stored in old folders")
        print("   4. Document the new folder structure")

def main():
    print("🏗️ Create New Folders for Missing Analysis Data")
    print("="*60)
    
    creator = FolderCreator()
    
    if not creator.authenticate():
        print("❌ Cannot proceed without authentication")
        return
    
    print("\n📋 Folders to create:")
    for i, folder in enumerate(creator.folders_to_create, 1):
        print(f"   {i}. {folder['name']} - {folder['description']}")
    
    print(f"\n🔗 All folders will be shared with: {creator.main_user_email}")
    
    response = input("\n❓ Do you want to create these folders? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        created_folders = creator.create_all_folders()
        creator.generate_config_update(created_folders)
        
        print("\n✨ **Folder creation complete!**")
        print("   - Check your Google Drive to see the new folders")
        print("   - Update your scripts with the new folder IDs")
        print("   - Re-run any analysis processes as needed")
    else:
        print("\n❌ Folder creation cancelled")
        print("   You can run this script again when ready")

if __name__ == "__main__":
    main()
