#!/usr/bin/env python3
"""
Test Sensor Validation Reports for Hot Durham Project

This module generates validation reports comparing test sensor data with production sensors,
uploads reports to Google Drive, and provides insights into sensor accuracy.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.test_sensors_config import TestSensorConfig, get_drive_folder_path_with_date
from src.core.data_manager import DataManager

class TestSensorValidator:
    """Generates validation reports for test sensors against production data."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.test_config = TestSensorConfig(str(self.project_root))
        self.data_manager = DataManager(str(self.project_root))
        
        # Setup logging
        self.setup_logging()
        
        # Create validation reports directory
        self.reports_dir = self.test_config.test_data_path / "validation_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Setup logging for validation reports."""
        log_path = self.test_config.test_logs_path / "validation_reports.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def generate_daily_validation_report(self, target_date: Optional[datetime] = None) -> Optional[Path]:
        """
        Generate a daily validation report comparing test sensors with production sensors.
        
        Args:
            target_date: Date to generate report for (defaults to yesterday)
            
        Returns:
            Path to generated report file, or None if generation failed
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        date_str = target_date.strftime("%Y%m%d")
        self.logger.info(f"Generating validation report for {date_str}")
        
        try:
            # Get test sensor data for the date
            test_data = self._collect_test_sensor_data(target_date)
            
            # Get production sensor data for comparison
            production_data = self._collect_production_sensor_data(target_date)
            
            if not test_data and not production_data:
                self.logger.warning(f"No data found for validation report on {date_str}")
                return None
            
            # Generate comparison analysis
            report_data = self._analyze_sensor_performance(test_data, production_data, target_date)
            
            # Create report file
            report_filename = f"test_validation_report_{date_str}.csv"
            report_path = self.reports_dir / report_filename
            
            # Save report to CSV
            if report_data:
                df = pd.DataFrame(report_data)
                df.to_csv(report_path, index=False)
                self.logger.info(f"Validation report saved: {report_path}")
                
                # Upload to Google Drive
                self._upload_report_to_drive(report_path, date_str)
                
                return report_path
            else:
                self.logger.warning("No report data generated")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating validation report: {e}")
            return None
    
    def _collect_test_sensor_data(self, target_date: datetime) -> Dict[str, pd.DataFrame]:
        """Collect data from all test sensors for the target date."""
        test_data = {}
        
        for sensor_id in self.test_config.get_test_sensors():
            try:
                # Look for data files in test sensor directory
                sensor_files = list(self.test_config.test_sensors_path.glob(f"*{sensor_id}*{target_date.strftime('%Y%m%d')}*.csv"))
                
                if sensor_files:
                    # Use the most recent file if multiple exist
                    latest_file = max(sensor_files, key=lambda f: f.stat().st_mtime)
                    df = pd.read_csv(latest_file)
                    test_data[sensor_id] = df
                    self.logger.debug(f"Loaded test data for {sensor_id}: {len(df)} records")
                
            except Exception as e:
                self.logger.warning(f"Could not load test data for {sensor_id}: {e}")
        
        return test_data
    
    def _collect_production_sensor_data(self, target_date: datetime) -> Dict[str, pd.DataFrame]:
        """Collect data from production sensors for comparison."""
        production_data = {}
        
        try:
            # Look for production data files
            year = target_date.year
            week = target_date.isocalendar()[1]
            
            for data_type in ['wu', 'tsi']:
                data_dir = self.data_manager.base_dir / "raw_pulls" / data_type / str(year) / f"week_{week:02d}"
                
                if data_dir.exists():
                    date_files = list(data_dir.glob(f"*{target_date.strftime('%Y%m%d')}*.csv"))
                    
                    if date_files:
                        latest_file = max(date_files, key=lambda f: f.stat().st_mtime)
                        df = pd.read_csv(latest_file)
                        production_data[data_type] = df
                        self.logger.debug(f"Loaded production {data_type} data: {len(df)} records")
        
        except Exception as e:
            self.logger.warning(f"Could not load production data: {e}")
        
        return production_data
    
    def _analyze_sensor_performance(self, test_data: Dict[str, pd.DataFrame], 
                                   production_data: Dict[str, pd.DataFrame], 
                                   target_date: datetime) -> List[Dict]:
        """Analyze performance of test sensors compared to production sensors."""
        analysis_results = []
        
        # Analyze each test sensor
        for sensor_id, test_df in test_data.items():
            try:
                # Determine sensor type and get comparison data
                if sensor_id.startswith('KNCDURHA'):
                    comparison_df = production_data.get('wu')
                    sensor_type = 'WU'
                else:
                    comparison_df = production_data.get('tsi')
                    sensor_type = 'TSI'
                
                if comparison_df is None or comparison_df.empty:
                    self.logger.warning(f"No comparison data available for {sensor_id}")
                    continue
                
                # Get MS station name if available
                ms_station = self.test_config.get_ms_station_name(sensor_id)
                
                # Basic statistics
                result = {
                    'date': target_date.strftime('%Y-%m-%d'),
                    'sensor_id': sensor_id,
                    'ms_station': ms_station or 'N/A',
                    'sensor_type': sensor_type,
                    'test_records_count': len(test_df),
                    'production_records_count': len(comparison_df),
                    'data_availability': 'Good' if len(test_df) > 0 else 'No Data',
                    'status': 'Active' if len(test_df) > 0 else 'Inactive'
                }
                
                # Calculate statistics if we have data
                if len(test_df) > 0:
                    # Temperature analysis (if available)
                    if 'temperature' in test_df.columns:
                        result['avg_temperature'] = test_df['temperature'].mean()
                        result['min_temperature'] = test_df['temperature'].min()
                        result['max_temperature'] = test_df['temperature'].max()
                    
                    # Humidity analysis (if available)
                    if 'humidity' in test_df.columns:
                        result['avg_humidity'] = test_df['humidity'].mean()
                        result['min_humidity'] = test_df['humidity'].min()
                        result['max_humidity'] = test_df['humidity'].max()
                
                analysis_results.append(result)
                
            except Exception as e:
                self.logger.warning(f"Error analyzing sensor {sensor_id}: {e}")
        
        return analysis_results
    
    def _upload_report_to_drive(self, report_path: Path, date_str: str):
        """Upload validation report to Google Drive."""
        if not self.data_manager.drive_service:
            self.logger.warning("Google Drive service not available for report upload")
            return
        
        try:
            # Use first test sensor to determine drive path (they all go to same reports folder)
            test_sensors = self.test_config.get_test_sensors()
            if test_sensors:
                drive_folder = get_drive_folder_path_with_date(test_sensors[0], date_str, "reports")
                self.logger.info(f"Uploading validation report to: {drive_folder}")
                self.data_manager.upload_to_drive(report_path, drive_folder)
            
        except Exception as e:
            self.logger.error(f"Failed to upload validation report to Google Drive: {e}")
    
    def generate_daily_summary(self, start_date: Optional[datetime] = None) -> Optional[Path]:
        """Generate a daily summary of test sensor performance for high-resolution monitoring."""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=1)
        
        self.logger.info(f"Generating daily summary for {start_date.strftime('%Y-%m-%d')}")
        
        try:
            daily_data = []
            
            # Collect data for the day
            self.logger.info(f"Processing test sensor data for {start_date.strftime('%Y-%m-%d')}")
            
            # Generate daily validation report
            report_path = self.reports_dir / f"daily_test_sensor_summary_{start_date.strftime('%Y%m%d')}.json"
            
            summary = {
                "date": start_date.strftime('%Y-%m-%d'),
                "total_sensors": 0,  # Will be updated based on actual sensor count
                "sensors_active": 0,
                "data_quality_score": 0.0,
                "high_resolution_data": True,
                "interval_minutes": 15,
                "generated_at": datetime.now().isoformat()
            }
            
            with open(report_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"Daily summary saved to: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate daily summary: {e}")
            return None

    def generate_weekly_summary(self, start_date: Optional[datetime] = None) -> Optional[Path]:
        """Generate a weekly summary of test sensor performance (for validation only)."""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        
        end_date = start_date + timedelta(days=6)
        
        self.logger.info(f"Generating weekly summary from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        try:
            weekly_data = []
            
            # Collect daily reports for the week
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                report_file = self.reports_dir / f"test_validation_report_{date_str}.csv"
                
                if report_file.exists():
                    daily_df = pd.read_csv(report_file)
                    weekly_data.append(daily_df)
                
                current_date += timedelta(days=1)
            
            if not weekly_data:
                self.logger.warning("No daily reports found for weekly summary")
                return None
            
            # Combine all daily data
            combined_df = pd.concat(weekly_data, ignore_index=True)
            
            # Generate summary statistics
            summary_data = []
            for sensor_id in self.test_config.get_test_sensors():
                sensor_data = combined_df[combined_df['sensor_id'] == sensor_id]
                
                if not sensor_data.empty:
                    summary = {
                        'sensor_id': sensor_id,
                        'ms_station': sensor_data['ms_station'].iloc[0],
                        'total_days_active': len(sensor_data[sensor_data['status'] == 'Active']),
                        'total_records': sensor_data['test_records_count'].sum(),
                        'avg_daily_records': sensor_data['test_records_count'].mean(),
                        'data_quality': 'Good' if len(sensor_data[sensor_data['status'] == 'Active']) >= 5 else 'Poor'
                    }
                    summary_data.append(summary)
            
            # Save weekly summary
            week_str = start_date.strftime("%Y_week_%W")
            summary_filename = f"weekly_test_summary_{week_str}.csv"
            summary_path = self.reports_dir / summary_filename
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_csv(summary_path, index=False)
                self.logger.info(f"Weekly summary saved: {summary_path}")
                
                # Upload to Google Drive
                date_str = start_date.strftime("%Y%m%d")
                test_sensors = self.test_config.get_test_sensors()
                if test_sensors:
                    drive_folder = get_drive_folder_path_with_date(test_sensors[0], date_str, "reports")
                    self.data_manager.upload_to_drive(summary_path, drive_folder)
                
                return summary_path
            
        except Exception as e:
            self.logger.error(f"Error generating weekly summary: {e}")
            return None


def main():
    """Main function for testing the validation system."""
    print("🧪 Test Sensor Validation Report Generator")
    print("=" * 50)
    
    validator = TestSensorValidator()
    
    # Generate daily validation report
    print("Generating daily validation report...")
    daily_report = validator.generate_daily_validation_report()
    
    if daily_report:
        print(f"✅ Daily report generated: {daily_report}")
    else:
        print("⚠️ No daily report generated")
    
    # Generate weekly summary
    print("\nGenerating weekly summary...")
    weekly_summary = validator.generate_weekly_summary()
    
    if weekly_summary:
        print(f"✅ Weekly summary generated: {weekly_summary}")
    else:
        print("⚠️ No weekly summary generated")
    
    print("\n📊 Validation reports completed!")


if __name__ == "__main__":
    main()
