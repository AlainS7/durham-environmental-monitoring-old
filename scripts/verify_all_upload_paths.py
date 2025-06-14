#!/usr/bin/env python3
"""
Final Verification: Check All Visualization Upload Paths
"""

import json
from pathlib import Path

def verify_upload_paths():
    """Verify all upload paths use the new folder structure"""
    
    project_root = Path(__file__).parent.parent
    issues_found = []
    
    # Check main upload summary
    summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        upload_folder = data.get('upload_info', {}).get('upload_folder', '')
        if '/Visualizations/' in upload_folder:
            issues_found.append(f"Upload summary still uses old path: {upload_folder}")
        else:
            print(f"✅ Upload summary uses correct path: {upload_folder}")
    
    # Check enhanced upload summaries
    enhanced_dir = project_root / 'sensor_visualizations' / 'enhanced_production_sensors'
    if enhanced_dir.exists():
        for summary_file in enhanced_dir.glob('ENHANCED_UPLOAD_SUMMARY_*.txt'):
            with open(summary_file, 'r') as f:
                content = f.read()
            
            if '/Visualizations/' in content:
                issues_found.append(f"Enhanced summary has old paths: {summary_file.name}")
            else:
                print(f"✅ Enhanced summary paths correct: {summary_file.name}")
    
    if issues_found:
        print(f"\n❌ ISSUES FOUND:")
        for issue in issues_found:
            print(f"   • {issue}")
        return False
    else:
        print(f"\n🎉 ALL PATHS VERIFIED CORRECT!")
        return True

if __name__ == "__main__":
    verify_upload_paths()
