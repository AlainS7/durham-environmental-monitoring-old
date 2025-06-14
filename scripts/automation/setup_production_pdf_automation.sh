#!/bin/bash

# Production Sensor PDF Report Automation Setup
# =============================================
# 
# This script sets up automated PDF report generation for production sensors
# using the Central Asian Data Center methodology adapted for Hot Durham.
#
# Features:
# - Weekly PDF report generation
# - Google Drive integration  
# - Automated cleanup of old reports
# - Integration with existing Hot Durham automation
# - Error handling and logging
#
# Usage:
#   ./setup_production_pdf_automation.sh [options]
#
# Options:
#   --install     : Install and configure automation
#   --start       : Start the PDF scheduler
#   --stop        : Stop the PDF scheduler  
#   --status      : Show scheduler status
#   --test        : Generate a test report
#   --uninstall   : Remove automation setup
#
# Author: Hot Durham Project
# Date: June 2025

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEDULER_SCRIPT="$PROJECT_ROOT/src/automation/production_pdf_scheduler.py"
GENERATOR_SCRIPT="$PROJECT_ROOT/generate_production_pdf_report.py"
CONFIG_FILE="$PROJECT_ROOT/config/production_pdf_config.json"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/production_pdf_scheduler.pid"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if Python environment is ready
check_python_environment() {
    log "Checking Python environment..."
    
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check required packages
    local required_packages=("pandas" "matplotlib" "seaborn" "pdfkit")
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" &> /dev/null; then
            error "Required Python package '$package' not found"
            echo "Please install with: pip install $package"
            exit 1
        fi
    done
    
    # Check for WeasyPrint (required for PDF generation)
    if ! python -c "import weasyprint" &> /dev/null; then
        warning "WeasyPrint not found - required for PDF generation"
        echo "Install with: pip install weasyprint"
        echo "May also need system dependencies: brew install cairo pango gdk-pixbuf libffi"
        exit 1
    fi
    
    success "Python environment ready"
}

# Check if scheduler is running
is_scheduler_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            # Remove stale PID file
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Install automation
install_automation() {
    log "Installing Production PDF Report Automation..."
    
    check_python_environment
    
    # Ensure required directories exist
    mkdir -p "$PROJECT_ROOT/sensor_visualizations/production_pdf_reports"
    mkdir -p "$LOG_DIR"
    
    # Make scripts executable
    chmod +x "$SCHEDULER_SCRIPT"
    chmod +x "$GENERATOR_SCRIPT"
    
    # Create launchd plist for macOS automation (optional)
    local plist_file="$HOME/Library/LaunchAgents/com.hotdurham.production.pdf.plist"
    
    cat > "$plist_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hotdurham.production.pdf</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$SCHEDULER_SCRIPT</string>
        <string>--run-once</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/production_pdf_launchd.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/production_pdf_launchd.error.log</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>2</integer>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
    
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF
    
    success "Production PDF automation installed successfully"
    
    echo ""
    echo "📋 Installation Summary:"
    echo "   - Scheduler script: $SCHEDULER_SCRIPT"
    echo "   - Generator script: $GENERATOR_SCRIPT"
    echo "   - Configuration: $CONFIG_FILE"
    echo "   - LaunchAgent: $plist_file"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Test generation: $0 --test"
    echo "   2. Start scheduler: $0 --start"
    echo "   3. Check status: $0 --status"
    echo ""
    echo "⚙️ To enable macOS LaunchAgent (optional):"
    echo "   launchctl load $plist_file"
}

# Start the scheduler
start_scheduler() {
    if is_scheduler_running; then
        warning "Scheduler is already running (PID: $(cat "$PID_FILE"))"
        return 0
    fi
    
    log "Starting Production PDF Report Scheduler..."
    
    check_python_environment
    
    # Start scheduler in background
    nohup python3 "$SCHEDULER_SCRIPT" > "$LOG_DIR/production_pdf_scheduler.log" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "$PID_FILE"
    
    # Wait a moment to check if it started successfully
    sleep 2
    
    if is_scheduler_running; then
        success "Scheduler started successfully (PID: $pid)"
        echo "📊 Monitor logs: tail -f $LOG_DIR/production_pdf_scheduler.log"
    else
        error "Failed to start scheduler"
        exit 1
    fi
}

# Stop the scheduler
stop_scheduler() {
    if ! is_scheduler_running; then
        warning "Scheduler is not running"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    log "Stopping Production PDF Report Scheduler (PID: $pid)..."
    
    # Send TERM signal
    kill "$pid"
    
    # Wait for graceful shutdown
    local count=0
    while is_scheduler_running && [[ $count -lt 10 ]]; do
        sleep 1
        ((count++))
    done
    
    # Force kill if still running
    if is_scheduler_running; then
        warning "Forcefully stopping scheduler..."
        kill -9 "$pid"
        sleep 1
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
    
    success "Scheduler stopped"
}

# Show scheduler status
show_status() {
    echo "📊 Production PDF Report Scheduler Status"
    echo "=========================================="
    
    if is_scheduler_running; then
        local pid=$(cat "$PID_FILE")
        echo "🟢 Status: Running (PID: $pid)"
        
        # Show uptime
        local start_time=$(ps -o lstart= -p "$pid" 2>/dev/null | xargs)
        if [[ -n "$start_time" ]]; then
            echo "⏰ Started: $start_time"
        fi
    else
        echo "🔴 Status: Not running"
    fi
    
    echo ""
    echo "📁 Configuration: $CONFIG_FILE"
    echo "📝 Log file: $LOG_DIR/production_pdf_scheduler.log"
    echo "📄 Output directory: $PROJECT_ROOT/sensor_visualizations/production_pdf_reports"
    
    # Show recent report info
    local last_info_file="$PROJECT_ROOT/sensor_visualizations/production_pdf_reports/last_generation_info.json"
    if [[ -f "$last_info_file" ]]; then
        echo ""
        echo "📊 Last Report Generation:"
        python3 -c "
import json
try:
    with open('$last_info_file') as f:
        info = json.load(f)
    print(f\"   - Generated: {info.get('timestamp', 'Unknown')}\")
    print(f\"   - Total sensors: {info.get('total_sensors', 'Unknown')}\")
    print(f\"   - Average uptime: {info.get('average_uptime', 0):.1f}%\")
    print(f\"   - Uploaded to Drive: {info.get('uploaded_to_drive', False)}\")
except Exception as e:
    print(f\"   - Error reading info: {e}\")
"
    fi
    
    # Show scheduler configuration status
    if [[ -f "$CONFIG_FILE" ]]; then
        echo ""
        echo "⚙️ Scheduler Configuration:"
        python3 -c "
import json
try:
    with open('$CONFIG_FILE') as f:
        config = json.load(f)
    schedule = config.get('schedule', {})
    print(f\"   - Type: {schedule.get('type', 'unknown')}\")
    print(f\"   - Time: {schedule.get('time', 'unknown')}\")
    print(f\"   - Day: {schedule.get('day', 'unknown')}\")
    print(f\"   - Enabled: {config.get('automation', {}).get('enabled', False)}\")
    print(f\"   - Upload to Drive: {config.get('report_settings', {}).get('upload_to_drive', False)}\")
except Exception as e:
    print(f\"   - Error reading config: {e}\")
"
    fi
}

# Test report generation
test_generation() {
    log "Testing Production PDF Report Generation..."
    
    check_python_environment
    
    echo "🧪 Running test generation (last 7 days, no upload)..."
    
    if python3 "$GENERATOR_SCRIPT" --days-back=7 --no-upload --verbose; then
        success "Test report generated successfully!"
        
        # Show output location
        local reports_dir="$PROJECT_ROOT/sensor_visualizations/production_pdf_reports"
        local latest_report=$(ls -t "$reports_dir"/*.pdf 2>/dev/null | head -1)
        
        if [[ -n "$latest_report" ]]; then
            echo "📄 Test report location: $latest_report"
            echo "📱 Open with: open '$latest_report'"
        fi
    else
        error "Test report generation failed"
        echo "📝 Check logs for details: $LOG_DIR/pdf_report_generation.log"
        exit 1
    fi
}

# Uninstall automation
uninstall_automation() {
    log "Uninstalling Production PDF Report Automation..."
    
    # Stop scheduler if running
    if is_scheduler_running; then
        stop_scheduler
    fi
    
    # Remove launchd plist
    local plist_file="$HOME/Library/LaunchAgents/com.hotdurham.production.pdf.plist"
    if [[ -f "$plist_file" ]]; then
        launchctl unload "$plist_file" 2>/dev/null || true
        rm -f "$plist_file"
        log "Removed LaunchAgent"
    fi
    
    # Clean up log files (optional)
    read -p "Remove log files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$LOG_DIR"/production_pdf_*
        log "Removed log files"
    fi
    
    success "Production PDF automation uninstalled"
}

# Show help
show_help() {
    cat << EOF
Production Sensor PDF Report Automation Setup

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --install       Install and configure automation
    --start         Start the PDF scheduler  
    --stop          Stop the PDF scheduler
    --status        Show scheduler status
    --test          Generate a test report
    --uninstall     Remove automation setup
    --help          Show this help message

EXAMPLES:
    $0 --install    # Initial setup
    $0 --test       # Test report generation
    $0 --start      # Start background scheduler
    $0 --status     # Check what's running

CONFIGURATION:
    Edit $CONFIG_FILE to customize:
    - Schedule (daily/weekly/monthly)
    - Report settings (days back, upload options)
    - Automation options (retries, thresholds)

LOGS:
    - Scheduler: $LOG_DIR/production_pdf_scheduler.log
    - Reports: $LOG_DIR/pdf_report_generation.log

For more information, see the Hot Durham documentation.
EOF
}

# Main execution
main() {
    case "${1:-}" in
        --install)
            install_automation
            ;;
        --start)
            start_scheduler
            ;;
        --stop)
            stop_scheduler
            ;;
        --status)
            show_status
            ;;
        --test)
            test_generation
            ;;
        --uninstall)
            uninstall_automation
            ;;
        --help)
            show_help
            ;;
        "")
            echo "🏭 Production Sensor PDF Report Automation"
            echo "==========================================="
            echo ""
            echo "Use --help to see available options"
            echo ""
            show_status
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
