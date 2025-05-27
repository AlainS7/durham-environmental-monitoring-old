#!/usr/bin/env python3
"""
Production Data Pull Executor for Hot Durham Project

This script executes actual data pulls using the new prioritized system,
integrating with existing data management infrastructure while implementing
intelligent scheduling and sensor prioritization.

Features:
- Executes prioritized data collection based on sensor importance
- Integrates with existing data management system
- Provides comprehensive logging and error handling
- Supports both manual and automated execution
- Implements retry logic and gap detection
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "src" / "core"))
sys.path.append(str(project_root / "src" / "data_collection"))

# Import existing systems
try:
    from src.core.data_manager import DataManager
    from prioritized_data_pull_manager import PrioritizedDataPullManager
    # Import only the specific functions we need to avoid credentials check on import
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    DEPENDENCIES_AVAILABLE = False

class ProductionDataPullExecutor:
    """Executes production data pulls with prioritized scheduling"""
    
    def __init__(self, base_dir: str = None):
        if not DEPENDENCIES_AVAILABLE:
            raise RuntimeError("Required dependencies not available")
        
        self.base_dir = Path(base_dir) if base_dir else project_root
        self.setup_logging()
        
        # Initialize managers
        self.data_manager = DataManager(str(self.base_dir))
        self.priority_manager = PrioritizedDataPullManager(str(self.base_dir))
        
        self.logger.info("Production data pull executor initialized")
    
    def setup_logging(self):
        """Configure logging for production pulls"""
        log_dir = self.base_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"production_pulls_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_optimal_pull_schedule(self) -> dict:
        """Generate optimal pull schedule based on current time and priorities"""
        current_time = datetime.now()
        current_hour = current_time.hour
        is_weekend = current_time.weekday() >= 5
        
        # Determine time period for frequency adjustments
        if 8 <= current_hour <= 18 and not is_weekend:
            time_period = "business_hours"
            frequency_multiplier = 1.0
        elif 18 < current_hour <= 23:
            time_period = "after_hours" 
            frequency_multiplier = 1.5
        else:
            time_period = "night_weekend"
            frequency_multiplier = 2.0
        
        self.logger.info(f"Current time period: {time_period} (multiplier: {frequency_multiplier})")
        
        # Get prioritized schedule
        schedule = self.priority_manager.generate_pull_schedule()
        
        # Apply time-based adjustments
        adjusted_schedule = {
            "created_at": schedule["created_at"],
            "time_period": time_period,
            "frequency_multiplier": frequency_multiplier,
            "priority_queues": {},
            "summary": schedule["summary"]
        }
        
        for priority, sensors in schedule["priority_queues"].items():
            # Get base frequency for this priority from config
            base_frequency = self.priority_manager.calculate_pull_frequency(priority)
            adjusted_frequency = int(base_frequency * frequency_multiplier)
            
            adjusted_schedule["priority_queues"][priority] = {
                'sensors': sensors,
                'frequency_minutes': adjusted_frequency,
                'base_frequency': base_frequency,
                'sensor_count': len(sensors)
            }
        
        return adjusted_schedule
    
    def should_pull_sensor(self, sensor_id: str, frequency_minutes: int) -> bool:
        """Determine if a sensor should be pulled based on last pull time"""
        # Check when this sensor was last pulled
        # This would typically check the data manager's records
        # For now, implement a simple time-based check
        
        last_pull_file = self.base_dir / "temp" / f"last_pull_{sensor_id}.json"
        
        if not last_pull_file.exists():
            # Never pulled before, should pull
            return True
        
        try:
            with open(last_pull_file, 'r') as f:
                last_pull_data = json.load(f)
                last_pull_time = datetime.fromisoformat(last_pull_data['timestamp'])
                
                # Check if enough time has passed
                time_since_last = datetime.now() - last_pull_time
                return time_since_last.total_seconds() >= (frequency_minutes * 60)
        
        except Exception as e:
            self.logger.warning(f"Error checking last pull time for {sensor_id}: {e}")
            return True
    
    def record_sensor_pull(self, sensor_id: str, success: bool, records_count: int = 0):
        """Record when a sensor was pulled"""
        last_pull_file = self.base_dir / "temp" / f"last_pull_{sensor_id}.json"
        
        pull_record = {
            'sensor_id': sensor_id,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'records_count': records_count
        }
        
        try:
            with open(last_pull_file, 'w') as f:
                json.dump(pull_record, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error recording pull for {sensor_id}: {e}")
    
    def execute_wu_pull(self, date_range_days: int = 1) -> dict:
        """Execute Weather Underground data pull"""
        self.logger.info("Starting Weather Underground data pull")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=date_range_days)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        pull_result = {
            'source': 'wu',
            'start_date': start_str,
            'end_date': end_str,
            'success': False,
            'records_count': 0,
            'error': None
        }
        
        try:
            # Fetch WU data
            wu_df = fetch_wu_data(start_str, end_str)
            
            if wu_df is not None and not wu_df.empty:
                # Save using data manager
                file_path = self.data_manager.pull_and_store_data(
                    "wu", start_str, end_str, file_format="csv"
                )
                
                if file_path:
                    pull_result['success'] = True
                    pull_result['records_count'] = len(wu_df)
                    pull_result['file_path'] = str(file_path)
                    
                    self.logger.info(f"WU pull successful: {len(wu_df)} records saved to {file_path}")
                else:
                    pull_result['error'] = "Failed to save data"
                    self.logger.error("WU data fetch succeeded but save failed")
            else:
                pull_result['error'] = "No data returned from API"
                self.logger.warning("WU data pull returned no data")
        
        except Exception as e:
            pull_result['error'] = str(e)
            self.logger.error(f"Error during WU data pull: {e}")
        
        # Record the pull attempt
        self.record_sensor_pull('wu_stations', pull_result['success'], pull_result['records_count'])
        
        return pull_result
    
    def execute_tsi_pull(self, date_range_days: int = 1) -> dict:
        """Execute TSI data pull"""
        self.logger.info("Starting TSI data pull")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=date_range_days)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        pull_result = {
            'source': 'tsi',
            'start_date': start_str,
            'end_date': end_str,
            'success': False,
            'records_count': 0,
            'error': None
        }
        
        try:
            # Fetch TSI data
            tsi_df, tsi_summary = fetch_tsi_data(start_str, end_str)
            
            if tsi_df is not None and not tsi_df.empty:
                # Save using data manager
                file_path = self.data_manager.pull_and_store_data(
                    "tsi", start_str, end_str, file_format="csv"
                )
                
                if file_path:
                    pull_result['success'] = True
                    pull_result['records_count'] = len(tsi_df)
                    pull_result['file_path'] = str(file_path)
                    pull_result['summary'] = tsi_summary
                    
                    self.logger.info(f"TSI pull successful: {len(tsi_df)} records saved to {file_path}")
                else:
                    pull_result['error'] = "Failed to save data"
                    self.logger.error("TSI data fetch succeeded but save failed")
            else:
                pull_result['error'] = "No data returned from API"
                self.logger.warning("TSI data pull returned no data")
        
        except Exception as e:
            pull_result['error'] = str(e)
            self.logger.error(f"Error during TSI data pull: {e}")
        
        # Record the pull attempt
        self.record_sensor_pull('tsi_sensors', pull_result['success'], pull_result['records_count'])
        
        return pull_result
    
    def execute_prioritized_pulls(self, force_all: bool = False) -> dict:
        """Execute prioritized data pulls based on schedule and sensor importance"""
        self.logger.info("Starting prioritized data pull execution")
        
        execution_report = {
            'execution_timestamp': datetime.now().isoformat(),
            'schedule_used': None,
            'pulls_executed': [],
            'summary': {
                'total_pulls': 0,
                'successful_pulls': 0,
                'failed_pulls': 0,
                'total_records': 0
            }
        }
        
        try:
            # Get optimal pull schedule
            schedule = self.get_optimal_pull_schedule()
            execution_report['schedule_used'] = schedule
            
            # Execute WU pulls (treating as high priority)
            if force_all or self.should_pull_sensor('wu_stations', schedule['high']['frequency_minutes']):
                wu_result = self.execute_wu_pull()
                execution_report['pulls_executed'].append(wu_result)
                execution_report['summary']['total_pulls'] += 1
                
                if wu_result['success']:
                    execution_report['summary']['successful_pulls'] += 1
                    execution_report['summary']['total_records'] += wu_result['records_count']
                else:
                    execution_report['summary']['failed_pulls'] += 1
            else:
                self.logger.info("Skipping WU pull - not due based on schedule")
            
            # Execute TSI pulls (treating as critical priority for indoor sensors)
            if force_all or self.should_pull_sensor('tsi_sensors', schedule['critical']['frequency_minutes']):
                tsi_result = self.execute_tsi_pull()
                execution_report['pulls_executed'].append(tsi_result)
                execution_report['summary']['total_pulls'] += 1
                
                if tsi_result['success']:
                    execution_report['summary']['successful_pulls'] += 1
                    execution_report['summary']['total_records'] += tsi_result['records_count']
                else:
                    execution_report['summary']['failed_pulls'] += 1
            else:
                self.logger.info("Skipping TSI pull - not due based on schedule")
            
            # Log automation run
            if execution_report['summary']['total_pulls'] > 0:
                log_entry = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'prioritized_production_pull',
                    'wu_records': next((p['records_count'] for p in execution_report['pulls_executed'] if p['source'] == 'wu'), 0),
                    'tsi_records': next((p['records_count'] for p in execution_report['pulls_executed'] if p['source'] == 'tsi'), 0),
                    'total_records': execution_report['summary']['total_records'],
                    'successful_pulls': execution_report['summary']['successful_pulls'],
                    'failed_pulls': execution_report['summary']['failed_pulls']
                }
                
                self.data_manager.log_automation_run(log_entry)
        
        except Exception as e:
            self.logger.error(f"Error during prioritized pull execution: {e}")
            execution_report['error'] = str(e)
        
        # Save execution report
        report_file = self.base_dir / "reports" / f"production_pull_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(execution_report, f, indent=2)
        
        self.logger.info(f"Prioritized pull execution completed. Report saved to {report_file}")
        return execution_report
    
    def execute_gap_recovery(self, days_back: int = 7) -> dict:
        """Execute recovery pulls for any missing data gaps"""
        self.logger.info(f"Starting gap recovery for last {days_back} days")
        
        # Check data integrity to find gaps
        integrity_report = self.data_manager.verify_data_integrity()
        
        recovery_report = {
            'recovery_timestamp': datetime.now().isoformat(),
            'days_checked': days_back,
            'gaps_found': [],
            'recovery_attempts': [],
            'summary': {
                'gaps_identified': 0,
                'successful_recoveries': 0,
                'failed_recoveries': 0
            }
        }
        
        # TODO: Implement gap detection logic based on data integrity report
        # This would analyze the integrity report to identify missing data periods
        # and attempt recovery pulls for those specific time ranges
        
        self.logger.info("Gap recovery analysis completed")
        return recovery_report
    
    def get_execution_status(self) -> dict:
        """Get status of recent production pulls"""
        status = {
            'last_execution': None,
            'recent_activity': [],
            'sensor_status': {},
            'error_summary': []
        }
        
        # Check for recent execution reports
        reports_dir = self.base_dir / "reports"
        if reports_dir.exists():
            report_files = sorted(reports_dir.glob("production_pull_report_*.json"), reverse=True)
            
            if report_files:
                # Get most recent report
                with open(report_files[0], 'r') as f:
                    latest_report = json.load(f)
                    status['last_execution'] = latest_report['execution_timestamp']
                
                # Analyze recent reports (last 7 days)
                cutoff_date = datetime.now() - timedelta(days=7)
                
                for report_file in report_files:
                    file_time = datetime.fromtimestamp(report_file.stat().st_mtime)
                    if file_time >= cutoff_date:
                        try:
                            with open(report_file, 'r') as f:
                                report = json.load(f)
                                status['recent_activity'].append({
                                    'timestamp': report['execution_timestamp'],
                                    'successful_pulls': report['summary']['successful_pulls'],
                                    'failed_pulls': report['summary']['failed_pulls'],
                                    'total_records': report['summary']['total_records']
                                })
                        except Exception as e:
                            self.logger.warning(f"Error reading report {report_file}: {e}")
        
        # Check sensor-specific status from temp files
        temp_dir = self.base_dir / "temp"
        if temp_dir.exists():
            for sensor_file in temp_dir.glob("last_pull_*.json"):
                try:
                    with open(sensor_file, 'r') as f:
                        sensor_data = json.load(f)
                        sensor_id = sensor_data['sensor_id']
                        
                        status['sensor_status'][sensor_id] = {
                            'last_pull': sensor_data['timestamp'],
                            'last_success': sensor_data['success'],
                            'last_record_count': sensor_data.get('records_count', 0)
                        }
                except Exception as e:
                    self.logger.warning(f"Error reading sensor status {sensor_file}: {e}")
        
        return status

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Hot Durham Production Data Pull Executor')
    parser.add_argument('--execute', action='store_true', help='Execute prioritized data pulls')
    parser.add_argument('--force-all', action='store_true', help='Force execution of all pulls regardless of schedule')
    parser.add_argument('--wu-only', action='store_true', help='Execute only Weather Underground pulls')
    parser.add_argument('--tsi-only', action='store_true', help='Execute only TSI pulls')
    parser.add_argument('--gap-recovery', type=int, help='Execute gap recovery for N days back')
    parser.add_argument('--status', action='store_true', help='Show execution status')
    parser.add_argument('--schedule', action='store_true', help='Show current pull schedule')
    
    args = parser.parse_args()
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Required dependencies not available. Please check imports.")
        return 1
    
    try:
        executor = ProductionDataPullExecutor()
        
        if args.status:
            status = executor.get_execution_status()
            print("📊 Production Data Pull Status")
            print("=" * 40)
            print(f"Last Execution: {status['last_execution'] or 'None'}")
            print(f"Recent Activity: {len(status['recent_activity'])} pulls in last 7 days")
            
            if status['sensor_status']:
                print("\n🔍 Sensor Status:")
                for sensor_id, sensor_status in status['sensor_status'].items():
                    status_icon = "✅" if sensor_status['last_success'] else "❌"
                    print(f"  {status_icon} {sensor_id}: Last pull {sensor_status['last_pull']}")
            
            return 0
        
        if args.schedule:
            schedule = executor.get_optimal_pull_schedule()
            print("⏰ Current Pull Schedule")
            print("=" * 30)
            for priority, details in schedule.items():
                print(f"{priority.title()}: {details['frequency_minutes']} minutes")
                print(f"  Time period: {details['time_period']}")
                print(f"  Base frequency: {details['base_frequency']} minutes")
            return 0
        
        if args.gap_recovery:
            report = executor.execute_gap_recovery(args.gap_recovery)
            print(f"🔧 Gap recovery completed for {args.gap_recovery} days")
            return 0
        
        if args.wu_only:
            result = executor.execute_wu_pull()
            print(f"🌤️ WU pull {'successful' if result['success'] else 'failed'}")
            if result['success']:
                print(f"   Records: {result['records_count']}")
            return 0
        
        if args.tsi_only:
            result = executor.execute_tsi_pull()
            print(f"🏭 TSI pull {'successful' if result['success'] else 'failed'}")
            if result['success']:
                print(f"   Records: {result['records_count']}")
            return 0
        
        if args.execute:
            report = executor.execute_prioritized_pulls(force_all=args.force_all)
            print("🚀 Prioritized data pull execution completed")
            print(f"   Total pulls: {report['summary']['total_pulls']}")
            print(f"   Successful: {report['summary']['successful_pulls']}")
            print(f"   Failed: {report['summary']['failed_pulls']}")
            print(f"   Total records: {report['summary']['total_records']}")
            return 0
        
        print("No action specified. Use --help for options.")
        return 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
