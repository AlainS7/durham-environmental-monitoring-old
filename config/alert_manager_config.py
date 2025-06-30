"""
Configuration for the Alert Manager.

This file centralizes all settings for the alert system, including SMTP server details,
API keys for other notification services, and the email addresses of recipients.
By using a dedicated configuration file, the alert manager becomes more modular,
easier to maintain, and less prone to errors from hardcoded values.
"""

import os

# --- SMTP Configuration ---
# These settings are for sending email alerts via an SMTP server.
# It is recommended to use environment variables for sensitive information.
SMTP_CONFIG = {
    "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
    "port": int(os.environ.get("SMTP_PORT", 587)),
    "sender_email": os.environ.get("SENDER_EMAIL", "your_email@example.com"),
    "sender_password": os.environ.get("SENDER_PASSWORD", "your_password"),
}

# --- Recipient Configuration ---
# A list of email addresses that will receive alerts.
RECIPIENT_EMAILS = [
    os.environ.get("RECIPIENT_EMAIL", "recipient@example.com"),
]

# --- Alert Thresholds ---
# Define the thresholds for triggering alerts.
ALERT_THRESHOLDS = {
    "pm25": {
        "high": 150,
        "medium": 100,
        "low": 50,
    },
}
