"""
Configuration for the Automated Data Pull Script.

This file centralizes all settings for the data pull process, including API credentials,
file paths, logging options, and other operational parameters. By using a dedicated
configuration file, the script becomes more modular, easier to maintain, and less
prone to errors from hardcoded values.
"""

import os
from config.base.paths import LOG_PATHS, DATA_PATHS

# Base directory of the project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Data Sources ---
# Enable or disable data sources for the pull.
# This allows for targeted data collection without modifying the script's logic.
ENABLED_SOURCES = {
    "wu": True,  # Weather Underground
    "tsi": True,  # TSI
}

# --- API Credentials ---
# Paths to credential files required for accessing Google services.
# Storing paths here avoids hardcoding them in the script.
GOOGLE_CREDS_PATH = os.path.join(PROJECT_ROOT, "creds", "google_creds.json")
TSI_CREDS_PATH = os.path.join(PROJECT_ROOT, "creds", "tsi_creds.json")

# --- File Paths ---
# Centralized paths for data, logs, and other artifacts.
# These are derived from the base paths configuration to ensure consistency.
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, DATA_PATHS["raw_data"])
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, LOG_PATHS["application"], "automated_pull.log")
SHEET_METADATA_PATH = os.path.join(PROJECT_ROOT, "data", "daily_sheets_metadata")

# --- Google Services ---
# Configuration for Google Sheets and Google Drive integration.
# Includes the email for sharing and the scope of API permissions.
GOOGLE_API_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SHARE_EMAIL = "hotdurham@gmail.com"

# --- Logging ---
# Settings for logging the script's execution.
# This includes the log file path and the logging level.
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file": LOG_FILE_PATH,
}

# --- Operational Parameters ---
# Default settings for the data pull process.
# These can be overridden by command-line arguments.
DEFAULT_PULL_TYPE = "daily"
DEFAULT_FILE_FORMAT = "csv"

# Ensure necessary directories exist
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
os.makedirs(SHEET_METADATA_PATH, exist_ok=True)
