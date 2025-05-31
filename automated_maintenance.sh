#!/bin/zsh
# automated_maintenance.sh - Automated maintenance scheduler for Hot Durham project

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
LOG_DIR="$PROJECT_ROOT/logs"
MAINTENANCE_LOG="$LOG_DIR/automated_maintenance_$(date +%Y%m%d_%H%M%S).log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MAINTENANCE_LOG"
}

# Function to run maintenance task
run_maintenance_task() {
    local task_name="$1"
    local script_path="$2"
    local frequency="$3"
    
    log_with_timestamp "🔄 Starting $task_name ($frequency)"
    
    if [ -f "$script_path" ] && [ -x "$script_path" ]; then
        cd "$PROJECT_ROOT"
        if "$script_path" >> "$MAINTENANCE_LOG" 2>&1; then
            log_with_timestamp "✅ $task_name completed successfully"
            return 0
        else
            log_with_timestamp "❌ $task_name failed"
            return 1
        fi
    else
        log_with_timestamp "❌ $task_name script not found or not executable: $script_path"
        return 1
    fi
}

# Main automation logic
main() {
    log_with_timestamp "🤖 Starting automated maintenance for Hot Durham project"
    
    local cleanup_success=0
    local security_success=0
    local maintenance_success=0
    
    # Always run cleanup (daily)
    run_maintenance_task "Project Cleanup" "$PROJECT_ROOT/cleanup_project.sh" "daily"
    cleanup_success=$?
    
    # Always run security check (daily)
    run_maintenance_task "Security Check" "$PROJECT_ROOT/security_check.sh" "daily"
    security_success=$?
    
    # Run full maintenance based on day of week
    local day_of_week=$(date +%u)  # 1=Monday, 7=Sunday
    
    if [ "$day_of_week" -eq 1 ] || [ "$1" = "--force-weekly" ]; then
        run_maintenance_task "Weekly Maintenance" "$PROJECT_ROOT/maintenance.sh" "weekly"
        maintenance_success=$?
    else
        log_with_timestamp "ℹ️  Skipping weekly maintenance (runs on Mondays)"
        maintenance_success=0
    fi
    
    # Summary
    log_with_timestamp "📊 Maintenance Summary:"
    log_with_timestamp "   Cleanup: $([ $cleanup_success -eq 0 ] && echo "✅ Success" || echo "❌ Failed")"
    log_with_timestamp "   Security: $([ $security_success -eq 0 ] && echo "✅ Success" || echo "❌ Failed")"
    log_with_timestamp "   Weekly: $([ $maintenance_success -eq 0 ] && echo "✅ Success" || echo "ℹ️  Skipped/Failed")"
    
    # Send notification if any task failed
    local total_failures=$((cleanup_success + security_success + maintenance_success))
    if [ $total_failures -gt 0 ]; then
        log_with_timestamp "⚠️  $total_failures maintenance task(s) failed - check logs"
        # Send system notification
        osascript -e "display notification \"Hot Durham maintenance tasks failed. Check logs at $MAINTENANCE_LOG\" with title \"Maintenance Alert\""
    else
        log_with_timestamp "🎉 All maintenance tasks completed successfully"
    fi
    
    log_with_timestamp "📝 Full log saved to: $MAINTENANCE_LOG"
    
    return $total_failures
}

# Handle command line arguments
case "$1" in
    --install-cron)
        echo "📅 Installing cron jobs for automated maintenance..."
        # Create cron entry for daily maintenance at 2 AM
        (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_ROOT/automated_maintenance.sh") | crontab -
        echo "✅ Cron job installed: Daily maintenance at 2:00 AM"
        echo "📋 To view: crontab -l"
        echo "📋 To remove: crontab -e (then delete the line)"
        ;;
    --uninstall-cron)
        echo "🗑️  Removing cron jobs..."
        crontab -l 2>/dev/null | grep -v "automated_maintenance.sh" | crontab -
        echo "✅ Cron jobs removed"
        ;;
    --force-weekly)
        echo "🔧 Running maintenance with forced weekly tasks..."
        main --force-weekly
        ;;
    --help|-h)
        echo "🤖 Hot Durham Automated Maintenance"
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  --install-cron     Install daily cron job (2 AM)"
        echo "  --uninstall-cron   Remove cron jobs"
        echo "  --force-weekly     Run all tasks including weekly"
        echo "  --help, -h         Show this help"
        echo ""
        echo "Without options: Run daily maintenance tasks"
        echo ""
        echo "Scheduled Tasks:"
        echo "  Daily:  cleanup_project.sh + security_check.sh"
        echo "  Weekly: maintenance.sh (Mondays only)"
        ;;
    *)
        main
        ;;
esac
