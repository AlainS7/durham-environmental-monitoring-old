"""
Centralized Path Configuration for the Project.

This file defines all relevant paths for data, logs, and other artifacts to ensure
consistency across the entire application. Using a centralized Python-based
configuration for paths makes them more manageable, less error-prone, and easier
to integrate with other modules.

This module replaces the static `paths.json` to provide a more flexible and
programmatic way of handling paths.
"""

import os

# --- Base Project Directory ---
# Defines the absolute path to the project's root directory.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Data Paths ---
# Defines paths for various data categories, ensuring a structured and predictable
# layout for raw, processed, and temporary data files.
DATA_PATHS = {
    "raw_data": os.path.join(PROJECT_ROOT, "data", "raw"),
    "processed_data": os.path.join(PROJECT_ROOT, "data", "processed"),
    "master_data": os.path.join(PROJECT_ROOT, "data", "master"),
    "temp_data": os.path.join(PROJECT_ROOT, "data", "temp"),
    "metadata": os.path.join(PROJECT_ROOT, "data", "metadata"),
}

# --- Log Paths ---
# Defines paths for different types of logs, helping to separate concerns and
# making it easier to debug and monitor the application.
LOG_PATHS = {
    "application": os.path.join(PROJECT_ROOT, "temp", "logs", "application"),
    "system": os.path.join(PROJECT_ROOT, "temp", "logs", "system"),
    "scheduler": os.path.join(PROJECT_ROOT, "temp", "logs", "scheduler"),
    "archive": os.path.join(PROJECT_ROOT, "temp", "logs", "archive"),
}

# --- Backup Paths ---
# Defines paths for storing backups of data and configurations, which is critical
# for disaster recovery and data integrity.
BACKUP_PATHS = {
    "automated": os.path.join(PROJECT_ROOT, "backup", "automated"),
    "manual": os.path.join(PROJECT_ROOT, "backup", "manual"),
    "configurations": os.path.join(PROJECT_ROOT, "backup", "configurations"),
}

# --- Credential Paths ---
# Defines the location for storing sensitive credentials, keeping them separate
# from the main codebase for improved security.
CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, "creds")

# --- Configuration Paths ---
# Defines paths for different configuration environments, allowing for tailored
# settings for development, testing, and production.
CONFIG_PATHS = {
    "base": os.path.join(PROJECT_ROOT, "config", "base"),
    "environments": os.path.join(PROJECT_ROOT, "config", "environments"),
    "production": os.path.join(PROJECT_ROOT, "config", "production"),
}

# --- Utility Function to Ensure Directories Exist ---
def ensure_all_dirs_exist():
    """
    Iterates through all defined path dictionaries and creates the directories
    if they do not already exist. This is useful for initializing the project
    structure on a new setup.
    """
    for path_dict in [DATA_PATHS, LOG_PATHS, BACKUP_PATHS, CONFIG_PATHS]:
        for path in path_dict.values():
            os.makedirs(path, exist_ok=True)

# --- Main Execution Block ---
# When this script is run directly, it will create all necessary directories,
# ensuring the project's folder structure is correctly initialized.
if __name__ == "__main__":
    ensure_all_dirs_exist()
    print("All necessary directories have been created.")
