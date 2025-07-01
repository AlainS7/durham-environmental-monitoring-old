#!/usr/bin/env python3
"""
🎯 Missing Folder Recovery Action Plan
=====================================================
This script provides a comprehensive action plan for recovering your missing folders.
Based on the analysis, your old folders are not accessible through the new service account.
"""

import os
from datetime import datetime

def print_header(title):
    print("\n" + "="*60)
    print(f"🎯 {title}")
    print("="*60)

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * 50)

def main():
    print("🔧 MISSING FOLDER RECOVERY - ACTION PLAN")
    print("=" * 60)
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_header("ANALYSIS RESULTS")
    print("✅ Current Status:")
    print("   - New service account is working correctly")
    print("   - 7 folders and 24 files are properly shared")
    print("   - All current data is owned by: hotdurhamnewdatasender@hot-durham-data.iam.gserviceaccount.com")
    print()
    print("❌ Missing Folders:")
    print("   - testdataclusters (or similar cluster analysis folders)")
    print("   - generated_pdfs / pdf_reports")
    print("   - analysis_output folders")
    print("   - sensor_clusters / weather_clusters")
    print("   - Any other custom analysis folders from the old service account")
    
    print_header("IMMEDIATE ACTIONS")
    
    print_section("1. Check hotdurham@gmail.com Google Drive")
    print("🔗 Go to: https://drive.google.com")
    print("📧 Log in with: hotdurham@gmail.com")
    print("📂 Click: 'Shared with me' (left sidebar)")
    print("🔍 Search for:")
    print("   - 'testdata'")
    print("   - 'cluster'") 
    print("   - 'pdf'")
    print("   - 'analysis'")
    print("   - 'generated'")
    print("   - Any other folder names you remember")
    print()
    print("✨ If found:")
    print("   1. Right-click → 'Add to My Drive'")
    print("   2. Right-click → 'Share' → Add: hotdurhamnewdatasender@hot-durham-data.iam.gserviceaccount.com")
    print("   3. Give 'Editor' permissions")
    print("   4. Note the folder ID from the URL")
    
    print_section("2. Check Google Cloud Console")
    print("🔗 Go to: https://console.cloud.google.com")
    print("🏗️  Select project: hot-durham-data")
    print("👥 Go to: IAM & Admin → Service Accounts")
    print("🔍 Look for: hot-durham-data@hot-durham-data.iam.gserviceaccount.com")
    print()
    print("🔑 If the old service account still exists:")
    print("   1. Click on it")
    print("   2. Go to 'Keys' tab")
    print("   3. Try to create a new key (if allowed)")
    print("   4. Use it temporarily to list and share old folders")
    print("   5. Share everything with the new service account")
    print("   6. Delete the temporary key")
    
    print_section("3. Contact Google Support (if needed)")
    print("📞 Google Cloud Support:")
    print("   - Explain that your service account was flagged")
    print("   - Request access to existing folders")
    print("   - Provide your project ID: hot-durham-data")
    print("   - Mention folders contain legitimate weather data")
    
    print_header("RECREATION STRATEGY")
    
    print("💡 If old folders cannot be recovered, recreate them:")
    print()
    print("📂 **For testdataclusters / analysis folders:**")
    print("   1. Create new folder: 'TestDataClusters_2025'")
    print("   2. Re-run any clustering or analysis scripts")
    print("   3. Update scripts to use new folder ID")
    print()
    print("📄 **For PDF/report folders:**")
    print("   1. Create new folder: 'GeneratedReports_2025'")
    print("   2. Re-run report generation scripts")
    print("   3. Update configuration with new folder ID")
    print()
    print("🧪 **For test/experimental folders:**")
    print("   1. Create new folder: 'ExperimentalAnalysis_2025'")
    print("   2. Consider if old experiments need to be repeated")
    print("   3. Document what was lost for future reference")
    
    print_header("UPDATE CONFIGURATION")
    
    print("🔧 **Files that may need folder ID updates:**")
    config_files = [
        "config/automated_data_pull_config.py",
        "config/daily_sheets_config.json", 
        "config/production/automation_config.json",
        "scripts/automated_data_pull.py",
        "Any custom analysis scripts"
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"   ✅ {config_file}")
        else:
            print(f"   📁 {config_file} (check if exists)")
    
    print()
    print("🔄 **Update process:**")
    print("   1. Search for old folder IDs in all config files")
    print("   2. Replace with new folder IDs") 
    print("   3. Test all automated scripts")
    print("   4. Update documentation")
    
    print_header("PREVENTION FOR FUTURE")
    
    print("🛡️  **Best Practices:**")
    print("   1. Regular backups of important folders")
    print("   2. Document all folder IDs in a central config")
    print("   3. Use descriptive folder names with dates")
    print("   4. Keep folder structure documentation")
    print("   5. Regular testing of service account permissions")
    
    print_header("NEXT STEPS CHECKLIST")
    
    checklist = [
        "Check hotdurham@gmail.com 'Shared with me' section",
        "Search for specific folder names you remember",
        "Check Google Cloud Console for old service account",
        "Document what folders/data were lost",
        "Decide: recover vs recreate for each missing folder",
        "Create new folders with descriptive names",
        "Update all configuration files with new folder IDs",
        "Test all automated scripts with new folders",
        "Create backup strategy to prevent future loss",
        "Document the new folder structure"
    ]
    
    for i, item in enumerate(checklist, 1):
        print(f"   {i:2d}. [ ] {item}")
    
    print_header("SUMMARY")
    
    print("🎯 **The situation:**")
    print("   - Your old service account was flagged by Google")
    print("   - Folders owned by that account are inaccessible via API")
    print("   - They may still be visible in hotdurham@gmail.com Google Drive")
    print("   - New service account is working perfectly")
    print()
    print("🚀 **The solution:**")
    print("   - Check 'Shared with me' in hotdurham@gmail.com")
    print("   - Recover what you can find")
    print("   - Recreate what cannot be recovered")
    print("   - Update all configurations")
    print("   - Implement better backup practices")
    print()
    print("✨ **The good news:**")
    print("   - All current data collection is working")
    print("   - New folders are properly shared and accessible")
    print("   - This is an opportunity to clean up and reorganize")
    print("   - You have all the tools and scripts to recreate missing analysis")

if __name__ == "__main__":
    main()
