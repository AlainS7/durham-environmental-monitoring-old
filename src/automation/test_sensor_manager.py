#!/usr/bin/env python3
"""
Test Sensor Automation Manager for Hot Durham Project

This script helps manage the 15-minute test sensor data collection automation.
It provides easy commands for starting, stopping, monitoring, and configuring
the test sensor scheduler.
"""

import os
import sys
import json
import subprocess
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestSensorManager:
    """Manager for test sensor automation operations."""
    
    def __init__(self):
        self.project_root = project_root
        self.scheduler_script = self.project_root / "src" / "automation" / "test_sensor_scheduler.py"
        self.pid_file = self.project_root / "logs" / "test_sensor_scheduler.pid"
        self.log_file = self.project_root / "logs" / "test_sensor_scheduler.log"
        self.config_file = self.project_root / "config" / "test_sensor_scheduler_config.json"
        
        # Ensure directories exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def is_running(self) -> bool:
        """Check if the test sensor scheduler is currently running."""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is still running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, ProcessLookupError):
            # Process doesn't exist, clean up stale PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False
    
    def start_scheduler(self, background: bool = True) -> bool:
        """Start the test sensor scheduler."""
        if self.is_running():
            print("❌ Test sensor scheduler is already running")
            return False
        
        print("🚀 Starting test sensor scheduler...")
        
        try:
            if background:
                # Start in background
                process = subprocess.Popen(
                    [sys.executable, str(self.scheduler_script), "--run"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(self.project_root)
                )
                
                # Save PID
                with open(self.pid_file, 'w') as f:
                    f.write(str(process.pid))
                
                # Wait a moment to check if it started successfully
                time.sleep(2)
                if process.poll() is None:
                    print(f"✅ Test sensor scheduler started successfully (PID: {process.pid})")
                    print(f"📝 Logs: {self.log_file}")
                    return True
                else:
                    print("❌ Failed to start test sensor scheduler")
                    return False
            else:
                # Start in foreground
                result = subprocess.run(
                    [sys.executable, str(self.scheduler_script), "--run"],
                    cwd=str(self.project_root)
                )
                return result.returncode == 0
                
        except Exception as e:
            print(f"❌ Error starting scheduler: {e}")
            return False
    
    def stop_scheduler(self) -> bool:
        """Stop the test sensor scheduler."""
        if not self.is_running():
            print("❌ Test sensor scheduler is not running")
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            print(f"🛑 Stopping test sensor scheduler (PID: {pid})...")
            
            # Try graceful shutdown first
            os.kill(pid, signal.SIGTERM)
            
            # Wait for up to 10 seconds for graceful shutdown
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except ProcessLookupError:
                    break
            else:
                # Force kill if still running
                print("⚠️ Forcing shutdown...")
                os.kill(pid, signal.SIGKILL)
            
            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("✅ Test sensor scheduler stopped successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error stopping scheduler: {e}")
            return False
    
    def restart_scheduler(self) -> bool:
        """Restart the test sensor scheduler."""
        print("🔄 Restarting test sensor scheduler...")
        
        if self.is_running():
            if not self.stop_scheduler():
                return False
            time.sleep(2)
        
        return self.start_scheduler()
    
    def check_status(self):
        """Check and display the status of the test sensor system."""
        print("🔍 Test Sensor Automation Status")
        print("=" * 40)
        
        # Check if scheduler is running
        if self.is_running():
            print("✅ Scheduler Status: Running")
            try:
                with open(self.pid_file, 'r') as f:
                    pid = f.read().strip()
                print(f"📊 Process ID: {pid}")
            except Exception:
                pass
        else:
            print("❌ Scheduler Status: Not running")
        
        # Check recent logs
        if self.log_file.exists():
            print(f"\n📝 Log File: {self.log_file}")
            try:
                # Get last few lines
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-5:] if len(lines) >= 5 else lines
                    
                if recent_lines:
                    print("📄 Recent Log Entries:")
                    for line in recent_lines:
                        print(f"   {line.strip()}")
            except Exception as e:
                print(f"⚠️ Error reading log file: {e}")
        else:
            print("📝 No log file found")
        
        # Check configuration
        if self.config_file.exists():
            print(f"\n⚙️ Configuration: {self.config_file}")
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    print(f"📊 Collection interval: {config.get('collection_settings', {}).get('interval_minutes', 15)} minutes")
                    print(f"📊 Test sensors: {len(config.get('test_sensors', {}).get('wu_sensors', []))} sensors")
                    print(f"📊 Automation enabled: {config.get('automation', {}).get('enabled', True)}")
            except Exception as e:
                print(f"⚠️ Error reading config: {e}")
        else:
            print("⚙️ No configuration file found (will use defaults)")
        
        # Check data directory
        data_dir = self.project_root / "data" / "test_sensors"
        if data_dir.exists():
            print(f"\n📁 Data Directory: {data_dir}")
            
            # Count recent files
            now = datetime.now()
            today_files = [
                f for f in data_dir.glob("test_sensors_*.json")
                if (now - datetime.fromtimestamp(f.stat().st_mtime)).days < 1
            ]
            
            print(f"📊 Data files (last 24h): {len(today_files)}")
            
            # Check last collection
            last_collection_file = data_dir / "last_collection.json"
            if last_collection_file.exists():
                try:
                    with open(last_collection_file, 'r') as f:
                        last_data = json.load(f)
                        last_time = last_data.get("last_collection_readable", "Unknown")
                        print(f"📊 Last collection: {last_time}")
                except Exception:
                    print("📊 Last collection: Unknown")
        else:
            print("📁 Data directory not found")
    
    def run_test_collection(self) -> bool:
        """Run a test collection to verify everything works."""
        print("🧪 Running test collection...")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.scheduler_script), "--test"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Test collection completed successfully")
                print(result.stdout)
                return True
            else:
                print("❌ Test collection failed")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error running test collection: {e}")
            return False
    
    def show_schedule_info(self):
        """Show information about the scheduled jobs."""
        print("📅 Test Sensor Schedule Information")
        print("=" * 40)
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.scheduler_script), "--schedule-info"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("❌ Error getting schedule info")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Error getting schedule info: {e}")
    
    def view_logs(self, lines: int = 50):
        """View recent log entries."""
        if not self.log_file.exists():
            print("📝 No log file found")
            return
        
        print(f"📝 Last {lines} lines from {self.log_file}")
        print("=" * 60)
        
        try:
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) >= lines else all_lines
                
                for line in recent_lines:
                    print(line.rstrip())
                    
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
    
    def edit_config(self):
        """Open the configuration file for editing."""
        if not self.config_file.exists():
            print("⚙️ Configuration file doesn't exist yet. Run --test first to create it.")
            return
        
        try:
            # Try to open with system default editor
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(self.config_file)])
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", str(self.config_file)])
            else:
                print(f"📝 Please edit the configuration file: {self.config_file}")
        except Exception as e:
            print(f"❌ Error opening config file: {e}")
            print(f"📝 Please manually edit: {self.config_file}")


def main():
    """Main entry point for the test sensor manager."""
    parser = argparse.ArgumentParser(
        description='Test Sensor Automation Manager for Hot Durham Project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start              # Start the 15-minute scheduler
  %(prog)s status             # Check system status
  %(prog)s test               # Run a test collection
  %(prog)s logs               # View recent logs
  %(prog)s stop               # Stop the scheduler
        """
    )
    
    parser.add_argument('command', nargs='?', 
                       choices=['start', 'stop', 'restart', 'status', 'test', 'schedule', 'logs', 'config'],
                       help='Command to execute')
    parser.add_argument('--foreground', action='store_true', 
                       help='Run scheduler in foreground (not as background process)')
    parser.add_argument('--lines', type=int, default=50,
                       help='Number of log lines to show (default: 50)')
    
    args = parser.parse_args()
    
    manager = TestSensorManager()
    
    if args.command == 'start':
        success = manager.start_scheduler(background=not args.foreground)
        sys.exit(0 if success else 1)
    
    elif args.command == 'stop':
        success = manager.stop_scheduler()
        sys.exit(0 if success else 1)
    
    elif args.command == 'restart':
        success = manager.restart_scheduler()
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        manager.check_status()
    
    elif args.command == 'test':
        success = manager.run_test_collection()
        sys.exit(0 if success else 1)
    
    elif args.command == 'schedule':
        manager.show_schedule_info()
    
    elif args.command == 'logs':
        manager.view_logs(args.lines)
    
    elif args.command == 'config':
        manager.edit_config()
    
    else:
        print("🤖 Hot Durham Test Sensor Automation Manager")
        print("=" * 45)
        print("")
        print("Available commands:")
        print("  start     - Start the 15-minute data collection scheduler")
        print("  stop      - Stop the scheduler")
        print("  restart   - Restart the scheduler")
        print("  status    - Check system status and recent activity")
        print("  test      - Run a test collection to verify setup")
        print("  schedule  - Show schedule information")
        print("  logs      - View recent log entries")
        print("  config    - Edit configuration file")
        print("")
        print("Quick start:")
        print("  1. Run 'python test_sensor_manager.py test' to verify setup")
        print("  2. Run 'python test_sensor_manager.py start' to begin automation")
        print("  3. Run 'python test_sensor_manager.py status' to monitor")


if __name__ == "__main__":
    main()
