#!/usr/bin/env python3
"""
Daily Sheets Scheduler for Hot Durham Air Quality Monitoring
Automates the daily generation of Google Sheets with sensor data.
"""

import os
import sys
import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.automation.daily_sheets_system import DailySheetsSystem

class DailySheetsScheduler:
    """
    Scheduler for automated daily Google Sheets generation
    
    Features:
    - Scheduled daily sheet creation
    - Error handling and recovery
    - Logging and monitoring
    - Configurable timing
    """
    
    def __init__(self):
        self.project_root = project_root
        self.setup_logging()
        self.daily_system = DailySheetsSystem(project_root)
        
    def setup_logging(self):
        """Setup logging for the scheduler"""
        log_dir = Path(self.project_root) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("DailySheetsScheduler")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = log_dir / "daily_sheets_scheduler.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def daily_job(self):
        """Job function that runs daily"""
        self.logger.info("=== SCHEDULED DAILY SHEETS JOB STARTING ===")
        
        try:
            # Run yesterday's data (since today's data might be incomplete)
            yesterday = datetime.now() - timedelta(days=1)
            
            self.logger.info(f"Generating daily sheet for {yesterday.strftime('%Y-%m-%d')}")
            
            # Run the daily generation
            result = self.daily_system.run_daily_generation(
                target_date=yesterday,
                replace_existing=True
            )
            
            if result:
                self.logger.info("✅ Scheduled daily sheet generation completed successfully")
                self.logger.info(f"Sheet URL: {result['sheet_url']}")
            else:
                self.logger.error("❌ Scheduled daily sheet generation failed")
            
        except Exception as e:
            self.logger.error(f"Error in scheduled daily job: {e}")
        
        self.logger.info("=== SCHEDULED DAILY SHEETS JOB COMPLETED ===")
    
    def weekly_cleanup_job(self):
        """Weekly cleanup job"""
        self.logger.info("=== SCHEDULED WEEKLY CLEANUP JOB STARTING ===")
        
        try:
            self.daily_system.cleanup_old_sheets()
            self.logger.info("✅ Weekly cleanup completed successfully")
        except Exception as e:
            self.logger.error(f"Error in weekly cleanup job: {e}")
        
        self.logger.info("=== SCHEDULED WEEKLY CLEANUP JOB COMPLETED ===")
    
    def setup_schedule(self):
        """Setup the schedule for automated runs"""
        # Daily sheet generation at 6:00 AM (after data is collected)
        schedule.every().day.at("06:00").do(self.daily_job)
        
        # Weekly cleanup on Sundays at 2:00 AM
        schedule.every().sunday.at("02:00").do(self.weekly_cleanup_job)
        
        self.logger.info("📅 Schedule configured:")
        self.logger.info("  - Daily sheets: Every day at 6:00 AM")
        self.logger.info("  - Weekly cleanup: Sundays at 2:00 AM")
    
    def run_scheduler(self):
        """Run the scheduler continuously"""
        self.logger.info("🚀 Starting Daily Sheets Scheduler...")
        self.setup_schedule()
        
        # Log next run times
        jobs = schedule.get_jobs()
        for job in jobs:
            self.logger.info(f"Next run: {job.next_run} - {job.job_func.__name__}")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")
    
    def run_test_job(self):
        """Run a test job to verify everything works"""
        self.logger.info("🧪 Running test daily sheet generation...")
        
        # Run for today's date as test
        result = self.daily_system.run_daily_generation(
            target_date=datetime.now(),
            replace_existing=True
        )
        
        if result:
            self.logger.info("✅ Test daily sheet generation successful!")
            self.logger.info(f"Test sheet URL: {result['sheet_url']}")
            return True
        else:
            self.logger.error("❌ Test daily sheet generation failed!")
            return False

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Daily Sheets Scheduler')
    parser.add_argument('--test', action='store_true', help='Run a test generation and exit')
    parser.add_argument('--run-now', action='store_true', help='Run daily job immediately and exit')
    parser.add_argument('--cleanup-now', action='store_true', help='Run cleanup job immediately and exit')
    parser.add_argument('--schedule', action='store_true', help='Start the continuous scheduler')
    
    args = parser.parse_args()
    
    scheduler = DailySheetsScheduler()
    
    if args.test:
        print("Running test daily sheet generation...")
        success = scheduler.run_test_job()
        sys.exit(0 if success else 1)
    
    elif args.run_now:
        print("Running daily job immediately...")
        scheduler.daily_job()
    
    elif args.cleanup_now:
        print("Running cleanup job immediately...")
        scheduler.weekly_cleanup_job()
    
    elif args.schedule:
        print("Starting continuous scheduler...")
        scheduler.run_scheduler()
    
    else:
        print("Please specify an action:")
        print("  --test: Run a test generation")
        print("  --run-now: Run daily job immediately")
        print("  --cleanup-now: Run cleanup immediately")
        print("  --schedule: Start continuous scheduler")

if __name__ == "__main__":
    main()
