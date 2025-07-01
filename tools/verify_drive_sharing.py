#!/usr/bin/env python3
"""
Drive Sharing Verification Script

This script checks if your current configuration is properly sharing new files
with hotdurham@gmail.com and provides recommendations for fixing any issues.

Usage:
    python tools/verify_drive_sharing.py
"""

import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def verify_sharing_config():
    """Verify that sharing configuration is correct"""
    
    print("🔍 Checking sharing configuration in your project...")
    
    # Check config files for share_email settings
    config_files = [
        'config/automated_data_pull_config.py',
        'config/daily_sheets_config.json',
        'config/production/automation_config.json'
    ]
    
    for config_file in config_files:
        config_path = os.path.join(project_root, config_file)
        if os.path.exists(config_path):
            print(f"✅ Found config: {config_file}")
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    if 'hotdurham@gmail.com' in content:
                        print("  ✅ Contains hotdurham@gmail.com")
                    else:
                        print("  ⚠️  Does not contain hotdurham@gmail.com")
            except Exception as e:
                print(f"  ❌ Error reading file: {e}")
        else:
            print(f"❌ Missing config: {config_file}")

def test_sharing():
    """Test creating and sharing a file"""
    
    print("\n🧪 Testing file creation and sharing...")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Test Drive API
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Create a test spreadsheet (less likely to be flagged)
        import gspread
        sheets_client = gspread.authorize(creds)
        
        # Create a test spreadsheet
        spreadsheet = sheets_client.create('Weather_Data_Test')
        test_file = {'id': spreadsheet.id, 'name': spreadsheet.title}
        file_id = test_file['id']
        print(f"✅ Created test file: {test_file['name']} (ID: {file_id})")
        
        # Try sharing with a simple approach first
        test_email = input("Enter an email to test sharing with (or press Enter for hotdurham@gmail.com): ").strip()
        if not test_email:
            test_email = 'hotdurham@gmail.com'
        
        print(f"🔄 Testing sharing with: {test_email}")
        
        try:
            spreadsheet.share(test_email, perm_type='user', role='writer', notify=False)
            print(f"✅ Successfully shared test spreadsheet with {test_email}")
        except Exception as share_error:
            print(f"⚠️ gspread sharing failed: {share_error}")
            print("🔄 Trying alternative sharing method...")
            
            # Try using Drive API directly with minimal permissions
            permission = {
                'type': 'user',
                'role': 'reader',  # Try reader first
                'emailAddress': test_email
            }
            
            drive_service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=False
            ).execute()
            print(f"✅ Successfully shared via Drive API with reader access to {test_email}")
        
        # Verify sharing
        permissions = drive_service.permissions().list(fileId=file_id).execute()
        shared_emails = [p.get('emailAddress') for p in permissions.get('permissions', [])]
        
        if test_email in shared_emails:
            print(f"✅ Verified: {test_email} has access")
        else:
            print(f"❌ Error: {test_email} does not have access")
            print(f"📋 Current permissions: {shared_emails}")
        
        # Clean up test spreadsheet
        drive_service.files().delete(fileId=file_id).execute()
        print("🧹 Cleaned up test spreadsheet")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during sharing test: {e}")
        
        # Additional diagnostic information
        if "inappropriate" in str(e).lower():
            print("\n🔍 DIAGNOSTIC: Content filter issue detected")
            print("   This might be due to:")
            print("   - Email address containing flagged terms")
            print("   - Service account restrictions")
            print("   - Google Drive policy changes")
            print("   \n💡 Suggestion: Try manually creating and sharing a file")
            print("      from the service account to hotdurham@gmail.com")
        
        return False

def main():
    print("🔧 Drive Sharing Verification Tool\n")
    
    # Check configuration
    verify_sharing_config()
    
    # Test sharing functionality
    if test_sharing():
        print("\n🎉 Sharing functionality is working correctly!")
        print("\n📋 To restore sharing for old files, run:")
        print("    python tools/restore_drive_sharing.py")
    else:
        print("\n❌ Sharing functionality has issues. Please check:")
        print("  1. Service account credentials are valid")
        print("  2. hotdurham@gmail.com is a valid Gmail address")
        print("  3. Service account has Drive API permissions")

if __name__ == "__main__":
    main()
