#!/bin/bash

# Hot Durham System - Quick Start Script
# =====================================
# This script starts all Hot Durham web applications for development and testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1
    else
        return 0
    fi
}

# Function to start web application
start_app() {
    local app_name=$1
    local script_path=$2
    local port=$3
    local extra_args=${4:-""}
    
    log "Starting $app_name on port $port..."
    
    if ! check_port $port; then
        warning "$app_name port $port is already in use"
        return 1
    fi
    
    # Start application in background
    if [[ "$app_name" == "Streamlit GUI" ]]; then
        PYTHONPATH="$PROJECT_ROOT" streamlit run "$script_path" --server.port $port $extra_args > "$LOG_DIR/${app_name,,}_output.log" 2>&1 &
    else
        cd "$PROJECT_ROOT" && python3 "$script_path" --port $port $extra_args > "$LOG_DIR/${app_name,,}_output.log" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$LOG_DIR/${app_name,,}_pid.txt"
    
    # Wait a moment and check if it started
    sleep 3
    if ps -p $pid > /dev/null; then
        success "$app_name started successfully (PID: $pid)"
        echo "   📍 URL: http://localhost:$port"
        return 0
    else
        error "$app_name failed to start"
        return 1
    fi
}

# Function to stop all applications
stop_all() {
    log "Stopping all Hot Durham applications..."
    
    # Stop by PID files
    for pid_file in "$LOG_DIR"/*_pid.txt; do
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            local app_name=$(basename "$pid_file" _pid.txt)
            
            if ps -p $pid > /dev/null; then
                log "Stopping $app_name (PID: $pid)..."
                kill $pid
                sleep 2
                
                # Force kill if still running
                if ps -p $pid > /dev/null; then
                    warning "Force killing $app_name..."
                    kill -9 $pid
                fi
                
                success "$app_name stopped"
            fi
            
            rm -f "$pid_file"
        fi
    done
    
    # Also stop any streamlit processes
    pkill -f streamlit 2>/dev/null || true
    
    success "All applications stopped"
}

# Function to show status
show_status() {
    log "Hot Durham System Status"
    echo "========================"
    
    # Check each application
    local apps=(
        "public_dashboard:5001:Public Dashboard"
        "live_sensor_map:5003:Live Sensor Map"
        "streamlit_gui:8502:Streamlit GUI"
    )
    
    for app in "${apps[@]}"; do
        IFS=':' read -r name port display_name <<< "$app"
        
        local pid_file="$LOG_DIR/${name}_pid.txt"
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null; then
                echo "✅ $display_name: Running (PID: $pid, Port: $port)"
            else
                echo "❌ $display_name: Stopped (stale PID file)"
                rm -f "$pid_file"
            fi
        else
            if check_port $port; then
                echo "⭕ $display_name: Not running"
            else
                echo "⚠️  $display_name: Port $port in use (unknown process)"
            fi
        fi
    done
    
    echo ""
    echo "📁 Log files: $LOG_DIR"
    echo "📊 Project root: $PROJECT_ROOT"
}

# Function to generate test report
generate_test_report() {
    log "Generating production PDF test report..."
    
    cd "$PROJECT_ROOT"
    if python3 generate_production_pdf_report.py --days-back=7 --no-upload --verbose; then
        success "Test PDF report generated successfully!"
        
        # Find the latest report
        local reports_dir="$PROJECT_ROOT/sensor_visualizations/production_pdf_reports"
        local latest_report=$(ls -t "$reports_dir"/*.pdf 2>/dev/null | head -1)
        
        if [[ -n "$latest_report" ]]; then
            echo "📄 Latest report: $latest_report"
            echo "📱 Open with: open '$latest_report'"
        fi
    else
        error "Test PDF report generation failed"
        return 1
    fi
}

# Function to open all applications in browser
open_browsers() {
    log "Opening all applications in browser..."
    
    local urls=(
        "http://localhost:5001"
        "http://localhost:5003"
        "http://localhost:8502"
    )
    
    for url in "${urls[@]}"; do
        log "Opening $url"
        if command -v open >/dev/null 2>&1; then
            open "$url"
        elif command -v xdg-open >/dev/null 2>&1; then
            xdg-open "$url"
        else
            echo "Please manually open: $url"
        fi
        sleep 1
    done
}

# Function to show help
show_help() {
    cat << EOF
🔥 Hot Durham System - Quick Start Script

USAGE:
    $0 [COMMAND]

COMMANDS:
    start           Start all web applications
    stop            Stop all running applications
    restart         Stop and start all applications
    status          Show current application status
    test-pdf        Generate a test PDF report
    open            Open all applications in browser
    logs            Show recent log output
    help            Show this help message

APPLICATIONS:
    📊 Public Dashboard     http://localhost:5001
    🗺️  Live Sensor Map      http://localhost:5003
    📈 Streamlit GUI        http://localhost:8502

EXAMPLES:
    $0 start        # Start all applications
    $0 status       # Check what's running
    $0 test-pdf     # Generate test report
    $0 stop         # Stop everything

LOG FILES:
    📁 Location: $LOG_DIR/
    📝 Output: {app_name}_output.log
    🆔 PIDs: {app_name}_pid.txt

For more information, see the Hot Durham documentation.
EOF
}

# Function to show logs
show_logs() {
    log "Recent log output from all applications:"
    echo "========================================"
    
    for log_file in "$LOG_DIR"/*_output.log; do
        if [[ -f "$log_file" ]]; then
            local app_name=$(basename "$log_file" _output.log)
            echo ""
            echo "=== $app_name ===" 
            tail -10 "$log_file" 2>/dev/null || echo "No logs available"
        fi
    done
}

# Main execution
main() {
    case "${1:-}" in
        start)
            log "🚀 Starting Hot Durham System..."
            echo ""
            
            # Start all applications
            start_app "Public Dashboard" "src/visualization/public_dashboard.py" 5001 "--debug"
            start_app "Live Sensor Map" "src/visualization/live_sensor_map.py" 5003
            start_app "Streamlit GUI" "src/gui/enhanced_streamlit_gui.py" 8502
            
            echo ""
            success "Hot Durham System started successfully!"
            echo ""
            echo "📊 Public Dashboard:  http://localhost:5001"
            echo "🗺️  Live Sensor Map:   http://localhost:5003"
            echo "📈 Streamlit GUI:     http://localhost:8502"
            echo ""
            echo "💡 Use '$0 status' to check running applications"
            echo "💡 Use '$0 test-pdf' to generate a test report"
            echo "💡 Use '$0 stop' to stop all applications"
            ;;
        stop)
            stop_all
            ;;
        restart)
            stop_all
            sleep 2
            main start
            ;;
        status)
            show_status
            ;;
        test-pdf)
            generate_test_report
            ;;
        open)
            open_browsers
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            log "🔥 Hot Durham Environmental Monitoring System"
            echo "============================================="
            echo ""
            echo "Use --help to see available commands"
            echo ""
            show_status
            ;;
        *)
            error "Unknown command: $1"
            echo "Use --help to see available commands"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
