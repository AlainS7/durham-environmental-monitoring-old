#!/bin/zsh
# setup_maintenance_automation.sh - Setup automated maintenance for Hot Durham project

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
PLIST_FILE="com.hotdurham.maintenance.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}🤖 Hot Durham Automated Maintenance Setup${NC}"
    echo -e "${BLUE}==========================================${NC}"
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if scripts exist and are executable
    local scripts=("cleanup_project.sh" "security_check.sh" "maintenance.sh" "automated_maintenance.sh")
    
    for script in "${scripts[@]}"; do
        if [ -f "$PROJECT_ROOT/$script" ] && [ -x "$PROJECT_ROOT/$script" ]; then
            print_status "$script is ready"
        else
            print_error "$script is missing or not executable"
            return 1
        fi
    done
    
    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/logs"
    print_status "Logs directory ready"
    
    return 0
}

install_launchd() {
    print_info "Installing macOS LaunchAgent for daily automation..."
    
    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$LAUNCHD_DIR"
    
    # Copy plist file
    cp "$PROJECT_ROOT/$PLIST_FILE" "$LAUNCHD_DIR/"
    
    # Load the launch agent
    launchctl load "$LAUNCHD_DIR/$PLIST_FILE"
    
    if [ $? -eq 0 ]; then
        print_status "LaunchAgent installed and loaded"
        print_info "Maintenance will run daily at 2:00 AM"
        return 0
    else
        print_error "Failed to load LaunchAgent"
        return 1
    fi
}

uninstall_launchd() {
    print_info "Uninstalling LaunchAgent..."
    
    # Unload the launch agent
    launchctl unload "$LAUNCHD_DIR/$PLIST_FILE" 2>/dev/null
    
    # Remove plist file
    rm -f "$LAUNCHD_DIR/$PLIST_FILE"
    
    print_status "LaunchAgent uninstalled"
}

install_cron() {
    print_info "Installing cron job for daily automation..."
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "automated_maintenance.sh"; then
        print_warning "Cron job already exists"
        return 0
    fi
    
    # Add cron job
    (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_ROOT/automated_maintenance.sh") | crontab -
    
    if [ $? -eq 0 ]; then
        print_status "Cron job installed (daily at 2:00 AM)"
        return 0
    else
        print_error "Failed to install cron job"
        return 1
    fi
}

uninstall_cron() {
    print_info "Removing cron job..."
    
    crontab -l 2>/dev/null | grep -v "automated_maintenance.sh" | crontab -
    print_status "Cron job removed"
}

show_status() {
    print_info "Current automation status:"
    
    # Check LaunchAgent
    if [ -f "$LAUNCHD_DIR/$PLIST_FILE" ]; then
        if launchctl list | grep -q "com.hotdurham.maintenance"; then
            print_status "LaunchAgent: Installed and running"
        else
            print_warning "LaunchAgent: Installed but not running"
        fi
    else
        echo "   LaunchAgent: Not installed"
    fi
    
    # Check cron
    if crontab -l 2>/dev/null | grep -q "automated_maintenance.sh"; then
        print_status "Cron job: Installed"
    else
        echo "   Cron job: Not installed"
    fi
    
    # Check recent logs
    echo ""
    print_info "Recent maintenance logs:"
    ls -lt "$PROJECT_ROOT/logs/automated_maintenance_"*.log 2>/dev/null | head -3 | while read line; do
        echo "   $line"
    done
}

test_automation() {
    print_info "Testing automation script..."
    
    cd "$PROJECT_ROOT"
    ./automated_maintenance.sh --force-weekly
    
    if [ $? -eq 0 ]; then
        print_status "Automation test completed successfully"
    else
        print_error "Automation test failed"
    fi
}

print_help() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  install-launchd    Install macOS LaunchAgent (recommended)"
    echo "  uninstall-launchd  Remove macOS LaunchAgent"
    echo "  install-cron       Install cron job (alternative)"
    echo "  uninstall-cron     Remove cron job"
    echo "  status            Show current automation status"
    echo "  test              Test the automation script"
    echo "  help              Show this help"
    echo ""
    echo "Recommended: Use 'install-launchd' for macOS"
}

# Main script logic
print_header

case "$1" in
    install-launchd)
        if check_prerequisites; then
            install_launchd
        fi
        ;;
    uninstall-launchd)
        uninstall_launchd
        ;;
    install-cron)
        if check_prerequisites; then
            install_cron
        fi
        ;;
    uninstall-cron)
        uninstall_cron
        ;;
    status)
        show_status
        ;;
    test)
        if check_prerequisites; then
            test_automation
        fi
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo "🚀 Quick Setup Options:"
        echo ""
        echo "1️⃣  Install automated maintenance (recommended):"
        echo "   ./setup_maintenance_automation.sh install-launchd"
        echo ""
        echo "2️⃣  Test the automation:"
        echo "   ./setup_maintenance_automation.sh test"
        echo ""
        echo "3️⃣  Check status:"
        echo "   ./setup_maintenance_automation.sh status"
        echo ""
        echo "For more options, run: ./setup_maintenance_automation.sh help"
        ;;
esac
