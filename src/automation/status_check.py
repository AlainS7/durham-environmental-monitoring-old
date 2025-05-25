#!/usr/bin/env python3
"""
Hot Durham Data Management - System Status Check

This script provides a quick overview of the data management system status,
recent activity, and any issues that need attention.

Usage:
    python status_check.py [--detailed] [--days N]
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import json

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, 'scripts'))

from data_manager import DataManager

def format_file_size(size_mb):
    """Format file size in human readable format"""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    elif size_mb < 1024:
        return f"{size_mb:.1f} MB"
    else:
        return f"{size_mb / 1024:.1f} GB"

def format_date(date_obj):
    """Format datetime object for display"""
    if date_obj is None:
        return "Never"
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')
        except:
            return date_obj
    return date_obj.strftime('%Y-%m-%d %H:%M')

def check_cron_status():
    """Check if cron jobs are set up"""
    try:
        import subprocess
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            cron_content = result.stdout
            hot_durham_jobs = [line for line in cron_content.split('\n') if 'Hot Durham' in line or 'automated_data_pull' in line]
            return len(hot_durham_jobs), hot_durham_jobs
        else:
            return 0, []
    except Exception:
        return -1, ["Error checking cron status"]

def check_credentials():
    """Check if all required credential files exist"""
    creds_path = os.path.join(project_root, 'creds')
    required_files = ['google_creds.json', 'tsi_creds.json', 'wu_api_key.json']
    
    status = {}
    for file in required_files:
        file_path = os.path.join(creds_path, file)
        status[file] = os.path.exists(file_path)
    
    return status

def main():
    parser = argparse.ArgumentParser(description='Check Hot Durham data management system status')
    parser.add_argument('--detailed', action='store_true', help='Show detailed information')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back for activity (default: 7)')
    
    args = parser.parse_args()
    
    print("🔍 Hot Durham Data Management - System Status")
    print("=" * 50)
    print(f"📅 Status check at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize data manager
    try:
        dm = DataManager(project_root)
        print("✅ Data manager initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing data manager: {e}")
        return 1
    
    # Check credentials
    print("\n🔐 Credentials Status:")
    creds_status = check_credentials()
    for file, exists in creds_status.items():
        status_icon = "✅" if exists else "❌"
        print(f"   {status_icon} {file}")
    
    missing_creds = [f for f, exists in creds_status.items() if not exists]
    if missing_creds:
        print(f"   ⚠️ Missing credentials: {', '.join(missing_creds)}")
    
    # Check cron status
    print("\n⏰ Automation Status:")
    cron_count, cron_jobs = check_cron_status()
    if cron_count == -1:
        print("   ❌ Error checking cron status")
    elif cron_count == 0:
        print("   ⚠️ No Hot Durham cron jobs found")
        print("   💡 Run ./setup_automation.sh to set up automated pulls")
    else:
        print(f"   ✅ {cron_count} cron job(s) configured")
        if args.detailed:
            for job in cron_jobs:
                if job.strip():
                    print(f"      {job.strip()}")
    
    # Get data summary
    print(f"\n📊 Data Activity (Last {args.days} days):")
    summary = dm.get_data_summary(days_back=args.days)
    
    print(f"   🌤️ Weather Underground pulls: {summary['wu_pulls']}")
    print(f"   🔬 TSI pulls: {summary['tsi_pulls']}")
    print(f"   📈 Total records collected: {summary['total_records']:,}")
    print(f"   📋 Google Sheets created: {summary['sheets_created']}")
    print(f"   🕐 Last pull: {format_date(summary['last_pull'])}")
    
    if summary['data_sources_active']:
        print(f"   🎯 Active sources: {', '.join(summary['data_sources_active'])}")
    else:
        print("   ⚠️ No recent data pulls detected")
    
    # Data integrity check
    print("\n💾 Data Storage Overview:")
    integrity_report = dm.verify_data_integrity()
    
    print(f"   📁 Total files: {integrity_report['total_files']}")
    print(f"   💿 Total size: {format_file_size(integrity_report['total_size_mb'])}")
    
    if integrity_report['date_range']:
        earliest = format_date(integrity_report['date_range']['earliest'])
        latest = format_date(integrity_report['date_range']['latest'])
        span = integrity_report['date_range']['span_days']
        print(f"   📅 Data span: {earliest} to {latest} ({span} days)")
    
    # Per-source breakdown
    if args.detailed:
        print("\n📂 Detailed Storage Breakdown:")
        for source, info in integrity_report['sources'].items():
            if info['files'] > 0:
                print(f"   {source.upper()}:")
                print(f"      Files: {info['files']}")
                print(f"      Size: {format_file_size(info['size_mb'])}")
                print(f"      Years: {', '.join(sorted(info['years']))}")
                print(f"      Range: {format_date(info['earliest_date'])} to {format_date(info['latest_date'])}")
    
    # Issues and warnings
    if integrity_report['issues']:
        print("\n⚠️ Issues Found:")
        for issue in integrity_report['issues']:
            print(f"   ❌ {issue}")
    
    # Check log files
    print("\n📋 Recent Log Activity:")
    logs_path = os.path.join(project_root, 'logs')
    if os.path.exists(logs_path):
        log_files = ['weekly_pull.log', 'monthly_pull.log', 'google_drive_sync.log']
        for log_file in log_files:
            log_path = os.path.join(logs_path, log_file)
            if os.path.exists(log_path):
                try:
                    mod_time = datetime.fromtimestamp(os.path.getmtime(log_path))
                    size = os.path.getsize(log_path)
                    print(f"   📄 {log_file}: {format_date(mod_time)} ({size} bytes)")
                except Exception:
                    print(f"   📄 {log_file}: Error reading file")
            else:
                print(f"   📄 {log_file}: Not found")
    else:
        print("   ⚠️ Logs directory not found")
    
    # System health summary
    print("\n🏥 System Health Summary:")
    
    health_score = 0
    max_score = 5
    
    # Check credentials (1 point)
    if all(creds_status.values()):
        print("   ✅ All credentials present")
        health_score += 1
    else:
        print("   ❌ Missing credentials")
    
    # Check automation (1 point)
    if cron_count > 0:
        print("   ✅ Automation configured")
        health_score += 1
    else:
        print("   ❌ No automation configured")
    
    # Check recent activity (1 point)
    if summary['wu_pulls'] > 0 or summary['tsi_pulls'] > 0:
        print("   ✅ Recent data pulls detected")
        health_score += 1
    else:
        print("   ❌ No recent activity")
    
    # Check data storage (1 point)
    if integrity_report['total_files'] > 0:
        print("   ✅ Data files present")
        health_score += 1
    else:
        print("   ❌ No data files found")
    
    # Check for issues (1 point)
    if not integrity_report['issues']:
        print("   ✅ No integrity issues found")
        health_score += 1
    else:
        print("   ❌ Data integrity issues detected")
    
    print(f"\n🎯 Overall Health Score: {health_score}/{max_score}")
    
    if health_score == max_score:
        print("   🎉 System is running perfectly!")
    elif health_score >= 3:
        print("   👍 System is mostly healthy")
    else:
        print("   ⚠️ System needs attention")
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    if missing_creds:
        print("   • Set up missing credentials in creds/ folder")
    
    if cron_count <= 0:
        print("   • Run ./setup_automation.sh to configure automated pulls")
    
    if summary['wu_pulls'] == 0 and summary['tsi_pulls'] == 0:
        print("   • Test data pulling with: python src/data_collection/automated_data_pull.py --weekly")
    
    if integrity_report['issues']:
        print("   • Fix data integrity issues listed above")
    
    # Cleanup suggestion
    temp_files = len([f for f in os.listdir(dm.temp_path) if os.path.isfile(os.path.join(dm.temp_path, f))]) if os.path.exists(dm.temp_path) else 0
    if temp_files > 10:
        print(f"   • Clean up {temp_files} temporary files with: dm.cleanup_temp_files()")
    
    print("\n✨ Status check complete!")
    return 0 if health_score >= 3 else 1

if __name__ == "__main__":
    sys.exit(main())
