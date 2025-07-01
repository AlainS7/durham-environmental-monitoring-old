#!/usr/bin/env python3
"""
Share All Folders Script

This script shares all folders owned by the service account with hotdurham@gmail.com
so you can access them from your personal Google Drive.

Usage:
    python tools/share_all_folders.py
"""

import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def share_all_folders():
    """Share all service account folders with hotdurham@gmail.com"""
    
    print("🔄 Sharing all folders with hotdurham@gmail.com...\n")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # Get all folders
        folder_results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)",
            pageSize=50
        ).execute()
        
        folders = folder_results.get('files', [])
        
        if not folders:
            print("❌ No folders found to share")
            return
        
        shared_count = 0
        failed_count = 0
        
        for folder in folders:
            folder_name = folder['name']
            folder_id = folder['id']
            
            try:
                # Share with hotdurham@gmail.com as editor
                permission = {
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': 'hotdurham@gmail.com'
                }
                
                service.permissions().create(
                    fileId=folder_id,
                    body=permission,
                    sendNotificationEmail=True  # Send notification so you know it's shared
                ).execute()
                
                shared_count += 1
                print(f"✅ Shared: {folder_name}")
                print(f"   🔗 https://drive.google.com/drive/folders/{folder_id}")
                
            except Exception as e:
                failed_count += 1
                print(f"❌ Failed to share {folder_name}: {e}")
        
        # Summary
        print("\n" + "="*50)
        print("📊 SHARING SUMMARY")
        print("="*50)
        print(f"✅ Successfully shared: {shared_count} folders")
        print(f"❌ Failed to share: {failed_count} folders")
        print("📧 Shared with: hotdurham@gmail.com")
        
        if shared_count > 0:
            print(f"\n🎉 Success! You should now see {shared_count} folders in your Google Drive.")
            print("📬 Check your email for sharing notifications.")
            print("\n📂 Folders shared:")
            
            # List the folders again to show what was shared
            for folder in folders:
                print(f"   • {folder['name']}")
        
        return shared_count > 0
        
    except Exception as e:
        print(f"❌ Error sharing folders: {e}")
        return False

def main():
    print("🔧 Share All Folders Tool")
    print("="*50)
    print("This will share all service account folders with hotdurham@gmail.com\n")
    
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Operation cancelled.")
        return
    
    success = share_all_folders()
    
    if success:
        print("\n🎉 All done! Check your hotdurham@gmail.com Google Drive.")
        print("The folders should appear in 'Shared with me' section.")
    else:
        print("\n❌ No folders were shared. Please check the error messages above.")

if __name__ == "__main__":
    main()
