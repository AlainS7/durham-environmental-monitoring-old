#!/usr/bin/env python3
"""
Master Data Scheduler for Hot Durham Air Quality Monitoring

Automated scheduler for master data file system that:
1. Runs weekly updates every Sunday at 2:00 AM
2. Monitors system health and data quality
3. Handles error recovery and notifications
4. Manages backup cleanup and maintenance

This scheduler integrates with the master data file system to ensure continuous
data collection and master file updates.
"""

import os
import sys
import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import traceback

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "src" / "automation"))

try:
    from master_data_file_system import MasterDataFileSystem
except ImportError as e:
    print(f"Error importing master data system: {e}")
    sys.exit(1)

class MasterDataScheduler:
    """Scheduler for automated master data file operations."""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else project_root / "config" / "master_data_config.json"
        self.log_file = project_root / "logs" / "master_data_scheduler.log"
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize master data system
        self.master_system = MasterDataFileSystem()
        
        # Setup schedules
        self.setup_schedules()
        
    def setup_logging(self):
        """Configure logging for scheduler operations."""
        # Ensure logs directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """Load scheduler configuration."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                self.logger.warning("Config file not found, using defaults")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return {}
            
    def setup_schedules(self):
        """Setup automated schedules based on configuration."""
        automation_config = self.config.get("automation", {})
        
        # Weekly master data update
        if automation_config.get("auto_weekly_update", True):
            update_day = automation_config.get("update_day_of_week", "sunday")
            update_time = automation_config.get("update_time", "02:00")
            
            getattr(schedule.every(), update_day).at(update_time).do(self.weekly_update_job)
            self.logger.info(f"Scheduled weekly updates for {update_day} at {update_time}")
            
        # Weekly backup cleanup (every Sunday at 3:00 AM)
        schedule.every().sunday.at("03:00").do(self.cleanup_job)
        self.logger.info("Scheduled weekly backup cleanup for Sunday at 03:00")
        
        # Daily health check (every day at 1:00 AM)
        schedule.every().day.at("01:00").do(self.health_check_job)
        self.logger.info("Scheduled daily health checks for 01:00")
        
        # Monthly exports (first day of month at 4:00 AM)
        schedule.every().day.at("04:00").do(self.monthly_export_job)
        self.logger.info("Scheduled monthly exports for 04:00 (runs on 1st of month)")
        
    def weekly_update_job(self):
        """Execute weekly master data update."""
        self.logger.info("🔄 Starting scheduled weekly master data update")
        
        try:
            # Record start time
            start_time = datetime.now()
            
            # Perform weekly update
            results = self.master_system.weekly_update()
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log results
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            if success_count == total_count:
                self.logger.info(f"✅ Weekly update completed successfully in {execution_time:.1f}s")
                self.logger.info(f"📊 Results: {results}")
            else:
                self.logger.warning(f"⚠️ Weekly update completed with issues: {results}")
                
            # Log execution metadata
            self.log_execution_metadata("weekly_update", {
                "start_time": start_time.isoformat(),
                "execution_time_seconds": execution_time,
                "results": results,
                "success": success_count == total_count
            })
            
            # Create combined master file if any updates succeeded
            if success_count > 0:
                self.master_system.create_combined_master_file()
                
        except Exception as e:
            self.logger.error(f"❌ Error during weekly update: {e}")
            self.logger.error(traceback.format_exc())
            
            # Log error metadata
            self.log_execution_metadata("weekly_update", {
                "start_time": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            })
            
    def cleanup_job(self):
        """Execute backup cleanup."""
        self.logger.info("🧹 Starting scheduled backup cleanup")
        
        try:
            retention_days = self.config.get("master_file_settings", {}).get("backup_retention_days", 365)
            self.master_system.cleanup_old_backups(retention_days)
            self.logger.info("✅ Backup cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error during backup cleanup: {e}")
            self.logger.error(traceback.format_exc())
            
    def health_check_job(self):
        """Execute daily health check."""
        self.logger.info("🔍 Starting scheduled health check")
        
        try:
            # Get master data summary
            summary = self.master_system.get_master_data_summary()
            
            # Check for issues
            issues = []
            
            # Check WU data
            wu_data = summary.get("wu_data", {})
            if not wu_data.get("file_exists", False):
                issues.append("WU master file does not exist")
            elif "error" in wu_data:
                issues.append(f"WU master file error: {wu_data['error']}")
            elif wu_data.get("total_records", 0) == 0:
                issues.append("WU master file has no records")
                
            # Check TSI data
            tsi_data = summary.get("tsi_data", {})
            if not tsi_data.get("file_exists", False):
                issues.append("TSI master file does not exist")
            elif "error" in tsi_data:
                issues.append(f"TSI master file error: {tsi_data['error']}")
            elif tsi_data.get("total_records", 0) == 0:
                issues.append("TSI master file has no records")
                
            # Check combined data
            combined_data = summary.get("combined_data", {})
            if not combined_data.get("file_exists", False):
                issues.append("Combined master file does not exist")
            elif "error" in combined_data:
                issues.append(f"Combined master file error: {combined_data['error']}")
                
            # Check data freshness (should be updated within last week)
            for data_type, data_info in [("WU", wu_data), ("TSI", tsi_data)]:
                if data_info.get("date_range_end"):
                    try:
                        last_data = datetime.fromisoformat(data_info["date_range_end"].replace('Z', '+00:00'))
                        if datetime.now() - last_data > timedelta(days=8):
                            issues.append(f"{data_type} data is stale (last update: {last_data.date()})")
                    except Exception:
                        pass
                        
            # Log health status
            if issues:
                self.logger.warning(f"⚠️ Health check found {len(issues)} issues:")
                for issue in issues:
                    self.logger.warning(f"  - {issue}")
            else:
                self.logger.info("✅ Health check passed - all systems operational")
                
            # Log health metadata
            self.log_execution_metadata("health_check", {
                "timestamp": datetime.now().isoformat(),
                "issues_count": len(issues),
                "issues": issues,
                "summary": summary
            })
            
        except Exception as e:
            self.logger.error(f"❌ Error during health check: {e}")
            self.logger.error(traceback.format_exc())
            
    def monthly_export_job(self):
        """Execute monthly data export on the first day of the month."""
        # Only run on the first day of the month
        if datetime.now().day != 1:
            return
            
        self.logger.info("📤 Starting scheduled monthly export")
        
        try:
            export_settings = self.config.get("export_settings", {})
            
            if not export_settings.get("enable_monthly_exports", True):
                self.logger.info("Monthly exports disabled in configuration")
                return
                
            # Get export formats
            formats = export_settings.get("export_formats", ["csv"])
            
            # Calculate last month's date range
            today = datetime.now()
            first_of_this_month = today.replace(day=1)
            last_month_end = first_of_this_month - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            
            start_date = last_month_start.strftime("%Y-%m-%d")
            end_date = last_month_end.strftime("%Y-%m-%d")
            
            # Export in each format
            exported_files = []
            for format in formats:
                files = self.master_system.export_data("all", format, start_date, end_date)
                exported_files.extend(files)
                
            self.logger.info(f"✅ Monthly export completed: {len(exported_files)} files created")
            for file in exported_files:
                self.logger.info(f"  - {file}")
                
        except Exception as e:
            self.logger.error(f"❌ Error during monthly export: {e}")
            self.logger.error(traceback.format_exc())
            
    def log_execution_metadata(self, job_type: str, metadata: dict):
        """Log execution metadata for monitoring and debugging."""
        metadata_file = project_root / "logs" / "master_data_execution.jsonl"
        
        try:
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "job_type": job_type,
                **metadata
            }
            
            with open(metadata_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Error logging execution metadata: {e}")
            
    def run_test_job(self, job_name: str = "weekly_update"):
        """Run a specific job for testing purposes."""
        self.logger.info(f"🧪 Running test job: {job_name}")
        
        if job_name == "weekly_update":
            self.weekly_update_job()
        elif job_name == "cleanup":
            self.cleanup_job()
        elif job_name == "health_check":
            self.health_check_job()
        elif job_name == "monthly_export":
            self.monthly_export_job()
        else:
            self.logger.error(f"Unknown test job: {job_name}")
            
    def get_schedule_info(self):
        """Get information about scheduled jobs."""
        jobs_info = []
        for job in schedule.jobs:
            jobs_info.append({
                "job": str(job.job_func.__name__),
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval),
                "unit": job.unit
            })
        return jobs_info
        
    def run_scheduler(self):
        """Run the scheduler continuously."""
        self.logger.info("🚀 Starting Master Data Scheduler")
        self.logger.info(f"📅 Scheduled jobs:")
        
        for job_info in self.get_schedule_info():
            self.logger.info(f"  - {job_info['job']}: every {job_info['interval']} {job_info['unit']}")
            
        self.logger.info("⏰ Scheduler is running. Press Ctrl+C to stop.")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("🛑 Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Scheduler error: {e}")
            self.logger.error(traceback.format_exc())

def main():
    """Main entry point for the master data scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Master Data Scheduler')
    parser.add_argument('--run', action='store_true', help='Run the scheduler continuously')
    parser.add_argument('--test', choices=['weekly_update', 'cleanup', 'health_check', 'monthly_export'], 
                       help='Run a specific job for testing')
    parser.add_argument('--schedule-info', action='store_true', help='Show scheduled jobs info')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Initialize scheduler
    scheduler = MasterDataScheduler(config_path=args.config)
    
    if args.run:
        scheduler.run_scheduler()
    elif args.test:
        scheduler.run_test_job(args.test)
    elif args.schedule_info:
        print("📅 Scheduled Jobs:")
        for job_info in scheduler.get_schedule_info():
            print(f"  - {job_info['job']}: every {job_info['interval']} {job_info['unit']}")
            if job_info['next_run']:
                print(f"    Next run: {job_info['next_run']}")
    else:
        print("ℹ️  Master Data Scheduler")
        print("💡 Use --run to start the scheduler")
        print("🧪 Use --test <job_name> to test individual jobs")
        print("📅 Use --schedule-info to see scheduled jobs")

if __name__ == "__main__":
    main()
