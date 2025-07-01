#!/usr/bin/env python3
"""
Google Drive Sharing Restoration Script

This script helps restore sharing permissions for files that were uploaded by your
service account but are no longer visible to hotdurham@gmail.com. It will:

1. List all files owned by the service account
2. Re-share them with hotdurham@gmail.com
3. Provide a summary of what was shared

Usage:
    python tools/restore_drive_sharing.py
"""

import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def restore_drive_sharing():
    """Main function to restore sharing permissions"""
    
    # Load service account credentials
    creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
    if not os.path.exists(creds_path):
        print(f"❌ Error: Could not find credentials at {creds_path}")
        return
    
    try:
        creds = Credentials.from_service_account_file(
            creds_path, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        print("✅ Successfully authenticated with Google Drive API")
    except Exception as e:
        print(f"❌ Error authenticating with Google Drive: {e}")
        return

    # Email to share with
    share_email = 'hotdurham@gmail.com'
    
    try:
        # Get all files owned by the service account
        print("🔍 Searching for files owned by service account...")
        
        files_processed = 0
        files_shared = 0
        files_already_shared = 0
        page_token = None
        
        while True:
            # List files in batches
            results = service.files().list(
                q="'me' in owners",
                fields="nextPageToken, files(id, name, mimeType, createdTime, permissions)",
                pageSize=100,
                pageToken=page_token
            ).execute()
            
            files = results.get('files', [])
            page_token = results.get('nextPageToken')
            
            if not files:
                break
                
            for file in files:
                files_processed += 1
                file_id = file['id']
                file_name = file['name']
                
                # Check if already shared with the target email
                permissions = file.get('permissions', [])
                already_shared = any(
                    perm.get('emailAddress') == share_email 
                    for perm in permissions
                )
                
                if already_shared:
                    files_already_shared += 1
                    print(f"⏭️  Already shared: {file_name}")
                    continue
                
                try:
                    # Share the file
                    permission = {
                        'type': 'user',
                        'role': 'writer',
                        'emailAddress': share_email
                    }
                    
                    service.permissions().create(
                        fileId=file_id,
                        body=permission,
                        sendNotificationEmail=False
                    ).execute()
                    
                    files_shared += 1
                    print(f"✅ Shared: {file_name}")
                    
                except Exception as e:
                    print(f"❌ Failed to share {file_name}: {e}")
            
            if not page_token:
                break
        
        # Summary
        print("\n" + "="*50)
        print("📊 SHARING RESTORATION SUMMARY")
        print("="*50)
        print(f"📁 Total files processed: {files_processed}")
        print(f"✅ Files newly shared: {files_shared}")
        print(f"⏭️  Files already shared: {files_already_shared}")
        print(f"👤 Shared with: {share_email}")
        
        if files_shared > 0:
            print(f"\n🎉 Successfully restored sharing for {files_shared} files!")
        else:
            print(f"\n✨ All files were already shared with {share_email}")
            
    except Exception as e:
        print(f"❌ Error during file sharing process: {e}")

def list_recent_files():
    """List recent files to verify sharing is working"""
    
    creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
    creds = Credentials.from_service_account_file(
        creds_path, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    service = build('drive', 'v3', credentials=creds)
    
    print("\n🔍 Recent files (last 10):")
    results = service.files().list(
        q="'me' in owners",
        orderBy="createdTime desc",
        fields="files(id, name, createdTime, permissions)",
        pageSize=10
    ).execute()
    
    files = results.get('files', [])
    for file in files:
        permissions = file.get('permissions', [])
        shared_with_target = any(
            perm.get('emailAddress') == 'hotdurham@gmail.com' 
            for perm in permissions
        )
        status = "✅ Shared" if shared_with_target else "❌ Not shared"
        print(f"  {status}: {file['name']} ({file['createdTime']})")

if __name__ == "__main__":
    print("🔧 Google Drive Sharing Restoration Tool")
    print("This will restore sharing permissions for hotdurham@gmail.com\n")
    
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        restore_drive_sharing()
        
        # Optionally show recent files
        show_recent = input("\nShow recent files status? (y/N): ").strip().lower()
        if show_recent in ['y', 'yes']:
            list_recent_files()
    else:
        print("Operation cancelled.")
