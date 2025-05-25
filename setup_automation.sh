#!/bin/bash

# Cron Setup Script for Hot Durham Automated Data Pulls
# This script helps set up automated scheduling for data pulls

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
PYTHON_PATH=$(which python3)
SCRIPT_PATH="$PROJECT_ROOT/scripts/automated_data_pull.py"

echo "🤖 Hot Durham - Automated Data Pull Setup"
echo "=========================================="
echo ""

# Check if the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: automated_data_pull.py not found at $SCRIPT_PATH"
    exit 1
fi

# Check if Python 3 is available
if [ ! -x "$PYTHON_PATH" ]; then
    echo "❌ Error: Python 3 not found. Please install Python 3."
    exit 1
fi

echo "✅ Script found: $SCRIPT_PATH"
echo "✅ Python found: $PYTHON_PATH"
echo ""

# Create log directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
echo "📁 Log directory: $LOG_DIR"
echo ""

# Display current crontab
echo "📋 Current crontab entries:"
crontab -l 2>/dev/null | grep -v "Hot Durham" || echo "No existing Hot Durham cron jobs found."
echo ""

# Offer to set up cron jobs
echo "🕒 Suggested cron schedules:"
echo ""
echo "1. Weekly data pull (every Monday at 6 AM):"
echo "   0 6 * * 1 cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --weekly >> $LOG_DIR/weekly_pull.log 2>&1"
echo ""
echo "2. Bi-weekly data pull (every other Monday at 6 AM):"
echo "   0 6 * * 1 [ \$(expr \$(date +\\%W) \\% 2) -eq 0 ] && cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --bi-weekly >> $LOG_DIR/biweekly_pull.log 2>&1"
echo ""
echo "3. Monthly data pull (1st of every month at 7 AM):"
echo "   0 7 1 * * cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --monthly >> $LOG_DIR/monthly_pull.log 2>&1"
echo ""

read -p "Would you like to set up automated weekly pulls? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create temporary cron file
    TEMP_CRON=$(mktemp)
    
    # Get existing crontab (ignore errors if no crontab exists)
    crontab -l 2>/dev/null > "$TEMP_CRON" || true
    
    # Add Hot Durham entries
    echo "" >> "$TEMP_CRON"
    echo "# Hot Durham Automated Data Pulls" >> "$TEMP_CRON"
    echo "# Weekly data pull every Monday at 6 AM" >> "$TEMP_CRON"
    echo "0 6 * * 1 cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --weekly >> $LOG_DIR/weekly_pull.log 2>&1" >> "$TEMP_CRON"
    echo "# Monthly summary on 1st of each month at 7 AM" >> "$TEMP_CRON"
    echo "0 7 1 * * cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --monthly >> $LOG_DIR/monthly_pull.log 2>&1" >> "$TEMP_CRON"
    
    # Install the new crontab
    crontab "$TEMP_CRON"
    
    # Clean up
    rm "$TEMP_CRON"
    
    echo "✅ Cron jobs installed successfully!"
    echo ""
    echo "📋 Updated crontab:"
    crontab -l | grep -A 10 "Hot Durham"
else
    echo "ℹ️ No cron jobs installed. You can set them up manually later."
fi

echo ""
echo "📖 Manual Setup Instructions:"
echo "To edit cron jobs manually, run: crontab -e"
echo "To view current cron jobs, run: crontab -l"
echo "To test the script manually, run:"
echo "cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --weekly"
echo ""

echo "📝 Log Files:"
echo "Weekly pulls: $LOG_DIR/weekly_pull.log"
echo "Monthly pulls: $LOG_DIR/monthly_pull.log"
echo ""

echo "🎉 Setup complete! The automation will:"
echo "• Pull data every Monday at 6 AM"
echo "• Generate monthly summaries on the 1st of each month"
echo "• Save data to organized folders in $PROJECT_ROOT/data/"
echo "• Sync to Google Drive automatically"
echo "• Create Google Sheets for each pull"
echo ""

# Create a wrapper script for easy testing
WRAPPER_SCRIPT="$PROJECT_ROOT/run_weekly_pull.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Quick test script for weekly data pull
cd "$PROJECT_ROOT"
"$PYTHON_PATH" "$SCRIPT_PATH" --weekly
EOF

chmod +x "$WRAPPER_SCRIPT"
echo "🔧 Created test script: $WRAPPER_SCRIPT"
echo "   Run this script to test the weekly pull manually."
