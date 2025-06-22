#!/usr/bin/env python3
"""
Anomaly Detection and Trend Analysis for Hot Durham Sensor Data

This script implements comprehensive trend analysis and anomaly detection for 
Weather Underground and TSI sensor data to investigate decreases and anomalies.
Addresses todo item: "Investigate reasons for any observed decreases or anomalies in sensor data"
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, timedelta
import json
import warnings
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

warnings.filterwarnings('ignore')

class AnomalyDetectionSystem:
    """Advanced anomaly detection and trend analysis for sensor data."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.raw_dir = self.base_dir / "raw_pulls"
        self.output_dir = self.base_dir / "reports" / "anomaly_analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.wu_data = []
        self.tsi_data = []
        self.wu_df = pd.DataFrame()
        self.tsi_df = pd.DataFrame()
        self.anomalies = {}
        self.trends = {}
        
        # Load configuration
        self.config = self.load_configuration()
        
    def load_configuration(self) -> dict:
        """Load or create default configuration for anomaly detection."""
        config_file = self.base_dir / "config" / "anomaly_detection_config.json"
        config_file.parent.mkdir(exist_ok=True)
        
        # Default configuration
        default_config = {
            "anomaly_thresholds": {
                "temperature": {
                    "z_score_threshold": 3.0,
                    "min_temp": -20.0,
                    "max_temp": 50.0
                },
                "humidity": {
                    "z_score_threshold": 3.0,
                    "min_humidity": 0.0,
                    "max_humidity": 100.0
                },
                "pm25": {
                    "z_score_threshold": 2.5,
                    "max_safe_level": 35.0,
                    "unhealthy_level": 55.0
                }
            },
            "trend_analysis": {
                "window_size_days": 7,
                "trend_threshold": 0.05,
                "seasonal_analysis": True
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Save default config
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
            
        return default_config
        
    def load_data(self):
        """Load all available raw data for analysis."""
        print("Loading raw data for anomaly analysis...")
        
        # Load Weather Underground data
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
        
        # Load TSI data
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
        
        self._process_data()
        
    def _process_data(self):
        """Clean and process loaded data."""
        # Process Weather Underground data
        if self.wu_data:
            self.wu_df = pd.concat(self.wu_data, ignore_index=True)
            if 'obsTimeUtc' in self.wu_df.columns:
                self.wu_df['timestamp'] = pd.to_datetime(self.wu_df['obsTimeUtc'])
            self.wu_df = self.wu_df.drop_duplicates()
            
            # Convert numeric columns
            numeric_cols = ['tempAvg', 'humidityAvg', 'windspeedAvg', 'precipTotal', 'heatindexAvg']
            for col in numeric_cols:
                if col in self.wu_df.columns:
                    self.wu_df[col] = pd.to_numeric(self.wu_df[col], errors='coerce')
        
        # Process TSI data
        if self.tsi_data:
            self.tsi_df = pd.concat(self.tsi_data, ignore_index=True)
            
            # Handle timestamp column
            timestamp_cols = ['timestamp', 'iso_timestamp', 'cloud_timestamp']
            for col in timestamp_cols:
                if col in self.tsi_df.columns:
                    self.tsi_df['timestamp'] = pd.to_datetime(self.tsi_df[col])
                    break
            
            # Handle device name column
            device_cols = ['device_name', 'friendly_name', 'Device Name']
            self.device_col = None
            for col in device_cols:
                if col in self.tsi_df.columns:
                    self.device_col = col
                    break
            
            # Convert numeric columns
            numeric_cols = ['PM 2.5', 'mcpm2x5', 'T (C)', 'temp_c', 'RH (%)', 'rh_percent']
            for col in numeric_cols:
                if col in self.tsi_df.columns:
                    self.tsi_df[col] = pd.to_numeric(self.tsi_df[col], errors='coerce')
        
        print(f"Processed {len(self.wu_df)} WU records and {len(self.tsi_df)} TSI records")
    
    def detect_weather_anomalies(self):
        """Detect anomalies in Weather Underground data."""
        if self.wu_df.empty:
            print("No WU data available for anomaly detection")
            return
        
        print("Analyzing Weather Underground data for anomalies...")
        
        # Group by station for analysis
        stations = self.wu_df['stationId'].unique() if 'stationId' in self.wu_df.columns else ['Unknown']
        
        wu_anomalies = {}
        
        for station in stations:
            if station != 'Unknown':
                station_data = self.wu_df[self.wu_df['stationId'] == station].copy()
            else:
                station_data = self.wu_df.copy()
                
            if len(station_data) < 10:  # Need minimum data for analysis
                continue
                
            station_data = station_data.sort_values('timestamp')
            station_anomalies = {}
            
            # Analyze each metric
            metrics = ['tempAvg', 'humidityAvg', 'windspeedAvg', 'precipTotal']
            
            for metric in metrics:
                if metric not in station_data.columns:
                    continue
                    
                values = station_data[metric].dropna()
                if len(values) < 5:
                    continue
                
                # Statistical outlier detection
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = station_data[(station_data[metric] < lower_bound) | 
                                      (station_data[metric] > upper_bound)]
                
                # Trend analysis - detect sudden drops/increases
                station_data[f'{metric}_rolling_mean'] = station_data[metric].rolling(window=24, min_periods=5).mean()
                station_data[f'{metric}_change'] = station_data[metric].diff()
                
                # Detect large sudden changes (>2 standard deviations)
                change_std = station_data[f'{metric}_change'].std()
                large_changes = station_data[abs(station_data[f'{metric}_change']) > 2 * change_std]
                
                # Zero/null value analysis
                zero_values = station_data[station_data[metric] == 0]
                null_values = station_data[station_data[metric].isna()]
                
                station_anomalies[metric] = {
                    'statistical_outliers': len(outliers),
                    'large_sudden_changes': len(large_changes),
                    'zero_values': len(zero_values),
                    'null_values': len(null_values),
                    'outlier_timestamps': outliers['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
                    'large_change_timestamps': large_changes['timestamp'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
                    'mean_value': float(values.mean()),
                    'std_value': float(values.std()),
                    'trend_slope': self._calculate_trend_slope(station_data['timestamp'], values)
                }
            
            wu_anomalies[station] = station_anomalies
        
        self.anomalies['wu'] = wu_anomalies
        return wu_anomalies
    
    def detect_tsi_anomalies(self):
        """Detect anomalies in TSI sensor data."""
        if self.tsi_df.empty or not self.device_col:
            print("No TSI data available for anomaly detection")
            return
        
        print("Analyzing TSI sensor data for anomalies...")
        
        devices = self.tsi_df[self.device_col].unique()
        tsi_anomalies = {}
        
        for device in devices:
            device_data = self.tsi_df[self.tsi_df[self.device_col] == device].copy()
            
            if len(device_data) < 10:
                continue
                
            device_data = device_data.sort_values('timestamp')
            device_anomalies = {}
            
            # Analyze PM2.5, Temperature, and Humidity
            metrics = []
            for col in ['PM 2.5', 'mcpm2x5']:
                if col in device_data.columns:
                    metrics.append((col, 'PM2.5'))
                    break
            for col in ['T (C)', 'temp_c']:
                if col in device_data.columns:
                    metrics.append((col, 'Temperature'))
                    break
            for col in ['RH (%)', 'rh_percent']:
                if col in device_data.columns:
                    metrics.append((col, 'Humidity'))
                    break
            
            for col, metric_name in metrics:
                values = device_data[col].dropna()
                if len(values) < 5:
                    device_anomalies[metric_name] = {
                        'status': 'insufficient_data',
                        'total_readings': len(device_data),
                        'valid_readings': len(values)
                    }
                    continue
                
                # Detect sensor malfunctions (stuck values)
                stuck_values = values.value_counts()
                max_repeated = stuck_values.iloc[0] if len(stuck_values) > 0 else 0
                stuck_percentage = (max_repeated / len(values)) * 100
                
                # Detect impossible values for each metric
                impossible_values = 0
                if metric_name == 'PM2.5':
                    impossible_values = len(values[(values < 0) | (values > 1000)])
                elif metric_name == 'Temperature':
                    impossible_values = len(values[(values < -50) | (values > 70)])
                elif metric_name == 'Humidity':
                    impossible_values = len(values[(values < 0) | (values > 100)])
                
                # Gap analysis
                device_data_sorted = device_data.sort_values('timestamp')
                time_diffs = device_data_sorted['timestamp'].diff()
                large_gaps = time_diffs[time_diffs > timedelta(hours=2)]
                
                device_anomalies[metric_name] = {
                    'total_readings': len(device_data),
                    'valid_readings': len(values),
                    'completeness_percentage': (len(values) / len(device_data)) * 100,
                    'stuck_value_percentage': stuck_percentage,
                    'impossible_values': impossible_values,
                    'large_time_gaps': len(large_gaps),
                    'mean_value': float(values.mean()) if len(values) > 0 else None,
                    'std_value': float(values.std()) if len(values) > 0 else None,
                    'trend_slope': self._calculate_trend_slope(device_data['timestamp'], values) if len(values) > 1 else None
                }
            
            tsi_anomalies[device] = device_anomalies
        
        self.anomalies['tsi'] = tsi_anomalies
        return tsi_anomalies
    
    def _calculate_trend_slope(self, timestamps, values):
        """Calculate trend slope using linear regression."""
        if len(timestamps) < 2 or len(values) < 2:
            return None
            
        # Convert timestamps to numeric (days since first timestamp)
        timestamp_numeric = [(t - timestamps.iloc[0]).total_seconds() / 86400 for t in timestamps]
        
        try:
            # Use direct unpacking which works with both old and new scipy versions
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamp_numeric, values)  # type: ignore
            return {
                'slope': float(slope),  # type: ignore
                'r_squared': float(r_value ** 2),  # type: ignore
                'p_value': float(p_value)  # type: ignore
            }
        except:
            return None
    
    def generate_trend_analysis(self):
        """Generate comprehensive trend analysis."""
        print("Generating trend analysis...")
        
        # Weather Underground trends
        if not self.wu_df.empty:
            self._analyze_wu_trends()
        
        # TSI trends
        if not self.tsi_df.empty and self.device_col:
            self._analyze_tsi_trends()
    
    def _analyze_wu_trends(self):
        """Analyze Weather Underground data trends."""
        stations = self.wu_df['stationId'].unique() if 'stationId' in self.wu_df.columns else ['Unknown']
        
        wu_trends = {}
        
        for station in stations:
            if station != 'Unknown':
                station_data = self.wu_df[self.wu_df['stationId'] == station].copy()
            else:
                station_data = self.wu_df.copy()
                
            station_data = station_data.sort_values('timestamp')
            
            # Daily aggregation for trend analysis
            station_data['date'] = station_data['timestamp'].dt.date
            daily_data = station_data.groupby('date').agg({
                'tempAvg': 'mean',
                'humidityAvg': 'mean',
                'windspeedAvg': 'mean',
                'precipTotal': 'sum'
            }).reset_index()
            
            station_trends = {}
            
            for metric in ['tempAvg', 'humidityAvg', 'windspeedAvg', 'precipTotal']:
                if metric in daily_data.columns:
                    values = daily_data[metric].dropna()
                    if len(values) > 3:
                        dates_numeric = [(d - daily_data['date'].iloc[0]).days for d in daily_data['date']]
                        
                        trend_info = self._calculate_trend_slope(pd.Series(dates_numeric), values)
                        if trend_info:
                            # Determine trend direction and significance
                            slope = trend_info['slope']
                            p_value = trend_info['p_value']
                            
                            if p_value < 0.05:  # Statistically significant
                                if slope > 0:
                                    direction = 'increasing'
                                else:
                                    direction = 'decreasing'
                            else:
                                direction = 'stable'
                            
                            station_trends[metric] = {
                                'direction': direction,
                                'slope_per_day': slope,
                                'r_squared': trend_info['r_squared'],
                                'p_value': p_value,
                                'significance': 'significant' if p_value < 0.05 else 'not_significant'
                            }
            
            wu_trends[station] = station_trends
        
        self.trends['wu'] = wu_trends
    
    def _analyze_tsi_trends(self):
        """Analyze TSI sensor data trends."""
        devices = self.tsi_df[self.device_col].unique()
        tsi_trends = {}
        
        for device in devices:
            device_data = self.tsi_df[self.tsi_df[self.device_col] == device].copy()
            device_data = device_data.sort_values('timestamp')
            
            # 15-minute interval aggregation for higher resolution trend analysis
            device_data['interval_15min'] = device_data['timestamp'].dt.floor('15min')
            interval_data = device_data.groupby('interval_15min').agg({
                col: 'mean' for col in ['PM 2.5', 'mcpm2x5', 'T (C)', 'temp_c', 'RH (%)', 'rh_percent']
                if col in device_data.columns
            }).reset_index()
            
            device_trends = {}
            
            # Map columns to standard names
            metric_mapping = {
                'PM 2.5': 'PM2.5', 'mcpm2x5': 'PM2.5',
                'T (C)': 'Temperature', 'temp_c': 'Temperature',
                'RH (%)': 'Humidity', 'rh_percent': 'Humidity'
            }
            
            for col in interval_data.columns:
                if col in metric_mapping:
                    metric_name = metric_mapping[col]
                    values = interval_data[col].dropna()
                    
                    if len(values) > 3:
                        # Convert 15-minute intervals to numeric (in hours)
                        intervals_numeric = [(t - interval_data['interval_15min'].iloc[0]).total_seconds() / 3600 
                                           for t in interval_data['interval_15min']]
                        
                        trend_info = self._calculate_trend_slope(pd.Series(intervals_numeric), values)
                        if trend_info:
                            slope = trend_info['slope']
                            p_value = trend_info['p_value']
                            
                            if p_value < 0.05:
                                direction = 'increasing' if slope > 0 else 'decreasing'
                            else:
                                direction = 'stable'
                            
                            device_trends[metric_name] = {
                                'direction': direction,
                                'slope_per_hour': slope,
                                'r_squared': trend_info['r_squared'],
                                'p_value': p_value,
                                'significance': 'significant' if p_value < 0.05 else 'not_significant'
                            }
            
            tsi_trends[device] = device_trends
        
        self.trends['tsi'] = tsi_trends
    
    def create_anomaly_visualizations(self):
        """Create comprehensive visualizations for anomaly analysis."""
        print("Creating anomaly analysis visualizations...")
        
        # Create Weather Underground anomaly plots
        if not self.wu_df.empty:
            self._create_wu_anomaly_plots()
        
        # Create TSI anomaly plots
        if not self.tsi_df.empty and self.device_col:
            self._create_tsi_anomaly_plots()
        
        # Create combined trend comparison
        self._create_trend_comparison_plot()
    
    def _create_wu_anomaly_plots(self):
        """Create Weather Underground anomaly visualization."""
        stations = self.wu_df['stationId'].unique() if 'stationId' in self.wu_df.columns else ['All']
        
        for station in stations:
            if station != 'All':
                station_data = self.wu_df[self.wu_df['stationId'] == station].copy()
                title_suffix = f" - {station}"
            else:
                station_data = self.wu_df.copy()
                title_suffix = ""
            
            station_data = station_data.sort_values('timestamp')
            
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'Weather Underground Anomaly Analysis{title_suffix}', fontsize=16, fontweight='bold')
            
            metrics = [
                ('tempAvg', 'Temperature (°C)', axes[0,0]),
                ('humidityAvg', 'Humidity (%)', axes[0,1]),
                ('windspeedAvg', 'Wind Speed', axes[1,0]),
                ('precipTotal', 'Precipitation', axes[1,1])
            ]
            
            for metric, ylabel, ax in metrics:
                if metric not in station_data.columns:
                    ax.text(0.5, 0.5, f'No {metric} data available', 
                           ha='center', va='center', transform=ax.transAxes)
                    continue
                
                values = station_data[metric].dropna()
                if len(values) == 0:
                    ax.text(0.5, 0.5, f'No valid {metric} data', 
                           ha='center', va='center', transform=ax.transAxes)
                    continue
                
                # Plot time series
                valid_data = station_data.dropna(subset=[metric])
                ax.plot(valid_data['timestamp'], valid_data[metric], 'b-', alpha=0.7, linewidth=1)
                
                # Add rolling mean
                window_size = min(24, len(valid_data) // 4)
                if window_size > 1:
                    rolling_mean = valid_data[metric].rolling(window=window_size).mean()
                    ax.plot(valid_data['timestamp'], rolling_mean, 'r-', linewidth=2, alpha=0.8, label='Rolling Mean')
                
                # Highlight outliers
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = valid_data[(valid_data[metric] < lower_bound) | (valid_data[metric] > upper_bound)]
                if not outliers.empty:
                    ax.scatter(outliers['timestamp'], outliers[metric], 
                             color='red', s=50, alpha=0.8, label='Outliers')
                
                ax.set_xlabel('Time')
                ax.set_ylabel(ylabel)
                ax.set_title(f'{ylabel} - Anomaly Detection')
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                # Rotate x-axis labels
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / f'wu_anomaly_analysis_{station}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()
    
    def _create_tsi_anomaly_plots(self):
        """Create TSI sensor anomaly visualization."""
        devices = self.tsi_df[self.device_col].unique()
        
        for device in devices:
            device_data = self.tsi_df[self.tsi_df[self.device_col] == device].copy()
            device_data = device_data.sort_values('timestamp')
            
            if len(device_data) < 5:
                continue
            
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'TSI Sensor Anomaly Analysis - {device}', fontsize=16, fontweight='bold')
            
            # Map available columns
            metrics = []
            for col in ['PM 2.5', 'mcpm2x5']:
                if col in device_data.columns:
                    metrics.append((col, 'PM2.5 (μg/m³)', axes[0,0]))
                    break
            for col in ['T (C)', 'temp_c']:
                if col in device_data.columns:
                    metrics.append((col, 'Temperature (°C)', axes[0,1]))
                    break
            for col in ['RH (%)', 'rh_percent']:
                if col in device_data.columns:
                    metrics.append((col, 'Humidity (%)', axes[1,0]))
                    break
            
            # Add data quality plot
            metrics.append(('data_quality', 'Data Quality', axes[1,1]))
            
            for metric, ylabel, ax in metrics:
                if metric == 'data_quality':
                    # Data quality visualization with 15-minute intervals
                    device_data['interval_15min'] = device_data['timestamp'].dt.floor('15min')
                    interval_counts = device_data.groupby('interval_15min').size()
                    
                    ax.bar(interval_counts.index, interval_counts.values, alpha=0.7, color='green')
                    ax.set_xlabel('Time')
                    ax.set_ylabel('Records per 15-min Interval')
                    ax.set_title('Data Collection Frequency (15-min intervals)')
                    ax.grid(True, alpha=0.3)
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
                    continue
                
                if metric not in device_data.columns:
                    ax.text(0.5, 0.5, f'No {metric} data available', 
                           ha='center', va='center', transform=ax.transAxes)
                    continue
                
                values = device_data[metric].dropna()
                if len(values) == 0:
                    ax.text(0.5, 0.5, f'No valid {metric} data', 
                           ha='center', va='center', transform=ax.transAxes)
                    continue
                
                # Plot time series
                valid_data = device_data.dropna(subset=[metric])
                ax.plot(valid_data['timestamp'], valid_data[metric], 'b-', alpha=0.7, linewidth=1)
                
                # Add rolling mean
                window_size = min(24, len(valid_data) // 4)
                if window_size > 1:
                    rolling_mean = valid_data[metric].rolling(window=window_size).mean()
                    ax.plot(valid_data['timestamp'], rolling_mean, 'r-', linewidth=2, alpha=0.8, label='Rolling Mean')
                
                # Detect and highlight stuck values
                value_counts = values.value_counts()
                if len(value_counts) > 0:
                    most_common_value = value_counts.index[0]
                    most_common_count = value_counts.iloc[0]
                    
                    if most_common_count > len(values) * 0.1:  # If more than 10% are the same value
                        stuck_data = valid_data[valid_data[metric] == most_common_value]
                        ax.scatter(stuck_data['timestamp'], stuck_data[metric], 
                                 color='orange', s=30, alpha=0.8, label=f'Potential Stuck Values ({most_common_value})')
                
                ax.set_xlabel('Time')
                ax.set_ylabel(ylabel)
                ax.set_title(f'{ylabel} - Anomaly Detection')
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            plt.savefig(self.output_dir / f'tsi_anomaly_analysis_{device}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()
    
    def _create_trend_comparison_plot(self):
        """Create trend comparison visualization."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Data Trends and Anomaly Summary', fontsize=16, fontweight='bold')
        
        # WU trend summary
        if 'wu' in self.trends:
            ax = axes[0,0]
            trend_counts = {'increasing': 0, 'decreasing': 0, 'stable': 0}
            
            for station, metrics in self.trends['wu'].items():
                for metric, trend_info in metrics.items():
                    trend_counts[trend_info['direction']] += 1
            
            ax.bar(trend_counts.keys(), trend_counts.values(), color=['green', 'red', 'blue'], alpha=0.7)
            ax.set_title('Weather Underground Trend Summary')
            ax.set_ylabel('Number of Metrics')
        
        # TSI trend summary
        if 'tsi' in self.trends:
            ax = axes[0,1]
            trend_counts = {'increasing': 0, 'decreasing': 0, 'stable': 0}
            
            for device, metrics in self.trends['tsi'].items():
                for metric, trend_info in metrics.items():
                    trend_counts[trend_info['direction']] += 1
            
            ax.bar(trend_counts.keys(), trend_counts.values(), color=['green', 'red', 'blue'], alpha=0.7)
            ax.set_title('TSI Sensor Trend Summary')
            ax.set_ylabel('Number of Metrics')
        
        # Data quality summary
        ax = axes[1,0]
        quality_scores = []
        labels = []
        
        if 'wu' in self.anomalies:
            for station in self.anomalies['wu'].keys():
                labels.append(f'WU-{station}')
                # Calculate quality score based on anomalies
                score = 100  # Start with perfect score
                station_anomalies = self.anomalies['wu'][station]
                for metric_anomalies in station_anomalies.values():
                    score -= metric_anomalies.get('statistical_outliers', 0) * 2
                    score -= metric_anomalies.get('null_values', 0) * 5
                quality_scores.append(max(0, score))
        
        if 'tsi' in self.anomalies:
            for device in self.anomalies['tsi'].keys():
                labels.append(f'TSI-{device}')
                score = 100
                device_anomalies = self.anomalies['tsi'][device]
                for metric_anomalies in device_anomalies.values():
                    if isinstance(metric_anomalies, dict):
                        completeness = metric_anomalies.get('completeness_percentage', 0)
                        score = min(score, completeness)
                quality_scores.append(max(0, score))
        
        if quality_scores:
            colors = ['green' if s > 80 else 'orange' if s > 50 else 'red' for s in quality_scores]
            ax.bar(range(len(quality_scores)), quality_scores, color=colors, alpha=0.7)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45)
            ax.set_title('Data Quality Scores')
            ax.set_ylabel('Quality Score (%)')
            ax.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='Good Threshold')
            ax.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='Poor Threshold')
            ax.legend()
        
        # Timeline of data availability
        ax = axes[1,1]
        
        if not self.wu_df.empty:
            wu_dates = self.wu_df['timestamp'].dt.date.unique()
            ax.scatter([1] * len(wu_dates), wu_dates, alpha=0.6, label='WU Data', color='blue')
        
        if not self.tsi_df.empty:
            tsi_dates = self.tsi_df['timestamp'].dt.date.unique()
            ax.scatter([2] * len(tsi_dates), tsi_dates, alpha=0.6, label='TSI Data', color='green')
        
        ax.set_xlim(0.5, 2.5)
        ax.set_xticks([1, 2])
        ax.set_xticklabels(['Weather Underground', 'TSI Sensors'])
        ax.set_title('Data Collection Timeline')
        ax.set_ylabel('Date')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_dir / f'trend_comparison_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_anomaly_report(self):
        """Generate comprehensive anomaly analysis report."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_summary': {
                'wu_data_records': len(self.wu_df),
                'tsi_data_records': len(self.tsi_df),
                'wu_date_range': {
                    'start': self.wu_df['timestamp'].min().isoformat() if not self.wu_df.empty else None,
                    'end': self.wu_df['timestamp'].max().isoformat() if not self.wu_df.empty else None
                },
                'tsi_date_range': {
                    'start': self.tsi_df['timestamp'].min().isoformat() if not self.tsi_df.empty else None,
                    'end': self.tsi_df['timestamp'].max().isoformat() if not self.tsi_df.empty else None
                }
            },
            'anomalies': self.anomalies,
            'trends': self.trends,
            'recommendations': self._generate_recommendations()
        }
        
        # Save detailed JSON report
        report_file = self.output_dir / f'anomaly_analysis_report_{timestamp}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate summary HTML report
        self._generate_html_report(report, timestamp)
        
        print(f"✓ Anomaly analysis report saved to: {report_file}")
        return report
    
    def _generate_recommendations(self):
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Check WU data quality
        if 'wu' in self.anomalies:
            for station, metrics in self.anomalies['wu'].items():
                for metric, anomaly_info in metrics.items():
                    if anomaly_info.get('null_values', 0) > 10:
                        recommendations.append({
                            'priority': 'high',
                            'type': 'data_quality',
                            'description': f'Weather Underground station {station} has {anomaly_info["null_values"]} null values for {metric}',
                            'action': 'Check station connectivity and data transmission'
                        })
                    
                    if anomaly_info.get('statistical_outliers', 0) > 5:
                        recommendations.append({
                            'priority': 'medium',
                            'type': 'data_validation',
                            'description': f'Weather Underground station {station} has {anomaly_info["statistical_outliers"]} outliers for {metric}',
                            'action': 'Review sensor calibration and environmental factors'
                        })
        
        # Check TSI data quality
        if 'tsi' in self.anomalies:
            for device, metrics in self.anomalies['tsi'].items():
                for metric, anomaly_info in metrics.items():
                    if isinstance(anomaly_info, dict):
                        completeness = anomaly_info.get('completeness_percentage', 0)
                        if completeness < 50:
                            recommendations.append({
                                'priority': 'critical',
                                'type': 'sensor_malfunction',
                                'description': f'TSI device {device} has only {completeness:.1f}% data completeness for {metric}',
                                'action': 'Immediate sensor inspection and maintenance required'
                            })
                        
                        stuck_percentage = anomaly_info.get('stuck_value_percentage', 0)
                        if stuck_percentage > 20:
                            recommendations.append({
                                'priority': 'high',
                                'type': 'sensor_calibration',
                                'description': f'TSI device {device} shows {stuck_percentage:.1f}% stuck values for {metric}',
                                'action': 'Sensor recalibration or replacement needed'
                            })
        
        # Check trends
        if 'wu' in self.trends:
            for station, metrics in self.trends['wu'].items():
                for metric, trend_info in metrics.items():
                    if trend_info['direction'] == 'decreasing' and trend_info['significance'] == 'significant':
                        recommendations.append({
                            'priority': 'medium',
                            'type': 'trend_analysis',
                            'description': f'Weather Underground station {station} shows significant decreasing trend for {metric}',
                            'action': 'Investigate environmental or instrumental factors causing decline'
                        })
        
        return recommendations
    
    def _generate_html_report(self, report, timestamp):
        """Generate HTML summary report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hot Durham Anomaly Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 10px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .critical {{ background-color: #ffe6e6; }}
                .high {{ background-color: #fff2e6; }}
                .medium {{ background-color: #ffffcc; }}
                .good {{ background-color: #e6ffe6; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔍 Hot Durham Anomaly Analysis Report</h1>
                <p><strong>Generated:</strong> {report['generated_at']}</p>
                <p><strong>Analysis Period:</strong> {report['analysis_summary']['wu_date_range']['start']} to {report['analysis_summary']['wu_date_range']['end']}</p>
            </div>
            
            <div class="section">
                <h2>📊 Data Summary</h2>
                <ul>
                    <li><strong>Weather Underground Records:</strong> {report['analysis_summary']['wu_data_records']:,}</li>
                    <li><strong>TSI Sensor Records:</strong> {report['analysis_summary']['tsi_data_records']:,}</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>⚠️ Key Findings & Recommendations</h2>
        """
        
        # Add recommendations
        for rec in report['recommendations'][:10]:  # Show top 10
            priority_class = rec['priority']
            html_content += f"""
                <div class="{priority_class}" style="margin: 10px 0; padding: 10px; border-radius: 5px;">
                    <strong>{rec['priority'].upper()}:</strong> {rec['description']}<br>
                    <em>Action:</em> {rec['action']}
                </div>
            """
        
        html_content += """
            </div>
            
            <div class="section">
                <h2>📈 Trend Analysis Summary</h2>
        """
        
        # Add trend summaries
        if 'wu' in report['trends']:
            html_content += "<h3>Weather Underground Trends</h3>"
            for station, metrics in report['trends']['wu'].items():
                html_content += f"<h4>Station: {station}</h4><ul>"
                for metric, trend in metrics.items():
                    direction_icon = "📈" if trend['direction'] == 'increasing' else "📉" if trend['direction'] == 'decreasing' else "➡️"
                    html_content += f"<li>{direction_icon} <strong>{metric}:</strong> {trend['direction']} ({trend['significance']})</li>"
                html_content += "</ul>"
        
        if 'tsi' in report['trends']:
            html_content += "<h3>TSI Sensor Trends</h3>"
            for device, metrics in report['trends']['tsi'].items():
                html_content += f"<h4>Device: {device}</h4><ul>"
                for metric, trend in metrics.items():
                    direction_icon = "📈" if trend['direction'] == 'increasing' else "📉" if trend['direction'] == 'decreasing' else "➡️"
                    html_content += f"<li>{direction_icon} <strong>{metric}:</strong> {trend['direction']} ({trend['significance']})</li>"
                html_content += "</ul>"
        
        html_content += """
            </div>
            
            <div class="section">
                <h2>🎯 Next Steps</h2>
                <ol>
                    <li>Address critical priority issues immediately</li>
                    <li>Schedule maintenance for high-priority sensor issues</li>
                    <li>Monitor trends for medium-priority concerns</li>
                    <li>Review data collection processes for identified gaps</li>
                    <li>Implement automated alerts for similar issues</li>
                </ol>
            </div>
            
            <footer style="margin-top: 40px; padding: 20px; background-color: #f9f9f9; border-radius: 5px;">
                <p><em>This report was automatically generated by the Hot Durham Anomaly Detection System.</em></p>
                <p><em>For detailed technical analysis, see the accompanying JSON report and visualization charts.</em></p>
            </footer>
        </body>
        </html>
        """
        
        html_file = self.output_dir / f'anomaly_analysis_summary_{timestamp}.html'
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"✓ HTML summary report saved to: {html_file}")
    
    def run_complete_analysis(self):
        """Run complete anomaly detection and trend analysis."""
        print("🔍 Starting comprehensive anomaly detection and trend analysis...")
        print("=" * 60)
        
        # Load data
        self.load_data()
        
        if self.wu_df.empty and self.tsi_df.empty:
            print("❌ No data available for analysis")
            return
        
        # Detect anomalies
        print("\n🔬 Detecting anomalies...")
        self.detect_weather_anomalies()
        self.detect_tsi_anomalies()
        
        # Analyze trends
        print("\n📈 Analyzing trends...")
        self.generate_trend_analysis()
        
        # Create visualizations
        print("\n📊 Creating visualizations...")
        self.create_anomaly_visualizations()
        
        # Generate report
        print("\n📝 Generating comprehensive report...")
        report = self.generate_anomaly_report()
        
        print("\n✅ Analysis complete!")
        print(f"📁 Results saved to: {self.output_dir}")
        print(f"📊 Total recommendations: {len(report['recommendations'])}")
        
        # Print summary of critical issues
        critical_issues = [r for r in report['recommendations'] if r['priority'] == 'critical']
        if critical_issues:
            print(f"\n🚨 {len(critical_issues)} CRITICAL ISSUES found:")
            for issue in critical_issues[:3]:  # Show first 3
                print(f"   • {issue['description']}")
        
        return report

def main():
    """Main execution function."""
    detector = AnomalyDetectionSystem()
    report = detector.run_complete_analysis()
    
    # Print quick summary
    if report:
        print("\n" + "="*60)
        print("📋 QUICK SUMMARY")
        print("="*60)
        print(f"Weather Underground Records: {report['analysis_summary']['wu_data_records']:,}")
        print(f"TSI Sensor Records: {report['analysis_summary']['tsi_data_records']:,}")
        print(f"Total Recommendations: {len(report['recommendations'])}")
        
        priority_counts = {}
        for rec in report['recommendations']:
            priority_counts[rec['priority']] = priority_counts.get(rec['priority'], 0) + 1
        
        for priority, count in priority_counts.items():
            print(f"{priority.capitalize()} Priority Issues: {count}")

if __name__ == "__main__":
    main()
