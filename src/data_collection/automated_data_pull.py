#!/usr/bin/env python3
"""
Automated Data Pull Script for Hot Durham Project

This script can be run on a schedule (e.g., via cron) to automatically pull
data from Weather Underground and TSI sources, organize it, and sync to Google Drive.

Usage:
    python automated_data_pull.py [--weekly|--bi-weekly|--monthly] [--wu-only|--tsi-only]
    
Examples:
    python automated_data_pull.py --weekly          # Pull last week's data
    python automated_data_pull.py --monthly --wu-only  # Pull last month's WU data only
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import json

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(project_root, 'src', 'core'))
sys.path.append(os.path.join(project_root, 'src', 'data_collection'))

from data_manager import DataManager

# Import the data fetching functions from the main script  
from faster_wu_tsi_to_sheets_async import fetch_wu_data, fetch_tsi_data

def get_date_range(pull_type):
    """Calculate start and end dates based on pull type"""
    today = datetime.now()
    
    if pull_type == 'weekly':
        # Last Monday to Sunday
        days_since_monday = today.weekday()
        start_date = today - timedelta(days=days_since_monday + 7)
        end_date = start_date + timedelta(days=6)
    elif pull_type == 'bi_weekly':
        # Last two weeks
        start_date = today - timedelta(days=14)
        end_date = today - timedelta(days=1)
    elif pull_type == 'monthly':
        # Last month
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    else:
        raise ValueError(f"Unsupported pull type: {pull_type}")
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def create_google_sheet(data_manager, wu_df, tsi_df, start_date, end_date, pull_type):
    """Create a Google Sheet with the pulled data"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCreds
        
        google_creds_path = os.path.join(project_root, 'creds', 'google_creds.json')
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = GCreds.from_service_account_file(google_creds_path, scopes=scope)
        client = gspread.authorize(creds)
        
        # Create spreadsheet
        sheet_name = f"Automated_{pull_type.title()}_Data_{start_date}_to_{end_date}_{datetime.now().strftime('%H%M%S')}"
        spreadsheet = client.create(sheet_name)
        
        # Add WU data if available
        if wu_df is not None and not wu_df.empty:
            wu_ws = spreadsheet.sheet1
            wu_ws.update_title("WU Data")
            wu_headers = wu_df.columns.tolist()
            wu_ws.update([wu_headers] + wu_df.values.tolist())
        
        # Add TSI data if available
        if tsi_df is not None and not tsi_df.empty:
            if wu_df is None or wu_df.empty:
                tsi_ws = spreadsheet.sheet1
                tsi_ws.update_title("TSI Data")
            else:
                tsi_ws = spreadsheet.add_worksheet(title="TSI Data", rows=len(tsi_df)+1, cols=len(tsi_df.columns))
            
            tsi_headers = tsi_df.columns.tolist()
            tsi_ws.update([tsi_headers] + tsi_df.values.tolist())
        
        # Share with configured email
        config_path = os.path.join(project_root, 'config', 'automation_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                if 'share_email' in config:
                    try:
                        spreadsheet.share(config['share_email'], perm_type='user', role='writer')
                        print(f"📧 Shared with {config['share_email']}")
                    except Exception as e:
                        print(f"⚠️ Failed to share with {config['share_email']}: {e}")
        
        return {
            'sheet_id': spreadsheet.id,
            'sheet_url': spreadsheet.url,
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range': f"{start_date} to {end_date}",
            'pull_type': pull_type,
            'data_sources': []
        }
    
    except Exception as e:
        print(f"⚠️ Failed to create Google Sheet: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Automated data pull for Hot Durham project')
    parser.add_argument('--weekly', action='store_true', help='Pull weekly data (last Monday-Sunday)')
    parser.add_argument('--bi-weekly', action='store_true', help='Pull bi-weekly data (last 2 weeks)')
    parser.add_argument('--monthly', action='store_true', help='Pull monthly data (last month)')
    parser.add_argument('--wu-only', action='store_true', help='Pull Weather Underground data only')
    parser.add_argument('--tsi-only', action='store_true', help='Pull TSI data only')
    parser.add_argument('--no-sheets', action='store_true', help='Skip Google Sheets creation')
    parser.add_argument('--no-sync', action='store_true', help='Skip Google Drive sync')
    
    args = parser.parse_args()
    
    # Determine pull type
    if args.weekly:
        pull_type = 'weekly'
    elif args.bi_weekly:
        pull_type = 'bi_weekly'
    elif args.monthly:
        pull_type = 'monthly'
    else:
        # Default to weekly if no type specified
        pull_type = 'weekly'
    
    # Determine data sources
    fetch_wu = not args.tsi_only
    fetch_tsi = not args.wu_only
    
    print(f"🤖 Starting automated {pull_type} data pull...")
    print(f"📊 Data sources: {'WU' if fetch_wu else ''}{' and ' if fetch_wu and fetch_tsi else ''}{'TSI' if fetch_tsi else ''}")
    
    # Get date range
    start_date, end_date = get_date_range(pull_type)
    print(f"📅 Date range: {start_date} to {end_date}")
    
    # Initialize data manager
    data_manager = DataManager(project_root)
    
    # Fetch data
    wu_df = None
    tsi_df = None
    
    if fetch_wu:
        print("🌤️ Fetching Weather Underground data...")
        try:
            wu_df = fetch_wu_data(start_date, end_date)
            if wu_df is not None and not wu_df.empty:
                print(f"✅ WU: {len(wu_df)} records fetched")
                # Save WU data
                wu_path = data_manager.save_raw_data(
                    data=wu_df,
                    source='wu',
                    start_date=start_date,
                    end_date=end_date,
                    pull_type=pull_type,
                    file_format='csv'
                )
                print(f"📁 WU data saved to: {wu_path}")
            else:
                print("⚠️ No WU data retrieved")
        except Exception as e:
            print(f"❌ Error fetching WU data: {e}")
    
    if fetch_tsi:
        print("🔬 Fetching TSI data...")
        try:
            tsi_df, _ = fetch_tsi_data(start_date, end_date)
            if tsi_df is not None and not tsi_df.empty:
                print(f"✅ TSI: {len(tsi_df)} records fetched")
                # Save TSI data
                tsi_path = data_manager.save_raw_data(
                    data=tsi_df,
                    source='tsi',
                    start_date=start_date,
                    end_date=end_date,
                    pull_type=pull_type,
                    file_format='csv'
                )
                print(f"📁 TSI data saved to: {tsi_path}")
            else:
                print("⚠️ No TSI data retrieved")
        except Exception as e:
            print(f"❌ Error fetching TSI data: {e}")
    
    # Create Google Sheet if data was retrieved and not disabled
    sheet_info = None
    if not args.no_sheets and ((wu_df is not None and not wu_df.empty) or (tsi_df is not None and not tsi_df.empty)):
        print("📊 Creating Google Sheet...")
        sheet_info = create_google_sheet(data_manager, wu_df, tsi_df, start_date, end_date, pull_type)
        if sheet_info:
            if fetch_wu and wu_df is not None and not wu_df.empty:
                sheet_info['data_sources'].append('Weather Underground')
            if fetch_tsi and tsi_df is not None and not tsi_df.empty:
                sheet_info['data_sources'].append('TSI')
            
            # Save sheet metadata
            data_manager.save_sheet_metadata(sheet_info, start_date, end_date, pull_type)
            print(f"🔗 Google Sheet created: {sheet_info['sheet_url']}")
    
    # Sync to Google Drive if not disabled
    if not args.no_sync:
        print("☁️ Syncing to Google Drive...")
        try:
            data_manager.sync_to_drive()
            print("✅ Google Drive sync completed!")
        except Exception as e:
            print(f"⚠️ Google Drive sync failed: {e}")
    
    print(f"🎉 Automated {pull_type} data pull completed!")
    
    # Log the completion
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'pull_type': pull_type,
        'date_range': f"{start_date} to {end_date}",
        'wu_records': len(wu_df) if wu_df is not None else 0,
        'tsi_records': len(tsi_df) if tsi_df is not None else 0,
        'sheet_created': sheet_info is not None,
        'sheet_url': sheet_info['sheet_url'] if sheet_info else None
    }
    
    # Save to automation log
    data_manager.log_automation_run(log_entry)

if __name__ == "__main__":
    main()
