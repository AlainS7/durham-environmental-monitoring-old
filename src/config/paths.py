"""
Path configuration for Hot Durham project.
Provides centralized path management for the organized structure.
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Data paths
DATA_ROOT = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_ROOT / "raw"
PROCESSED_DATA_PATH = DATA_ROOT / "processed"
MASTER_DATA_PATH = DATA_ROOT / "master"
TEMP_DATA_PATH = DATA_ROOT / "temp"

# Log paths
LOG_ROOT = PROJECT_ROOT / "logs"
APPLICATION_LOG_PATH = LOG_ROOT / "application"
SYSTEM_LOG_PATH = LOG_ROOT / "system"
SCHEDULER_LOG_PATH = LOG_ROOT / "scheduler"
ARCHIVE_LOG_PATH = LOG_ROOT / "archive"

# Backup paths
BACKUP_ROOT = PROJECT_ROOT / "backup"
AUTOMATED_BACKUP_PATH = BACKUP_ROOT / "automated"
MANUAL_BACKUP_PATH = BACKUP_ROOT / "manual"
CONFIG_BACKUP_PATH = BACKUP_ROOT / "configurations"

# Configuration paths
CONFIG_ROOT = PROJECT_ROOT / "config"
BASE_CONFIG_PATH = CONFIG_ROOT / "base"
ENV_CONFIG_PATH = CONFIG_ROOT / "environments"
FEATURE_CONFIG_PATH = CONFIG_ROOT / "features"

# Legacy compatibility paths
LEGACY_RAW_PULLS = PROJECT_ROOT / "raw_pulls"
LEGACY_PROCESSED = PROJECT_ROOT / "processed"

def get_data_path(data_type: str, sensor_type: str = None, environment: str = "production", year: str = None) -> Path:
    """Get appropriate data path based on type and environment."""
    base_path = RAW_DATA_PATH if data_type == "raw" else PROCESSED_DATA_PATH
    
    if sensor_type:
        base_path = base_path / sensor_type / environment
        if year:
            base_path = base_path / year
    
    return base_path

def get_log_path(log_type: str, sub_type: str = None) -> Path:
    """Get appropriate log path based on type."""
    log_paths = {
        "application": APPLICATION_LOG_PATH,
        "system": SYSTEM_LOG_PATH,
        "scheduler": SCHEDULER_LOG_PATH,
        "archive": ARCHIVE_LOG_PATH
    }
    
    base_path = log_paths.get(log_type, APPLICATION_LOG_PATH)
    if sub_type:
        base_path = base_path / sub_type
    
    return base_path

def get_config_path(config_type: str, environment: str = "base") -> Path:
    """Get appropriate config path based on type and environment."""
    if environment == "base":
        return BASE_CONFIG_PATH / f"{config_type}.json"
    else:
        return ENV_CONFIG_PATH / environment / f"{config_type}.json"

def get_backup_path(backup_type: str, sub_type: str = None) -> Path:
    """Get appropriate backup path based on type."""
    backup_paths = {
        "automated": AUTOMATED_BACKUP_PATH,
        "manual": MANUAL_BACKUP_PATH,
        "config": CONFIG_BACKUP_PATH
    }
    
    base_path = backup_paths.get(backup_type, AUTOMATED_BACKUP_PATH)
    if sub_type:
        base_path = base_path / sub_type
    
    return base_path

def validate_paths() -> bool:
    """Validate that all required paths exist or can be created."""
    required_paths = [
        DATA_ROOT, RAW_DATA_PATH, PROCESSED_DATA_PATH, MASTER_DATA_PATH,
        LOG_ROOT, APPLICATION_LOG_PATH, SYSTEM_LOG_PATH,
        BACKUP_ROOT, AUTOMATED_BACKUP_PATH, CONFIG_ROOT, BASE_CONFIG_PATH
    ]
    
    for path in required_paths:
        try:
            ensure_path_exists(path)
        except Exception as e:
            print(f"Error validating path {path}: {e}")
            return False
    
    return True

def ensure_path_exists(path: Path) -> Path:
    """Ensure path exists, create if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path
