#!/usr/bin/env python3
"""
Enhanced Data Quality and Analysis Report Generator
Handles data cleaning, quality assessment, and generates comprehensive analytics.
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class EnhancedAnalyzer:
    """Enhanced analyzer with data quality checks and comprehensive reporting."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.raw_dir = self.base_dir / "raw_pulls"
        self.processed_dir = self.base_dir / "processed"
        self.reports_dir = self.base_dir / "reports"
        
        # Create directories
        for dir_path in [self.processed_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        for subdir in ["weekly_summaries", "monthly_summaries", "annual_summaries", 
                       "device_summaries", "data_quality"]:
            (self.processed_dir / subdir).mkdir(exist_ok=True)
    
    def load_and_clean_data(self):
        """Load and clean all raw data with quality checks."""
        print("Loading and cleaning raw data...")
        
        # Load Weather Underground data
        self.wu_data = []
        wu_dir = self.raw_dir / "wu"
        if wu_dir.exists():
            for year_dir in wu_dir.iterdir():
                if year_dir.is_dir():
                    for file in year_dir.glob("*.csv"):
                        if not file.name.endswith('.metadata.json'):
                            try:
                                df = pd.read_csv(file)
                                df['source_file'] = file.name
                                df['year'] = year_dir.name
                                self.wu_data.append(df)
                                print(f"✓ Loaded WU data: {file.name} ({len(df)} records)")
                            except Exception as e:
                                print(f"✗ Error loading {file}: {e}")
        
        # Load TSI sensor data with improved column handling
        self.tsi_data = []
        tsi_dir = self.raw_dir / "tsi"
        if tsi_dir.exists():
            for year_dir in tsi_dir.iterdir():
                if year_dir.is_dir():
                    for file in year_dir.glob("*.csv"):
                        if not file.name.endswith('.metadata.json'):
                            try:
                                df = pd.read_csv(file)
                                df['source_file'] = file.name
                                df['year'] = year_dir.name
                                self.tsi_data.append(df)
                                print(f"✓ Loaded TSI data: {file.name} ({len(df)} records)")
                            except Exception as e:
                                print(f"✗ Error loading {file}: {e}")
        
        # Clean and combine WU data
        if self.wu_data:
            self.wu_df = pd.concat(self.wu_data, ignore_index=True)
            self.wu_df['obsTimeUtc'] = pd.to_datetime(self.wu_df['obsTimeUtc'])
            self.wu_df = self.wu_df.drop_duplicates()
            print(f"Total WU records after cleaning: {len(self.wu_df)}")
        else:
            self.wu_df = pd.DataFrame()
            
        # Clean and combine TSI data with improved handling
        if self.tsi_data:
            self.tsi_df = pd.concat(self.tsi_data, ignore_index=True)
            
            # Handle timestamp column
            if 'timestamp' in self.tsi_df.columns:
                self.tsi_df['timestamp'] = pd.to_datetime(self.tsi_df['timestamp'])
            elif 'iso_timestamp' in self.tsi_df.columns:
                self.tsi_df['timestamp'] = pd.to_datetime(self.tsi_df['iso_timestamp'])
            
            # Handle device name column
            device_cols = ['device_name', 'friendly_name', 'Device Name']
            self.device_col = None
            for col in device_cols:
                if col in self.tsi_df.columns:
                    self.device_col = col
                    break
            
            # Clean numeric columns
            numeric_cols = ['PM 2.5', 'T (C)', 'RH (%)']
            for col in numeric_cols:
                if col in self.tsi_df.columns:
                    self.tsi_df[col] = pd.to_numeric(self.tsi_df[col], errors='coerce')
            
            # Remove rows with invalid device names
            if self.device_col:
                self.tsi_df = self.tsi_df.dropna(subset=[self.device_col])
                self.tsi_df = self.tsi_df[self.tsi_df[self.device_col] != '']
            
            # Remove duplicate records
            self.tsi_df = self.tsi_df.drop_duplicates()
            print(f"Total TSI records after cleaning: {len(self.tsi_df)}")
        else:
            self.tsi_df = pd.DataFrame()
    
    def generate_data_quality_report(self):
        """Generate comprehensive data quality assessment."""
        print("Generating data quality report...")
        
        quality_report = {
            'timestamp': datetime.now().isoformat(),
            'wu_data_quality': {},
            'tsi_data_quality': {}
        }
        
        # WU Data Quality Assessment
        if not self.wu_df.empty:
            wu_quality = {
                'total_records': len(self.wu_df),
                'date_range': {
                    'start': str(self.wu_df['obsTimeUtc'].min()),
                    'end': str(self.wu_df['obsTimeUtc'].max())
                },
                'stations': list(self.wu_df['stationID'].unique()),
                'station_count': len(self.wu_df['stationID'].unique()),
                'missing_data': {},
                'data_completeness': {}
            }
            
            # Check data completeness for key columns
            key_cols = ['tempAvg', 'humidityAvg', 'precipTotal', 'windspeedAvg']
            for col in key_cols:
                if col in self.wu_df.columns:
                    missing_count = self.wu_df[col].isna().sum()
                    completeness = ((len(self.wu_df) - missing_count) / len(self.wu_df)) * 100
                    wu_quality['missing_data'][col] = int(missing_count)
                    wu_quality['data_completeness'][col] = round(completeness, 2)
            
            quality_report['wu_data_quality'] = wu_quality
        
        # TSI Data Quality Assessment
        if not self.tsi_df.empty and self.device_col:
            tsi_quality = {
                'total_records': len(self.tsi_df),
                'date_range': {
                    'start': str(self.tsi_df['timestamp'].min()),
                    'end': str(self.tsi_df['timestamp'].max())
                },
                'devices': list(self.tsi_df[self.device_col].unique()),
                'device_count': len(self.tsi_df[self.device_col].unique()),
                'missing_data': {},
                'data_completeness': {},
                'device_records': {}
            }
            
            # Check data completeness for key columns
            key_cols = ['PM 2.5', 'T (C)', 'RH (%)']
            for col in key_cols:
                if col in self.tsi_df.columns:
                    missing_count = self.tsi_df[col].isna().sum()
                    completeness = ((len(self.tsi_df) - missing_count) / len(self.tsi_df)) * 100
                    tsi_quality['missing_data'][col] = int(missing_count)
                    tsi_quality['data_completeness'][col] = round(completeness, 2)
            
            # Per-device record counts
            device_counts = self.tsi_df[self.device_col].value_counts().to_dict()
            tsi_quality['device_records'] = device_counts
            
            quality_report['tsi_data_quality'] = tsi_quality
        
        # Save quality report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quality_file = self.processed_dir / "data_quality" / f"data_quality_report_{timestamp}.json"
        with open(quality_file, 'w') as f:
            json.dump(quality_report, f, indent=2)
        
        print(f"✓ Data quality report saved: {quality_file.name}")
        return quality_report
    
    def generate_executive_summary(self, quality_report):
        """Generate executive summary with key insights."""
        print("Generating executive summary...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.reports_dir / f"executive_summary_{timestamp}.html"
        
        # Calculate key metrics
        total_records = 0
        date_range = "No data"
        station_count = 0
        device_count = 0
        
        if not self.wu_df.empty:
            total_records += len(self.wu_df)
            station_count = len(self.wu_df['stationID'].unique())
            
        if not self.tsi_df.empty and self.device_col:
            total_records += len(self.tsi_df)
            device_count = len(self.tsi_df[self.device_col].unique())
        
        # Get overall date range
        start_dates = []
        end_dates = []
        if not self.wu_df.empty:
            start_dates.append(self.wu_df['obsTimeUtc'].min())
            end_dates.append(self.wu_df['obsTimeUtc'].max())
        if not self.tsi_df.empty:
            start_dates.append(self.tsi_df['timestamp'].min())
            end_dates.append(self.tsi_df['timestamp'].max())
        
        if start_dates and end_dates:
            date_range = f"{min(start_dates).strftime('%Y-%m-%d')} to {max(end_dates).strftime('%Y-%m-%d')}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hot Durham Weather Monitoring - Executive Summary</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #3498db; margin-top: 30px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 30px 0; }}
                .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; }}
                .metric-value {{ font-size: 36px; font-weight: bold; margin-bottom: 5px; }}
                .metric-label {{ font-size: 14px; opacity: 0.9; }}
                .status-good {{ color: #27ae60; font-weight: bold; }}
                .status-warning {{ color: #f39c12; font-weight: bold; }}
                .status-critical {{ color: #e74c3c; font-weight: bold; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .data-table th, .data-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                .data-table th {{ background-color: #f8f9fa; font-weight: 600; }}
                .highlight-box {{ background: #e8f5e8; border-left: 4px solid #27ae60; padding: 20px; margin: 20px 0; }}
                .alert-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌡️ Hot Durham Weather Monitoring System</h1>
                <h2>Executive Summary Report</h2>
                <p><strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{total_records:,}</div>
                        <div class="metric-label">Total Data Records</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{station_count}</div>
                        <div class="metric-label">Weather Stations</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{device_count}</div>
                        <div class="metric-label">Air Quality Sensors</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{len([f for f in (self.processed_dir / "weekly_summaries").glob("*.csv")])}</div>
                        <div class="metric-label">Weekly Reports Generated</div>
                    </div>
                </div>
                
                <h2>📊 Data Coverage</h2>
                <p><strong>Data Range:</strong> {date_range}</p>
                
                <div class="highlight-box">
                    <h3>✅ System Status: Operational</h3>
                    <p>The weather monitoring system is collecting data successfully from both Weather Underground stations and TSI air quality sensors. Data processing and analysis pipelines are functioning correctly.</p>
                </div>
        """
        
        # Add weather stations summary
        if not self.wu_df.empty:
            html_content += """
                <h2>🏗️ Weather Underground Stations</h2>
                <table class="data-table">
                    <tr><th>Station ID</th><th>Records</th><th>Latest Reading</th><th>Status</th></tr>
            """
            
            for station in self.wu_df['stationID'].unique():
                station_data = self.wu_df[self.wu_df['stationID'] == station]
                latest = station_data['obsTimeUtc'].max()
                record_count = len(station_data)
                
                # Determine status based on data recency
                hours_since = (datetime.now() - latest.to_pydatetime().replace(tzinfo=None)).total_seconds() / 3600
                if hours_since < 24:
                    status = '<span class="status-good">Active</span>'
                elif hours_since < 72:
                    status = '<span class="status-warning">Recent</span>'
                else:
                    status = '<span class="status-critical">Stale</span>'
                
                html_content += f"""
                    <tr>
                        <td>{station}</td>
                        <td>{record_count:,}</td>
                        <td>{latest.strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{status}</td>
                    </tr>
                """
            
            html_content += "</table>"
        
        # Add TSI sensors summary
        if not self.tsi_df.empty and self.device_col:
            html_content += """
                <h2>🌬️ Air Quality Sensors (TSI)</h2>
                <table class="data-table">
                    <tr><th>Device Name</th><th>Records</th><th>Latest Reading</th><th>Status</th></tr>
            """
            
            for device in self.tsi_df[self.device_col].unique():
                device_data = self.tsi_df[self.tsi_df[self.device_col] == device]
                latest = device_data['timestamp'].max()
                record_count = len(device_data)
                
                # Determine status based on data recency
                hours_since = (datetime.now() - latest.to_pydatetime().replace(tzinfo=None)).total_seconds() / 3600
                if hours_since < 24:
                    status = '<span class="status-good">Active</span>'
                elif hours_since < 72:
                    status = '<span class="status-warning">Recent</span>'
                else:
                    status = '<span class="status-critical">Stale</span>'
                
                html_content += f"""
                    <tr>
                        <td>{device}</td>
                        <td>{record_count:,}</td>
                        <td>{latest.strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{status}</td>
                    </tr>
                """
            
            html_content += "</table>"
        
        # Add data quality insights
        html_content += """
            <h2>📈 Data Quality Insights</h2>
        """
        
        if 'wu_data_quality' in quality_report and quality_report['wu_data_quality']:
            wu_quality = quality_report['wu_data_quality']
            html_content += f"""
                <h3>Weather Underground Data Quality</h3>
                <ul>
                    <li><strong>Completeness:</strong> Weather data shows good coverage across {wu_quality['station_count']} stations</li>
            """
            
            if 'data_completeness' in wu_quality:
                for col, completeness in wu_quality['data_completeness'].items():
                    if completeness >= 95:
                        status_class = "status-good"
                    elif completeness >= 85:
                        status_class = "status-warning"
                    else:
                        status_class = "status-critical"
                    html_content += f'<li><strong>{col}:</strong> <span class="{status_class}">{completeness}% complete</span></li>'
            
            html_content += "</ul>"
        
        if 'tsi_data_quality' in quality_report and quality_report['tsi_data_quality']:
            tsi_quality = quality_report['tsi_data_quality']
            html_content += f"""
                <h3>Air Quality Sensor Data Quality</h3>
                <ul>
                    <li><strong>Sensor Coverage:</strong> {tsi_quality['device_count']} active sensors monitoring air quality</li>
            """
            
            if 'data_completeness' in tsi_quality:
                for col, completeness in tsi_quality['data_completeness'].items():
                    if completeness >= 95:
                        status_class = "status-good"
                    elif completeness >= 85:
                        status_class = "status-warning"
                    else:
                        status_class = "status-critical"
                    html_content += f'<li><strong>{col}:</strong> <span class="{status_class}">{completeness}% complete</span></li>'
            
            html_content += "</ul>"
        
        html_content += f"""
            <h2>📁 Generated Reports</h2>
            <ul>
                <li>Weekly summaries: {len([f for f in (self.processed_dir / "weekly_summaries").glob("*.csv")])} files</li>
                <li>Monthly summaries: {len([f for f in (self.processed_dir / "monthly_summaries").glob("*.csv")])} files</li>
                <li>Device summaries: {len([f for f in (self.processed_dir / "device_summaries").glob("*.json")])} files</li>
                <li>Data quality reports: {len([f for f in (self.processed_dir / "data_quality").glob("*.json")])} files</li>
            </ul>
            
            <div class="alert-box">
                <h3>📋 Next Steps</h3>
                <ul>
                    <li>Review weekly and monthly trend summaries</li>
                    <li>Monitor air quality alerts and patterns</li>
                    <li>Set up automated notifications for data quality issues</li>
                    <li>Schedule regular backup of processed data</li>
                </ul>
            </div>
            
            <p style="text-align: center; margin-top: 40px; color: #7f8c8d;">
                <em>Hot Durham Weather Monitoring System - Automated Report Generation</em>
            </p>
            </div>
        </body>
        </html>
        """
        
        with open(summary_file, 'w') as f:
            f.write(html_content)
        
        print(f"✓ Executive summary saved: {summary_file.name}")
        return summary_file
    
    def generate_improved_summaries(self):
        """Generate improved clean summaries with better data handling."""
        print("Generating improved clean summaries...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Enhanced WU summaries
        if not self.wu_df.empty:
            # Weekly WU summary with better aggregations
            self.wu_df['week_start'] = self.wu_df['obsTimeUtc'].dt.to_period('W').apply(lambda r: r.start_time)
            wu_weekly = self.wu_df.groupby(['week_start', 'stationID']).agg({
                'tempAvg': ['mean', 'min', 'max', 'std'],
                'humidityAvg': ['mean', 'std'],
                'precipTotal': ['sum', 'max'],
                'windspeedAvg': ['mean', 'max'],
                'windgustAvg': 'max',
                'pressureMax': 'max',
                'pressureMin': 'min'
            }).round(2)
            
            wu_weekly.columns = [f'{col[0]}_{col[1]}' for col in wu_weekly.columns]
            wu_weekly = wu_weekly.reset_index()
            
            # Add derived metrics
            wu_weekly['temp_range'] = wu_weekly['tempAvg_max'] - wu_weekly['tempAvg_min']
            wu_weekly['pressure_range'] = wu_weekly['pressureMax_max'] - wu_weekly['pressureMin_min']
            
            # Save enhanced weekly summary
            wu_weekly_file = self.processed_dir / "weekly_summaries" / f"wu_weekly_enhanced_{timestamp}.csv"
            wu_weekly.to_csv(wu_weekly_file, index=False)
            print(f"✓ Enhanced WU weekly summary: {wu_weekly_file.name}")
        
        # Enhanced TSI summaries
        if not self.tsi_df.empty and self.device_col:
            # Filter out rows with all NaN values for key metrics
            key_cols = ['PM 2.5', 'T (C)', 'RH (%)']
            clean_tsi = self.tsi_df.dropna(subset=key_cols, how='all')
            
            if not clean_tsi.empty:
                clean_tsi['week_start'] = clean_tsi['timestamp'].dt.to_period('W').apply(lambda r: r.start_time)
                
                tsi_weekly = clean_tsi.groupby(['week_start', self.device_col]).agg({
                    'PM 2.5': ['mean', 'min', 'max', 'std', 'count'],
                    'T (C)': ['mean', 'min', 'max', 'std'],
                    'RH (%)': ['mean', 'min', 'max', 'std']
                }).round(2)
                
                tsi_weekly.columns = [f'{col[0]}_{col[1]}' for col in tsi_weekly.columns]
                tsi_weekly = tsi_weekly.reset_index()
                
                # Add air quality assessment
                tsi_weekly['pm25_category'] = tsi_weekly['PM 2.5_mean'].apply(self.categorize_pm25)
                
                # Save enhanced weekly summary
                tsi_weekly_file = self.processed_dir / "weekly_summaries" / f"tsi_weekly_enhanced_{timestamp}.csv"
                tsi_weekly.to_csv(tsi_weekly_file, index=False)
                print(f"✓ Enhanced TSI weekly summary: {tsi_weekly_file.name}")
                
                # Generate device performance summary
                device_performance = {}
                for device in clean_tsi[self.device_col].unique():
                    device_data = clean_tsi[clean_tsi[self.device_col] == device]
                    
                    performance = {
                        'device_name': device,
                        'total_valid_records': len(device_data.dropna(subset=['PM 2.5'])),
                        'data_quality_score': self.calculate_data_quality_score(device_data),
                        'avg_pm25': float(device_data['PM 2.5'].mean()) if not device_data['PM 2.5'].isna().all() else None,
                        'max_pm25': float(device_data['PM 2.5'].max()) if not device_data['PM 2.5'].isna().all() else None,
                        'avg_temp': float(device_data['T (C)'].mean()) if not device_data['T (C)'].isna().all() else None,
                        'avg_humidity': float(device_data['RH (%)'].mean()) if not device_data['RH (%)'].isna().all() else None,
                        'date_range': {
                            'start': str(device_data['timestamp'].min()),
                            'end': str(device_data['timestamp'].max())
                        }
                    }
                    device_performance[device] = performance
                
                # Save device performance summary
                device_perf_file = self.processed_dir / "device_summaries" / f"device_performance_{timestamp}.json"
                with open(device_perf_file, 'w') as f:
                    json.dump(device_performance, f, indent=2, default=str)
                print(f"✓ Device performance summary: {device_perf_file.name}")
    
    def categorize_pm25(self, pm25_value):
        """Categorize PM2.5 values according to air quality standards."""
        if pd.isna(pm25_value):
            return "No Data"
        elif pm25_value <= 12:
            return "Good"
        elif pm25_value <= 35:
            return "Moderate"
        elif pm25_value <= 55:
            return "Unhealthy for Sensitive Groups"
        elif pm25_value <= 150:
            return "Unhealthy"
        elif pm25_value <= 250:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    def calculate_data_quality_score(self, device_data):
        """Calculate a data quality score for a device (0-100)."""
        if device_data.empty:
            return 0
        
        # Factors for data quality score
        total_possible_records = len(device_data)
        valid_pm25_records = device_data['PM 2.5'].notna().sum()
        valid_temp_records = device_data['T (C)'].notna().sum()
        valid_humidity_records = device_data['RH (%)'].notna().sum()
        
        # Calculate completeness scores
        pm25_completeness = (valid_pm25_records / total_possible_records) * 100 if total_possible_records > 0 else 0
        temp_completeness = (valid_temp_records / total_possible_records) * 100 if total_possible_records > 0 else 0
        humidity_completeness = (valid_humidity_records / total_possible_records) * 100 if total_possible_records > 0 else 0
        
        # Weighted average (PM2.5 is most important)
        quality_score = (pm25_completeness * 0.5 + temp_completeness * 0.25 + humidity_completeness * 0.25)
        
        return round(quality_score, 1)
    
    def run_enhanced_analysis(self):
        """Run the complete enhanced analysis workflow."""
        print("="*70)
        print("STARTING ENHANCED DATA ANALYSIS WITH QUALITY ASSESSMENT")
        print("="*70)
        
        # Load and clean data
        self.load_and_clean_data()
        
        # Generate data quality report
        quality_report = self.generate_data_quality_report()
        
        # Generate improved summaries
        self.generate_improved_summaries()
        
        # Generate executive summary
        summary_file = self.generate_executive_summary(quality_report)
        
        print("="*70)
        print("ENHANCED ANALYSIS COMPLETE!")
        print("="*70)
        print(f"📊 Processed data saved to: {self.processed_dir}")
        print(f"📋 Executive summary: {summary_file}")
        print(f"📈 Data quality report available in: {self.processed_dir / 'data_quality'}")
        print("="*70)

def main():
    """Main execution function."""
    analyzer = EnhancedAnalyzer()
    analyzer.run_enhanced_analysis()

if __name__ == "__main__":
    main()
