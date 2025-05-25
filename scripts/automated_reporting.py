#!/usr/bin/env python3
"""
Automated Reporting System for Hot Durham Weather Monitoring
Designed to run on schedule (daily/weekly) to generate consistent reports
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import logging

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"automated_reports_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

class AutomatedReportingSystem:
    def __init__(self, base_dir="/Users/alainsoto/IdeaProjects/Hot Durham"):
        self.base_dir = Path(base_dir)
        self.raw_data_dir = self.base_dir / "raw_data"
        self.processed_dir = self.base_dir / "processed"
        self.reports_dir = self.base_dir / "reports"
        self.scripts_dir = self.base_dir / "scripts"
        
        # Ensure directories exist
        for dir_path in [self.processed_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def check_data_freshness(self, max_age_hours=25):
        """Check if raw data files are recent enough for processing"""
        fresh_files = []
        stale_files = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for data_file in self.raw_data_dir.glob("*.csv"):
            try:
                mod_time = datetime.fromtimestamp(data_file.stat().st_mtime)
                if mod_time > cutoff_time:
                    fresh_files.append(str(data_file))
                else:
                    stale_files.append((str(data_file), mod_time))
                    
            except Exception as e:
                logging.warning(f"Could not check modification time for {data_file}: {e}")
        
        return fresh_files, stale_files
    
    def run_data_analysis(self):
        """Execute the enhanced data analysis script"""
        try:
            script_path = self.scripts_dir / "enhanced_data_analysis.py"
            if not script_path.exists():
                logging.error(f"Enhanced data analysis script not found: {script_path}")
                return False
            
            logging.info("Running enhanced data analysis...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logging.info("Enhanced data analysis completed successfully")
                logging.info(f"Analysis output: {result.stdout}")
                return True
            else:
                logging.error(f"Enhanced data analysis failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("Enhanced data analysis timed out")
            return False
        except Exception as e:
            logging.error(f"Error running enhanced data analysis: {e}")
            return False
    
    def generate_system_status_report(self):
        """Generate a comprehensive system status report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Check data freshness
        fresh_files, stale_files = self.check_data_freshness()
        
        # Get latest data quality report
        quality_reports = list((self.processed_dir / "data_quality").glob("data_quality_report_*.json"))
        latest_quality_report = None
        if quality_reports:
            latest_quality_report = max(quality_reports, key=lambda x: x.stat().st_mtime)
        
        # Count processed files
        processed_counts = {
            "weekly_summaries": len(list((self.processed_dir / "weekly_summaries").glob("*.csv"))),
            "monthly_summaries": len(list((self.processed_dir / "monthly_summaries").glob("*.csv"))),
            "device_summaries": len(list((self.processed_dir / "device_summaries").glob("*.json"))),
            "data_quality_reports": len(list((self.processed_dir / "data_quality").glob("*.json")))
        }
        
        # Create status report
        status_report = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "operational" if fresh_files else "stale_data",
            "data_freshness": {
                "fresh_files_count": len(fresh_files),
                "stale_files_count": len(stale_files),
                "fresh_files": fresh_files[:10],  # Limit for readability
                "stale_files": [(f, t.isoformat()) for f, t in stale_files[:10]]
            },
            "processed_file_counts": processed_counts,
            "latest_quality_report": str(latest_quality_report) if latest_quality_report else None,
            "total_raw_files": len(list(self.raw_data_dir.glob("*.csv"))),
            "disk_usage": {
                "raw_data_mb": sum(f.stat().st_size for f in self.raw_data_dir.glob("*.csv")) / (1024*1024),
                "processed_data_mb": sum(f.stat().st_size for f in self.processed_dir.rglob("*") if f.is_file()) / (1024*1024),
                "reports_mb": sum(f.stat().st_size for f in self.reports_dir.rglob("*") if f.is_file()) / (1024*1024)
            }
        }
        
        # Save status report
        status_file = self.reports_dir / f"system_status_{timestamp}.json"
        with open(status_file, 'w') as f:
            json.dump(status_report, f, indent=2)
        
        logging.info(f"System status report saved: {status_file}")
        return status_report
    
    def cleanup_old_files(self, days_to_keep=30):
        """Clean up old processed files and reports"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        removed_count = 0
        
        # Clean old reports
        for report_file in self.reports_dir.glob("*.html"):
            try:
                if datetime.fromtimestamp(report_file.stat().st_mtime) < cutoff_date:
                    report_file.unlink()
                    removed_count += 1
                    logging.info(f"Removed old report: {report_file}")
            except Exception as e:
                logging.warning(f"Could not remove {report_file}: {e}")
        
        # Clean old status reports (keep more recent ones)
        status_files = list(self.reports_dir.glob("system_status_*.json"))
        if len(status_files) > 50:  # Keep last 50 status reports
            status_files.sort(key=lambda x: x.stat().st_mtime)
            for old_status in status_files[:-50]:
                try:
                    old_status.unlink()
                    removed_count += 1
                    logging.info(f"Removed old status report: {old_status}")
                except Exception as e:
                    logging.warning(f"Could not remove {old_status}: {e}")
        
        logging.info(f"Cleanup completed: {removed_count} files removed")
        return removed_count
    
    def run_full_cycle(self):
        """Run a complete automated reporting cycle"""
        logging.info("=" * 60)
        logging.info("STARTING AUTOMATED REPORTING CYCLE")
        logging.info("=" * 60)
        
        try:
            # Generate system status
            status = self.generate_system_status_report()
            
            # Run data analysis if we have fresh data
            if status["data_freshness"]["fresh_files_count"] > 0:
                analysis_success = self.run_data_analysis()
                if not analysis_success:
                    logging.warning("Data analysis failed, but continuing with status report")
            else:
                logging.warning("No fresh data files found, skipping data analysis")
            
            # Cleanup old files
            self.cleanup_old_files()
            
            logging.info("=" * 60)
            logging.info("AUTOMATED REPORTING CYCLE COMPLETED")
            logging.info(f"System Status: {status['system_status']}")
            logging.info(f"Fresh Files: {status['data_freshness']['fresh_files_count']}")
            logging.info(f"Processed Files: {sum(status['processed_file_counts'].values())}")
            logging.info("=" * 60)
            
            return True
            
        except Exception as e:
            logging.error(f"Automated reporting cycle failed: {e}")
            return False

def main():
    """Main entry point for automated reporting"""
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = "/Users/alainsoto/IdeaProjects/Hot Durham"
    
    reporter = AutomatedReportingSystem(base_dir)
    success = reporter.run_full_cycle()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
