#!/usr/bin/env python3
"""
Search for Old Project Folders

This script helps you search for folders from your old service account that may
still exist but aren't accessible through the new service account. It will also
provide strategies to recover them.

Usage:
    python tools/search_old_folders.py
"""

import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def search_for_old_patterns():
    """Search for folders that might match old naming patterns"""
    
    print("🔍 Searching for folders with old naming patterns...\n")
    
    # Common patterns that might exist in old folders
    search_patterns = [
        "pdf",
        "test",
        "cluster",
        "data",
        "sensor",
        "hot",
        "durham",
        "generated",
        "report",
        "analysis"
    ]
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        found_folders = []
        
        for pattern in search_patterns:
            print(f"🔍 Searching for folders containing '{pattern}'...")
            
            try:
                # Search for folders with this pattern
                query = f"mimeType='application/vnd.google-apps.folder' and name contains '{pattern}'"
                results = service.files().list(
                    q=query,
                    fields="files(id, name, createdTime, owners)",
                    pageSize=20
                ).execute()
                
                folders = results.get('files', [])
                
                if folders:
                    print(f"   Found {len(folders)} folders:")
                    for folder in folders:
                        folder_info = {
                            'name': folder['name'],
                            'id': folder['id'],
                            'created': folder.get('createdTime', 'Unknown'),
                            'owners': folder.get('owners', [])
                        }
                        found_folders.append(folder_info)
                        
                        owner_emails = [owner.get('emailAddress', 'Unknown') for owner in folder_info['owners']]
                        print(f"      📂 {folder['name']} ({folder.get('createdTime', 'Unknown')})")
                        print(f"         Owners: {', '.join(owner_emails)}")
                else:
                    print(f"   No folders found with '{pattern}'")
                    
            except Exception as e:
                print(f"   ❌ Error searching for '{pattern}': {e}")
            
            print()
        
        return found_folders
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return []

def check_shared_with_hotdurham():
    """Check what folders are currently shared with hotdurham@gmail.com"""
    
    print("📧 Checking folders shared with hotdurham@gmail.com...\n")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # Search for folders where hotdurham@gmail.com has access
        # Note: This only shows folders owned by this service account
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name, createdTime, permissions)",
            pageSize=50
        ).execute()
        
        folders = results.get('files', [])
        shared_folders = []
        
        for folder in folders:
            # Check if shared with hotdurham@gmail.com
            try:
                permissions = service.permissions().list(fileId=folder['id']).execute()
                perm_list = permissions.get('permissions', [])
                
                hotdurham_has_access = any(
                    perm.get('emailAddress') == 'hotdurham@gmail.com' 
                    for perm in perm_list
                )
                
                if hotdurham_has_access:
                    shared_folders.append(folder)
                    
            except Exception:
                pass  # Skip if can't check permissions
        
        print(f"📊 Currently shared folders: {len(shared_folders)}")
        for folder in shared_folders:
            print(f"   📂 {folder['name']}")
        
        return shared_folders
        
    except Exception as e:
        print(f"❌ Error checking shared folders: {e}")
        return []

def provide_recovery_instructions():
    """Provide instructions for recovering old folders"""
    
    print("\n💡 RECOVERY STRATEGIES")
    print("="*60)
    
    print("🔍 **1. Search in hotdurham@gmail.com Google Drive:**")
    print("   - Log into https://drive.google.com with hotdurham@gmail.com")
    print("   - Go to 'Shared with me' section")
    print("   - Look for old folders shared by your previous service account")
    print("   - Search for: 'testdataclusters', 'pdf', 'generated'")
    print()
    
    print("📧 **2. Check your old service account email:**")
    print("   - Old service account: hot-durham-data@hot-durham-data.iam.gserviceaccount.com")
    print("   - Those folders still exist, but aren't accessible via API due to flagging")
    print()
    
    print("🔄 **3. Manual recovery options:**")
    print("   a) If you can still access Google Cloud Console:")
    print("      - Try to create a new key for the old service account")
    print("      - Use it temporarily to share folders with the new account")
    print()
    print("   b) Contact Google Cloud Support:")
    print("      - Explain the situation about the flagged service account")
    print("      - Request help recovering access to existing folders")
    print()
    print("   c) Re-create missing folders:")
    print("      - Create new 'testdataclusters' and 'generated_pdfs' folders")
    print("      - Re-run any scripts that generate PDFs or analysis")
    print()
    
    print("🎯 **4. Specific folders you mentioned:**")
    print("   - 'testdataclusters' or similar: Look for test/cluster analysis folders")
    print("   - 'generated PDFs': Look for folders containing PDF reports")
    print("   - These were likely created months ago by the old service account")
    print()
    
    print("🚨 **Important:** The old folders still exist in Google Drive,")
    print("    but they're owned by the flagged service account.")

def main():
    print("🔧 Search for Old Project Folders")
    print("="*50)
    
    # Search for folders with common patterns
    found_folders = search_for_old_patterns()
    
    # Check what's currently shared
    shared_folders = check_shared_with_hotdurham()
    
    # Summary
    print("\n📊 SEARCH RESULTS SUMMARY")
    print("="*50)
    
    if found_folders:
        print(f"🔍 Found {len(found_folders)} folders matching search patterns")
        print("   (Note: These are owned by the current service account)")
    else:
        print("🔍 No folders found matching old naming patterns")
        print("   This confirms old folders are from the previous service account")
    
    print(f"📧 Currently shared with hotdurham@gmail.com: {len(shared_folders)} folders")
    
    # Provide recovery instructions
    provide_recovery_instructions()
    
    print("\n🎯 **Next Steps:**")
    print("1. Check hotdurham@gmail.com Google Drive 'Shared with me'")
    print("2. Search for the specific folder names you remember")
    print("3. If not found, the folders need manual recovery or recreation")

if __name__ == "__main__":
    main()
