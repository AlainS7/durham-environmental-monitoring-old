#!/usr/bin/env python3
"""
Extract folder names from the recovery report
"""

import json
import sys

def extract_folder_names(report_file):
    """Extract and print folder names from the recovery report."""
    try:
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        shared_folders = report.get('shared_with_main_user', {}).get('folders', [])
        
        print(f"📂 Found {len(shared_folders)} files/folders shared with hotdurham@gmail.com")
        print("="*60)
        
        folders = []
        files = []
        
        for item in shared_folders:
            name = item.get('name', 'Unknown')
            item_id = item.get('id', 'Unknown')
            created = item.get('createdTime', 'Unknown')
            
            # Check if it's likely a folder (no file extension or specific patterns)
            if ('.' not in name or 
                name.endswith('_folder') or 
                'cluster' in name.lower() or 
                'pdf' in name.lower() or
                'analysis' in name.lower() or
                'test' in name.lower()):
                folders.append((name, item_id, created))
            else:
                files.append((name, item_id, created))
        
        print(f"📁 FOLDERS ({len(folders)}):")
        for name, item_id, created in folders:
            print(f"   📂 {name}")
            print(f"      ID: {item_id}")
            print(f"      Created: {created}")
            print()
        
        print(f"📄 FILES ({len(files)}):")
        for name, item_id, created in files[:10]:  # Show first 10 files
            print(f"   📄 {name}")
            print(f"      ID: {item_id}")
            print(f"      Created: {created}")
            print()
        
        if len(files) > 10:
            print(f"   ... and {len(files) - 10} more files")
        
        # Look for specific patterns
        print("\n🔍 SEARCHING FOR SPECIFIC PATTERNS:")
        patterns = ['test', 'cluster', 'pdf', 'analysis', 'generated', 'sensor', 'weather']
        
        for pattern in patterns:
            matches = [item for item in shared_folders if pattern.lower() in item.get('name', '').lower()]
            if matches:
                print(f"   🎯 '{pattern}': {len(matches)} matches")
                for match in matches[:3]:  # Show first 3 matches
                    print(f"      - {match.get('name', 'Unknown')}")
                if len(matches) > 3:
                    print(f"      ... and {len(matches) - 3} more")
            else:
                print(f"   ❌ '{pattern}': No matches")
        
        return folders, files
        
    except Exception as e:
        print(f"❌ Error reading report: {e}")
        return [], []

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_folder_names.py <report_file>")
        sys.exit(1)
    
    report_file = sys.argv[1]
    folders, files = extract_folder_names(report_file)
    
    print("\n📊 SUMMARY:")
    print(f"   📁 Folders: {len(folders)}")
    print(f"   📄 Files: {len(files)}")
    print(f"   🔗 Total shared items: {len(folders) + len(files)}")

if __name__ == "__main__":
    main()
