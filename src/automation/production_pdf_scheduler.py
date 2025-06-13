#!/usr/bin/env python3
"""
Production Sensor PDF Report Automation
========================================

This script automates the generation of production sensor PDF reports on a schedule.
It integrates with the existing Hot Durham automation system and can be run
daily, weekly, or on-demand.

Features:
- Automated PDF report generation
- Smart scheduling (daily/weekly/monthly)
- Google Drive integration
- Error handling and logging
- Status tracking and monitoring
- Integration with existing automation framework

Usage:
    python src/automation/production_pdf_scheduler.py [options]

Options:
    --schedule TYPE   : Schedule type (daily/weekly/monthly)
    --force          : Force generation regardless of schedule
    --config FILE    : Custom configuration file
    --dry-run        : Show what would be done without executing

Author: Hot Durham Project
Date: June 2025
"""

import sys
import os
import json
import argparse
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class ProductionPDFScheduler:
    """Scheduler for automated production sensor PDF report generation."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.project_root = project_root
        self.config_file = config_file or (self.project_root / "config" / "production_pdf_config.json")
        self.log_file = self.project_root / "logs" / "production_pdf_scheduler.log"
        self.status_file = self.project_root / "logs" / "production_pdf_status.json"
        
        # Ensure directories exist
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.config = self.load_configuration()
        
        # Status tracking
        self.status = self.load_status()
        
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_configuration(self) -> Dict:
        """Load scheduler configuration."""
        default_config = {
            "schedule": {
                "type": "weekly",  # daily, weekly, monthly
                "time": "06:00",   # Time to run (24-hour format)
                "day": "monday"    # Day for weekly/monthly (monday, tuesday, etc.)
            },
            "report_settings": {
                "days_back": 16,
                "upload_to_drive": True,
                "retention_days": 30
            },
            "automation": {
                "enabled": True,
                "max_retries": 3,
                "retry_delay_minutes": 15
            },
            "notifications": {
                "log_level": "INFO",
                "alert_on_failure": True
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    default_config.update(user_config)
                    self.logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                self.logger.warning(f"Error loading config file, using defaults: {e}")
        else:
            # Create default config file
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                self.logger.info(f"Created default configuration at {self.config_file}")
            except Exception as e:
                self.logger.warning(f"Could not create config file: {e}")
        
        return default_config
    
    def load_status(self) -> Dict:
        """Load scheduler status."""
        default_status = {
            "last_run": None,
            "last_success": None,
            "consecutive_failures": 0,
            "total_runs": 0,
            "total_successes": 0
        }
        
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading status file: {e}")
        
        return default_status
    
    def save_status(self):
        """Save scheduler status."""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving status: {e}")
    
    def should_run_today(self) -> bool:
        """Check if report should be generated today based on schedule."""
        if not self.config["automation"]["enabled"]:
            return False
        
        schedule_type = self.config["schedule"]["type"]
        
        if schedule_type == "daily":
            return True
        elif schedule_type == "weekly":
            target_day = self.config["schedule"]["day"].lower()
            today = datetime.now().strftime("%A").lower()
            return today == target_day
        elif schedule_type == "monthly":
            # Run on first occurrence of target day each month
            today = datetime.now()
            target_day = self.config["schedule"]["day"].lower()
            
            # Find first occurrence of target day this month
            first_day = today.replace(day=1)
            days_ahead = (list(["monday", "tuesday", "wednesday", "thursday", 
                               "friday", "saturday", "sunday"]).index(target_day) - 
                         first_day.weekday()) % 7
            target_date = first_day + timedelta(days=days_ahead)
            
            return today.date() == target_date.date()
        
        return False
    
    def generate_report(self, force: bool = False) -> bool:
        """
        Generate production sensor PDF report.
        
        Args:
            force: Force generation regardless of schedule
            
        Returns:
            True if successful, False otherwise
        """
        self.status["total_runs"] += 1
        self.status["last_run"] = datetime.now().isoformat()
        
        try:
            self.logger.info("Starting production sensor PDF report generation")
            
            # Check if we should run today
            if not force and not self.should_run_today():
                self.logger.info("Skipping report generation - not scheduled for today")
                return True
            
            # Import and run the report generator
            sys.path.insert(0, str(self.project_root))
            
            # Use subprocess to run the standalone script
            import subprocess
            
            script_path = self.project_root / "generate_production_pdf_report.py"
            
            cmd = [
                sys.executable,
                str(script_path),
                f"--days-back={self.config['report_settings']['days_back']}"
            ]
            
            if self.config["report_settings"]["upload_to_drive"]:
                cmd.append("--upload-drive")
            else:
                cmd.append("--no-upload")
            
            # Run the report generation
            self.logger.info(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )
            
            if result.returncode == 0:
                self.logger.info("PDF report generation completed successfully")
                self.status["last_success"] = datetime.now().isoformat()
                self.status["consecutive_failures"] = 0
                self.status["total_successes"] += 1
                
                # Log output
                if result.stdout:
                    self.logger.info(f"Generator output: {result.stdout}")
                
                return True
            else:
                self.logger.error(f"PDF report generation failed with return code {result.returncode}")
                if result.stderr:
                    self.logger.error(f"Error output: {result.stderr}")
                
                self.status["consecutive_failures"] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Error during report generation: {e}", exc_info=True)
            self.status["consecutive_failures"] += 1
            return False
        finally:
            self.save_status()
    
    def cleanup_old_reports(self):
        """Clean up old PDF reports based on retention policy."""
        try:
            retention_days = self.config["report_settings"]["retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            reports_dir = self.project_root / "sensor_visualizations" / "production_pdf_reports"
            
            if not reports_dir.exists():
                return
            
            deleted_count = 0
            for pdf_file in reports_dir.glob("*.pdf"):
                if pdf_file.stat().st_mtime < cutoff_date.timestamp():
                    try:
                        pdf_file.unlink()
                        deleted_count += 1
                        self.logger.info(f"Deleted old report: {pdf_file.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete {pdf_file.name}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old PDF reports")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_status_summary(self) -> Dict:
        """Get status summary for monitoring."""
        return {
            "scheduler_active": self.config["automation"]["enabled"],
            "schedule_type": self.config["schedule"]["type"],
            "last_run": self.status.get("last_run"),
            "last_success": self.status.get("last_success"),
            "consecutive_failures": self.status.get("consecutive_failures", 0),
            "total_runs": self.status.get("total_runs", 0),
            "total_successes": self.status.get("total_successes", 0),
            "success_rate": (self.status.get("total_successes", 0) / 
                           max(1, self.status.get("total_runs", 1))) * 100
        }
    
    def run_scheduler(self):
        """Run the scheduler in continuous mode."""
        self.logger.info("Starting Production PDF Report Scheduler")
        self.logger.info(f"Schedule: {self.config['schedule']['type']} at {self.config['schedule']['time']}")
        
        # Setup schedule
        schedule_time = self.config["schedule"]["time"]
        
        if self.config["schedule"]["type"] == "daily":
            schedule.every().day.at(schedule_time).do(self.generate_report)
        elif self.config["schedule"]["type"] == "weekly":
            day = self.config["schedule"]["day"].lower()
            getattr(schedule.every(), day).at(schedule_time).do(self.generate_report)
        elif self.config["schedule"]["type"] == "monthly":
            # For monthly, we'll check daily and use should_run_today logic
            schedule.every().day.at(schedule_time).do(self.generate_report)
        
        # Also schedule cleanup
        schedule.every().day.at("02:00").do(self.cleanup_old_reports)
        
        self.logger.info("Scheduler started, waiting for scheduled times...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Production Sensor PDF Report Automation"
    )
    
    parser.add_argument(
        '--schedule',
        choices=['daily', 'weekly', 'monthly'],
        help='Override schedule type'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force generation regardless of schedule'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Custom configuration file path'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without executing'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show scheduler status and exit'
    )
    
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run report generation once and exit'
    )
    
    args = parser.parse_args()
    
    try:
        scheduler = ProductionPDFScheduler(args.config)
        
        if args.status:
            # Show status
            status = scheduler.get_status_summary()
            print("\n📊 Production PDF Scheduler Status")
            print("=" * 40)
            for key, value in status.items():
                print(f"{key}: {value}")
            return 0
        
        if args.run_once or args.force:
            # Run once
            print("🔄 Running production PDF report generation...")
            success = scheduler.generate_report(force=True)
            if success:
                print("✅ Report generation completed successfully")
                return 0
            else:
                print("❌ Report generation failed")
                return 1
        
        if args.dry_run:
            print("🔍 Dry run mode - showing configuration:")
            print(f"Schedule: {scheduler.config['schedule']}")
            print(f"Would run today: {scheduler.should_run_today()}")
            print(f"Upload to drive: {scheduler.config['report_settings']['upload_to_drive']}")
            return 0
        
        # Run scheduler continuously
        scheduler.run_scheduler()
        
    except KeyboardInterrupt:
        print("\n⏹️ Scheduler stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
