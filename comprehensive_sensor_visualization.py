#!/usr/bin/env python3
"""
Comprehensive Multi-Sensor Visualization Dashboard
Inspired by Central Asian Data Center visualization techniques
Shows all test sensors and their historical data on unified graphs
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
import json
import ast
import os
import glob
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style for professional visualizations
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

class MultiSensorVisualizer:
    def __init__(self, data_directory):
        self.data_directory = Path(data_directory)
        self.sensors_data = {}
        self.combined_data = None
        self.output_directory = Path("sensor_visualizations")
        self.output_directory.mkdir(exist_ok=True)
        
    def load_all_sensor_data(self):
        """Load data from all sensor CSV files"""
        print("Loading data from all sensor files...")
        
        # Find all CSV files
        csv_files = list(self.data_directory.glob("KNCDURHA*_complete_history_*.csv"))
        
        all_data = []
        
        for csv_file in csv_files:
            print(f"Processing {csv_file.name}...")
            df = pd.read_csv(csv_file)
            
            # Parse the metric column (contains JSON-like string)
            df['metric_parsed'] = df['metric'].apply(self._parse_metric_column)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Extract metric values as separate columns
            metric_df = pd.json_normalize(df['metric_parsed'])
            df = pd.concat([df, metric_df], axis=1)
            
            all_data.append(df)
            
            # Store individual sensor data
            sensor_id = df['sensor_id'].iloc[0]
            self.sensors_data[sensor_id] = df
            
        # Combine all data
        self.combined_data = pd.concat(all_data, ignore_index=True)
        print(f"Loaded data for {len(self.sensors_data)} sensors")
        print(f"Total records: {len(self.combined_data)}")
        
    def _parse_metric_column(self, metric_str):
        """Parse the metric column which contains dictionary-like strings"""
        try:
            return ast.literal_eval(metric_str)
        except:
            return {}
    
    def create_temperature_comparison(self):
        """Create temperature comparison across all sensors"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('Temperature Analysis Across All Test Sensors', fontsize=16, fontweight='bold')
        
        # 1. Temperature trends over time
        for sensor_id, data in self.sensors_data.items():
            ax1.plot(data['timestamp'], data['tempAvg'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax1.set_title('Average Temperature Trends')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Temperature (°C)')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. Temperature distribution box plot
        temp_data = []
        sensor_labels = []
        for sensor_id, data in self.sensors_data.items():
            temp_data.extend(data['tempAvg'].dropna())
            sensor_labels.extend([sensor_id] * len(data['tempAvg'].dropna()))
        
        temp_df = pd.DataFrame({'Temperature': temp_data, 'Sensor': sensor_labels})
        sns.boxplot(data=temp_df, x='Sensor', y='Temperature', ax=ax2)
        ax2.set_title('Temperature Distribution by Sensor')
        ax2.tick_params(axis='x', rotation=45)
        
        # 3. Temperature range (High - Low) over time
        for sensor_id, data in self.sensors_data.items():
            temp_range = data['tempHigh'] - data['tempLow']
            ax3.plot(data['timestamp'], temp_range, 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax3.set_title('Temperature Range (High - Low)')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Temperature Range (°C)')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. Heat map of average temperatures by sensor and hour
        hourly_temps = {}
        for sensor_id, data in self.sensors_data.items():
            data_copy = data.copy()
            data_copy['hour'] = data_copy['timestamp'].dt.hour
            hourly_avg = data_copy.groupby('hour')['tempAvg'].mean()
            hourly_temps[sensor_id] = hourly_avg
        
        heatmap_data = pd.DataFrame(hourly_temps).T
        sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax4)
        ax4.set_title('Average Temperature by Hour (Heatmap)')
        ax4.set_xlabel('Hour of Day')
        ax4.set_ylabel('Sensor ID')
        
        plt.tight_layout()
        plt.savefig(self.output_directory / 'temperature_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def create_humidity_analysis(self):
        """Create humidity analysis across all sensors"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('Humidity Analysis Across All Test Sensors', fontsize=16, fontweight='bold')
        
        # 1. Humidity trends over time
        for sensor_id, data in self.sensors_data.items():
            ax1.plot(data['timestamp'], data['humidityAvg'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax1.set_title('Average Humidity Trends')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Humidity (%)')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. Humidity vs Temperature scatter plot
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.sensors_data)))
        for i, (sensor_id, data) in enumerate(self.sensors_data.items()):
            ax2.scatter(data['tempAvg'], data['humidityAvg'], 
                       alpha=0.6, c=[colors[i]], label=f'{sensor_id}', s=20)
        
        ax2.set_title('Humidity vs Temperature Correlation')
        ax2.set_xlabel('Temperature (°C)')
        ax2.set_ylabel('Humidity (%)')
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        # 3. Humidity range over time
        for sensor_id, data in self.sensors_data.items():
            humidity_range = data['humidityHigh'] - data['humidityLow']
            ax3.plot(data['timestamp'], humidity_range, 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax3.set_title('Humidity Range (High - Low)')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Humidity Range (%)')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. Daily humidity patterns
        daily_patterns = {}
        for sensor_id, data in self.sensors_data.items():
            data_copy = data.copy()
            data_copy['hour'] = data_copy['timestamp'].dt.hour
            hourly_avg = data_copy.groupby('hour')['humidityAvg'].mean()
            daily_patterns[sensor_id] = hourly_avg
        
        pattern_df = pd.DataFrame(daily_patterns)
        pattern_df.plot(ax=ax4, alpha=0.7, linewidth=2)
        ax4.set_title('Daily Humidity Patterns (Average by Hour)')
        ax4.set_xlabel('Hour of Day')
        ax4.set_ylabel('Average Humidity (%)')
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_directory / 'humidity_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def create_pressure_wind_analysis(self):
        """Create pressure and wind analysis"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('Pressure & Wind Analysis Across All Test Sensors', fontsize=16, fontweight='bold')
        
        # 1. Pressure trends
        for sensor_id, data in self.sensors_data.items():
            pressure_avg = (data['pressureMax'] + data['pressureMin']) / 2
            ax1.plot(data['timestamp'], pressure_avg, 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax1.set_title('Average Pressure Trends')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Pressure (mb)')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. Wind speed trends
        for sensor_id, data in self.sensors_data.items():
            ax2.plot(data['timestamp'], data['windspeedAvg'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax2.set_title('Average Wind Speed Trends')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Wind Speed (km/h)')
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax2.tick_params(axis='x', rotation=45)
        
        # 3. Wind gust analysis
        for sensor_id, data in self.sensors_data.items():
            ax3.plot(data['timestamp'], data['windgustHigh'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        
        ax3.set_title('Wind Gust Highs')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Wind Gust (km/h)')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. Pressure vs Wind Speed correlation
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.sensors_data)))
        for i, (sensor_id, data) in enumerate(self.sensors_data.items()):
            pressure_avg = (data['pressureMax'] + data['pressureMin']) / 2
            ax4.scatter(pressure_avg, data['windspeedAvg'], 
                       alpha=0.6, c=[colors[i]], label=f'{sensor_id}', s=20)
        
        ax4.set_title('Pressure vs Wind Speed Correlation')
        ax4.set_xlabel('Pressure (mb)')
        ax4.set_ylabel('Wind Speed (km/h)')
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_directory / 'pressure_wind_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def create_sensor_correlation_matrix(self):
        """Create correlation analysis between sensors"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('Inter-Sensor Correlation Analysis', fontsize=16, fontweight='bold')
        
        # Find the minimum length across all sensors to align data
        min_length = min(len(data) for data in self.sensors_data.values())
        
        # Prepare data for correlation analysis - use only the first min_length records
        temp_correlations = {}
        humidity_correlations = {}
        pressure_correlations = {}
        wind_correlations = {}
        
        for sensor_id, data in self.sensors_data.items():
            # Sort by timestamp and take first min_length records
            data_sorted = data.sort_values('timestamp').iloc[:min_length]
            temp_correlations[sensor_id] = data_sorted['tempAvg'].values
            humidity_correlations[sensor_id] = data_sorted['humidityAvg'].values
            pressure_correlations[sensor_id] = ((data_sorted['pressureMax'] + data_sorted['pressureMin']) / 2).values
            wind_correlations[sensor_id] = data_sorted['windspeedAvg'].values
        
        # Temperature correlation heatmap
        temp_df = pd.DataFrame(temp_correlations)
        temp_corr = temp_df.corr()
        sns.heatmap(temp_corr, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=ax1, cbar_kws={'label': 'Correlation'})
        ax1.set_title('Temperature Correlation Between Sensors')
        
        # Humidity correlation heatmap
        humidity_df = pd.DataFrame(humidity_correlations)
        humidity_corr = humidity_df.corr()
        sns.heatmap(humidity_corr, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=ax2, cbar_kws={'label': 'Correlation'})
        ax2.set_title('Humidity Correlation Between Sensors')
        
        # Pressure correlation heatmap
        pressure_df = pd.DataFrame(pressure_correlations)
        pressure_corr = pressure_df.corr()
        sns.heatmap(pressure_corr, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=ax3, cbar_kws={'label': 'Correlation'})
        ax3.set_title('Pressure Correlation Between Sensors')
        
        # Wind correlation heatmap
        wind_df = pd.DataFrame(wind_correlations)
        wind_corr = wind_df.corr()
        sns.heatmap(wind_corr, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=ax4, cbar_kws={'label': 'Correlation'})
        ax4.set_title('Wind Speed Correlation Between Sensors')
        
        plt.tight_layout()
        plt.savefig(self.output_directory / 'sensor_correlations.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def create_data_quality_dashboard(self):
        """Create data quality and sensor status dashboard"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('Data Quality & Sensor Status Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Data completeness by sensor
        completeness = {}
        total_expected = max(len(data) for data in self.sensors_data.values())
        
        for sensor_id, data in self.sensors_data.items():
            completeness[sensor_id] = len(data) / total_expected * 100
        
        sensors = list(completeness.keys())
        completeness_values = list(completeness.values())
        
        bars = ax1.bar(sensors, completeness_values, 
                      color=['green' if x >= 95 else 'orange' if x >= 90 else 'red' 
                            for x in completeness_values])
        ax1.set_title('Data Completeness by Sensor (%)')
        ax1.set_ylabel('Completeness (%)')
        ax1.tick_params(axis='x', rotation=45)
        ax1.axhline(y=95, color='red', linestyle='--', alpha=0.7, label='95% Threshold')
        ax1.legend()
        
        # Add value labels on bars
        for bar, value in zip(bars, completeness_values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom', fontsize=8)
        
        # 2. QC Status distribution
        qc_status_counts = {}
        for sensor_id, data in self.sensors_data.items():
            qc_counts = data['qcStatus'].value_counts()
            qc_status_counts[sensor_id] = qc_counts
        
        qc_df = pd.DataFrame(qc_status_counts).fillna(0).T
        qc_df.plot(kind='bar', stacked=True, ax=ax2, 
                  color=['green', 'orange', 'red'])
        ax2.set_title('QC Status Distribution by Sensor')
        ax2.set_xlabel('Sensor ID')
        ax2.set_ylabel('Number of Records')
        ax2.tick_params(axis='x', rotation=45)
        ax2.legend(title='QC Status')
        
        # 3. Data collection timeline
        for sensor_id, data in self.sensors_data.items():
            data_sorted = data.sort_values('timestamp')
            ax3.plot(data_sorted['timestamp'], [sensor_id] * len(data_sorted), 
                    '|', markersize=1, alpha=0.7, label=f'{sensor_id}')
        
        ax3.set_title('Data Collection Timeline')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Sensor ID')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. Missing data patterns
        missing_data = {}
        for sensor_id, data in self.sensors_data.items():
            missing_count = data[['tempAvg', 'humidityAvg', 'windspeedAvg']].isnull().sum()
            missing_data[sensor_id] = missing_count
        
        missing_df = pd.DataFrame(missing_data).T
        missing_df.plot(kind='bar', ax=ax4)
        ax4.set_title('Missing Data Count by Parameter')
        ax4.set_xlabel('Sensor ID')
        ax4.set_ylabel('Missing Data Points')
        ax4.tick_params(axis='x', rotation=45)
        ax4.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_directory / 'data_quality_dashboard.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def create_environmental_dashboard(self):
        """Create comprehensive environmental conditions dashboard"""
        fig = plt.figure(figsize=(24, 16))
        
        # Create a complex grid layout
        gs = fig.add_gridspec(4, 4, hspace=0.3, wspace=0.3)
        
        fig.suptitle('Comprehensive Environmental Monitoring Dashboard - All Test Sensors', 
                    fontsize=20, fontweight='bold', y=0.98)
        
        # 1. Temperature overview (large plot)
        ax1 = fig.add_subplot(gs[0, :2])
        for sensor_id, data in self.sensors_data.items():
            ax1.plot(data['timestamp'], data['tempAvg'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        ax1.set_title('Temperature Trends - All Sensors', fontweight='bold')
        ax1.set_ylabel('Temperature (°C)')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        
        # 2. Humidity overview
        ax2 = fig.add_subplot(gs[0, 2:])
        for sensor_id, data in self.sensors_data.items():
            ax2.plot(data['timestamp'], data['humidityAvg'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        ax2.set_title('Humidity Trends - All Sensors', fontweight='bold')
        ax2.set_ylabel('Humidity (%)')
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        
        # 3. Pressure trends
        ax3 = fig.add_subplot(gs[1, :2])
        for sensor_id, data in self.sensors_data.items():
            pressure_avg = (data['pressureMax'] + data['pressureMin']) / 2
            ax3.plot(data['timestamp'], pressure_avg, 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        ax3.set_title('Pressure Trends - All Sensors', fontweight='bold')
        ax3.set_ylabel('Pressure (mb)')
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        
        # 4. Wind speed trends
        ax4 = fig.add_subplot(gs[1, 2:])
        for sensor_id, data in self.sensors_data.items():
            ax4.plot(data['timestamp'], data['windspeedAvg'], 
                    label=f'{sensor_id}', alpha=0.7, linewidth=1.5)
        ax4.set_title('Wind Speed Trends - All Sensors', fontweight='bold')
        ax4.set_ylabel('Wind Speed (km/h)')
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        
        # 5. Summary statistics table
        ax5 = fig.add_subplot(gs[2, :2])
        ax5.axis('tight')
        ax5.axis('off')
        
        # Create summary statistics
        summary_stats = []
        for sensor_id, data in self.sensors_data.items():
            stats = {
                'Sensor': sensor_id,
                'Temp Avg': f"{data['tempAvg'].mean():.1f}°C",
                'Temp Range': f"{data['tempAvg'].max() - data['tempAvg'].min():.1f}°C",
                'Humidity Avg': f"{data['humidityAvg'].mean():.1f}%",
                'Wind Avg': f"{data['windspeedAvg'].mean():.1f} km/h",
                'Records': len(data)
            }
            summary_stats.append(stats)
        
        summary_df = pd.DataFrame(summary_stats)
        table = ax5.table(cellText=summary_df.values, colLabels=summary_df.columns,
                         cellLoc='center', loc='center', fontsize=8)
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        ax5.set_title('Summary Statistics by Sensor', fontweight='bold', pad=20)
        
        # 6. Environmental correlation matrix
        ax6 = fig.add_subplot(gs[2, 2:])
        
        # Create correlation matrix for environmental parameters
        env_data = []
        for sensor_id, data in self.sensors_data.items():
            sensor_env = {
                'Temperature': data['tempAvg'].mean(),
                'Humidity': data['humidityAvg'].mean(),
                'Pressure': ((data['pressureMax'] + data['pressureMin']) / 2).mean(),
                'Wind Speed': data['windspeedAvg'].mean(),
                'Wind Gust': data['windgustHigh'].mean()
            }
            env_data.append(sensor_env)
        
        env_df = pd.DataFrame(env_data, index=list(self.sensors_data.keys()))
        corr_matrix = env_df.corr()
        
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=ax6, cbar_kws={'label': 'Correlation'})
        ax6.set_title('Environmental Parameters Correlation', fontweight='bold')
        
        # 7. Sensor status overview
        ax7 = fig.add_subplot(gs[3, :])
        
        # Create sensor uptime/status visualization
        sensor_status = []
        colors = []
        
        for sensor_id, data in self.sensors_data.items():
            completeness = len(data) / max(len(d) for d in self.sensors_data.values()) * 100
            qc_good = (data['qcStatus'] <= 1).mean() * 100
            
            sensor_status.append(completeness)
            
            if completeness >= 95 and qc_good >= 95:
                colors.append('green')
            elif completeness >= 90 and qc_good >= 90:
                colors.append('orange')
            else:
                colors.append('red')
        
        bars = ax7.bar(list(self.sensors_data.keys()), sensor_status, color=colors)
        ax7.set_title('Sensor Status Overview (Data Completeness %)', fontweight='bold')
        ax7.set_ylabel('Completeness (%)')
        ax7.tick_params(axis='x', rotation=45)
        ax7.axhline(y=95, color='red', linestyle='--', alpha=0.7, label='95% Threshold')
        ax7.axhline(y=90, color='orange', linestyle='--', alpha=0.7, label='90% Threshold')
        ax7.legend()
        
        # Add status labels
        for bar, value in zip(bars, sensor_status):
            ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{value:.1f}%', ha='center', va='bottom', fontsize=8)
        
        plt.savefig(self.output_directory / 'environmental_dashboard.png', dpi=300, bbox_inches='tight')
        plt.show()
        
    def generate_summary_report(self):
        """Generate a summary report of the analysis"""
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_sensors': len(self.sensors_data),
            'total_records': len(self.combined_data),
            'data_period': {
                'start': self.combined_data['timestamp'].min().isoformat(),
                'end': self.combined_data['timestamp'].max().isoformat()
            },
            'sensor_summary': {}
        }
        
        for sensor_id, data in self.sensors_data.items():
            sensor_summary = {
                'records_count': len(data),
                'data_completeness': len(data) / max(len(d) for d in self.sensors_data.values()) * 100,
                'qc_status_distribution': data['qcStatus'].value_counts().to_dict(),
                'temperature_stats': {
                    'min': float(data['tempAvg'].min()),
                    'max': float(data['tempAvg'].max()),
                    'mean': float(data['tempAvg'].mean()),
                    'std': float(data['tempAvg'].std())
                },
                'humidity_stats': {
                    'min': float(data['humidityAvg'].min()),
                    'max': float(data['humidityAvg'].max()),
                    'mean': float(data['humidityAvg'].mean()),
                    'std': float(data['humidityAvg'].std())
                },
                'wind_stats': {
                    'min': float(data['windspeedAvg'].min()),
                    'max': float(data['windspeedAvg'].max()),
                    'mean': float(data['windspeedAvg'].mean()),
                    'std': float(data['windspeedAvg'].std())
                }
            }
            report['sensor_summary'][sensor_id] = sensor_summary
        
        # Save report
        with open(self.output_directory / 'analysis_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Analysis complete! Generated {len(os.listdir(self.output_directory))} visualization files.")
        print(f"Output directory: {self.output_directory.absolute()}")
        
        return report
    
    def run_complete_analysis(self):
        """Run the complete visualization analysis"""
        print("Starting comprehensive sensor visualization analysis...")
        print("=" * 60)
        
        # Load data
        self.load_all_sensor_data()
        
        # Generate all visualizations
        print("\n1. Creating temperature analysis...")
        self.create_temperature_comparison()
        
        print("\n2. Creating humidity analysis...")
        self.create_humidity_analysis()
        
        print("\n3. Creating pressure and wind analysis...")
        self.create_pressure_wind_analysis()
        
        print("\n4. Creating sensor correlation analysis...")
        self.create_sensor_correlation_matrix()
        
        print("\n5. Creating data quality dashboard...")
        self.create_data_quality_dashboard()
        
        print("\n6. Creating comprehensive environmental dashboard...")
        self.create_environmental_dashboard()
        
        print("\n7. Generating summary report...")
        report = self.generate_summary_report()
        
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE!")
        print(f"Total sensors analyzed: {len(self.sensors_data)}")
        print(f"Total data points: {len(self.combined_data):,}")
        print(f"Analysis period: {report['data_period']['start']} to {report['data_period']['end']}")
        print(f"Visualizations saved to: {self.output_directory.absolute()}")
        
        return report

if __name__ == "__main__":
    # Initialize the visualizer
    data_dir = "/Users/alainsoto/IdeaProjects/Hot Durham/data/historical_test_sensors"
    visualizer = MultiSensorVisualizer(data_dir)
    
    # Run complete analysis
    report = visualizer.run_complete_analysis()
