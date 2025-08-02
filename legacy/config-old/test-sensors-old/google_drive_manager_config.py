"""
Configuration for the Enhanced Google Drive Manager.

This file centralizes all settings for the Google Drive manager, including rate
limiting, retry logic, and other operational parameters. By using a dedicated
configuration file, the Google Drive manager becomes more modular, easier to
maintain, and less prone to errors from hardcoded values.
"""

# --- Rate Limiting ---
# These settings control how many requests the Google Drive manager can make in a
# given time period. This is important for preventing API throttling.
RATE_LIMITING = {
    "requests_per_second": 5,
    "burst_allowance": 10,
    "backoff_factor": 5,
    "max_retries": 10,
    "chunk_size_mb": 20,
}

# --- Performance ---
# These settings control the performance of the Google Drive manager.
PERFORMANCE = {
    "enable_chunked_upload": True,
    "parallel_uploads": False,
    "cache_folder_ids": True,
    "compress_large_files": False,
}

# --- Monitoring ---
# These settings control the monitoring of the Google Drive manager.
MONITORING = {
    "enable_performance_tracking": True,
    "log_api_calls": True,
    "alert_on_failures": True,
}

# --- Sharing ---
# The email address to share uploaded files with.
SHARE_EMAIL = "hotdurham@gmail.com"
