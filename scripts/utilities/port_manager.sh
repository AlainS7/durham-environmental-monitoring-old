#!/bin/bash
# Hot Durham Port Management Script - ZSH Compatible
# Manages all service ports for Hot Durham system

# Color functions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

# Port Configuration (using simple variables for zsh compatibility)
PORTS="5001 5002 5003 5004 8502"
SERVICE_NAMES="public_dashboard api_server live_sensor_map predictive_api streamlit_gui"

# Get service name for port
get_service_name() {
    local port=$1
    case $port in
        5001) echo "public_dashboard" ;;
        5002) echo "api_server" ;;
        5003) echo "live_sensor_map" ;;
        5004) echo "predictive_api" ;;
        8502) echo "streamlit_gui" ;;
        *) echo "unknown" ;;
    esac
}

# Check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Get process using port
get_port_process() {
    local port=$1
    lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null
}

# Get process info
get_process_info() {
    local pid=$1
    if [[ -n "$pid" ]]; then
        ps -p $pid -o pid,comm,args --no-headers 2>/dev/null
    fi
}

# Kill process on port
kill_port() {
    local port=$1
    local force=${2:-false}
    
    local pid=$(get_port_process $port)
    if [[ -n "$pid" ]]; then
        local process_info=$(get_process_info $pid)
        info "Found process on port $port: $process_info"
        
        if [[ "$force" == "true" ]]; then
            kill -9 $pid 2>/dev/null
            success "Force killed process $pid on port $port"
        else
            kill $pid 2>/dev/null
            success "Gracefully terminated process $pid on port $port"
        fi
        
        # Wait and verify
        sleep 1
        if check_port $port; then
            warning "Process still running, trying force kill..."
            kill -9 $pid 2>/dev/null
            sleep 1
        fi
        
        if ! check_port $port; then
            success "Port $port is now free"
            return 0
        else
            error "Failed to free port $port"
            return 1
        fi
    else
        info "Port $port is already free"
        return 0
    fi
}

# Show port status
show_port_status() {
    echo ""
    echo -e "${CYAN}🔌 Hot Durham Port Status${NC}"
    echo "=================================="
    
    for port in $PORTS; do
        local service=$(get_service_name $port)
        local status_color=$RED
        local status_text="❌ FREE"
        local process_info=""
        
        if check_port $port; then
            status_color=$GREEN
            status_text="✅ ACTIVE"
            local pid=$(get_port_process $port)
            process_info=" (PID: $pid)"
        fi
        
        printf "%-20s Port %-5s %s%s%s%s\n" "$service" "$port" "$status_color" "$status_text" "$NC" "$process_info"
    done
    
    echo ""
}

# Kill all Hot Durham services
kill_all_services() {
    local force=${1:-false}
    
    echo ""
    info "Stopping all Hot Durham services..."
    echo ""
    
    local killed_count=0
    
    for port in $PORTS; do
        if check_port $port; then
            if kill_port $port $force; then
                ((killed_count++))
            fi
        fi
    done
    
    echo ""
    if [[ $killed_count -gt 0 ]]; then
        success "Stopped $killed_count service(s)"
    else
        info "No services were running"
    fi
}

# Kill specific service
kill_service() {
    local service_name=$1
    local force=${2:-false}
    
    local port=""
    case $service_name in
        public_dashboard) port=5001 ;;
        api_server) port=5002 ;;
        live_sensor_map) port=5003 ;;
        predictive_api) port=5004 ;;
        streamlit_gui) port=8502 ;;
        *)
            error "Unknown service: $service_name"
            echo "Available services: public_dashboard api_server live_sensor_map predictive_api streamlit_gui"
            return 1
            ;;
    esac
    
    echo ""
    info "Stopping $service_name on port $port..."
    
    if kill_port $port $force; then
        success "$service_name stopped successfully"
    else
        error "Failed to stop $service_name"
        return 1
    fi
}

# Check for port conflicts
check_conflicts() {
    echo ""
    info "Checking for port conflicts..."
    
    local conflicts_found=false
    
    for port in $PORTS; do
        if check_port $port; then
            local pid=$(get_port_process $port)
            local process_info=$(get_process_info $pid)
            
            # Check if it's a Hot Durham service
            if [[ "$process_info" == *"python"* ]] && [[ "$process_info" == *"src/"* ]]; then
                info "Hot Durham service found on port $port: $process_info"
            else
                warning "Non-Hot Durham process on port $port: $process_info"
                conflicts_found=true
            fi
        fi
    done
    
    if [[ "$conflicts_found" == "false" ]]; then
        success "No port conflicts detected"
    else
        warning "Port conflicts detected - use 'kill-conflicts' to resolve"
    fi
    echo ""
}

# Kill non-Hot Durham processes on our ports
kill_conflicts() {
    local force=${1:-false}
    
    echo ""
    info "Checking for non-Hot Durham processes on our ports..."
    
    local conflicts_killed=0
    
    for port in $PORTS; do
        if check_port $port; then
            local pid=$(get_port_process $port)
            local process_info=$(get_process_info $pid)
            
            # Check if it's NOT a Hot Durham service
            if [[ "$process_info" != *"src/"* ]] || [[ "$process_info" != *"python"* ]]; then
                warning "Killing non-Hot Durham process on port $port: $process_info"
                if kill_port $port $force; then
                    ((conflicts_killed++))
                fi
            fi
        fi
    done
    
    if [[ $conflicts_killed -gt 0 ]]; then
        success "Killed $conflicts_killed conflicting process(es)"
    else
        info "No conflicting processes found"
    fi
    echo ""
}

# Show usage
show_usage() {
    echo ""
    echo -e "${CYAN}🔌 Hot Durham Port Management${NC}"
    echo "============================="
    echo ""
    echo "USAGE:"
    echo "  $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "COMMANDS:"
    echo "  status              Show current port status"
    echo "  kill-all [--force]  Stop all Hot Durham services"
    echo "  kill-service NAME   Stop specific service"
    echo "  check-conflicts     Check for port conflicts"
    echo "  kill-conflicts      Kill non-Hot Durham processes on our ports"
    echo "  help                Show this help message"
    echo ""
    echo "SERVICES & PORTS:"
    echo "  public_dashboard    Port 5001"
    echo "  api_server          Port 5002"
    echo "  live_sensor_map     Port 5003"
    echo "  predictive_api      Port 5004"
    echo "  streamlit_gui       Port 8502"
    echo ""
    echo "OPTIONS:"
    echo "  --force             Force kill processes (SIGKILL instead of SIGTERM)"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 status                    # Show all port status"
    echo "  $0 kill-all                  # Gracefully stop all services"
    echo "  $0 kill-all --force          # Force stop all services"
    echo "  $0 kill-service api_server   # Stop just the API server"
    echo "  $0 check-conflicts           # Check for port conflicts"
    echo ""
}

# Main function
main() {
    case "${1:-status}" in
        "status")
            show_port_status
            ;;
        "kill-all")
            local force=false
            if [[ "$2" == "--force" ]]; then
                force=true
            fi
            kill_all_services $force
            ;;
        "kill-service")
            if [[ -z "$2" ]]; then
                error "Service name required"
                echo "Available services: public_dashboard api_server live_sensor_map predictive_api streamlit_gui"
                exit 1
            fi
            local force=false
            if [[ "$3" == "--force" ]]; then
                force=true
            fi
            kill_service "$2" $force
            ;;
        "check-conflicts")
            check_conflicts
            ;;
        "kill-conflicts")
            local force=false
            if [[ "$2" == "--force" ]]; then
                force=true
            fi
            kill_conflicts $force
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
