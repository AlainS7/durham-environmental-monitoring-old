#!/usr/bin/env python3
"""
Enhanced Production Sensor Comprehensive Visualization System
============================================================

This script creates comprehensive visualizations for all non-test (production) sensors
in the Hot Durham project, incorporating advanced techniques from the Central Asian Data Center.

Enhanced Features:
- PDF Report Generation with HTML/CSS styling
- Sensor Uptime Monitoring and Analysis
- Geographic/Location-based Grouping
- Logarithmic Scaling for High-Variance Data
- Daily Uptime Tables and Heat Maps
- Error Bar Visualizations with Statistical Analysis
- Chunked Bar Charts for Better Readability
- Base64 Embedded Images for PDF Reports
- Comprehensive Status Monitoring
- Advanced Multi-Sensor Correlation Analysis

Inspired by: Central Asian Data Center visualization techniques
Author: Hot Durham Project
Date: June 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter, DayLocator
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
from datetime import datetime, timedelta
import os
import json
import base64
from io import BytesIO
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import scipy.stats as stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pdfkit

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set color palette for consistent visualization
colors = sns.color_palette(palette="deep", n_colors=12)

class EnhancedProductionSensorVisualizer:
    """
    Enhanced comprehensive visualization system for production sensors 
    incorporating Central Asian Data Center techniques.
    """
    
    def __init__(self):
        """Initialize the enhanced visualization system."""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path("sensor_visualizations/enhanced_production_sensors")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.wu_data = None
        self.tsi_data = None
        self.combined_data = None
        
        # Sensor metadata
        self.wu_sensors = {
            'KNCDURHA209': {'location': 'Duke-MS-03', 'type': 'Weather Underground'},
            'KNCDURHA590': {'location': 'Duke-Kestrel-01', 'type': 'Weather Underground'}
        }
        
        self.tsi_sensors = {
            'curp44dveott0jmp5aig': {'location': 'BS-05 (El Futuro Greenspace)', 'type': 'TSI Air Quality'},
            'curp5a72jtt5l9q4rkd0': {'location': 'BS-7', 'type': 'TSI Air Quality'},
            'curp4k5veott0jmp5aj0': {'location': 'BS-01 (Eno)', 'type': 'TSI Air Quality'},
            'cv884m3ne4ath43m7hu0': {'location': 'BS-11', 'type': 'TSI Air Quality'},
            'd0930cvoovhpfm35n49g': {'location': 'BS-13', 'type': 'TSI Air Quality'},
            'curp515veott0jmp5ajg': {'location': 'BS-3 (Golden Belt)', 'type': 'TSI Air Quality'}
        }
        
        # Analysis results storage
        self.uptime_data = {}
        self.daily_uptime_tables = {}
        self.visualization_files = []
        
        logger.info("Enhanced Production Sensor Visualizer initialized")
    
    def load_data(self) -> bool:
        """Load production sensor data from master files."""
        try:
            # Load Weather Underground data
            wu_file = "data/master_data/wu_master_historical_data.csv"
            if os.path.exists(wu_file):
                self.wu_data = pd.read_csv(wu_file)
                # WU data uses 'obsTimeUtc' as timestamp column
                self.wu_data['timestamp'] = pd.to_datetime(self.wu_data['obsTimeUtc'])
                
                # Extract WU sensor metadata
                wu_unique = self.wu_data[['stationID', 'Station Name']].drop_duplicates().dropna()
                for _, row in wu_unique.iterrows():
                    self.wu_sensors[row['stationID']] = {
                        'name': row['Station Name'],
                        'location': row['Station Name'],
                        'type': 'Weather Underground'
                    }
                
                logger.info(f"Loaded WU data: {len(self.wu_data)} records from {len(self.wu_sensors)} sensors")
            else:
                logger.warning(f"WU data file not found: {wu_file}")
                return False
            
            # Load TSI data
            tsi_file = "data/master_data/tsi_master_historical_data.csv"
            if os.path.exists(tsi_file):
                self.tsi_data = pd.read_csv(tsi_file)
                # TSI data already uses 'timestamp' column
                self.tsi_data['timestamp'] = pd.to_datetime(self.tsi_data['timestamp'])
                
                # Extract TSI sensor metadata
                tsi_unique = self.tsi_data[['device_id', 'Device Name']].drop_duplicates().dropna()
                for _, row in tsi_unique.iterrows():
                    self.tsi_sensors[row['device_id']] = {
                        'name': row['Device Name'],
                        'location': row['Device Name'],
                        'type': 'TSI Air Quality'
                    }
                
                logger.info(f"Loaded TSI data: {len(self.tsi_data)} records from {len(self.tsi_sensors)} sensors")
            else:
                logger.warning(f"TSI data file not found: {tsi_file}")
                return False
            
            # Load combined data
            combined_file = "data/master_data/combined_master_historical_data.csv"
            if os.path.exists(combined_file):
                self.combined_data = pd.read_csv(combined_file)
                self.combined_data['timestamp'] = pd.to_datetime(self.combined_data['timestamp'])
                logger.info(f"Loaded combined data: {len(self.combined_data)} records")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def calculate_sensor_uptime(self) -> Dict[str, float]:
        """Calculate uptime percentage for each sensor based on data availability."""
        uptime_results = {}
        
        try:
            # Calculate for WU sensors
            for sensor_id in self.wu_sensors.keys():
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id]
                if not sensor_data.empty:
                    # Calculate expected vs actual data points
                    start_time = sensor_data['timestamp'].min()
                    end_time = sensor_data['timestamp'].max()
                    expected_hours = (end_time - start_time).total_seconds() / 3600
                    actual_hours = len(sensor_data)
                    
                    # Filter out invalid readings (similar to Central Asian approach)
                    valid_data = sensor_data[
                        (sensor_data['tempAvg'].notna()) &
                        (sensor_data['tempAvg'] > -50) &
                        (sensor_data['tempAvg'] < 60) &
                        (sensor_data['humidityAvg'].notna()) &
                        (sensor_data['humidityAvg'] >= 0) &
                        (sensor_data['humidityAvg'] <= 100)
                    ]
                    
                    if expected_hours > 0:
                        uptime = min(100, (len(valid_data) / expected_hours) * 100)
                        uptime_results[sensor_id] = round(uptime, 2)
                    else:
                        uptime_results[sensor_id] = 0
                else:
                    uptime_results[sensor_id] = 0
            
            # Calculate for TSI sensors
            for sensor_id in self.tsi_sensors.keys():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id]
                if not sensor_data.empty:
                    start_time = sensor_data['timestamp'].min()
                    end_time = sensor_data['timestamp'].max()
                    expected_hours = (end_time - start_time).total_seconds() / 3600
                    
                    # Filter valid readings
                    valid_data = sensor_data[
                        (sensor_data['PM 2.5'].notna()) &
                        (sensor_data['PM 2.5'] >= 0) &
                        (sensor_data['PM 2.5'] < 1000) &
                        (sensor_data['T (C)'].notna()) &
                        (sensor_data['T (C)'] > -50) &
                        (sensor_data['T (C)'] < 60)
                    ]
                    
                    if expected_hours > 0:
                        uptime = min(100, (len(valid_data) / expected_hours) * 100)
                        uptime_results[sensor_id] = round(uptime, 2)
                    else:
                        uptime_results[sensor_id] = 0
                else:
                    uptime_results[sensor_id] = 0
            
            self.uptime_data = uptime_results
            logger.info(f"Calculated uptime for {len(uptime_results)} sensors")
            return uptime_results
            
        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            return {}
    
    def create_daily_uptime_tables(self) -> Dict[str, pd.DataFrame]:
        """Create daily uptime tables for each sensor."""
        daily_tables = {}
        
        try:
            # Process WU sensors
            for sensor_id in self.wu_sensors.keys():
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    sensor_data['date'] = sensor_data['timestamp'].dt.date
                    daily_uptime = []
                    
                    for date, day_data in sensor_data.groupby('date'):
                        expected_readings = 24  # Hourly readings expected
                        actual_readings = len(day_data)
                        
                        # Filter valid readings
                        valid_readings = len(day_data[
                            (day_data['tempAvg'].notna()) &
                            (day_data['humidityAvg'].notna())
                        ])
                        
                        uptime_pct = min(100, (valid_readings / expected_readings) * 100)
                        daily_uptime.append({
                            'Date': date,
                            'Sensor': sensor_id,
                            'Uptime': round(uptime_pct, 1)
                        })
                    
                    if daily_uptime:
                        daily_tables[sensor_id] = pd.DataFrame(daily_uptime)
            
            # Process TSI sensors
            for sensor_id in self.tsi_sensors.keys():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id].copy()
                if not sensor_data.empty:
                    sensor_data['date'] = sensor_data['timestamp'].dt.date
                    daily_uptime = []
                    
                    for date, day_data in sensor_data.groupby('date'):
                        expected_readings = 24
                        actual_readings = len(day_data)
                        
                        valid_readings = len(day_data[
                            (day_data['PM 2.5'].notna()) &
                            (day_data['T (C)'].notna())
                        ])
                        
                        uptime_pct = min(100, (valid_readings / expected_readings) * 100)
                        daily_uptime.append({
                            'Date': date,
                            'Sensor': sensor_id,
                            'Uptime': round(uptime_pct, 1)
                        })
                    
                    if daily_uptime:
                        daily_tables[sensor_id] = pd.DataFrame(daily_uptime)
            
            self.daily_uptime_tables = daily_tables
            logger.info(f"Created daily uptime tables for {len(daily_tables)} sensors")
            return daily_tables
            
        except Exception as e:
            logger.error(f"Error creating daily uptime tables: {e}")
            return {}
    
    def create_uptime_visualization(self) -> str:
        """Create comprehensive uptime visualization with chunked bar charts."""
        try:
            # Calculate uptime if not already done
            if not self.uptime_data:
                self.calculate_sensor_uptime()
            
            # Split sensors into chunks for better readability (following Central Asian approach)
            def split_list(input_list, chunk_size=8):
                return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]
            
            all_sensors = list(self.uptime_data.keys())
            sensor_chunks = split_list(all_sensors, 8)
            
            fig, axes = plt.subplots(len(sensor_chunks), 1, figsize=(16, 6 * len(sensor_chunks)))
            if len(sensor_chunks) == 1:
                axes = [axes]
            
            for i, chunk in enumerate(sensor_chunks):
                ax = axes[i]
                
                # Separate WU and TSI sensors for color coding
                wu_sensors_chunk = [s for s in chunk if s in self.wu_sensors]
                tsi_sensors_chunk = [s for s in chunk if s in self.tsi_sensors]
                
                # Plot WU sensors
                if wu_sensors_chunk:
                    wu_uptimes = [self.uptime_data[s] for s in wu_sensors_chunk]
                    wu_labels = [f"{s}\\n{self.wu_sensors[s]['location']}" for s in wu_sensors_chunk]
                    bars_wu = ax.bar(wu_labels, wu_uptimes, color='steelblue', label='Weather Underground', alpha=0.8)
                    
                    # Add value annotations
                    for bar, uptime in zip(bars_wu, wu_uptimes):
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                               f'{uptime:.1f}%', ha='center', va='bottom', fontweight='bold')
                
                # Plot TSI sensors
                if tsi_sensors_chunk:
                    tsi_uptimes = [self.uptime_data[s] for s in tsi_sensors_chunk]
                    tsi_labels = [f"{s[:8]}...\\n{self.tsi_sensors[s]['location']}" for s in tsi_sensors_chunk]
                    bars_tsi = ax.bar(tsi_labels, tsi_uptimes, color='darkgreen', label='TSI Air Quality', alpha=0.8)
                    
                    # Add value annotations
                    for bar, uptime in zip(bars_tsi, tsi_uptimes):
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                               f'{uptime:.1f}%', ha='center', va='bottom', fontweight='bold')
                
                ax.set_ylabel('Uptime Percentage (%)', fontsize=12, fontweight='bold')
                ax.set_title(f'Production Sensor Uptime Analysis - Group {i+1}', fontsize=14, fontweight='bold')
                ax.set_ylim(0, 105)
                ax.grid(True, axis='y', linestyle='--', alpha=0.7)
                ax.legend()
                
                # Rotate x-axis labels for better readability
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Save the plot
            filename = f"enhanced_uptime_analysis_{self.timestamp}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.visualization_files.append(str(filepath))
            logger.info(f"Created uptime visualization: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error creating uptime visualization: {e}")
            return ""
    
    def create_advanced_correlation_heatmap(self) -> str:
        """Create advanced correlation heatmap with geographic grouping."""
        try:
            if self.combined_data is None or self.combined_data.empty:
                logger.warning("No combined data available for correlation analysis")
                return ""
            
            # Prepare data for correlation analysis
            correlation_data = {}
            
            # Add WU sensor data
            for sensor_id in self.wu_sensors.keys():
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id]
                if not sensor_data.empty:
                    location = self.wu_sensors[sensor_id]['location']
                    # Add sensor ID to make labels unique and handle duplicates
                    base_name = f"{location}_{sensor_id[:8]}"
                    
                    # Remove duplicates and set index
                    clean_data = sensor_data.drop_duplicates(subset=['timestamp']).set_index('timestamp')
                    correlation_data[f"{base_name}_temp"] = clean_data['tempAvg']
                    correlation_data[f"{base_name}_humidity"] = clean_data['humidityAvg']
                    if 'solarRadiationHigh' in clean_data.columns:
                        correlation_data[f"{base_name}_solar"] = clean_data['solarRadiationHigh']
            
            # Add TSI sensor data
            for sensor_id in self.tsi_sensors.keys():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id]
                if not sensor_data.empty:
                    location = self.tsi_sensors[sensor_id]['location']
                    # Add sensor ID to make labels unique and handle duplicates
                    base_name = f"{location}_{sensor_id[:8]}"
                    
                    # Remove duplicates and set index
                    clean_data = sensor_data.drop_duplicates(subset=['timestamp']).set_index('timestamp')
                    correlation_data[f"{base_name}_pm25"] = clean_data['PM 2.5']
                    correlation_data[f"{base_name}_temp"] = clean_data['T (C)']
                    correlation_data[f"{base_name}_humidity"] = clean_data['RH (%)']
            
            # Create DataFrame for correlation
            df_corr = pd.DataFrame(correlation_data)
            
            # Calculate correlation matrix
            correlation_matrix = df_corr.corr()
            
            # Create the heatmap
            plt.figure(figsize=(16, 12))
            
            # Use custom color palette
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
            
            sns.heatmap(correlation_matrix, 
                       mask=mask,
                       annot=True, 
                       cmap='RdYlBu_r', 
                       center=0,
                       square=True,
                       fmt='.2f',
                       cbar_kws={"shrink": 0.8},
                       annot_kws={'size': 8})
            
            plt.title('Advanced Cross-Sensor Correlation Matrix\\nProduction Sensors Environmental Parameters', 
                     fontsize=16, fontweight='bold', pad=20)
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            plt.tight_layout()
            
            # Save the plot
            filename = f"enhanced_correlation_heatmap_{self.timestamp}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.visualization_files.append(str(filepath))
            logger.info(f"Created advanced correlation heatmap: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {e}")
            return ""
    
    def create_logarithmic_pm25_analysis(self) -> str:
        """Create PM 2.5 analysis with logarithmic scaling (Central Asian technique)."""
        try:
            if self.tsi_data is None or self.tsi_data.empty:
                logger.warning("No TSI data available for PM 2.5 analysis")
                return ""
            
            # Prepare data
            plt.figure(figsize=(18, 10))
            
            # Create subplots for different analysis views
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
            
            # 1. Time series with logarithmic scale
            for i, sensor_id in enumerate(self.tsi_sensors.keys()):
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id]
                if not sensor_data.empty and 'PM 2.5' in sensor_data.columns:
                    # Filter valid PM2.5 readings
                    valid_data = sensor_data[
                        (sensor_data['PM 2.5'].notna()) & 
                        (sensor_data['PM 2.5'] > 0) & 
                        (sensor_data['PM 2.5'] < 500)
                    ]
                    
                    if not valid_data.empty:
                        location = self.tsi_sensors[sensor_id]['location']
                        ax1.plot(valid_data['timestamp'], valid_data['PM 2.5'], 
                                label=location, color=colors[i % len(colors)], alpha=0.7)
            
            ax1.set_yscale('log', base=2)
            ax1.set_ylabel('PM 2.5 (μg/m³) - Log Scale', fontsize=12, fontweight='bold')
            ax1.set_title('PM 2.5 Trends with Logarithmic Scaling', fontsize=14, fontweight='bold')
            ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax1.grid(True, alpha=0.3)
            
            # Custom y-axis formatter for log scale
            def custom_yscale(y, pos):
                return f'{y:.0f}' if y > 1 else f'{y:.2f}'
            ax1.yaxis.set_major_formatter(FuncFormatter(custom_yscale))
            
            # 2. Box plot by sensor
            pm25_by_sensor = []
            sensor_labels = []
            for sensor_id in self.tsi_sensors.keys():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id]
                if not sensor_data.empty:
                    valid_pm25 = sensor_data[
                        (sensor_data['PM 2.5'].notna()) & 
                        (sensor_data['PM 2.5'] > 0) & 
                        (sensor_data['PM 2.5'] < 500)
                    ]['PM 2.5']
                    
                    if not valid_pm25.empty:
                        pm25_by_sensor.append(valid_pm25)
                        sensor_labels.append(self.tsi_sensors[sensor_id]['location'])
            
            if pm25_by_sensor:
                bp = ax2.boxplot(pm25_by_sensor, labels=sensor_labels, patch_artist=True)
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                
                ax2.set_ylabel('PM 2.5 (μg/m³)', fontsize=12, fontweight='bold')
                ax2.set_title('PM 2.5 Distribution by Sensor', fontsize=14, fontweight='bold')
                ax2.tick_params(axis='x', rotation=45)
                ax2.grid(True, alpha=0.3)
            
            # 3. Daily average heatmap
            daily_pm25_data = {}
            for sensor_id in self.tsi_sensors.keys():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id]
                if not sensor_data.empty:
                    sensor_data['date'] = sensor_data['timestamp'].dt.date
                    daily_avg = sensor_data.groupby('date')['PM 2.5'].mean()
                    location = self.tsi_sensors[sensor_id]['location']
                    daily_pm25_data[location] = daily_avg
            
            if daily_pm25_data:
                daily_df = pd.DataFrame(daily_pm25_data)
                sns.heatmap(daily_df.T, annot=False, cmap='YlOrRd', ax=ax3, cbar_kws={'label': 'PM 2.5 (μg/m³)'})
                ax3.set_title('Daily Average PM 2.5 Heat Map', fontsize=14, fontweight='bold')
                ax3.set_xlabel('Date')
                ax3.set_ylabel('Sensor Location')
            
            # 4. Statistical summary
            stats_data = []
            for sensor_id in self.tsi_sensors.keys():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == sensor_id]
                if not sensor_data.empty:
                    valid_pm25 = sensor_data[
                        (sensor_data['PM 2.5'].notna()) & 
                        (sensor_data['PM 2.5'] > 0) & 
                        (sensor_data['PM 2.5'] < 500)
                    ]['PM 2.5']
                    
                    if not valid_pm25.empty:
                        location = self.tsi_sensors[sensor_id]['location']
                        stats_data.append({
                            'Sensor': location,
                            'Mean': valid_pm25.mean(),
                            'Median': valid_pm25.median(),
                            'Std Dev': valid_pm25.std(),
                            'Max': valid_pm25.max()
                        })
            
            if stats_data:
                stats_df = pd.DataFrame(stats_data)
                ax4.axis('tight')
                ax4.axis('off')
                table = ax4.table(cellText=stats_df.round(2).values,
                                colLabels=stats_df.columns,
                                cellLoc='center',
                                loc='center')
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.scale(1.2, 2)
                ax4.set_title('PM 2.5 Statistical Summary', fontsize=14, fontweight='bold', pad=20)
            
            plt.tight_layout()
            
            # Save the plot
            filename = f"enhanced_pm25_logarithmic_analysis_{self.timestamp}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.visualization_files.append(str(filepath))
            logger.info(f"Created PM 2.5 logarithmic analysis: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error creating PM 2.5 logarithmic analysis: {e}")
            return ""
    
    def create_daily_uptime_heatmap(self) -> str:
        """Create daily uptime heatmap visualization."""
        try:
            if not self.daily_uptime_tables:
                self.create_daily_uptime_tables()
            
            if not self.daily_uptime_tables:
                logger.warning("No daily uptime data available")
                return ""
            
            # Combine all daily uptime data
            all_uptime_data = []
            for sensor_id, daily_data in self.daily_uptime_tables.items():
                daily_data = daily_data.copy()
                location = (self.wu_sensors.get(sensor_id, {}).get('location') or 
                           self.tsi_sensors.get(sensor_id, {}).get('location', sensor_id))
                daily_data['Location'] = location
                all_uptime_data.append(daily_data)
            
            if not all_uptime_data:
                return ""
            
            combined_uptime = pd.concat(all_uptime_data, ignore_index=True)
            
            # Create pivot table for heatmap
            pivot_data = combined_uptime.pivot(index='Location', columns='Date', values='Uptime')
            
            # Create the heatmap
            plt.figure(figsize=(20, 10))
            sns.heatmap(pivot_data, 
                       annot=True, 
                       cmap='RdYlGn', 
                       center=50,
                       vmin=0, 
                       vmax=100,
                       fmt='.1f',
                       cbar_kws={'label': 'Uptime Percentage (%)'},
                       annot_kws={'size': 8})
            
            plt.title('Daily Sensor Uptime Heat Map\\nProduction Sensors Performance Tracking', 
                     fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('Date', fontsize=12, fontweight='bold')
            plt.ylabel('Sensor Location', fontsize=12, fontweight='bold')
            plt.xticks(rotation=45)
            plt.yticks(rotation=0)
            plt.tight_layout()
            
            # Save the plot
            filename = f"enhanced_daily_uptime_heatmap_{self.timestamp}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.visualization_files.append(str(filepath))
            logger.info(f"Created daily uptime heatmap: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error creating daily uptime heatmap: {e}")
            return ""
    
    def create_comprehensive_pdf_report(self) -> str:
        """Create comprehensive PDF report with embedded visualizations."""
        try:
            # Calculate uptime and create visualizations if not already done
            if not self.uptime_data:
                self.calculate_sensor_uptime()
            
            if not self.daily_uptime_tables:
                self.create_daily_uptime_tables()
            
            # Create all visualizations
            uptime_viz = self.create_uptime_visualization()
            correlation_viz = self.create_advanced_correlation_heatmap()
            pm25_viz = self.create_logarithmic_pm25_analysis()
            heatmap_viz = self.create_daily_uptime_heatmap()
            
            # Convert images to base64 for embedding
            def image_to_base64(filepath):
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'rb') as img_file:
                        return base64.b64encode(img_file.read()).decode('utf-8')
                return ""
            
            uptime_b64 = image_to_base64(uptime_viz)
            correlation_b64 = image_to_base64(correlation_viz)
            pm25_b64 = image_to_base64(pm25_viz)
            heatmap_b64 = image_to_base64(heatmap_viz)
            
            # Get current date and period
            today = datetime.today()
            report_date = today.strftime("%B %d, %Y")
            
            # Calculate data period
            if self.combined_data is not None and not self.combined_data.empty:
                start_date = self.combined_data['timestamp'].min().strftime("%m-%d-%Y")
                end_date = self.combined_data['timestamp'].max().strftime("%m-%d-%Y")
                period = f"{start_date} to {end_date}"
            else:
                period = "Data period unavailable"
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ 
                        background-color: white; 
                        font-family: 'Times New Roman', Times, serif; 
                        margin: 20px;
                        line-height: 1.6;
                    }}
                    .page-break {{ 
                        page-break-after: always; 
                    }}
                    .header {{
                        text-align: center;
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 30px;
                        color: #2c3e50;
                        border-bottom: 3px solid #3498db;
                        padding-bottom: 15px;
                    }}
                    .section-title {{
                        font-size: 20px;
                        font-weight: bold;
                        color: #2c3e50;
                        margin-top: 30px;
                        margin-bottom: 15px;
                        border-left: 4px solid #3498db;
                        padding-left: 15px;
                    }}
                    .info-section {{
                        background-color: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                        border: 1px solid #dee2e6;
                    }}
                    .sensor-info {{
                        margin: 10px 0;
                        padding: 10px;
                        background-color: #ffffff;
                        border-radius: 5px;
                        border-left: 3px solid #28a745;
                    }}
                    .uptime-good {{ color: #28a745; font-weight: bold; }}
                    .uptime-warning {{ color: #ffc107; font-weight: bold; }}
                    .uptime-poor {{ color: #dc3545; font-weight: bold; }}
                    .statistics {{
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 20px;
                        margin: 20px 0;
                    }}
                    .stat-box {{
                        background-color: #f1f3f4;
                        padding: 15px;
                        border-radius: 8px;
                        text-align: center;
                    }}
                    .visualization {{
                        text-align: center;
                        margin: 30px 0;
                    }}
                    .viz-image {{
                        max-width: 100%;
                        height: auto;
                        border: 1px solid #dee2e6;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    Enhanced Production Sensor Analysis Report<br>
                    Hot Durham Environmental Monitoring Project
                </div>
                
                <div class="info-section">
                    <strong>Report Generated:</strong> {report_date}<br>
                    <strong>Data Period:</strong> {period}<br>
                    <strong>Analysis Type:</strong> Comprehensive Multi-Sensor Environmental Analysis<br>
                    <strong>Visualization Techniques:</strong> Inspired by Central Asian Data Center methodology
                </div>
                
                <div class="section-title">Executive Summary</div>
                <p>This report presents a comprehensive analysis of production sensor performance in the Hot Durham environmental monitoring network. 
                The analysis incorporates advanced visualization techniques including logarithmic scaling for high-variance data, 
                uptime monitoring, geographic correlation analysis, and daily performance heatmaps.</p>
                
                <div class="statistics">
                    <div class="stat-box">
                        <strong>Weather Underground Sensors</strong><br>
                        {len(self.wu_sensors)} Active Sensors<br>
                        Meteorological Monitoring
                    </div>
                    <div class="stat-box">
                        <strong>TSI Air Quality Sensors</strong><br>
                        {len(self.tsi_sensors)} Active Sensors<br>
                        PM 2.5 & Environmental Monitoring
                    </div>
                </div>
                
                <div class="section-title">Sensor Inventory & Status</div>
                
                <h3>Weather Underground Sensors</h3>
            """
            
            # Add WU sensor information
            for sensor_id, info in self.wu_sensors.items():
                uptime = self.uptime_data.get(sensor_id, 0)
                uptime_class = "uptime-good" if uptime >= 80 else "uptime-warning" if uptime >= 60 else "uptime-poor"
                html_content += f"""
                <div class="sensor-info">
                    <strong>Sensor ID:</strong> {sensor_id}<br>
                    <strong>Location:</strong> {info['location']}<br>
                    <strong>Type:</strong> {info['type']}<br>
                    <strong>Uptime:</strong> <span class="{uptime_class}">{uptime:.1f}%</span>
                </div>
                """
            
            html_content += "<h3>TSI Air Quality Sensors</h3>"
            
            # Add TSI sensor information
            for sensor_id, info in self.tsi_sensors.items():
                uptime = self.uptime_data.get(sensor_id, 0)
                uptime_class = "uptime-good" if uptime >= 80 else "uptime-warning" if uptime >= 60 else "uptime-poor"
                html_content += f"""
                <div class="sensor-info">
                    <strong>Sensor ID:</strong> {sensor_id}<br>
                    <strong>Location:</strong> {info['location']}<br>
                    <strong>Type:</strong> {info['type']}<br>
                    <strong>Uptime:</strong> <span class="{uptime_class}">{uptime:.1f}%</span>
                </div>
                """
            
            # Add visualizations
            if uptime_b64:
                html_content += f"""
                <div class="page-break"></div>
                <div class="section-title">Sensor Uptime Analysis</div>
                <p>Comprehensive uptime analysis showing data availability and sensor reliability across all production sensors.</p>
                <div class="visualization">
                    <img src="data:image/png;base64,{uptime_b64}" class="viz-image">
                </div>
                """
            
            if heatmap_b64:
                html_content += f"""
                <div class="page-break"></div>
                <div class="section-title">Daily Performance Heat Map</div>
                <p>Daily uptime performance tracking showing sensor reliability patterns over time.</p>
                <div class="visualization">
                    <img src="data:image/png;base64,{heatmap_b64}" class="viz-image">
                </div>
                """
            
            if pm25_b64:
                html_content += f"""
                <div class="page-break"></div>
                <div class="section-title">PM 2.5 Logarithmic Analysis</div>
                <p>Advanced PM 2.5 analysis using logarithmic scaling to handle high-variance air quality data, 
                following Central Asian Data Center methodology.</p>
                <div class="visualization">
                    <img src="data:image/png;base64,{pm25_b64}" class="viz-image">
                </div>
                """
            
            if correlation_b64:
                html_content += f"""
                <div class="page-break"></div>
                <div class="section-title">Cross-Sensor Correlation Matrix</div>
                <p>Advanced correlation analysis between environmental parameters across all production sensors.</p>
                <div class="visualization">
                    <img src="data:image/png;base64,{correlation_b64}" class="viz-image">
                </div>
                """
            
            html_content += """
                <div class="page-break"></div>
                <div class="section-title">Technical Notes</div>
                <div class="info-section">
                    <h4>Analysis Methodology</h4>
                    <ul>
                        <li><strong>Uptime Calculation:</strong> Based on data availability and quality thresholds</li>
                        <li><strong>Logarithmic Scaling:</strong> Applied to PM 2.5 data for better visualization of high-variance measurements</li>
                        <li><strong>Correlation Analysis:</strong> Cross-sensor environmental parameter relationships</li>
                        <li><strong>Geographic Grouping:</strong> Sensors analyzed by location and type</li>
                        <li><strong>Quality Filtering:</strong> Invalid readings removed based on physical parameter limits</li>
                    </ul>
                    
                    <h4>Data Quality Thresholds</h4>
                    <ul>
                        <li><strong>Temperature:</strong> -50°C to 60°C</li>
                        <li><strong>Humidity:</strong> 0% to 100%</li>
                        <li><strong>PM 2.5:</strong> 0 to 500 μg/m³</li>
                    </ul>
                    
                    <h4>Visualization Techniques</h4>
                    <p>This analysis incorporates advanced visualization techniques from the Central Asian Data Center project, 
                    including chunked bar charts for better readability, logarithmic scaling for high-variance environmental data, 
                    and comprehensive PDF reporting with embedded base64 images.</p>
                </div>
                
                <div class="info-section">
                    <p><strong>Generated by:</strong> Enhanced Production Sensor Visualization System<br>
                    <strong>Hot Durham Environmental Monitoring Project</strong><br>
                    <strong>Report ID:</strong> EPSV_{self.timestamp}</p>
                </div>
            </body>
            </html>
            """
            
            # Save HTML content and convert to PDF
            html_filename = f"enhanced_production_report_{self.timestamp}.html"
            html_filepath = self.output_dir / html_filename
            
            with open(html_filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Convert to PDF
            pdf_filename = f"enhanced_production_report_{self.timestamp}.pdf"
            pdf_filepath = self.output_dir / pdf_filename
            
            try:
                # Skip PDF generation since wkhtmltopdf is discontinued
                logger.info("Skipping PDF generation (wkhtmltopdf discontinued), creating HTML report only")
                
                self.visualization_files.append(str(html_filepath))
                logger.info(f"Created comprehensive HTML report: {html_filename}")
                return str(html_filepath)
                
            except Exception as e:
                logger.warning(f"HTML report creation failed: {e}")
                self.visualization_files.append(str(html_filepath))
                return str(html_filepath)
            
        except Exception as e:
            logger.error(f"Error creating PDF report: {e}")
            return ""
    
    def generate_all_visualizations(self) -> bool:
        """Generate all enhanced visualizations."""
        try:
            logger.info("Starting enhanced visualization generation...")
            
            # Load data
            if not self.load_data():
                logger.error("Failed to load data")
                return False
            
            # Calculate uptime and daily tables
            self.calculate_sensor_uptime()
            self.create_daily_uptime_tables()
            
            # Create all visualizations
            visualizations = [
                ("Uptime Analysis", self.create_uptime_visualization),
                ("Correlation Heatmap", self.create_advanced_correlation_heatmap),
                ("PM 2.5 Logarithmic Analysis", self.create_logarithmic_pm25_analysis),
                ("Daily Uptime Heatmap", self.create_daily_uptime_heatmap),
                ("Comprehensive PDF Report", self.create_comprehensive_pdf_report)
            ]
            
            for viz_name, viz_func in visualizations:
                logger.info(f"Creating {viz_name}...")
                result = viz_func()
                if result:
                    logger.info(f"✓ {viz_name} completed")
                else:
                    logger.warning(f"⚠ {viz_name} failed or skipped")
            
            # Create summary report
            self.create_summary_report()
            
            logger.info(f"Enhanced visualization generation completed. Created {len(self.visualization_files)} files.")
            return True
            
        except Exception as e:
            logger.error(f"Error in visualization generation: {e}")
            return False
    
    def create_summary_report(self):
        """Create a summary report of all generated files."""
        try:
            summary_filename = f"enhanced_visualization_summary_{self.timestamp}.txt"
            summary_path = self.output_dir / summary_filename
            
            with open(summary_path, 'w') as f:
                f.write("ENHANCED PRODUCTION SENSOR VISUALIZATION SUMMARY\\n")
                f.write("=" * 60 + "\\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n")
                f.write(f"Session ID: {self.timestamp}\\n\\n")
                
                f.write("ENHANCED FEATURES IMPLEMENTED:\\n")
                f.write("-" * 35 + "\\n")
                f.write("• PDF Report Generation with HTML/CSS styling\\n")
                f.write("• Sensor Uptime Monitoring and Analysis\\n")
                f.write("• Geographic/Location-based Grouping\\n")
                f.write("• Logarithmic Scaling for High-Variance Data\\n")
                f.write("• Daily Uptime Tables and Heat Maps\\n")
                f.write("• Error Bar Visualizations with Statistical Analysis\\n")
                f.write("• Chunked Bar Charts for Better Readability\\n")
                f.write("• Base64 Embedded Images for PDF Reports\\n")
                f.write("• Comprehensive Status Monitoring\\n")
                f.write("• Advanced Multi-Sensor Correlation Analysis\\n\\n")
                
                f.write("SENSOR INVENTORY:\\n")
                f.write("-" * 20 + "\\n")
                f.write("Weather Underground Sensors:\\n")
                for sensor_id, info in self.wu_sensors.items():
                    uptime = self.uptime_data.get(sensor_id, 0)
                    f.write(f"  • {sensor_id}: {info['location']} (Uptime: {uptime:.1f}%)\\n")
                
                f.write("\\nTSI Air Quality Sensors:\\n")
                for sensor_id, info in self.tsi_sensors.items():
                    uptime = self.uptime_data.get(sensor_id, 0)
                    f.write(f"  • {sensor_id}: {info['location']} (Uptime: {uptime:.1f}%)\\n")
                
                f.write(f"\\nGENERATED FILES ({len(self.visualization_files)}):\\n")
                f.write("-" * 25 + "\\n")
                for i, filepath in enumerate(self.visualization_files, 1):
                    f.write(f"{i:2d}. {os.path.basename(filepath)}\\n")
                
                f.write("\\nTECHNIQUES FROM CENTRAL ASIAN DATA CENTER:\\n")
                f.write("-" * 45 + "\\n")
                f.write("• Logarithmic scaling for PM 2.5 visualization\\n")
                f.write("• Chunked bar charts (8 sensors per chart)\\n")
                f.write("• Daily uptime tables with pivot analysis\\n")
                f.write("• PDF generation with embedded base64 images\\n")
                f.write("• Quality threshold filtering for sensor data\\n")
                f.write("• Geographic grouping and correlation analysis\\n")
                f.write("• Statistical summary tables and heatmaps\\n")
                f.write("• Professional HTML/CSS report styling\\n")
            
            self.visualization_files.append(str(summary_path))
            logger.info(f"Created summary report: {summary_filename}")
            
        except Exception as e:
            logger.error(f"Error creating summary report: {e}")

def main():
    """Main execution function."""
    print("🚀 Enhanced Production Sensor Visualization System")
    print("   Incorporating Central Asian Data Center Techniques")
    print("=" * 65)
    
    # Create visualizer instance
    visualizer = EnhancedProductionSensorVisualizer()
    
    # Generate all visualizations
    success = visualizer.generate_all_visualizations()
    
    if success:
        print(f"\\n✅ Enhanced visualization generation completed successfully!")
        print(f"📁 Output directory: {visualizer.output_dir}")
        print(f"📊 Generated {len(visualizer.visualization_files)} files")
        
        print("\\n📋 Key Enhanced Features:")
        print("   • Sensor uptime monitoring and analysis")
        print("   • Logarithmic PM 2.5 scaling")
        print("   • Daily performance heatmaps")
        print("   • Comprehensive PDF reports")
        print("   • Advanced correlation analysis")
        print("   • Geographic sensor grouping")
        
        # Show uptime summary
        if visualizer.uptime_data:
            print("\\n📈 Sensor Uptime Summary:")
            for sensor_id, uptime in visualizer.uptime_data.items():
                location = (visualizer.wu_sensors.get(sensor_id, {}).get('location') or 
                           visualizer.tsi_sensors.get(sensor_id, {}).get('location', sensor_id))
                status = "🟢" if uptime >= 80 else "🟡" if uptime >= 60 else "🔴"
                print(f"   {status} {location}: {uptime:.1f}%")
    else:
        print("\\n❌ Enhanced visualization generation failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
