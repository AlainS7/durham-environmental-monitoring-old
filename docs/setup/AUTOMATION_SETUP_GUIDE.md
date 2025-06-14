# 🤖 Automated Maintenance Setup Guide

## Quick Setup (Recommended)

### 1. Install Automated Maintenance
```bash
./setup_maintenance_automation.sh install-launchd
```

This will:
- ✅ Install a macOS LaunchAgent that runs daily at 2:00 AM
- ✅ Automatically run cleanup, security checks, and weekly maintenance
- ✅ Send notifications if tasks fail
- ✅ Log all activities

### 2. Check Status
```bash
./setup_maintenance_automation.sh status
```

### 3. Test Before Installing
```bash
./setup_maintenance_automation.sh test
```

## What Gets Automated

### Daily Tasks (Every day at 2:00 AM):
- **Cleanup**: `./cleanup_project.sh`
  - Remove Python cache files
  - Clean temporary files
  - Remove old logs
  - Clean auto-generated configs
  
- **Security Check**: `./security_check.sh`
  - Scan for sensitive files in Git
  - Check for hardcoded secrets
  - Verify .gitignore effectiveness
  - Check for large files

### Weekly Tasks (Mondays at 2:00 AM):
- **Full Maintenance**: `./maintenance.sh`
  - All daily tasks plus:
  - Git repository health check
  - Python package update checks
  - Repository size analysis

## Manual Commands

You can still run these manually anytime:

```bash
# Individual tasks
./cleanup_project.sh          # Clean up files
./security_check.sh           # Security audit
./maintenance.sh              # Full maintenance

# Automated maintenance script
./automated_maintenance.sh                # Daily tasks only
./automated_maintenance.sh --force-weekly # Force all tasks
```

## Automation Options

### Option 1: macOS LaunchAgent (Recommended)
```bash
./setup_maintenance_automation.sh install-launchd
```
- ✅ More reliable than cron on macOS
- ✅ Runs even if Terminal is closed
- ✅ Better error handling
- ✅ System notifications

### Option 2: Cron Job (Alternative)
```bash
./setup_maintenance_automation.sh install-cron
```
- ✅ Traditional Unix scheduling
- ✅ Works on all Unix systems
- ⚠️  May not run if system is sleeping

## Logs and Monitoring

### Log Locations:
- `logs/automated_maintenance_YYYYMMDD_HHMMSS.log` - Detailed logs
- `logs/launchd_maintenance.log` - LaunchAgent output
- `logs/launchd_maintenance_error.log` - LaunchAgent errors

### Monitoring:
- System notifications for failures
- Detailed logs for troubleshooting
- Status command to check current state

## Uninstalling

To remove automation:
```bash
# Remove LaunchAgent
./setup_maintenance_automation.sh uninstall-launchd

# Remove cron job
./setup_maintenance_automation.sh uninstall-cron
```

## Troubleshooting

### Check if automation is running:
```bash
./setup_maintenance_automation.sh status
```

### View recent logs:
```bash
ls -la logs/automated_maintenance_*.log | tail -5
tail -20 logs/automated_maintenance_*.log
```

### Test manually:
```bash
./setup_maintenance_automation.sh test
```

### Force run with all tasks:
```bash
./automated_maintenance.sh --force-weekly
```

## Summary

Once installed, your Hot Durham project will automatically:
- 🧹 Stay clean and organized
- 🔒 Remain secure from accidental commits
- 📊 Monitor repository health
- 📝 Generate detailed logs
- 🔔 Alert you to any issues

**Installation is one command**: `./setup_maintenance_automation.sh install-launchd`
