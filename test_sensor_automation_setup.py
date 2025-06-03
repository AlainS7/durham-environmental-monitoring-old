#!/usr/bin/env python3
"""
Test Sensor Automation Setup and Integration Script

This script helps integrate the 15-minute test sensor automation with the existing
Hot Durham automation infrastructure. It provides setup, monitoring, and management
capabilities for the test sensor data collection system.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_header():
    print("🧪 Hot Durham Test Sensor 15-Minute Automation Setup")
    print("=" * 55)
    print()

def print_status(message):
    print(f"✅ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def check_system_requirements():
    """Check if all required components are available."""
    print_info("Checking system requirements...")
    
    issues = []
    
    # Check Python modules
    required_modules = ['pandas', 'requests', 'httpx', 'schedule', 'nest_asyncio']
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            issues.append(f"Missing Python module: {module}")
    
    # Check credential files
    creds_dir = project_root / "creds"
    required_creds = ['wu_api_key.json', 'google_creds.json']
    for cred_file in required_creds:
        if not (creds_dir / cred_file).exists():
            issues.append(f"Missing credential file: {cred_file}")
    
    # Check test sensor configuration
    config_file = project_root / "config" / "test_sensors_config.py"
    if not config_file.exists():
        issues.append("Missing test sensor configuration file")
    
    if issues:
        print_error("System requirements check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print_status("All system requirements met")
        return True

def setup_test_sensor_automation():
    """Set up the test sensor automation system."""
    print_info("Setting up test sensor automation...")
    
    # Run a test collection to verify everything works
    manager_script = project_root / "src" / "automation" / "test_sensor_manager.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(manager_script), "test"],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_status("Test sensor system verified and configured")
            return True
        else:
            print_error("Test sensor system verification failed")
            print(result.stderr)
            return False
    except Exception as e:
        print_error(f"Error setting up test sensor automation: {e}")
        return False

def create_launch_daemon():
    """Create a macOS launch daemon for the test sensor automation."""
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hotdurham.testsensor.automation</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{project_root}/src/automation/test_sensor_manager.py</string>
        <string>start</string>
        <string>--foreground</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{project_root}</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>{project_root}/logs/test_sensor_launchd.out</string>
    
    <key>StandardErrorPath</key>
    <string>{project_root}/logs/test_sensor_launchd.err</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>"""
    
    plist_file = project_root / "com.hotdurham.testsensor.automation.plist"
    
    try:
        with open(plist_file, 'w') as f:
            f.write(plist_content)
        print_status(f"Created launch daemon plist: {plist_file}")
        return plist_file
    except Exception as e:
        print_error(f"Error creating launch daemon: {e}")
        return None

def install_launch_daemon():
    """Install the macOS launch daemon."""
    plist_file = create_launch_daemon()
    if not plist_file:
        return False
    
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(exist_ok=True)
    
    target_plist = launch_agents_dir / "com.hotdurham.testsensor.automation.plist"
    
    try:
        # Copy plist to LaunchAgents directory
        import shutil
        shutil.copy2(plist_file, target_plist)
        
        # Load the launch agent
        result = subprocess.run(
            ["launchctl", "load", str(target_plist)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_status("Test sensor automation installed and started")
            print_info("The 15-minute test sensor collection will run automatically")
            return True
        else:
            print_error(f"Failed to load launch agent: {result.stderr}")
            return False
            
    except Exception as e:
        print_error(f"Error installing launch daemon: {e}")
        return False

def create_monitoring_script():
    """Create a script to monitor test sensor automation."""
    monitoring_script_content = f"""#!/usr/bin/env python3
\"\"\"
Test Sensor Monitoring Script
Checks the health and status of the 15-minute test sensor automation.
\"\"\"

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path("{project_root}")
sys.path.insert(0, str(project_root))

def check_test_sensor_health():
    \"\"\"Check the health of the test sensor automation system.\"\"\"
    print("🔍 Test Sensor Health Check")
    print("=" * 30)
    
    issues = []
    
    # Check last collection time
    last_collection_file = project_root / "data" / "test_sensors" / "last_collection.json"
    if last_collection_file.exists():
        try:
            with open(last_collection_file, 'r') as f:
                data = json.load(f)
                last_collection = datetime.fromisoformat(data["last_collection"])
                time_since = datetime.now() - last_collection
                
                if time_since > timedelta(minutes=30):
                    issues.append(f"Last collection was {{time_since}} ago (expected < 30 min)")
                else:
                    print(f"✅ Last collection: {{data['last_collection_readable']}}")
        except Exception as e:
            issues.append(f"Error reading last collection: {{e}}")
    else:
        issues.append("No collection history found")
    
    # Check recent data files
    data_dir = project_root / "data" / "test_sensors"
    if data_dir.exists():
        now = datetime.now()
        recent_files = [
            f for f in data_dir.glob("test_sensors_*.json")
            if (now - datetime.fromtimestamp(f.stat().st_mtime)).hours < 24
        ]
        
        if len(recent_files) < 80:  # Should have ~96 files per day
            issues.append(f"Only {{len(recent_files)}} collection files in last 24h (expected ~96)")
        else:
            print(f"✅ Data files (24h): {{len(recent_files)}}")
    
    # Report issues
    if issues:
        print("\\n⚠️ Issues found:")
        for issue in issues:
            print(f"  - {{issue}}")
        return False
    else:
        print("\\n✅ Test sensor system is healthy")
        return True

if __name__ == "__main__":
    success = check_test_sensor_health()
    sys.exit(0 if success else 1)
"""
    
    monitoring_script = project_root / "test_sensor_health_check.py"
    
    try:
        with open(monitoring_script, 'w') as f:
            f.write(monitoring_script_content)
        
        # Make executable
        monitoring_script.chmod(0o755)
        print_status(f"Created monitoring script: {monitoring_script}")
        return monitoring_script
    except Exception as e:
        print_error(f"Error creating monitoring script: {e}")
        return None

def integrate_with_existing_automation():
    """Integrate test sensor monitoring with existing automation."""
    print_info("Integrating with existing Hot Durham automation...")
    
    # Create the monitoring script
    monitoring_script = create_monitoring_script()
    if not monitoring_script:
        return False
    
    # Add to existing maintenance script
    maintenance_script = project_root / "automated_maintenance.sh"
    if maintenance_script.exists():
        try:
            with open(maintenance_script, 'r') as f:
                content = f.read()
            
            # Check if test sensor monitoring is already integrated
            if "test_sensor_health_check.py" not in content:
                # Find a good place to add the health check
                # Add it after the security check
                integration_line = """
    # Test sensor health check
    run_maintenance_task "Test Sensor Health Check" "$PROJECT_ROOT/test_sensor_health_check.py" "daily"
    test_sensor_success=$?
"""
                
                # Find the security check line and add after it
                if "security_success=$?" in content:
                    content = content.replace(
                        "    security_success=$?",
                        f"    security_success=$?{integration_line}"
                    )
                    
                    # Update the summary section
                    if "log_with_timestamp \"   Security:" in content:
                        content = content.replace(
                            'log_with_timestamp "   Security: $([ $security_success -eq 0 ] && echo "✅ Success" || echo "❌ Failed")"',
                            '''log_with_timestamp "   Security: $([ $security_success -eq 0 ] && echo "✅ Success" || echo "❌ Failed")"
    log_with_timestamp "   Test Sensors: $([ $test_sensor_success -eq 0 ] && echo "✅ Healthy" || echo "⚠️ Issues")"'''
                        )
                    
                    # Update failure count calculation
                    content = content.replace(
                        "local total_failures=$((cleanup_success + security_success + maintenance_success))",
                        "local total_failures=$((cleanup_success + security_success + test_sensor_success + maintenance_success))"
                    )
                    
                    with open(maintenance_script, 'w') as f:
                        f.write(content)
                    
                    print_status("Integrated test sensor monitoring with automated maintenance")
                    return True
                else:
                    print_warning("Could not find integration point in maintenance script")
                    return False
            else:
                print_status("Test sensor monitoring already integrated")
                return True
                
        except Exception as e:
            print_error(f"Error integrating with maintenance script: {e}")
            return False
    else:
        print_warning("Automated maintenance script not found - manual integration required")
        return False

def show_status():
    """Show the current status of test sensor automation."""
    print_info("Current Test Sensor Automation Status:")
    print()
    
    # Check if launch daemon is running
    try:
        result = subprocess.run(
            ["launchctl", "list", "com.hotdurham.testsensor.automation"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_status("Launch daemon is running")
        else:
            print_warning("Launch daemon is not running")
    except Exception:
        print_warning("Could not check launch daemon status")
    
    # Check recent activity
    manager_script = project_root / "src" / "automation" / "test_sensor_manager.py"
    try:
        result = subprocess.run(
            [sys.executable, str(manager_script), "status"],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )
        print(result.stdout)
    except Exception as e:
        print_error(f"Error checking status: {e}")

def main():
    """Main entry point for test sensor automation setup."""
    parser = argparse.ArgumentParser(
        description='Test Sensor 15-Minute Automation Setup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s setup              # Full setup and installation
  %(prog)s install-daemon     # Install macOS launch daemon
  %(prog)s integrate          # Integrate with existing automation
  %(prog)s status             # Show current status
  %(prog)s monitor            # Run health check
        """
    )
    
    parser.add_argument('command', nargs='?',
                       choices=['setup', 'install-daemon', 'integrate', 'status', 'monitor'],
                       help='Command to execute')
    
    args = parser.parse_args()
    
    print_header()
    
    if args.command == 'setup':
        print_info("Running full test sensor automation setup...")
        
        if not check_system_requirements():
            sys.exit(1)
        
        if not setup_test_sensor_automation():
            sys.exit(1)
        
        if install_launch_daemon():
            print_status("✅ Test sensor automation setup completed successfully!")
            print()
            print_info("The system will now:")
            print("  • Collect data from 14 test sensors every 15 minutes")
            print("  • Store data locally and upload to Google Drive")
            print("  • Run health checks and monitoring")
            print("  • Integrate with existing Hot Durham automation")
            print()
            print_info("Use 'python test_sensor_automation_setup.py status' to monitor")
        else:
            print_error("Setup completed with issues - manual start may be required")
            sys.exit(1)
    
    elif args.command == 'install-daemon':
        if install_launch_daemon():
            print_status("Launch daemon installed successfully")
        else:
            sys.exit(1)
    
    elif args.command == 'integrate':
        if integrate_with_existing_automation():
            print_status("Integration completed successfully")
        else:
            sys.exit(1)
    
    elif args.command == 'status':
        show_status()
    
    elif args.command == 'monitor':
        monitoring_script = project_root / "test_sensor_health_check.py"
        if monitoring_script.exists():
            subprocess.run([sys.executable, str(monitoring_script)])
        else:
            print_error("Monitoring script not found - run setup first")
    
    else:
        print("🚀 Quick Setup Guide:")
        print()
        print("1️⃣  Full automated setup (recommended):")
        print("   python test_sensor_automation_setup.py setup")
        print()
        print("2️⃣  Check current status:")
        print("   python test_sensor_automation_setup.py status")
        print()
        print("3️⃣  Monitor system health:")
        print("   python test_sensor_automation_setup.py monitor")
        print()
        print("📋 Manual Management:")
        print("   python src/automation/test_sensor_manager.py start     # Start manually")
        print("   python src/automation/test_sensor_manager.py stop      # Stop manually")
        print("   python src/automation/test_sensor_manager.py test      # Test collection")
        print()
        print("For detailed help: python test_sensor_automation_setup.py --help")

if __name__ == "__main__":
    main()
