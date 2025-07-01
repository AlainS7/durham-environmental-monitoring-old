#!/usr/bin/env python3
"""
🔧 Old Folder Recovery Tool
============================================================
This script helps recover access to folders created by the old service account.
It provides multiple strategies for finding and restoring access to missing folders.
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict

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

class OldFolderRecovery:
    def __init__(self):
        self.creds_path = "creds/google_creds.json"
        self.main_user_email = "hotdurham@gmail.com"
        self.old_service_account = "hot-durham-data@hot-durham-data.iam.gserviceaccount.com"
        self.service = None
        self.known_missing_folders = [
            "testdataclusters",
            "generated_pdfs", 
            "pdf_reports",
            "analysis_output",
            "cluster_analysis",
            "test_data_clusters",
            "sensor_clusters",
            "weather_clusters"
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
    
    def search_by_pattern(self, pattern: str, exact_match: bool = False) -> List[Dict]:
        """Search for folders by name pattern."""
        if not self.service:
            print("❌ Service not authenticated")
            return []
            
        try:
            if exact_match:
                query = f"name = '{pattern}' and mimeType = 'application/vnd.google-apps.folder'"
            else:
                query = f"name contains '{pattern}' and mimeType = 'application/vnd.google-apps.folder'"
            
            results = self.service.files().list(
                q=query,
                pageSize=50,
                fields="nextPageToken, files(id, name, createdTime, owners, permissions)"
            ).execute()
            
            return results.get('files', [])
        except HttpError as e:
            print(f"❌ Error searching for pattern '{pattern}': {e}")
            return []
    
    def search_shared_with_user(self) -> List[Dict]:
        """Search for folders shared with the main user."""
        if not self.service:
            print("❌ Service not authenticated")
            return []
            
        try:
            # This searches folders where main user has some permission
            query = f"'{self.main_user_email}' in readers or '{self.main_user_email}' in writers"
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, createdTime, owners, permissions)"
            ).execute()
            
            return results.get('files', [])
        except HttpError as e:
            print(f"❌ Error searching shared files: {e}")
            return []
    
    def check_folder_accessibility(self, folder_id: str) -> Dict:
        """Check if a folder is accessible and get its details."""
        if not self.service:
            return {"error": "Service not authenticated"}
            
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="id, name, createdTime, owners, permissions, shared"
            ).execute()
            return folder
        except HttpError as e:
            return {"error": str(e)}
    
    def attempt_share_with_main_user(self, folder_id: str, folder_name: str) -> bool:
        """Attempt to share a folder with the main user."""
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
            
            print(f"✅ Successfully shared '{folder_name}' with {self.main_user_email}")
            return True
        except HttpError as e:
            print(f"❌ Failed to share '{folder_name}': {e}")
            return False
    
    def generate_recovery_report(self) -> Dict:
        """Generate a comprehensive recovery report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "search_results": {},
            "recommendations": [],
            "manual_steps": []
        }
        
        print("🔍 Searching for potentially missing folders...")
        
        # Search for each known missing folder pattern
        for pattern in self.known_missing_folders:
            print(f"   Searching for '{pattern}'...")
            exact_results = self.search_by_pattern(pattern, exact_match=True)
            contains_results = self.search_by_pattern(pattern, exact_match=False)
            
            report["search_results"][pattern] = {
                "exact_matches": len(exact_results),
                "partial_matches": len(contains_results),
                "folders": exact_results + contains_results
            }
            
            if exact_results or contains_results:
                print(f"      Found {len(exact_results)} exact, {len(contains_results)} partial matches")
        
        # Search for folders shared with main user
        print("🔍 Searching for folders shared with main user...")
        shared_folders = self.search_shared_with_user()
        report["shared_with_main_user"] = {
            "count": len(shared_folders),
            "folders": shared_folders
        }
        
        return report
    
    def print_recovery_guide(self):
        """Print a comprehensive recovery guide."""
        print("\n" + "="*60)
        print("🎯 FOLDER RECOVERY GUIDE")
        print("="*60)
        
        print("\n📋 **Step 1: Check hotdurham@gmail.com Google Drive**")
        print("   1. Go to https://drive.google.com")
        print("   2. Log in with hotdurham@gmail.com")
        print("   3. Click 'Shared with me' in the left sidebar")
        print("   4. Look for these folders:")
        for folder in self.known_missing_folders:
            print(f"      - {folder}")
        print("   5. If found, right-click → 'Add to My Drive'")
        
        print("\n🔧 **Step 2: Check Google Cloud Console**")
        print("   1. Go to https://console.cloud.google.com")
        print("   2. Select your 'hot-durham-data' project")
        print("   3. Go to IAM & Admin → Service Accounts")
        print("   4. Look for your old service account:")
        print(f"      {self.old_service_account}")
        print("   5. If it still exists, try creating a new key")
        
        print("\n📧 **Step 3: Manual Recovery Process**")
        print("   If folders are found in 'Shared with me':")
        print("   1. Copy important files to a new folder")
        print("   2. Share the new folder with the new service account")
        print("   3. Update your scripts to use new folder IDs")
        
        print("\n🔄 **Step 4: Recreation Strategy**")
        print("   If folders cannot be recovered:")
        print("   1. Create new folders with similar names")
        print("   2. Re-run any data processing scripts")
        print("   3. Regenerate PDF reports if needed")
        print("   4. Update all folder IDs in your configuration")
        
        print("\n⚠️  **Important Notes:**")
        print("   - Old folders still exist but are owned by flagged account")
        print("   - Google may have restricted access to prevent abuse")
        print("   - Manual intervention is likely required")
        print("   - Consider this an opportunity to clean up old data")
        
        print("\n🎯 **Next Actions:**")
        print("   1. Run this script to get current status")
        print("   2. Check hotdurham@gmail.com 'Shared with me'")
        print("   3. Document what you find")
        print("   4. Decide whether to recover or recreate")
        print("   5. Update all configuration files with new folder IDs")

def main():
    print("🔧 Old Folder Recovery Tool")
    print("="*50)
    
    recovery = OldFolderRecovery()
    
    if not recovery.authenticate():
        print("❌ Cannot proceed without authentication")
        return
    
    print("\n🔍 Generating recovery report...")
    report = recovery.generate_recovery_report()
    
    # Print summary
    print("\n📊 RECOVERY REPORT SUMMARY")
    print("="*50)
    
    total_found = 0
    for pattern, results in report["search_results"].items():
        count = results["exact_matches"] + results["partial_matches"]
        if count > 0:
            print(f"📂 {pattern}: {count} folders found")
            total_found += count
    
    shared_count = report["shared_with_main_user"]["count"]
    print(f"📧 Shared with main user: {shared_count} folders")
    
    if total_found == 0 and shared_count == 0:
        print("\n⚠️  **NO OLD FOLDERS FOUND**")
        print("   This confirms that the old folders are not accessible")
        print("   through the new service account. Manual recovery needed.")
    
    # Save detailed report
    report_file = f"recovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n💾 Detailed report saved to: {report_file}")
    
    # Print recovery guide
    recovery.print_recovery_guide()

if __name__ == "__main__":
    main()
