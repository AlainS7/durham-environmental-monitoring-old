#!/usr/bin/env python3
"""
Google Drive Folder Access Checker

This script checks what folders and files your service account can access,
and specifically looks for any folders that should be shared with hotdurham@gmail.com.

Usage:
    python tools/check_drive_access.py
"""

import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_folders_and_sharing():
    """Check all folders and their sharing status"""
    
    print("🔍 Checking Google Drive folders and sharing...\n")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # Search for folders
        print("📁 Searching for folders...")
        folder_results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name, createdTime, permissions, parents)",
            pageSize=50
        ).execute()
        
        folders = folder_results.get('files', [])
        
        if not folders:
            print("❌ No folders found owned by this service account")
            return
        
        print(f"Found {len(folders)} folders:\n")
        
        hotdurham_shared_folders = []
        
        for folder in folders:
            folder_name = folder['name']
            folder_id = folder['id']
            created = folder.get('createdTime', 'Unknown')
            
            print(f"📂 {folder_name}")
            print(f"   ID: {folder_id}")
            print(f"   Created: {created}")
            
            # Check permissions
            try:
                permissions = service.permissions().list(fileId=folder_id).execute()
                perm_list = permissions.get('permissions', [])
                
                # Check if shared with hotdurham@gmail.com
                hotdurham_access = False
                user_shares = []
                
                for perm in perm_list:
                    if perm.get('emailAddress') == 'hotdurham@gmail.com':
                        hotdurham_access = True
                        hotdurham_shared_folders.append({
                            'name': folder_name,
                            'id': folder_id,
                            'role': perm.get('role', 'Unknown')
                        })
                    elif perm.get('type') == 'user' and perm.get('emailAddress'):
                        user_shares.append(f"{perm.get('emailAddress')} ({perm.get('role')})")
                
                if hotdurham_access:
                    print("   ✅ Shared with hotdurham@gmail.com")
                else:
                    print("   ❌ NOT shared with hotdurham@gmail.com")
                
                if user_shares:
                    print(f"   👥 Other shares: {', '.join(user_shares)}")
                else:
                    print("   👥 No other user shares")
                    
            except Exception as perm_error:
                print(f"   ⚠️ Could not check permissions: {perm_error}")
            
            print()
        
        # Summary
        print("="*50)
        print("📊 SUMMARY")
        print("="*50)
        
        if hotdurham_shared_folders:
            print(f"✅ Found {len(hotdurham_shared_folders)} folders shared with hotdurham@gmail.com:")
            for folder in hotdurham_shared_folders:
                print(f"   📂 {folder['name']} (Role: {folder['role']})")
                print(f"      🔗 https://drive.google.com/drive/folders/{folder['id']}")
        else:
            print("❌ No folders are currently shared with hotdurham@gmail.com")
            print("\n💡 This means:")
            print("   - The folder may have been created by the old service account")
            print("   - You may need to manually share existing folders")
            print("   - Or create a new shared folder with the new service account")
        
        return hotdurham_shared_folders
        
    except Exception as e:
        print(f"❌ Error checking folders: {e}")
        return []

def check_recent_files():
    """Check recent files to see what the service account has been creating"""
    
    print("\n🔍 Checking recent files...\n")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # Get recent files (not folders)
        results = service.files().list(
            q="mimeType!='application/vnd.google-apps.folder'",
            orderBy="createdTime desc",
            pageSize=10,
            fields="files(id, name, createdTime, mimeType, parents)"
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            print(f"📄 Recent files ({len(files)} shown):")
            for file in files:
                print(f"   • {file['name']} ({file.get('createdTime', 'Unknown')})")
                if file.get('parents'):
                    print(f"     📁 In folder ID: {file['parents'][0]}")
        else:
            print("📄 No recent files found")
            
    except Exception as e:
        print(f"❌ Error checking files: {e}")

def suggest_solutions():
    """Suggest solutions for missing folder access"""
    
    print("\n💡 SOLUTIONS")
    print("="*50)
    print("If you don't see your shared folder:")
    print()
    print("1. 🔄 **Create a new shared folder:**")
    print("   - The old folder was owned by your previous service account")
    print("   - Create a new folder with your new service account")
    print("   - Share it with hotdurham@gmail.com")
    print()
    print("2. 🔍 **Search for the old folder:**")
    print("   - Log into hotdurham@gmail.com Google Drive")
    print("   - Look for folders shared with you")
    print("   - The old folder should still be there")
    print()
    print("3. 🔗 **Manually share the old folder:**")
    print("   - If you can access the old service account")
    print("   - Find the folder and share it with the new service account")
    print()
    print("4. 🆕 **Start fresh:**")
    print("   - Create a new project folder structure")
    print("   - Use the new service account for all future uploads")

def main():
    print("🔧 Google Drive Folder Access Checker")
    print("="*50)
    
    # Check folders and sharing
    shared_folders = check_folders_and_sharing()
    
    # Check recent files
    check_recent_files()
    
    # Provide solutions if no shared folders found
    if not shared_folders:
        suggest_solutions()

if __name__ == "__main__":
    main()
