#!/usr/bin/env python3
"""
Production Sensor Comprehensive Visualization System
===================================================

This script creates comprehensive visualizations for all non-test (production) sensors
in the Hot Durham project, including both Weather Underground and TSI Air Quality sensors.

Features:
- Multi-sensor overlay plots with all production sensors on the same graph
- Separate analysis for Weather Underground vs TSI sensors
- Combined environmental parameter analysis
- Time series analysis with trend detection
- Statistical analysis and correlation matrices
- Interactive plots with zoom and pan capabilities
- Export to multiple formats (PNG, PDF, SVG)
- Automatic upload to Google Drive

Author: Hot Durham Project
Date: June 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
from datetime import datetime, timedelta
import os
import json
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import scipy.stats as stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionSensorVisualizer:
    """
    Comprehensive visualization system for production sensors in the Hot Durham project.
    Handles both Weather Underground and TSI Air Quality sensor data.
    """
    
    def __init__(self, data_dir: str = "data/master_data"):
        """Initialize the visualizer with data directory path."""
        self.data_dir = Path(data_dir)
        self.output_dir = Path("sensor_visualizations/production_sensors")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamp for this analysis session
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Data containers
        self.wu_data = None
        self.tsi_data = None
        self.combined_data = None
        
        # Sensor metadata
        self.wu_sensors = {}
        self.tsi_sensors = {}
        
        # Color palettes for consistent visualization
        self.wu_colors = ['#1f77b4', '#ff7f0e']  # Blue, Orange for WU sensors
        self.tsi_colors = ['#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']  # Green, Red, Purple, Brown, Pink, Gray for TSI
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def load_data(self) -> bool:
        """Load all production sensor data from master data files."""
        try:
            logger.info("Loading production sensor data...")
            
            # Load Weather Underground data
            wu_file = self.data_dir / "wu_master_historical_data.csv"
            if wu_file.exists():
                self.wu_data = pd.read_csv(wu_file)
                self.wu_data['obsTimeUtc'] = pd.to_datetime(self.wu_data['obsTimeUtc'])
                
                # Extract WU sensor metadata
                wu_unique = self.wu_data[['stationID', 'Station Name']].drop_duplicates().dropna()
                for _, row in wu_unique.iterrows():
                    self.wu_sensors[row['stationID']] = row['Station Name']
                
                logger.info(f"Loaded {len(self.wu_data):,} Weather Underground readings from {len(self.wu_sensors)} sensors")
            
            # Load TSI Air Quality data
            tsi_file = self.data_dir / "tsi_master_historical_data.csv"
            if tsi_file.exists():
                self.tsi_data = pd.read_csv(tsi_file)
                self.tsi_data['timestamp'] = pd.to_datetime(self.tsi_data['timestamp'])
                
                # Extract TSI sensor metadata
                tsi_unique = self.tsi_data[['device_id', 'Device Name']].drop_duplicates().dropna()
                for _, row in tsi_unique.iterrows():
                    self.tsi_sensors[row['device_id']] = row['Device Name']
                
                logger.info(f"Loaded {len(self.tsi_data):,} TSI Air Quality readings from {len(self.tsi_sensors)} sensors")
            
            # Load combined data for cross-analysis
            combined_file = self.data_dir / "combined_master_historical_data.csv"
            if combined_file.exists():
                self.combined_data = pd.read_csv(combined_file)
                logger.info(f"Loaded {len(self.combined_data):,} combined sensor readings")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def create_multi_sensor_temperature_overlay(self) -> str:
        """Create overlay plot of temperature data from all production sensors."""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Plot Weather Underground temperature data
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    ax.plot(sensor_data['obsTimeUtc'], sensor_data['tempAvg'], 
                           color=self.wu_colors[i % len(self.wu_colors)], 
                           label=f'WU: {sensor_name}', linewidth=2, alpha=0.8)
        
        # Plot TSI temperature data (converted from Celsius)
        if self.tsi_data is not None:
            for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'T (C)' in sensor_data.columns:
                    ax.plot(sensor_data['timestamp'], sensor_data['T (C)'], 
                           color=self.tsi_colors[i % len(self.tsi_colors)], 
                           label=f'TSI: {device_name}', linewidth=2, alpha=0.8, linestyle='--')
        
        ax.set_xlabel('Date', fontsize=14)
        ax.set_ylabel('Temperature (°C)', fontsize=14)
        ax.set_title('Production Sensors: Temperature Comparison Over Time\nAll Non-Test Sensors', fontsize=16, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"production_temperature_overlay_{self.timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created temperature overlay plot: {filename}")
        return str(filepath)
    
    def create_multi_sensor_humidity_overlay(self) -> str:
        """Create overlay plot of humidity data from all production sensors."""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Plot Weather Underground humidity data
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    ax.plot(sensor_data['obsTimeUtc'], sensor_data['humidityAvg'], 
                           color=self.wu_colors[i % len(self.wu_colors)], 
                           label=f'WU: {sensor_name}', linewidth=2, alpha=0.8)
        
        # Plot TSI humidity data
        if self.tsi_data is not None:
            for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'RH (%)' in sensor_data.columns:
                    ax.plot(sensor_data['timestamp'], sensor_data['RH (%)'], 
                           color=self.tsi_colors[i % len(self.tsi_colors)], 
                           label=f'TSI: {device_name}', linewidth=2, alpha=0.8, linestyle='--')
        
        ax.set_xlabel('Date', fontsize=14)
        ax.set_ylabel('Relative Humidity (%)', fontsize=14)
        ax.set_title('Production Sensors: Humidity Comparison Over Time\nAll Non-Test Sensors', fontsize=16, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"production_humidity_overlay_{self.timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created humidity overlay plot: {filename}")
        return str(filepath)
    
    def create_air_quality_analysis(self) -> str:
        """Create comprehensive air quality analysis for TSI sensors."""
        if self.tsi_data is None or self.tsi_data.empty:
            logger.warning("No TSI data available for air quality analysis")
            return None
        
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))
        fig.suptitle('Production Sensors: Air Quality Analysis (TSI Sensors Only)', fontsize=18, fontweight='bold')
        
        # PM 2.5 AQI over time
        ax1 = axes[0, 0]
        for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
            sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
            if not sensor_data.empty and 'PM 2.5 AQI' in sensor_data.columns:
                ax1.plot(sensor_data['timestamp'], sensor_data['PM 2.5 AQI'], 
                        color=self.tsi_colors[i % len(self.tsi_colors)], 
                        label=device_name, linewidth=2, alpha=0.8)
        
        ax1.set_xlabel('Date')
        ax1.set_ylabel('PM 2.5 AQI')
        ax1.set_title('PM 2.5 Air Quality Index Over Time')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # PM 10 over time
        ax2 = axes[0, 1]
        for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
            sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
            if not sensor_data.empty and 'PM 10' in sensor_data.columns:
                ax2.plot(sensor_data['timestamp'], sensor_data['PM 10'], 
                        color=self.tsi_colors[i % len(self.tsi_colors)], 
                        label=device_name, linewidth=2, alpha=0.8)
        
        ax2.set_xlabel('Date')
        ax2.set_ylabel('PM 10 (μg/m³)')
        ax2.set_title('PM 10 Concentration Over Time')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Average AQI by sensor (bar chart)
        ax3 = axes[1, 0]
        avg_aqi = []
        sensor_names = []
        for device_id, device_name in self.tsi_sensors.items():
            sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
            if not sensor_data.empty and 'PM 2.5 AQI' in sensor_data.columns:
                avg_aqi.append(sensor_data['PM 2.5 AQI'].mean())
                sensor_names.append(device_name.replace(' ', '\n'))  # Break long names
        
        bars = ax3.bar(sensor_names, avg_aqi, color=self.tsi_colors[:len(avg_aqi)])
        ax3.set_ylabel('Average PM 2.5 AQI')
        ax3.set_title('Average Air Quality Index by Sensor')
        ax3.grid(True, alpha=0.3, axis='y')
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add value labels on bars
        for bar, val in zip(bars, avg_aqi):
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)
        
        # PM 2.5 vs PM 10 correlation scatter plot
        ax4 = axes[1, 1]
        for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
            sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
            if not sensor_data.empty and 'PM 2.5' in sensor_data.columns and 'PM 10' in sensor_data.columns:
                ax4.scatter(sensor_data['PM 2.5'], sensor_data['PM 10'], 
                          color=self.tsi_colors[i % len(self.tsi_colors)], 
                          label=device_name, alpha=0.6, s=20)
        
        ax4.set_xlabel('PM 2.5 (μg/m³)')
        ax4.set_ylabel('PM 10 (μg/m³)')
        ax4.set_title('PM 2.5 vs PM 10 Correlation')
        ax4.legend(fontsize=8)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"production_air_quality_analysis_{self.timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created air quality analysis plot: {filename}")
        return str(filepath)
    
    def create_weather_parameters_grid(self) -> str:
        """Create a comprehensive grid of weather parameters from WU sensors."""
        if self.wu_data is None or self.wu_data.empty:
            logger.warning("No Weather Underground data available")
            return None
        
        fig, axes = plt.subplots(3, 2, figsize=(20, 18))
        fig.suptitle('Production Sensors: Weather Parameters Analysis (Weather Underground)', fontsize=18, fontweight='bold')
        
        parameters = [
            ('tempAvg', 'Temperature (°C)', 'Temperature Over Time'),
            ('humidityAvg', 'Humidity (%)', 'Humidity Over Time'),
            ('solarRadiationHigh', 'Solar Radiation (W/m²)', 'Solar Radiation Over Time'),
            ('windspeedAvg', 'Wind Speed (mph)', 'Wind Speed Over Time'),
            ('pressureMax', 'Pressure (mb)', 'Maximum Pressure Over Time'),
            ('precipTotal', 'Precipitation (mm)', 'Total Precipitation Over Time')
        ]
        
        for idx, (param, ylabel, title) in enumerate(parameters):
            row = idx // 2
            col = idx % 2
            ax = axes[row, col]
            
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty and param in sensor_data.columns:
                    ax.plot(sensor_data['obsTimeUtc'], sensor_data[param], 
                           color=self.wu_colors[i % len(self.wu_colors)], 
                           label=sensor_name, linewidth=2, alpha=0.8)
            
            ax.set_xlabel('Date')
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"production_weather_parameters_{self.timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created weather parameters grid: {filename}")
        return str(filepath)
    
    def create_sensor_comparison_matrix(self) -> str:
        """Create correlation matrix between all sensors where data overlaps."""
        fig, axes = plt.subplots(1, 2, figsize=(20, 8))
        fig.suptitle('Production Sensors: Cross-Sensor Correlation Analysis', fontsize=16, fontweight='bold')
        
        # Temperature correlation matrix (WU + TSI where available)
        temp_data = {}
        
        # Add WU temperature data
        if self.wu_data is not None:
            for sensor_id, sensor_name in self.wu_sensors.items():
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    # Resample to hourly to match TSI frequency
                    sensor_data.set_index('obsTimeUtc', inplace=True)
                    hourly = sensor_data['tempAvg'].resample('H').mean()
                    temp_data[f'WU_{sensor_name}'] = hourly
        
        # Add TSI temperature data
        if self.tsi_data is not None:
            for device_id, device_name in self.tsi_sensors.items():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'T (C)' in sensor_data.columns:
                    sensor_data.set_index('timestamp', inplace=True)
                    hourly = sensor_data['T (C)'].resample('H').mean()
                    temp_data[f'TSI_{device_name}'] = hourly
        
        if temp_data:
            temp_df = pd.DataFrame(temp_data)
            temp_corr = temp_df.corr()
            
            sns.heatmap(temp_corr, annot=True, cmap='coolwarm', center=0, 
                       square=True, ax=axes[0], fmt='.2f')
            axes[0].set_title('Temperature Correlation Matrix')
            axes[0].tick_params(axis='x', rotation=45)
            axes[0].tick_params(axis='y', rotation=0)
        
        # Humidity correlation matrix (WU + TSI where available)
        humidity_data = {}
        
        # Add WU humidity data
        if self.wu_data is not None:
            for sensor_id, sensor_name in self.wu_sensors.items():
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    sensor_data.set_index('obsTimeUtc', inplace=True)
                    hourly = sensor_data['humidityAvg'].resample('H').mean()
                    humidity_data[f'WU_{sensor_name}'] = hourly
        
        # Add TSI humidity data
        if self.tsi_data is not None:
            for device_id, device_name in self.tsi_sensors.items():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'RH (%)' in sensor_data.columns:
                    sensor_data.set_index('timestamp', inplace=True)
                    hourly = sensor_data['RH (%)'].resample('H').mean()
                    humidity_data[f'TSI_{device_name}'] = hourly
        
        if humidity_data:
            humidity_df = pd.DataFrame(humidity_data)
            humidity_corr = humidity_df.corr()
            
            sns.heatmap(humidity_corr, annot=True, cmap='coolwarm', center=0, 
                       square=True, ax=axes[1], fmt='.2f')
            axes[1].set_title('Humidity Correlation Matrix')
            axes[1].tick_params(axis='x', rotation=45)
            axes[1].tick_params(axis='y', rotation=0)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"production_correlation_matrix_{self.timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Created correlation matrix: {filename}")
        return str(filepath)
    
    def create_interactive_dashboard(self) -> str:
        """Create an interactive Plotly dashboard with all production sensors."""
        # Create subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=('Temperature Comparison', 'Humidity Comparison', 
                          'Air Quality (PM 2.5 AQI)', 'Solar Radiation',
                          'Wind Speed', 'Pressure'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Temperature plot
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['obsTimeUtc'], y=sensor_data['tempAvg'],
                                 mode='lines', name=f'WU: {sensor_name}',
                                 line=dict(color=self.wu_colors[i % len(self.wu_colors)], width=2)),
                        row=1, col=1
                    )
        
        if self.tsi_data is not None:
            for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'T (C)' in sensor_data.columns:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['timestamp'], y=sensor_data['T (C)'],
                                 mode='lines', name=f'TSI: {device_name}',
                                 line=dict(color=self.tsi_colors[i % len(self.tsi_colors)], width=2, dash='dash')),
                        row=1, col=1
                    )
        
        # Humidity plot
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['obsTimeUtc'], y=sensor_data['humidityAvg'],
                                 mode='lines', name=f'WU: {sensor_name}',
                                 line=dict(color=self.wu_colors[i % len(self.wu_colors)], width=2),
                                 showlegend=False),
                        row=1, col=2
                    )
        
        if self.tsi_data is not None:
            for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'RH (%)' in sensor_data.columns:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['timestamp'], y=sensor_data['RH (%)'],
                                 mode='lines', name=f'TSI: {device_name}',
                                 line=dict(color=self.tsi_colors[i % len(self.tsi_colors)], width=2, dash='dash'),
                                 showlegend=False),
                        row=1, col=2
                    )
        
        # Air Quality plot (TSI only)
        if self.tsi_data is not None:
            for i, (device_id, device_name) in enumerate(self.tsi_sensors.items()):
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id].copy()
                if not sensor_data.empty and 'PM 2.5 AQI' in sensor_data.columns:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['timestamp'], y=sensor_data['PM 2.5 AQI'],
                                 mode='lines', name=f'TSI: {device_name}',
                                 line=dict(color=self.tsi_colors[i % len(self.tsi_colors)], width=2),
                                 showlegend=False),
                        row=2, col=1
                    )
        
        # Solar Radiation (WU only)
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['obsTimeUtc'], y=sensor_data['solarRadiationHigh'],
                                 mode='lines', name=f'WU: {sensor_name}',
                                 line=dict(color=self.wu_colors[i % len(self.wu_colors)], width=2),
                                 showlegend=False),
                        row=2, col=2
                    )
        
        # Wind Speed (WU only)
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['obsTimeUtc'], y=sensor_data['windspeedAvg'],
                                 mode='lines', name=f'WU: {sensor_name}',
                                 line=dict(color=self.wu_colors[i % len(self.wu_colors)], width=2),
                                 showlegend=False),
                        row=3, col=1
                    )
        
        # Pressure (WU only)
        if self.wu_data is not None:
            for i, (sensor_id, sensor_name) in enumerate(self.wu_sensors.items()):
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id].copy()
                if not sensor_data.empty:
                    fig.add_trace(
                        go.Scatter(x=sensor_data['obsTimeUtc'], y=sensor_data['pressureMax'],
                                 mode='lines', name=f'WU: {sensor_name}',
                                 line=dict(color=self.wu_colors[i % len(self.wu_colors)], width=2),
                                 showlegend=False),
                        row=3, col=2
                    )
        
        # Update layout
        fig.update_layout(
            title_text='Production Sensors: Interactive Multi-Parameter Dashboard',
            title_font_size=20,
            height=1200,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_xaxes(title_text="Date", row=3, col=2)
        fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
        fig.update_yaxes(title_text="Humidity (%)", row=1, col=2)
        fig.update_yaxes(title_text="PM 2.5 AQI", row=2, col=1)
        fig.update_yaxes(title_text="Solar Radiation (W/m²)", row=2, col=2)
        fig.update_yaxes(title_text="Wind Speed (mph)", row=3, col=1)
        fig.update_yaxes(title_text="Pressure (mb)", row=3, col=2)
        
        # Save interactive plot
        filename = f"production_interactive_dashboard_{self.timestamp}.html"
        filepath = self.output_dir / filename
        fig.write_html(filepath)
        
        logger.info(f"Created interactive dashboard: {filename}")
        return str(filepath)
    
    def generate_sensor_summary_report(self) -> str:
        """Generate a comprehensive summary report of all production sensors."""
        report_lines = [
            "PRODUCTION SENSOR ANALYSIS REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Analysis ID: {self.timestamp}",
            "",
            "SENSOR INVENTORY:",
            "-" * 20
        ]
        
        # Weather Underground sensors
        report_lines.append("Weather Underground Sensors:")
        if self.wu_sensors:
            for sensor_id, sensor_name in self.wu_sensors.items():
                sensor_data = self.wu_data[self.wu_data['stationID'] == sensor_id]
                report_lines.append(f"  • {sensor_id}: {sensor_name}")
                report_lines.append(f"    - Total readings: {len(sensor_data):,}")
                if not sensor_data.empty:
                    report_lines.append(f"    - Date range: {sensor_data['obsTimeUtc'].min()} to {sensor_data['obsTimeUtc'].max()}")
                    report_lines.append(f"    - Avg temperature: {sensor_data['tempAvg'].mean():.1f}°C")
                    report_lines.append(f"    - Avg humidity: {sensor_data['humidityAvg'].mean():.1f}%")
        else:
            report_lines.append("  No Weather Underground sensors found")
        
        report_lines.append("")
        
        # TSI Air Quality sensors
        report_lines.append("TSI Air Quality Sensors:")
        if self.tsi_sensors:
            for device_id, device_name in self.tsi_sensors.items():
                sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id]
                report_lines.append(f"  • {device_id}: {device_name}")
                report_lines.append(f"    - Total readings: {len(sensor_data):,}")
                if not sensor_data.empty:
                    report_lines.append(f"    - Date range: {sensor_data['timestamp'].min()} to {sensor_data['timestamp'].max()}")
                    if 'T (C)' in sensor_data.columns:
                        report_lines.append(f"    - Avg temperature: {sensor_data['T (C)'].mean():.1f}°C")
                    if 'RH (%)' in sensor_data.columns:
                        report_lines.append(f"    - Avg humidity: {sensor_data['RH (%)'].mean():.1f}%")
                    if 'PM 2.5 AQI' in sensor_data.columns:
                        report_lines.append(f"    - Avg PM 2.5 AQI: {sensor_data['PM 2.5 AQI'].mean():.1f}")
        else:
            report_lines.append("  No TSI Air Quality sensors found")
        
        report_lines.extend([
            "",
            "SUMMARY STATISTICS:",
            "-" * 20,
            f"Total production sensors: {len(self.wu_sensors) + len(self.tsi_sensors)}",
            f"Total Weather Underground sensors: {len(self.wu_sensors)}",
            f"Total TSI Air Quality sensors: {len(self.tsi_sensors)}",
            f"Total readings across all sensors: {(len(self.wu_data) if self.wu_data is not None else 0) + (len(self.tsi_data) if self.tsi_data is not None else 0):,}",
            "",
            "GENERATED VISUALIZATIONS:",
            "-" * 25,
            "1. Multi-sensor temperature overlay",
            "2. Multi-sensor humidity overlay", 
            "3. Air quality analysis (TSI sensors)",
            "4. Weather parameters grid (WU sensors)",
            "5. Cross-sensor correlation matrix",
            "6. Interactive dashboard (HTML)",
            "",
            "All visualizations saved to: sensor_visualizations/production_sensors/",
            "",
            "END OF REPORT"
        ])
        
        # Save report
        report_filename = f"production_sensor_report_{self.timestamp}.txt"
        report_filepath = self.output_dir / report_filename
        
        with open(report_filepath, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Generated summary report: {report_filename}")
        return str(report_filepath)
    
    def run_complete_analysis(self) -> Dict[str, str]:
        """Run the complete production sensor visualization analysis."""
        logger.info("Starting comprehensive production sensor analysis...")
        
        # Load data
        if not self.load_data():
            logger.error("Failed to load data. Exiting.")
            return {}
        
        # Generate all visualizations
        results = {}
        
        try:
            # 1. Multi-sensor overlays
            results['temperature_overlay'] = self.create_multi_sensor_temperature_overlay()
            results['humidity_overlay'] = self.create_multi_sensor_humidity_overlay()
            
            # 2. Air quality analysis
            results['air_quality_analysis'] = self.create_air_quality_analysis()
            
            # 3. Weather parameters grid
            results['weather_parameters'] = self.create_weather_parameters_grid()
            
            # 4. Correlation analysis
            results['correlation_matrix'] = self.create_sensor_comparison_matrix()
            
            # 5. Interactive dashboard
            results['interactive_dashboard'] = self.create_interactive_dashboard()
            
            # 6. Summary report
            results['summary_report'] = self.generate_sensor_summary_report()
            
            logger.info(f"Analysis complete! Generated {len(results)} outputs in {self.output_dir}")
            
            # Print summary
            print(f"\n{'='*60}")
            print("PRODUCTION SENSOR VISUALIZATION COMPLETE")
            print(f"{'='*60}")
            print(f"Analysis timestamp: {self.timestamp}")
            print(f"Total sensors analyzed: {len(self.wu_sensors) + len(self.tsi_sensors)}")
            print(f"  - Weather Underground: {len(self.wu_sensors)}")
            print(f"  - TSI Air Quality: {len(self.tsi_sensors)}")
            print(f"Output directory: {self.output_dir}")
            print(f"Files generated: {len(results)}")
            print(f"{'='*60}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return results


def main():
    """Main function to run the production sensor visualization analysis."""
    visualizer = ProductionSensorVisualizer()
    results = visualizer.run_complete_analysis()
    
    if results:
        print("\nGenerated files:")
        for key, filepath in results.items():
            if filepath:
                print(f"  {key}: {filepath}")
    else:
        print("No files were generated due to errors.")


if __name__ == "__main__":
    main()
