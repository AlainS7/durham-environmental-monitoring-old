#!/bin/bash

# Hot Durham Weather Monitoring - Automated Scheduling Setup
# This script sets up cron jobs for automated report generation

echo "=== Hot Durham Weather Monitoring - Automated Scheduling Setup ==="

# Check if we're running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS system"
    SYSTEM="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux system"
    SYSTEM="linux"
else
    echo "Unsupported system: $OSTYPE"
    exit 1
fi

# Get the project directory
PROJECT_DIR="/Users/alainsoto/IdeaProjects/Hot Durham"
PYTHON_PATH=$(which python3)
SCRIPT_PATH="$PROJECT_DIR/src/automation/automated_reporting.py"

echo "Project Directory: $PROJECT_DIR"
echo "Python Path: $PYTHON_PATH"
echo "Script Path: $SCRIPT_PATH"

# Make the automated reporting script executable
chmod +x "$SCRIPT_PATH"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Create a wrapper script for cron (cron has minimal environment)
WRAPPER_SCRIPT="$PROJECT_DIR/src/automation/run_automated_reports.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
export PATH=/usr/local/bin:/usr/bin:/bin
cd "$PROJECT_DIR"
"$PYTHON_PATH" "$SCRIPT_PATH" "$PROJECT_DIR" >> "$PROJECT_DIR/logs/cron_output.log" 2>&1
EOF

chmod +x "$WRAPPER_SCRIPT"

echo "Created wrapper script: $WRAPPER_SCRIPT"

# Create cron entries
CRON_DAILY="0 6 * * * $WRAPPER_SCRIPT"
CRON_WEEKLY="0 7 * * 1 $WRAPPER_SCRIPT"

echo ""
echo "=== CRON JOB SETUP ==="
echo "Choose an option:"
echo "1) Daily reports (6:00 AM every day)"
echo "2) Weekly reports (7:00 AM every Monday)"
echo "3) Both daily and weekly"
echo "4) Custom schedule"
echo "5) Just show commands (don't install)"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo "Setting up daily reports..."
        (crontab -l 2>/dev/null; echo "$CRON_DAILY") | crontab -
        echo "Daily cron job installed: $CRON_DAILY"
        ;;
    2)
        echo "Setting up weekly reports..."
        (crontab -l 2>/dev/null; echo "$CRON_WEEKLY") | crontab -
        echo "Weekly cron job installed: $CRON_WEEKLY"
        ;;
    3)
        echo "Setting up both daily and weekly reports..."
        (crontab -l 2>/dev/null; echo "$CRON_DAILY"; echo "$CRON_WEEKLY") | crontab -
        echo "Both cron jobs installed:"
        echo "  Daily: $CRON_DAILY"
        echo "  Weekly: $CRON_WEEKLY"
        ;;
    4)
        echo "For custom scheduling, manually add this line to your crontab:"
        echo "  $WRAPPER_SCRIPT"
        echo ""
        echo "Example cron formats:"
        echo "  0 6 * * *     # Daily at 6:00 AM"
        echo "  0 */6 * * *   # Every 6 hours"
        echo "  30 2 * * 1    # Weekly on Monday at 2:30 AM"
        echo ""
        echo "Run 'crontab -e' to edit your crontab manually"
        ;;
    5)
        echo "Manual cron job commands:"
        echo "For daily reports:"
        echo "  (crontab -l 2>/dev/null; echo '$CRON_DAILY') | crontab -"
        echo ""
        echo "For weekly reports:"
        echo "  (crontab -l 2>/dev/null; echo '$CRON_WEEKLY') | crontab -"
        ;;
    *)
        echo "Invalid choice. Exiting without installing cron jobs."
        exit 1
        ;;
esac

echo ""
echo "=== SETUP COMPLETE ==="
echo ""
echo "Files created:"
echo "  - Automated reporting script: $SCRIPT_PATH"
echo "  - Wrapper script for cron: $WRAPPER_SCRIPT"
echo "  - Logs directory: $PROJECT_DIR/logs"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove cron jobs: crontab -r"
echo ""
echo "Logs will be written to:"
echo "  - Application logs: $PROJECT_DIR/logs/automated_reports_YYYYMMDD.log"
echo "  - Cron output: $PROJECT_DIR/logs/cron_output.log"
echo ""
echo "Test the automated reporting manually:"
echo "  $WRAPPER_SCRIPT"
