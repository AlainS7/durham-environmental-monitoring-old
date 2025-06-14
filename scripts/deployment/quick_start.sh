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
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PORT_MANAGER="$PROJECT_ROOT/scripts/utilities/port_manager.sh"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Port Configuration - ZSH Compatible
# Using simple variables instead of associative arrays
PUBLIC_DASHBOARD_PORT=5001
API_SERVER_PORT=5002
LIVE_SENSOR_MAP_PORT=5003
PREDICTIVE_API_PORT=5004
STREAMLIT_GUI_PORT=8502

# Function to get port by service name
get_service_port() {
    case $1 in
        "public_dashboard") echo $PUBLIC_DASHBOARD_PORT ;;
        "api_server") echo $API_SERVER_PORT ;;
        "live_sensor_map") echo $LIVE_SENSOR_MAP_PORT ;;
        "predictive_api") echo $PREDICTIVE_API_PORT ;;
        "streamlit_gui") echo $STREAMLIT_GUI_PORT ;;
        *) echo "0" ;;
    esac
}

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

# Function to clean ports before starting
clean_ports() {
    log "🧹 Cleaning ports before starting services..."
    
    if [[ -x "$PORT_MANAGER" ]]; then
        "$PORT_MANAGER" kill-all --force >/dev/null 2>&1
        success "All ports cleaned using port manager"
    else
        warning "Port manager not found, using fallback cleanup"
        # Fallback: Kill known ports manually
        for port in 5001 5002 5003 5004 8502; do
            local pid=$(lsof -ti:$port 2>/dev/null)
            if [[ -n "$pid" ]]; then
                kill -9 $pid 2>/dev/null || true
                log "Killed process on port $port"
            fi
        done
    fi
    
    # Also clean up any orphaned streamlit processes
    pkill -f streamlit 2>/dev/null || true
    
    sleep 2
}

# Function to check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port in use
    else
        return 0  # Port available
    fi
}

# Function to start web application with enhanced port management
start_app() {
    local app_name=$1
    local script_path=$2
    local port=$3
    local extra_args=${4:-""}
    
    log "🚀 Starting $app_name on port $port..."
    
    # Double-check port availability
    if ! check_port $port; then
        warning "Port $port is still in use, attempting to free it..."
        local pid=$(lsof -ti:$port 2>/dev/null)
        if [[ -n "$pid" ]]; then
            kill -9 $pid 2>/dev/null || true
            sleep 1
        fi
        
        if ! check_port $port; then
            error "$app_name port $port could not be freed"
            return 1
        fi
    fi
    
    # Prepare log files
    local app_log="$LOG_DIR/${app_name// /_}_output.log"
    local app_pid="$LOG_DIR/${app_name// /_}_pid.txt"
    
    # Remove old log files
    rm -f "$app_log" "$app_pid"
    
    # Start application based on type
    local cmd_pid
    cd "$PROJECT_ROOT"
    
    if [[ "$app_name" == "Streamlit GUI" ]]; then
        # Special handling for Streamlit
        PYTHONPATH="$PROJECT_ROOT" streamlit run "$script_path" \
            --server.port $port \
            --server.headless true \
            --server.runOnSave false \
            --browser.gatherUsageStats false \
            $extra_args > "$app_log" 2>&1 &
        cmd_pid=$!
    elif [[ "$script_path" == *"public_api.py" ]]; then
        # API server with custom port argument
        python3 "$script_path" --port $port $extra_args > "$app_log" 2>&1 &
        cmd_pid=$!
    else
        # Standard Flask apps
        python3 "$script_path" --port $port $extra_args > "$app_log" 2>&1 &
        cmd_pid=$!
    fi
    
    # Save PID
    echo $cmd_pid > "$app_pid"
    
    # Wait and verify startup
    sleep 3
    
    if ps -p $cmd_pid > /dev/null 2>&1; then
        # Additional check: verify port is actually in use
        if check_port $port; then
            warning "$app_name process started but port $port not in use yet, waiting..."
            sleep 2
        fi
        
        if check_port $port; then
            error "$app_name failed to bind to port $port"
            kill $cmd_pid 2>/dev/null || true
            return 1
        fi
        
        success "$app_name started successfully (PID: $cmd_pid)"
        echo "   📍 URL: http://localhost:$port"
        return 0
    else
        error "$app_name failed to start (check $app_log for details)"
        return 1
    fi
}

# Function to stop all applications with enhanced cleanup
stop_all() {
    log "🛑 Stopping all Hot Durham applications..."
    
    # Use port manager if available
    if [[ -x "$PORT_MANAGER" ]]; then
        "$PORT_MANAGER" kill-all
        success "All services stopped using port manager"
    else
        warning "Port manager not found, using fallback cleanup"
        
        # Stop by PID files
        for pid_file in "$LOG_DIR"/*_pid.txt; do
            if [[ -f "$pid_file" ]]; then
                local pid=$(cat "$pid_file" 2>/dev/null)
                local app_name=$(basename "$pid_file" _pid.txt)
                
                if [[ -n "$pid" ]] && ps -p "$pid" > /dev/null 2>&1; then
                    log "Stopping $app_name (PID: $pid)..."
                    kill "$pid" 2>/dev/null || true
                    sleep 2
                    
                    # Force kill if still running
                    if ps -p "$pid" > /dev/null 2>&1; then
                        warning "Force killing $app_name..."
                        kill -9 "$pid" 2>/dev/null || true
                    fi
                    
                    success "$app_name stopped"
                fi
                
                rm -f "$pid_file"
            fi
        done
        
        # Kill any remaining processes on our ports
        for port in 5001 5002 5003 5004 8502; do
            local pid=$(lsof -ti:$port 2>/dev/null)
            if [[ -n "$pid" ]]; then
                kill -9 $pid 2>/dev/null || true
            fi
        done
    fi
    
    # Also stop any streamlit processes
    pkill -f streamlit 2>/dev/null || true
    
    success "All applications stopped"
}

# Function to show enhanced status
show_status() {
    echo ""
    echo -e "${BLUE}🔍 Hot Durham System Status${NC}"
    echo "============================"
    
    # Use port manager if available for detailed status
    if [[ -x "$PORT_MANAGER" ]]; then
        "$PORT_MANAGER" status
    else
        # Fallback status check
        echo ""
        echo "Service Status:"
        
        local services_running=0
        local total_services=0
        
        local services="public_dashboard api_server live_sensor_map predictive_api streamlit_gui"
        
        for service in $services; do
            ((total_services++))
            local port=$(get_service_port $service)
            local status="❌ STOPPED"
            local pid_info=""
            
            if ! check_port $port; then
                status="✅ RUNNING"
                ((services_running++))
                local pid=$(lsof -ti:$port 2>/dev/null)
                if [[ -n "$pid" ]]; then
                    pid_info=" (PID: $pid)"
                fi
            fi
            
            printf "  %-20s Port %-5s %s%s\n" "$service" "$port" "$status" "$pid_info"
        done
        
        echo ""
        echo "Summary: $services_running/$total_services services running"
    fi
    
    echo ""
    echo "🌐 Service URLs:"
    echo "  📊 Public Dashboard:   http://localhost:$PUBLIC_DASHBOARD_PORT"
    echo "  🔌 API Server:         http://localhost:$API_SERVER_PORT"
    echo "  🗺️  Live Sensor Map:    http://localhost:$LIVE_SENSOR_MAP_PORT"
    echo "  🤖 Predictive API:     http://localhost:$PREDICTIVE_API_PORT"
    echo "  📈 Streamlit GUI:      http://localhost:$STREAMLIT_GUI_PORT"
    echo ""
}

# Function to test PDF report generation
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
    log "🌐 Opening all applications in browser..."
    
    local urls=(
        "http://localhost:$PUBLIC_DASHBOARD_PORT"
        "http://localhost:$API_SERVER_PORT"
        "http://localhost:$LIVE_SENSOR_MAP_PORT"
        "http://localhost:$STREAMLIT_GUI_PORT"
    )
    
    local names=(
        "Public Dashboard"
        "API Server"
        "Live Sensor Map"
        "Streamlit GUI"
    )
    
    for i in "${!urls[@]}"; do
        local url="${urls[$i]}"
        local name="${names[$i]}"
        
        log "Opening $name: $url"
        if command -v open >/dev/null 2>&1; then
            open "$url"
        elif command -v xdg-open >/dev/null 2>&1; then
            xdg-open "$url"
        else
            echo "Please manually open: $url"
        fi
        sleep 1
    done
    
    success "All applications opened in browser"
}

# Function to show help
show_help() {
    cat << EOF
🔥 Hot Durham System - Quick Start Script

USAGE:
    $0 [COMMAND]

COMMANDS:
    start           Start all web applications (with port cleanup)
    stop            Stop all running applications
    restart         Stop and start all applications
    status          Show current application status
    ports           Show detailed port status using port manager
    test-pdf        Generate a test PDF report
    open            Open all applications in browser
    logs            Show recent log output
    help            Show this help message

APPLICATIONS & PORTS:
    📊 Public Dashboard     http://localhost:$PUBLIC_DASHBOARD_PORT
    🔌 API Server           http://localhost:$API_SERVER_PORT
    🗺️  Live Sensor Map      http://localhost:$LIVE_SENSOR_MAP_PORT
    🤖 Predictive API       http://localhost:$PREDICTIVE_API_PORT
    📈 Streamlit GUI        http://localhost:$STREAMLIT_GUI_PORT

EXAMPLES:
    $0 start        # Start all applications
    $0 status       # Check what's running
    $0 ports        # Detailed port management
    $0 test-pdf     # Generate test report
    $0 stop         # Stop everything

LOG FILES:
    📁 Location: $LOG_DIR/
    📝 Output: {app_name}_output.log
    🆔 PIDs: {app_name}_pid.txt

PORT MANAGEMENT:
    Use the port manager for advanced port operations:
    $PROJECT_ROOT/scripts/utilities/port_manager.sh [command]

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
            
            # Clean ports before starting
            clean_ports
            
            echo ""
            log "🚀 Starting all applications with enhanced port management..."
            echo ""
            
            # Start all applications with better port separation
            start_app "Public Dashboard" "src/visualization/public_dashboard.py" $PUBLIC_DASHBOARD_PORT "--debug"
            start_app "API Server" "src/api/public_api.py" $API_SERVER_PORT ""
            start_app "Live Sensor Map" "src/visualization/live_sensor_map.py" $LIVE_SENSOR_MAP_PORT ""
            start_app "Streamlit GUI" "src/gui/enhanced_streamlit_gui.py" $STREAMLIT_GUI_PORT ""
            
            echo ""
            success "🎉 Hot Durham System started successfully!"
            echo ""
            echo "🌐 Service URLs:"
            echo "  📊 Public Dashboard:   http://localhost:$PUBLIC_DASHBOARD_PORT"
            echo "  🔌 API Server:         http://localhost:$API_SERVER_PORT"
            echo "  🗺️  Live Sensor Map:    http://localhost:$LIVE_SENSOR_MAP_PORT"
            echo "  📈 Streamlit GUI:      http://localhost:$STREAMLIT_GUI_PORT"
            echo ""
            echo "💡 Use '$0 status' to check running applications"
            echo "💡 Use '$0 test-pdf' to generate a test report"
            echo "💡 Use '$0 stop' to stop all applications"
            echo "💡 Use '$PROJECT_ROOT/scripts/utilities/port_manager.sh' for port management"
            ;;
        stop)
            stop_all
            ;;
        restart)
            log "🔄 Restarting Hot Durham System..."
            stop_all
            sleep 3
            main start
            ;;
        status)
            show_status
            ;;
        ports)
            if [[ -x "$PORT_MANAGER" ]]; then
                "$PORT_MANAGER" status
            else
                warning "Port manager not found at $PORT_MANAGER"
                show_status
            fi
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
