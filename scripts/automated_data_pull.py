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
import pandas as pd
from datetime import datetime, timedelta

# Add project root to Python path for module imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import configuration and core components
from config.automated_data_pull_config import (
    LOGGING_CONFIG, RAW_DATA_PATH, SHEET_METADATA_PATH, DEFAULT_PULL_TYPE, 
    DEFAULT_FILE_FORMAT, ENABLED_SOURCES, GOOGLE_CREDS_PATH, GOOGLE_API_SCOPE, 
    SHARE_EMAIL
)
from config.alert_manager_config import SMTP_CONFIG, RECIPIENT_EMAILS
from src.alerts.alert_manager import AlertManager
from src.visualization.generate_charts import create_time_series_plot
from src.reporting.pdf_generator import create_pdf_report

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

def fetch_data_source(source_name, fetch_function, start_date, end_date, alert_manager):
    """Fetches data from a single source (WU or TSI) and returns it as a DataFrame."""
    logging.info(f"Fetching {source_name} data from {start_date} to {end_date}...")
    try:
        if source_name.lower() == 'tsi':
            df, _ = fetch_function(start_date, end_date)
        else:
            df = fetch_function(start_date, end_date)
        
        if df is not None and not df.empty:
            logging.info(f"Successfully fetched {len(df)} records from {source_name}.")
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
        sheet_name = f"Hot Durham Data - {start_date} to {end_date}"
        spreadsheet = client.create(sheet_name)

        if wu_df is not None and not wu_df.empty:
            ws = spreadsheet.sheet1
            ws.update_title("WU Data")
            ws.update([wu_df.columns.tolist()] + wu_df.values.tolist())

        if tsi_df is not None and not tsi_df.empty:
            ws = spreadsheet.add_worksheet(title="TSI Data", rows=len(tsi_df) + 1, cols=len(tsi_df.columns))
            # Convert all non-serializable columns to strings before upload
            for col in tsi_df.columns:
                if any(isinstance(i, (dict, list)) for i in tsi_df[col]):
                    tsi_df[col] = tsi_df[col].astype(str)
                elif pd.api.types.is_datetime64_any_dtype(tsi_df[col]):
                    tsi_df[col] = tsi_df[col].astype(str)
            ws.update([tsi_df.columns.tolist()] + tsi_df.values.tolist())

        try:
            spreadsheet.share(SHARE_EMAIL, perm_type='user', role='writer')
            logging.info(f"Shared Google Sheet with {SHARE_EMAIL}")
        except Exception as e:
            logging.error(f"Could not share Google Sheet. It may be flagged. Error: {e}")

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
    parser.add_argument("--generate-report", action='store_true', help="Generate a PDF report with charts.")
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

    wu_df, tsi_df = None, None

    if ENABLED_SOURCES["wu"]:
        wu_df = fetch_data_source("WU", fetch_wu_data, start_date, end_date, alert_manager)
        if wu_df is not None and not wu_df.empty:
            logging.info(f"WU DataFrame columns: {wu_df.columns.tolist()}")
            logging.info(f"WU DataFrame head:\n{wu_df.head()}")
    if ENABLED_SOURCES["tsi"]:
        tsi_df = fetch_data_source("TSI", fetch_tsi_data, start_date, end_date, alert_manager)
        if tsi_df is not None and not tsi_df.empty:
            logging.info(f"TSI DataFrame columns: {tsi_df.columns.tolist()}")
            logging.info(f"TSI DataFrame head:\n{tsi_df.head()}")

    if not args.no_sheets and (wu_df is not None or tsi_df is not None):
        sheet_info = create_google_sheet(wu_df, tsi_df, start_date, end_date, args.pull_type, alert_manager)
        if sheet_info:
            save_sheet_metadata(sheet_info, args.pull_type, start_date, end_date)

    if args.generate_report and (wu_df is not None or tsi_df is not None):
        logging.info("Generating PDF report...")
        try:
            reports_dir = os.path.join(PROJECT_ROOT, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            chart_path = os.path.join(reports_dir, f"{args.pull_type}_{start_date}_to_{end_date}_chart.png")
            pdf_path = os.path.join(reports_dir, f"{args.pull_type}_{start_date}_to_{end_date}_report.pdf")
            template_path = "templates/report_template.html"

            report_df = tsi_df if tsi_df is not None else wu_df

            if report_df is not None and not report_df.empty and 'timestamp' in report_df.columns and 'mcpm2x5' in report_df.columns:
                create_time_series_plot(
                    data=report_df,
                    x_col='timestamp',
                    y_col='mcpm2x5',
                    title=f'PM2.5 Readings ({start_date} to {end_date})',
                    x_label='Timestamp',
                    y_label='PM2.5 Concentration (mcpm2x5)',
                    file_path=chart_path
                )
                logging.info(f"Chart saved to {chart_path}")

                template_data = {
                    "title": f"Hot Durham {args.pull_type.title()} Report",
                    "date_range": f"{start_date} to {end_date}",
                    "table_html": report_df.to_html(index=False, classes='table table-striped')
                }

                create_pdf_report(
                    template_path=template_path,
                    context=template_data,
                    output_path=pdf_path
                )
                logging.info(f"PDF report saved to {pdf_path}")
            else:
                logging.warning("Could not generate report: DataFrame is empty or missing required columns ('timestamp', 'pm25').")

        except Exception as e:
            logging.error(f"Failed to generate PDF report: {e}", exc_info=True)
            alert_manager.send_alert("PDF Report Generation Failed", f"An error occurred while generating the PDF report: {e}")

    

    logging.info(f"{args.pull_type.title()} data pull completed.")

if __name__ == "__main__":
    main()