"""
Refactored Automated Data Pull Script for Hot Durham Project

This script is designed to be run on a schedule (e.g., via cron) to automatically
pull data from Weather Underground and TSI sources, organize it, and sync it to
Google Drive. It is now fully integrated with the project's configuration system,
making it more modular, maintainable, and easier to debug.

Key Improvements:
- Centralized configuration management via `automated_data_pull_config.py`.
- Modular design with functions for each distinct task (e.g., fetching, saving, logging).
- Improved error handling and logging for better traceability.
- Simplified command-line interface for easier execution.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to Python path for module imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import configuration and core components
from config.automated_data_pull_config import (
    LOGGING_CONFIG, RAW_DATA_PATH, SHEET_METADATA_PATH, DEFAULT_PULL_TYPE, 
    DEFAULT_FILE_FORMAT, ENABLED_SOURCES, GOOGLE_CREDS_PATH, GOOGLE_API_SCOPE, 
    SHARE_EMAIL, SMTP_CONFIG, RECIPIENT_EMAILS
)
from src.alerts.alert_manager import AlertManager

# Attempt to import core components with robust error handling
try:
    from src.core.data_manager import DataManager
    from src.data_collection.faster_wu_tsi_to_sheets_async import fetch_wu_data, fetch_tsi_data
    import gspread
    from google.oauth2.service_account import Credentials as GCreds
except ImportError as e:
    logging.error(f"Failed to import a required module: {e}")
    sys.exit(1)

def setup_logging():
    """Configures logging for the script based on centralized settings."""
    logging.basicConfig(
        level=LOGGING_CONFIG["level"],
        format=LOGGING_CONFIG["format"],
        filename=LOGGING_CONFIG["file"],
        filemode='a'
    )
    # Add a handler to print to console as well
    console = logging.StreamHandler()
    console.setLevel(LOGGING_CONFIG["level"])
    console.setFormatter(logging.Formatter(LOGGING_CONFIG["format"]))
    logging.getLogger('').addHandler(console)

def get_date_range(pull_type):
    """Calculates the start and end dates for the data pull."""
    today = datetime.now()
    if pull_type == 'daily':
        start_date = end_date = today - timedelta(days=1)
    elif pull_type == 'weekly':
        start_of_week = today - timedelta(days=today.weekday())
        start_date = start_of_week - timedelta(days=7)
        end_date = start_date + timedelta(days=6)
    elif pull_type == 'monthly':
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    else:
        raise ValueError(f"Unsupported pull type: {pull_type}")
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def fetch_data_source(source_name, fetch_function, start_date, end_date, data_manager, pull_type, alert_manager):
    """Fetches and saves data from a single source (WU or TSI)."""
    logging.info(f"Fetching {source_name} data from {start_date} to {end_date}...")
    try:
        if source_name.lower() == 'tsi':
            df, _ = fetch_function(start_date, end_date)
        else:
            df = fetch_function(start_date, end_date)
        
        if df is not None and not df.empty:
            logging.info(f"Successfully fetched {len(df)} records from {source_name}.")
            file_path = data_manager.save_raw_data(
                df, source_name.lower(), start_date, end_date, pull_type, DEFAULT_FILE_FORMAT
            )
            logging.info(f"Saved {source_name} data to {file_path}")
            return df
        else:
            logging.warning(f"No data retrieved from {source_name}.")
            alert_manager.send_alert(f"{source_name} Data Collection Warning", f"No data was retrieved for the period: {start_date} to {end_date}.")
            return None
    except Exception as e:
        logging.error(f"Error fetching {source_name} data: {e}", exc_info=True)
        alert_manager.send_alert(f"{source_name} Data Collection Failed", f"An error occurred while fetching data: {e}")
        return None

def create_google_sheet(wu_df, tsi_df, start_date, end_date, pull_type, alert_manager):
    """Creates and populates a Google Sheet with the fetched data."""
    logging.info("Creating Google Sheet...")
    try:
        creds = GCreds.from_service_account_file(GOOGLE_CREDS_PATH, scopes=GOOGLE_API_SCOPE)
        client = gspread.authorize(creds)
        sheet_name = f"Automated_{pull_type.title()}_Data_{start_date}_to_{end_date}"
        spreadsheet = client.create(sheet_name)

        if wu_df is not None and not wu_df.empty:
            ws = spreadsheet.sheet1
            ws.update_title("WU Data")
            ws.update([wu_df.columns.tolist()] + wu_df.values.tolist())

        if tsi_df is not None and not tsi_df.empty:
            ws = spreadsheet.add_worksheet(title="TSI Data", rows=len(tsi_df) + 1, cols=len(tsi_df.columns))
            ws.update([tsi_df.columns.tolist()] + tsi_df.values.tolist())

        spreadsheet.share(SHARE_EMAIL, perm_type='user', role='writer')
        logging.info(f"Shared Google Sheet with {SHARE_EMAIL}")
        return {
            'sheet_id': spreadsheet.id,
            'sheet_url': spreadsheet.url,
            'created_at': datetime.now().isoformat(),
        }
    except Exception as e:
        logging.error(f"Failed to create or share Google Sheet: {e}", exc_info=True)
        alert_manager.send_alert("Google Sheet Creation Failed", f"An error occurred while creating the Google Sheet: {e}")
        return None

def save_sheet_metadata(sheet_info, pull_type, start_date, end_date):
    """Saves metadata about the created Google Sheet to a JSON file."""
    metadata_file = os.path.join(SHEET_METADATA_PATH, f"{pull_type}_{start_date}_to_{end_date}.json")
    try:
        with open(metadata_file, 'w') as f:
            json.dump(sheet_info, f, indent=4)
        logging.info(f"Saved sheet metadata to {metadata_file}")
    except IOError as e:
        logging.error(f"Failed to save sheet metadata: {e}", exc_info=True)

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Automated Data Pull Script")
    parser.add_argument("--pull_type", type=str, default=DEFAULT_PULL_TYPE, choices=['daily', 'weekly', 'monthly'], help="The type of data pull to perform.")
    parser.add_argument("--no_sheets", action='store_true', help="Skip creating a Google Sheet.")
    parser.add_argument("--no_sync", action='store_true', help="Skip syncing to Google Drive.")
    return parser.parse_args()

def main():
    """Main function to orchestrate the data pull process."""
    setup_logging()
    args = parse_arguments()
    alert_manager = AlertManager(
        smtp_server=SMTP_CONFIG["server"],
        smtp_port=SMTP_CONFIG["port"],
        sender_email=SMTP_CONFIG["sender_email"],
        sender_password=SMTP_CONFIG["sender_password"],
        recipient_email=RECIPIENT_EMAILS[0]
    )
    logging.info(f"Starting {args.pull_type} data pull...")

    try:
        start_date, end_date = get_date_range(args.pull_type)
        logging.info(f"Date range: {start_date} to {end_date}")
    except ValueError as e:
        logging.error(str(e), exc_info=True)
        alert_manager.send_alert("Data Pull Failed", f"Invalid pull type specified: {args.pull_type}")
        sys.exit(1)

    data_manager = DataManager(PROJECT_ROOT)
    wu_df, tsi_df = None, None

    if ENABLED_SOURCES["wu"]:
        wu_df = fetch_data_source("WU", fetch_wu_data, start_date, end_date, data_manager, args.pull_type, alert_manager)
    if ENABLED_SOURCES["tsi"]:
        tsi_df = fetch_data_source("TSI", fetch_tsi_data, start_date, end_date, data_manager, args.pull_type, alert_manager)

    if not args.no_sheets and (wu_df is not None or tsi_df is not None):
        sheet_info = create_google_sheet(wu_df, tsi_df, start_date, end_date, args.pull_type, alert_manager)
        if sheet_info:
            save_sheet_metadata(sheet_info, args.pull_type, start_date, end_date)

    if not args.no_sync:
        try:
            data_manager.sync_to_drive()
            logging.info("Successfully synced data to Google Drive.")
        except Exception as e:
            logging.error(f"Google Drive sync failed: {e}", exc_info=True)
            alert_manager.send_alert("Google Drive Sync Failed", f"An error occurred while syncing data to Google Drive: {e}")

    logging.info(f"{args.pull_type.title()} data pull completed.")

if __name__ == "__main__":
    main()