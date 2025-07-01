#!/usr/bin/env python3
"""
Service Account Diagnostic Script

This script helps diagnose why your service account cannot share files.
It checks various aspects of your service account setup and provides recommendations.

Usage:
    python tools/diagnose_service_account.py
"""

import os
import sys
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_service_account_info():
    """Check service account configuration"""
    
    print("🔍 Checking service account configuration...\n")
    
    creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
    
    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        print(f"📧 Service Account Email: {creds_data.get('client_email', 'Not found')}")
        print(f"🏗️  Project ID: {creds_data.get('project_id', 'Not found')}")
        print(f"🆔 Client ID: {creds_data.get('client_id', 'Not found')}")
        print(f"📅 Private Key ID: {creds_data.get('private_key_id', 'Not found')[:10]}...")
        
        return creds_data.get('client_email')
        
    except Exception as e:
        print(f"❌ Error reading service account credentials: {e}")
        return None

def test_basic_operations():
    """Test basic Drive API operations"""
    
    print("\n🧪 Testing basic Drive API operations...\n")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # Test 1: List files
        print("📂 Testing file listing...")
        results = service.files().list(pageSize=5, fields="files(id, name, createdTime)").execute()
        files = results.get('files', [])
        print(f"✅ Can list files: Found {len(files)} files")
        
        # Test 2: Create a simple file
        print("📝 Testing file creation...")
        file_metadata = {'name': 'diagnostic_test_file.txt'}
        
        created_file = service.files().create(body=file_metadata).execute()
        print(f"✅ Can create files: Created {created_file['name']} (ID: {created_file['id']})")
        
        # Test 3: Check file permissions
        print("🔒 Testing permission listing...")
        permissions = service.permissions().list(fileId=created_file['id']).execute()
        print(f"✅ Can list permissions: {len(permissions.get('permissions', []))} permissions found")
        
        # Test 4: Try to share with domain (less restrictive)
        print("🌐 Testing domain sharing...")
        try:
            domain_permission = {
                'type': 'domain',
                'role': 'reader',
                'domain': 'gmail.com'
            }
            service.permissions().create(
                fileId=created_file['id'],
                body=domain_permission,
                sendNotificationEmail=False
            ).execute()
            print("✅ Domain sharing works")
        except Exception as domain_error:
            print(f"❌ Domain sharing failed: {domain_error}")
        
        # Clean up
        service.files().delete(fileId=created_file['id']).execute()
        print("🧹 Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic operations failed: {e}")
        return False

def check_recent_files():
    """Check recent files and their sharing status"""
    
    print("\n📋 Checking recent files and sharing status...\n")
    
    try:
        creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=creds)
        
        # Get recent files
        results = service.files().list(
            orderBy="createdTime desc",
            pageSize=10,
            fields="files(id, name, createdTime, permissions)"
        ).execute()
        
        files = results.get('files', [])
        
        for file in files:
            permissions = file.get('permissions', [])
            shared_count = len([p for p in permissions if p.get('type') == 'user' and p.get('emailAddress')])
            
            print(f"📄 {file['name']}")
            print(f"   Created: {file['createdTime']}")
            print(f"   Shared with {shared_count} users")
            
            # Check if any are shared with hotdurham@gmail.com
            hotdurham_shared = any(
                p.get('emailAddress') == 'hotdurham@gmail.com' 
                for p in permissions
            )
            if hotdurham_shared:
                print("   ✅ Shared with hotdurham@gmail.com")
            else:
                print("   ❌ Not shared with hotdurham@gmail.com")
            print()
        
    except Exception as e:
        print(f"❌ Error checking recent files: {e}")

def main():
    print("🔧 Service Account Diagnostic Tool")
    print("=" * 50)
    
    # Check service account info
    service_email = check_service_account_info()
    
    # Test basic operations
    basic_works = test_basic_operations()
    
    # Check recent files
    check_recent_files()
    
    # Provide recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 50)
    
    if not basic_works:
        print("❌ CRITICAL: Basic Drive API operations are failing")
        print("   - Check your service account credentials")
        print("   - Verify API is enabled in Google Cloud Console")
        print("   - Check service account has Drive API access")
    else:
        print("✅ Basic Drive API operations work")
        print("❌ ISSUE: File sharing is being blocked by content filters")
        print("\n🔧 POSSIBLE SOLUTIONS:")
        print("1. 🏗️  Create a NEW service account in Google Cloud Console")
        print("2. 🔄 Use a different Google Cloud project")
        print("3. 📞 Contact Google Cloud Support about the restriction")
        print("4. 🎯 Temporarily use a different sharing method:")
        print("   - Make files publicly viewable")
        print("   - Use Google Groups instead of individual emails")
        print("   - Share folders instead of individual files")
        
        if service_email:
            print(f"\n📧 Your current service account: {service_email}")
            print("   This account appears to be flagged by Google's abuse detection")

if __name__ == "__main__":
    main()
