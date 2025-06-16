#!/bin/bash
# Hot Durham Automated Maintenance Script
# This script performs routine maintenance tasks for the project.

# Set up logging
MAINTENANCE_LOG="/Users/alainsoto/IdeaProjects/Hot Durham/logs/maintenance_$(date +%Y-%m-%d_%H-%M-%S).log"
PROJECT_DIR="/Users/alainsoto/IdeaProjects/Hot Durham"

# Create logs directory if it doesn't exist
mkdir -p "${PROJECT_DIR}/logs"

# Function to log messages
log_message() {
    echo "[ $(date) ] $1" | tee -a "$MAINTENANCE_LOG"
}

log_message "Starting automated maintenance..."

# Clean up logs older than 30 days
log_message "Cleaning up old log files..."
find "${PROJECT_DIR}/logs" -name "*.log" -type f -mtime +30 -delete
log_message "Old log files cleanup completed."

# Clean up temporary files
log_message "Cleaning up temporary files..."
find "${PROJECT_DIR}/temp" -type f -mtime +7 -delete 2>/dev/null || true
log_message "Temporary files cleanup completed."

# Clean up old test log files specifically
log_message "Cleaning up test log files..."
find "${PROJECT_DIR}/logs" -name "*_test_*.log" -type f -mtime +3 -delete 2>/dev/null || true
log_message "Test log files cleanup completed."

# Check disk usage and warn if high
DISK_USAGE=$(df "${PROJECT_DIR}" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log_message "WARNING: Disk usage is high (${DISK_USAGE}%)"
fi

log_message "Maintenance completed successfully."
