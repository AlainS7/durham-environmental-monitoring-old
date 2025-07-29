#!/usr/bin/env python3
"""
Comprehensive Summary Report Generator for Hot Durham Weather Monitoring System
Generates detailed reports, aggregations, and visualizations from existing data.
"""

import json
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style for visualizations
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class SummaryReportGenerator:
    """Generates comprehensive summary reports and aggregations."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.raw_dir = self.base_dir / "raw_pulls"
        self.processed_dir = self.base_dir / "processed"
        self.reports_dir = self.base_dir / "reports"
        self.charts_dir = self.reports_dir / "charts"
        
        # Create directories
        for dir_path in [self.processed_dir, self.reports_dir, self.charts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        # Create subdirectories in processed
        for subdir in ["weekly_summaries", "monthly_summaries", "annual_summaries", "device_summaries"]:
            (self.processed_dir / subdir).mkdir(exist_ok=True)
            
    def load_data(self):
        """Load all available raw data files."""
        print("Loading raw data files...")
        
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
                                print(f"Loaded WU data: {file.name}")
                            except Exception as e:
                                print(f"Error loading {file}: {e}")
        
        # Load TSI sensor data
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
                                print(f"Loaded TSI data: {file.name}")
                            except Exception as e:
                                print(f"Error loading {file}: {e}")
        
        # Combine data
        if self.wu_data:
            self.wu_df = pd.concat(self.wu_data, ignore_index=True)
            self.wu_df['obsTimeUtc'] = pd.to_datetime(self.wu_df['obsTimeUtc'])
            print(f"Total WU records: {len(self.wu_df)}")
        else:
            self.wu_df = pd.DataFrame()
            
        if self.tsi_data:
            self.tsi_df = pd.concat(self.tsi_data, ignore_index=True)
            if 'timestamp' in self.tsi_df.columns:
                self.tsi_df['timestamp'] = pd.to_datetime(self.tsi_df['timestamp'])
            elif 'iso_timestamp' in self.tsi_df.columns:
                self.tsi_df['timestamp'] = pd.to_datetime(self.tsi_df['iso_timestamp'])
            print(f"Total TSI records: {len(self.tsi_df)}")
        else:
            self.tsi_df = pd.DataFrame()
            
    def generate_wu_summaries(self):
        """Generate Weather Underground data summaries."""
        if self.wu_df.empty:
            print("No WU data available for summaries")
            return
            
        print("Generating Weather Underground summaries...")
        
        # Daily aggregations
        daily_wu = self.wu_df.groupby([
            self.wu_df['obsTimeUtc'].dt.date,
            'stationID'
        ]).agg({
            'tempAvg': ['mean', 'min', 'max'],
            'humidityAvg': 'mean',
            'precipTotal': 'sum',
            'windspeedAvg': 'mean',
            'windgustAvg': 'max',
            'pressureMax': 'max',
            'pressureMin': 'min'
        }).round(2)
        
        daily_wu.columns = [f'{col[0]}_{col[1]}' for col in daily_wu.columns]
        daily_wu = daily_wu.reset_index()
        daily_wu.rename(columns={'obsTimeUtc': 'date'}, inplace=True)
        
        # Daily aggregations (changed from weekly for higher resolution)
        self.wu_df['day_start'] = self.wu_df['obsTimeUtc'].dt.to_period('D').apply(lambda r: r.start_time)
        daily_wu_agg = self.wu_df.groupby(['day_start', 'stationID']).agg({
            'tempAvg': ['mean', 'min', 'max'],
            'humidityAvg': 'mean',
            'precipTotal': 'sum',
            'windspeedAvg': 'mean',
            'windgustAvg': 'max',
            'pressureMax': 'max',
            'pressureMin': 'min'
        }).round(2)
        
        daily_wu_agg.columns = [f'{col[0]}_{col[1]}' for col in daily_wu_agg.columns]
        daily_wu_agg = daily_wu_agg.reset_index()
        
        # Monthly aggregations
        self.wu_df['month_start'] = self.wu_df['obsTimeUtc'].dt.to_period('M').apply(lambda r: r.start_time)
        monthly_wu = self.wu_df.groupby(['month_start', 'stationID']).agg({
            'tempAvg': ['mean', 'min', 'max'],
            'humidityAvg': 'mean',
            'precipTotal': 'sum',
            'windspeedAvg': 'mean',
            'windgustAvg': 'max',
            'pressureMax': 'max',
            'pressureMin': 'min'
        }).round(2)
        
        monthly_wu.columns = [f'{col[0]}_{col[1]}' for col in monthly_wu.columns]
        monthly_wu = monthly_wu.reset_index()
        
        # Save summaries
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Daily summaries (higher resolution data)
        daily_file = self.processed_dir / "daily_summaries" / f"wu_daily_summary_{timestamp}.csv"
        daily_wu_agg.to_csv(daily_file, index=False)
        print(f"Saved daily WU summary: {daily_file.name}")
        
        # Monthly summaries
        monthly_file = self.processed_dir / "monthly_summaries" / f"wu_monthly_summary_{timestamp}.csv"
        monthly_wu.to_csv(monthly_file, index=False)
        print(f"Saved monthly WU summary: {monthly_file.name}")
        
        return daily_wu, daily_wu_agg, monthly_wu
        
    def generate_tsi_summaries(self):
        """Generate TSI sensor data summaries."""
        if self.tsi_df.empty:
            print("No TSI data available for summaries")
            return
            
        print("Generating TSI sensor summaries...")
        
        # Get device names
        device_col = None
        if 'device_name' in self.tsi_df.columns:
            device_col = 'device_name'
        elif 'friendly_name' in self.tsi_df.columns:
            device_col = 'friendly_name'
        elif 'Device Name' in self.tsi_df.columns:
            device_col = 'Device Name'
        
        if not device_col:
            print("No device name column found in TSI data")
            return
            
        # Daily aggregations
        daily_tsi = self.tsi_df.groupby([
            self.tsi_df['timestamp'].dt.date,
            device_col
        ]).agg({
            'PM 2.5': ['mean', 'min', 'max'],
            'T (C)': ['mean', 'min', 'max'],
            'RH (%)': 'mean'
        }).round(2)
        
        daily_tsi.columns = [f'{col[0]}_{col[1]}' for col in daily_tsi.columns]
        daily_tsi = daily_tsi.reset_index()
        daily_tsi.rename(columns={'timestamp': 'date'}, inplace=True)
        
        # Daily aggregations (changed from weekly for higher resolution)
        self.tsi_df['day_start'] = self.tsi_df['timestamp'].dt.to_period('D').apply(lambda r: r.start_time)
        daily_tsi_agg = self.tsi_df.groupby(['day_start', device_col]).agg({
            'PM 2.5': ['mean', 'min', 'max'],
            'T (C)': ['mean', 'min', 'max'], 
            'RH (%)': 'mean'
        }).round(2)
        
        daily_tsi_agg.columns = [f'{col[0]}_{col[1]}' for col in daily_tsi_agg.columns]
        daily_tsi_agg = daily_tsi_agg.reset_index()
        
        # Monthly aggregations
        self.tsi_df['month_start'] = self.tsi_df['timestamp'].dt.to_period('M').apply(lambda r: r.start_time)
        monthly_tsi = self.tsi_df.groupby(['month_start', device_col]).agg({
            'PM 2.5': ['mean', 'min', 'max'],
            'T (C)': ['mean', 'min', 'max'],
            'RH (%)': 'mean'
        }).round(2)
        
        monthly_tsi.columns = [f'{col[0]}_{col[1]}' for col in monthly_tsi.columns]
        monthly_tsi = monthly_tsi.reset_index()
        
        # Device-specific summaries
        device_summaries = {}
        for device in self.tsi_df[device_col].unique():
            device_data = self.tsi_df[self.tsi_df[device_col] == device].copy()
            summary = {
                'device_name': device,
                'total_records': len(device_data),
                'date_range': f"{device_data['timestamp'].min()} to {device_data['timestamp'].max()}",
                'avg_pm25': device_data['PM 2.5'].mean(),
                'max_pm25': device_data['PM 2.5'].max(),
                'min_pm25': device_data['PM 2.5'].min(),
                'avg_temp': device_data['T (C)'].mean(),
                'max_temp': device_data['T (C)'].max(),
                'min_temp': device_data['T (C)'].min(),
                'avg_humidity': device_data['RH (%)'].mean()
            }
            device_summaries[device] = summary
        
        # Save summaries
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Daily summaries (higher resolution data)
        daily_file = self.processed_dir / "daily_summaries" / f"tsi_daily_summary_{timestamp}.csv"
        daily_tsi_agg.to_csv(daily_file, index=False)
        print(f"Saved daily TSI summary: {daily_file.name}")
        
        # Monthly summaries
        monthly_file = self.processed_dir / "monthly_summaries" / f"tsi_monthly_summary_{timestamp}.csv"
        monthly_tsi.to_csv(monthly_file, index=False)
        print(f"Saved monthly TSI summary: {monthly_file.name}")
        
        # Device summaries
        device_file = self.processed_dir / "device_summaries" / f"tsi_device_summary_{timestamp}.json"
        with open(device_file, 'w') as f:
            json.dump(device_summaries, f, indent=2, default=str)
        print(f"Saved device summaries: {device_file.name}")
        
        return daily_tsi, daily_tsi_agg, monthly_tsi, device_summaries
        
    def generate_visualizations(self, daily_wu=None, daily_wu_agg=None, monthly_wu=None, 
                              daily_tsi=None, daily_tsi_agg=None, monthly_tsi=None):
        """Generate comprehensive visualizations using daily aggregations for higher resolution."""
        print("Generating visualizations...")
        
        # Weather Underground visualizations - using daily aggregations for high resolution
        if daily_wu_agg is not None and not daily_wu_agg.empty:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Weather Underground Daily Trends (High Resolution)', fontsize=16)
            
            # Temperature trends
            for station in daily_wu_agg['stationID'].unique():
                station_data = daily_wu_agg[daily_wu_agg['stationID'] == station]
                axes[0,0].plot(station_data['day_start'], station_data['tempAvg_mean'], 
                              marker='o', label=station)
            axes[0,0].set_title('Average Temperature by Day')
            axes[0,0].set_ylabel('Temperature (°C)')
            axes[0,0].legend()
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # Humidity trends
            for station in daily_wu_agg['stationID'].unique():
                station_data = daily_wu_agg[daily_wu_agg['stationID'] == station]
                axes[0,1].plot(station_data['day_start'], station_data['humidityAvg_mean'], 
                              marker='s', label=station)
            axes[0,1].set_title('Average Humidity by Day')
            axes[0,1].set_ylabel('Humidity (%)')
            axes[0,1].legend()
            axes[0,1].tick_params(axis='x', rotation=45)
            
            # Precipitation totals
            for station in daily_wu_agg['stationID'].unique():
                station_data = daily_wu_agg[daily_wu_agg['stationID'] == station]
                axes[1,0].bar(station_data['day_start'], station_data['precipTotal_sum'], 
                             alpha=0.7, label=station)
            axes[1,0].set_title('Daily Precipitation Total')
            axes[1,0].set_ylabel('Precipitation (mm)')
            axes[1,0].legend()
            axes[1,0].tick_params(axis='x', rotation=45)
            
            # Wind speed
            for station in daily_wu_agg['stationID'].unique():
                station_data = daily_wu_agg[daily_wu_agg['stationID'] == station]
                axes[1,1].plot(station_data['day_start'], station_data['windspeedAvg_mean'], 
                              marker='^', label=station)
            axes[1,1].set_title('Average Wind Speed by Day')
            axes[1,1].set_ylabel('Wind Speed (km/h)')
            axes[1,1].legend()
            axes[1,1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            chart_file = self.charts_dir / f"wu_daily_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Saved WU chart: {chart_file.name}")
        
        # TSI sensor visualizations - using daily aggregations for high resolution
        if daily_tsi_agg is not None and not daily_tsi_agg.empty:
            device_col = daily_tsi_agg.columns[1]  # Second column should be device name
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('TSI Air Quality Sensors Daily Trends (High Resolution)', fontsize=16)
            
            # PM2.5 trends
            for device in daily_tsi_agg[device_col].unique():
                device_data = daily_tsi_agg[daily_tsi_agg[device_col] == device]
                axes[0,0].plot(device_data['day_start'], device_data['PM 2.5_mean'], 
                              marker='o', label=device[:20])  # Truncate long names
            axes[0,0].set_title('Average PM2.5 by Day')
            axes[0,0].set_ylabel('PM2.5 (µg/m³)')
            axes[0,0].legend()
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # Temperature trends
            for device in daily_tsi_agg[device_col].unique():
                device_data = daily_tsi_agg[daily_tsi_agg[device_col] == device]
                axes[0,1].plot(device_data['day_start'], device_data['T (C)_mean'], 
                              marker='s', label=device[:20])
            axes[0,1].set_title('Average Temperature by Day')
            axes[0,1].set_ylabel('Temperature (°C)')
            axes[0,1].legend()
            axes[0,1].tick_params(axis='x', rotation=45)
            
            # Humidity trends
            for device in daily_tsi_agg[device_col].unique():
                device_data = daily_tsi_agg[daily_tsi_agg[device_col] == device]
                axes[1,0].plot(device_data['day_start'], device_data['RH (%)_mean'], 
                              marker='^', label=device[:20])
            axes[1,0].set_title('Average Humidity by Day')
            axes[1,0].set_ylabel('Humidity (%)')
            axes[1,0].legend()
            axes[1,0].tick_params(axis='x', rotation=45)
            
            # PM2.5 distribution
            pm25_data = []
            device_names = []
            for device in daily_tsi_agg[device_col].unique():
                device_data = daily_tsi_agg[daily_tsi_agg[device_col] == device]
                pm25_data.append(device_data['PM 2.5_mean'].dropna())
                device_names.append(device[:20])
            
            axes[1,1].boxplot(pm25_data, labels=device_names)
            axes[1,1].set_title('PM2.5 Distribution by Device')
            axes[1,1].set_ylabel('PM2.5 (µg/m³)')
            axes[1,1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            chart_file = self.charts_dir / f"tsi_daily_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Saved TSI chart: {chart_file.name}")
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive HTML report."""
        print("Generating comprehensive report...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"comprehensive_report_{timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hot Durham Weather Monitoring System - Comprehensive Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #3498db; }}
                .summary {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
                .metric-label {{ font-size: 14px; color: #7f8c8d; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Hot Durham Weather Monitoring System</h1>
            <h2>Comprehensive Data Analysis Report</h2>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h3>Data Summary</h3>
                <div class="metric">
                    <div class="metric-value">{len(self.wu_df) if not self.wu_df.empty else 0}</div>
                    <div class="metric-label">Weather Underground Records</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(self.tsi_df) if not self.tsi_df.empty else 0}</div>
                    <div class="metric-label">TSI Sensor Records</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(self.wu_df['stationID'].unique()) if not self.wu_df.empty else 0}</div>
                    <div class="metric-label">Weather Stations</div>
                </div>
        """
        
        if not self.tsi_df.empty:
            device_col = None
            for col in ['device_name', 'friendly_name', 'Device Name']:
                if col in self.tsi_df.columns:
                    device_col = col
                    break
            if device_col:
                html_content += f"""
                <div class="metric">
                    <div class="metric-value">{len(self.tsi_df[device_col].unique())}</div>
                    <div class="metric-label">Air Quality Sensors</div>
                </div>
                """
        
        html_content += """
            </div>
            
            <h3>Data Coverage</h3>
        """
        
        if not self.wu_df.empty:
            html_content += f"""
            <p><strong>Weather Underground Data:</strong> {self.wu_df['obsTimeUtc'].min()} to {self.wu_df['obsTimeUtc'].max()}</p>
            """
            
        if not self.tsi_df.empty:
            html_content += f"""
            <p><strong>TSI Sensor Data:</strong> {self.tsi_df['timestamp'].min()} to {self.tsi_df['timestamp'].max()}</p>
            """
        
        html_content += """
            <h3>Processing Status</h3>
            <ul>
                <li>✅ Raw data loaded and processed</li>
                <li>✅ Weekly aggregations generated</li>
                <li>✅ Monthly aggregations generated</li>
                <li>✅ Device summaries created</li>
                <li>✅ Visualizations generated</li>
                <li>✅ Processed data exported to CSV files</li>
            </ul>
            
            <h3>Files Generated</h3>
            <p>Summary files have been saved to the <code>processed/</code> directory:</p>
            <ul>
                <li><strong>weekly_summaries/</strong> - Weekly aggregated data</li>
                <li><strong>monthly_summaries/</strong> - Monthly aggregated data</li>
                <li><strong>device_summaries/</strong> - Individual device statistics</li>
            </ul>
            
            <p>Visualization charts have been saved to the <code>reports/charts/</code> directory.</p>
            
            <h3>Next Steps</h3>
            <ul>
                <li>Review generated summary files</li>
                <li>Examine trend visualizations</li>
                <li>Set up automated scheduling for regular updates</li>
                <li>Configure Google Drive sync for backup</li>
            </ul>
        </body>
        </html>
        """
        
        with open(report_file, 'w') as f:
            f.write(html_content)
            
        print(f"Comprehensive report saved: {report_file.name}")
        return report_file
    
    def run_complete_analysis(self):
        """Run the complete analysis workflow."""
        print("="*60)
        print("STARTING COMPREHENSIVE DATA ANALYSIS")
        print("="*60)
        
        # Load data
        self.load_data()
        
        # Generate summaries
        wu_summaries = self.generate_wu_summaries()
        tsi_summaries = self.generate_tsi_summaries()
        
        # Generate visualizations
        if wu_summaries:
            daily_wu, weekly_wu, monthly_wu = wu_summaries
        else:
            daily_wu = weekly_wu = monthly_wu = None
            
        if tsi_summaries:
            daily_tsi, weekly_tsi, monthly_tsi, device_summaries = tsi_summaries
        else:
            daily_tsi = weekly_tsi = monthly_tsi = device_summaries = None
        
        self.generate_visualizations(daily_wu, weekly_wu, monthly_wu, 
                                   daily_tsi, weekly_tsi, monthly_tsi)
        
        # Generate comprehensive report
        report_file = self.generate_comprehensive_report()
        
        print("="*60)
        print("ANALYSIS COMPLETE!")
        print("="*60)
        print(f"Summary files saved to: {self.processed_dir}")
        print(f"Charts saved to: {self.charts_dir}")
        print(f"Report saved to: {report_file}")
        print("="*60)

def main():
    """Main execution function."""
    generator = SummaryReportGenerator()
    generator.run_complete_analysis()

if __name__ == "__main__":
    main()
