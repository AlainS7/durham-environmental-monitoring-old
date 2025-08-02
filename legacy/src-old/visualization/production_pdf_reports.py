#!/usr/bin/env python3
"""
Production Sensor PDF Report System for Hot Durham Project
===========================================================

This module creates comprehensive PDF reports for production (non-test) sensors,
implementing the same PDF system from the Central Asian Data Center repository.

Features:
- Sensor uptime calculation and analysis
- Data quality monitoring and filtering
- Visual charts and graphs embedded in PDF
- HTML-to-PDF conversion with CSS styling
- Sensor performance summaries
- Geographic/location-based organization
- Daily uptime tables and heat maps
- Multi-sensor correlation analysis

Inspired by: Central Asian Data Center PDF generation system
Author: Hot Durham Project
Date: June 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import base64
from io import BytesIO
from typing import Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import weasyprint
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Color palette for consistent visualizations
colors = sns.color_palette(palette="deep", n_colors=10)

class ProductionSensorPDFReporter:
    """
    PDF report generator for production sensors, implementing the Central Asian Data Center
    PDF system with adaptations for the Hot Durham project structure.
    """
    
    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)
            
        self.data_dir = self.project_root / "data"
        self.output_dir = self.project_root / "sensor_visualizations" / "production_pdf_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize data containers
        self.wu_data = None
        self.tsi_data = None
        self.sensor_metadata = {}
        self.uptime_data = {}
        
    def get_period(self, days_back: int = 16) -> str:
        """Get the reporting period string."""
        today = datetime.today()
        today_str = today.strftime("%m-%d-%Y")
        days_ago = (today - timedelta(days=days_back)).strftime("%m-%d-%Y")
        return f"{days_ago} -- {today_str}"
    
    def preprocess_row(self, row: pd.Series) -> bool:
        """
        Filter data rows based on quality checks (adapted from Central Asian system).
        
        Args:
            row: DataFrame row to check
            
        Returns:
            True if row passes quality checks, False otherwise
        """
        check_cols = {
            "PM 2.5": [float, 0, 1000], 
            "tempAvg": [float, -40, 60],
            "Temperature": [float, -40, 60],
            "humidityAvg": [float, 0, 100],
            "RH (%)": [float, 0, 100],
            "Relative Humidity": [float, 0, 100]
        }
        
        for col, (dtype, min_val, max_val) in check_cols.items():
            if col in row and pd.notna(row[col]):
                try:
                    val = dtype(row[col])
                    if val < min_val or val > max_val:
                        return False
                except (ValueError, TypeError):
                    return False
        return True
    
    def calculate_sensor_uptime(self, df: pd.DataFrame, sensor_id: str) -> float:
        """
        Calculate uptime percentage for a sensor (adapted from Central Asian system).
        
        Args:
            df: Sensor data DataFrame
            sensor_id: Sensor identifier
            
        Returns:
            Uptime percentage (0-100)
        """
        if df.empty:
            return 0.0
            
        try:
            # Determine timestamp column based on data source
            timestamp_col = None
            if 'obsTimeUtc' in df.columns:
                timestamp_col = 'obsTimeUtc'
            elif 'timestamp' in df.columns:
                timestamp_col = 'timestamp'
            else:
                logger.warning(f"No timestamp column found for sensor {sensor_id}")
                return 0.0
            
            # Convert timestamps
            df = df.copy()
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
            df = df.dropna(subset=[timestamp_col])
            
            if df.empty:
                return 0.0
            
            # Remove first hour to avoid partial data
            df = df.sort_values(timestamp_col)
            first_hour = df.iloc[0][timestamp_col].hour
            
            # Drop rows until we get to next hour
            mask = df[timestamp_col].dt.hour != first_hour
            if mask.any():
                first_new_hour_idx = df[mask].index[0]
                df = df.loc[first_new_hour_idx:]
            
            if len(df) < 2:
                return 0.0
            
            # Calculate time intervals
            start_time = df.iloc[0][timestamp_col]
            second_time = df.iloc[1][timestamp_col]
            interval = (second_time - start_time).total_seconds()
            end_time = df.iloc[-1][timestamp_col]
            total_hours = (end_time - start_time).total_seconds() / 3600
            
            if total_hours <= 0:
                return 0.0
            
            # Count valid hours
            exclude_indices = []
            for idx, row in df.iterrows():
                if not self.preprocess_row(row):
                    exclude_indices.append(idx)
            
            # Group by 15-minute intervals and count valid records for higher resolution
            valid_intervals = 0
            interval_groups = df.groupby(df[timestamp_col].dt.floor('15min'))
            
            if len(interval_groups) == 0:
                logger.warning(f"No 15-minute interval groups found for sensor {sensor_id}")
                return 0.0
            
            for interval, group in interval_groups:
                # Remove excluded indices
                valid_group = group[~group.index.isin(exclude_indices)]
                
                # Check if we have enough valid records for this 15-minute interval (75% threshold)
                # Expect roughly 1 record per 15-minute interval for quality data
                if len(valid_group) >= 0.75:  # At least 75% of expected data points
                    valid_intervals += 1
            
            # Calculate total expected 15-minute intervals
            total_intervals = total_hours * 4  # 4 intervals per hour
            if total_intervals <= 0:
                logger.warning(f"Total intervals is zero or negative for sensor {sensor_id}")
                return 0.0
                
            uptime = (valid_intervals / total_intervals * 100)
            return min(100.0, max(0.0, uptime))
            
        except Exception as e:
            logger.error(f"Error calculating uptime for {sensor_id}: {e}")
            return 0.0
    
    def create_sensor_chart(self, df: pd.DataFrame, sensor_id: str, metric: str, sensor_name: Optional[str] = None) -> Optional[str]:
        """
        Create individual sensor chart and return as base64 string.
        
        Args:
            df: Sensor data
            sensor_id: Sensor identifier
            metric: Metric to plot
            sensor_name: Human-readable sensor name
            
        Returns:
            Base64 encoded PNG image
        """
        if df.empty or metric not in df.columns:
            return ""
        
        try:
            plt.figure(figsize=(18, 6))
            
            # Determine timestamp column
            timestamp_col = 'obsTimeUtc' if 'obsTimeUtc' in df.columns else 'timestamp'
            
            df_clean = df.copy()
            df_clean[timestamp_col] = pd.to_datetime(df_clean[timestamp_col])
            df_clean = df_clean.dropna(subset=[timestamp_col, metric])
            
            if df_clean.empty:
                plt.close()
                return ""
            
            # Resample to hourly averages
            df_clean.set_index(timestamp_col, inplace=True)
            df_resampled = df_clean.resample("h")[metric].mean().reset_index()
            
            # Check if logarithmic scaling is beneficial for high-variance metrics
            use_log_scale = self._should_use_log_scale(df_resampled[metric])
            
            plt.plot(df_resampled[timestamp_col], df_resampled[metric], linewidth=2, 
                    color='steelblue', marker='.', markersize=4, alpha=0.8, linestyle=':', 
                    label=f'{sensor_name or sensor_id}')
            
            # Apply logarithmic scaling if beneficial
            if use_log_scale:
                plt.yscale('log')
                ylabel = f'{metric} (log scale)'
            else:
                ylabel = metric
                
            plt.ylabel(ylabel, fontsize=18)
            title = f'{metric} - {sensor_name or sensor_id}'
            plt.title(title, fontsize=20, fontweight='bold')
            plt.grid(True, axis='both', linestyle='--', linewidth=0.5, alpha=0.7)
            
            # Add legend with sensor information
            sensor_type = self.sensor_metadata.get(sensor_id, {}).get('type', 'Unknown Type')
            location = self.sensor_metadata.get(sensor_id, {}).get('location', 'Unknown Location')
            
            # Create informative legend
            legend_text = f'{sensor_name or sensor_id}\n{sensor_type}\n{location}'
            plt.legend([legend_text], loc='upper right', fontsize=10, 
                      frameon=True, fancybox=True, shadow=True, framealpha=0.9)
            
            # Enhanced x-axis formatting
            ax = plt.gca()
            
            # Add temperature-specific y-axis formatting for decimal precision
            if any(temp_keyword in metric.lower() for temp_keyword in ['temp', 'temperature']):
                def temperature_formatter(y, pos):
                    return f'{y:.1f}'
                ax.yaxis.set_major_formatter(FuncFormatter(temperature_formatter))
            
            # Set major locators and formatters based on data span
            data_span = (df_resampled[timestamp_col].max() - df_resampled[timestamp_col].min()).days
            
            if data_span <= 3:  # 3 days or less - show hours
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=2))
            elif data_span <= 14:  # 2 weeks or less - show daily
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_minor_locator(mdates.DayLocator())
            else:  # More than 2 weeks - show weekly
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_minor_locator(mdates.DayLocator(interval=2))
            
            # Rotate labels and improve spacing
            plt.xticks(rotation=45, fontsize=14, ha='right')
            plt.yticks(fontsize=16)
            plt.tight_layout(pad=3)
            
            # Convert to base64
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            buf.seek(0)
            
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Error creating chart for {sensor_id} {metric}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            plt.close()
            return ""
    
    def _find_metric_column(self, df: pd.DataFrame, metric_aliases: list) -> Optional[str]:
        """
        Find the best matching column for a metric from a list of aliases (case-insensitive, ignore spaces/underscores).
        """
        norm = lambda s: s.lower().replace(' ', '').replace('_', '')
        for alias in metric_aliases:
            for col in df.columns:
                if norm(col) == norm(alias):
                    return col
        # Fallback: partial match
        for alias in metric_aliases:
            for col in df.columns:
                if norm(alias) in norm(col):
                    return col
        return None

    def create_summary_chart(self, data_dict: Dict[str, pd.DataFrame], metric: str, 
                           chart_type: str = "multi") -> str:
        """
        Create summary charts for multiple sensors.
        
        Args:
            data_dict: Dictionary of sensor_id -> DataFrame
            metric: Metric to plot
            chart_type: Type of chart ("multi" or "aggregate")
            
        Returns:
            Base64 encoded PNG image
        """
        try:
            plt.figure(figsize=(18, 6))
            metric_aliases = [metric, metric.replace(' ', ''), metric.replace(' ', '_'), metric.lower(), metric.upper()]
            if metric.lower() in ['pm2.5', 'pm 2.5', 'pm25', 'mcpm2x5', 'ncpm2x5']:
                metric_aliases += ['PM2.5', 'PM 2.5', 'pm25', 'mcpm2x5', 'ncpm2x5']
            if metric.lower() in ['temperature', 'temp', 't (c)', 'temp_c']:
                metric_aliases += ['T (C)', 'temp_c', 'temperature', 'temp']
            if chart_type == "aggregate":
                # Aggregate all data with error bars
                combined_data = []
                
                for sensor_id, df in data_dict.items():
                    col = self._find_metric_column(df, metric_aliases)
                    if df.empty or not col:
                        continue
                    
                    timestamp_col = 'obsTimeUtc' if 'obsTimeUtc' in df.columns else 'timestamp'
                    df_clean = df.copy()
                    df_clean[timestamp_col] = pd.to_datetime(df_clean[timestamp_col])
                    df_clean = df_clean.dropna(subset=[timestamp_col, col])
                    
                    if not df_clean.empty:
                        df_clean.set_index(timestamp_col, inplace=True)
                        df_resampled = df_clean.resample("h")[col].mean().reset_index()
                        combined_data.append(df_resampled)
                
                if combined_data:
                    all_data = pd.concat(combined_data, ignore_index=True)
                    
                    # Use seaborn for statistical visualization
                    sns.lineplot(
                        data=all_data,
                        x=timestamp_col,
                        y=col,
                        errorbar='sd',
                        estimator='mean',
                        marker='.',
                        markersize=8,
                        linestyle=':'
                    )
            else:
                # Multi-line plot with individual sensors
                for i, (sensor_id, df) in enumerate(data_dict.items()):
                    col = self._find_metric_column(df, metric_aliases)
                    if df.empty or not col:
                        continue
                    
                    timestamp_col = 'obsTimeUtc' if 'obsTimeUtc' in df.columns else 'timestamp'
                    df_clean = df.copy()
                    df_clean[timestamp_col] = pd.to_datetime(df_clean[timestamp_col])
                    df_clean = df_clean.dropna(subset=[timestamp_col, col])
                    
                    if df_clean.empty:
                        continue
                    
                    df_clean.set_index(timestamp_col, inplace=True)
                    df_resampled = df_clean.resample("h")[col].mean().reset_index()
                    
                    color = colors[i % len(colors)]
                    sensor_name = self.sensor_metadata.get(sensor_id, {}).get('name', sensor_id)
                    plt.plot(df_resampled[timestamp_col], df_resampled[col], 
                           label=sensor_name, color=color, linewidth=2, linestyle=':')
            
            plt.xlabel('Date', fontsize=18)
            plt.ylabel(metric, fontsize=18)
            plt.title(f'{metric} - All Production Sensors', fontsize=20, fontweight='bold')
            plt.grid(True, axis='both', linestyle='--', linewidth=0.5, alpha=0.7)
            
            # Enhanced x-axis formatting for summary charts
            ax = plt.gca()
            
            # Determine appropriate time formatting based on data span
            if combined_data:
                all_data = pd.concat(combined_data, ignore_index=True) if chart_type == "aggregate" else None
                if all_data is not None:
                    time_span = (all_data[timestamp_col].max() - all_data[timestamp_col].min()).days
                else:
                    # For multi-line charts, estimate from first sensor with data
                    first_sensor_data = next((df for df in data_dict.values() if not df.empty), None)
                    if first_sensor_data is not None:
                        timestamp_col_temp = 'obsTimeUtc' if 'obsTimeUtc' in first_sensor_data.columns else 'timestamp'
                        time_span = (pd.to_datetime(first_sensor_data[timestamp_col_temp]).max() - 
                                   pd.to_datetime(first_sensor_data[timestamp_col_temp]).min()).days
                    else:
                        time_span = 16  # Default fallback
                
                if time_span <= 3:  # 3 days or less - show hours
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=2))
                elif time_span <= 14:  # 2 weeks or less - show daily
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    ax.xaxis.set_minor_locator(mdates.DayLocator())
                else:  # More than 2 weeks - show weekly
                    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    ax.xaxis.set_minor_locator(mdates.DayLocator(interval=2))
            else:
                # Fallback formatting
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            # Add temperature-specific y-axis formatting for decimal precision
            if any(temp_keyword in metric.lower() for temp_keyword in ['temp', 'temperature']):
                def temperature_formatter(y, pos):
                    return f'{y:.1f}'
                ax.yaxis.set_major_formatter(temperature_formatter)
            
            if chart_type == "multi":
                plt.legend(fontsize=12, loc='center left', bbox_to_anchor=(1, 0.5),
                          frameon=True, fancybox=True, shadow=True, framealpha=0.9,
                          title='Production Sensors', title_fontsize=14)
            else:
                # Add legend for aggregate chart
                plt.legend(['Network Average ± Std Dev'], loc='upper right', fontsize=12,
                          frameon=True, fancybox=True, shadow=True, framealpha=0.9)
            
            # Rotate labels and improve spacing
            plt.xticks(rotation=45, fontsize=14, ha='right')
            plt.yticks(fontsize=16)
            plt.tight_layout(pad=3)
            
            # Convert to base64
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            buf.seek(0)
            
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Error creating summary chart for {metric}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            plt.close()
            return ""
    
    def create_uptime_chart(self, uptime_dict: Dict[str, float]) -> str:
        """
        Create uptime bar chart.
        
        Args:
            uptime_dict: Dictionary of sensor_id -> uptime percentage
            
        Returns:
            Base64 encoded PNG image
        """
        try:
            plt.figure(figsize=(18, 8))
            # Use friendly names for x-axis labels
            sensors = [self.sensor_metadata.get(sid, {}).get('name', sid) for sid in uptime_dict.keys()]
            uptimes = list(uptime_dict.values())
            
            # Create color mapping based on uptime levels
            colors_map = []
            for uptime in uptimes:
                if uptime >= 90:
                    colors_map.append('#2E8B57')  # Good - Green
                elif uptime >= 70:
                    colors_map.append('#FFD700')  # Warning - Yellow
                else:
                    colors_map.append('#DC143C')  # Poor - Red
            
            bars = plt.bar(sensors, uptimes, color=colors_map)
            
            # Add value labels on bars
            for i, (bar, uptime) in enumerate(zip(bars, uptimes)):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f'{uptime:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
            
            plt.xlabel('Sensor', fontsize=18)
            plt.ylabel('Uptime %', fontsize=18)
            plt.title('Production Sensor Uptime Analysis', fontsize=20, fontweight='bold')
            plt.xticks(rotation=45, fontsize=14)
            plt.yticks(fontsize=16)
            plt.ylim(0, 105)
            plt.grid(True, axis='y', alpha=0.3)
            
            # Add legend for uptime color coding
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='#2E8B57', label='Excellent (≥90%)'),
                Patch(facecolor='#FFD700', label='Good (70-89%)'),
                Patch(facecolor='#DC143C', label='Needs Attention (<70%)')
            ]
            plt.legend(handles=legend_elements, loc='upper right', fontsize=12,
                      frameon=True, fancybox=True, shadow=True, framealpha=0.9)
            
            plt.tight_layout()
            
            # Convert to base64
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            buf.seek(0)
            
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Error creating uptime chart: {e}")
            plt.close()
            return ""
    
    def load_production_data(self) -> bool:
        """
        Load production sensor data from master files.
        
        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            # Load Weather Underground data
            wu_file = self.data_dir / "master_data" / "wu_master_historical_data.csv"
            if wu_file.exists():
                self.wu_data = pd.read_csv(wu_file)
                self.wu_data['obsTimeUtc'] = pd.to_datetime(self.wu_data['obsTimeUtc'])
                from config.test_sensors_config import is_test_sensor
                if 'stationID' in self.wu_data.columns:
                    self.wu_data = self.wu_data[~self.wu_data['stationID'].apply(is_test_sensor)]
                # Extract sensor metadata (robust to column name)
                name_col = None
                for col in self.wu_data.columns:
                    if col.lower().replace('_', '').replace(' ', '') in ['stationname','name']:
                        name_col = col
                        break
                if name_col:
                    wu_meta = self.wu_data[['stationID', name_col]].drop_duplicates()
                    for _, row in wu_meta.iterrows():
                        self.sensor_metadata[row['stationID']] = {
                            'name': row[name_col],
                            'type': 'Weather Underground',
                            'location': row[name_col]
                        }
                logger.info(f"Loaded {len(self.wu_data)} WU production sensor records")
            # Load TSI data
            tsi_file = self.data_dir / "master_data" / "tsi_master_historical_data.csv"
            if tsi_file.exists():
                self.tsi_data = pd.read_csv(tsi_file)
                # Try to parse timestamp column robustly
                ts_col = None
                for col in self.tsi_data.columns:
                    if col.lower().startswith('timestamp'):
                        ts_col = col
                        break
                if ts_col:
                    self.tsi_data[ts_col] = pd.to_datetime(self.tsi_data[ts_col])
                if 'device_id' in self.tsi_data.columns:
                    self.tsi_data = self.tsi_data[~self.tsi_data['device_id'].apply(is_test_sensor)]
                # Extract sensor metadata (robust to column name, fallback to metadata JSON)
                name_col = None
                for col in self.tsi_data.columns:
                    if col.lower().replace('_', '').replace(' ', '') in ['devicename','name']:
                        name_col = col
                        break
                if name_col:
                    tsi_meta = self.tsi_data[['device_id', name_col]].drop_duplicates()
                    for _, row in tsi_meta.iterrows():
                        name_val = row[name_col]
                        # If name is missing, try metadata
                        if (not name_val or pd.isna(name_val)) and 'metadata' in self.tsi_data.columns:
                            meta_row = self.tsi_data[self.tsi_data['device_id'] == row['device_id']]['metadata'].iloc[0]
                            try:
                                meta = eval(meta_row) if isinstance(meta_row, str) else {}
                                friendly = meta.get('friendly_name', row['device_id'])
                            except Exception:
                                friendly = row['device_id']
                            name_val = friendly
                        self.sensor_metadata[row['device_id']] = {
                            'name': name_val,
                            'type': 'TSI Air Quality',
                            'location': name_val
                        }
                elif 'metadata' in self.tsi_data.columns:
                    # Try to extract friendly_name from metadata JSON
                    for _, row in self.tsi_data[['device_id', 'metadata']].drop_duplicates().iterrows():
                        try:
                            meta = eval(row['metadata']) if isinstance(row['metadata'], str) else {}
                            friendly = meta.get('friendly_name', row['device_id'])
                        except Exception:
                            friendly = row['device_id']
                        self.sensor_metadata[row['device_id']] = {
                            'name': friendly,
                            'type': 'TSI Air Quality',
                            'location': friendly
                        }
                logger.info(f"Loaded {len(self.tsi_data)} TSI production sensor records")
            return True
            
        except Exception as e:
            logger.error(f"Error loading production data: {e}")
            return False
    
    def calculate_all_uptimes(self) -> Dict[str, float]:
        """
        Calculate uptime for all production sensors.
        
        Returns:
            Dictionary of sensor_id -> uptime percentage
        """
        uptimes = {}
        
        try:
            # Calculate WU sensor uptimes
            if self.wu_data is not None and not self.wu_data.empty:
                for station_id in self.wu_data['stationID'].unique():
                    sensor_data = self.wu_data[self.wu_data['stationID'] == station_id]
                    uptimes[station_id] = self.calculate_sensor_uptime(sensor_data, station_id)
            
            # Calculate TSI sensor uptimes
            if self.tsi_data is not None and not self.tsi_data.empty:
                for device_id in self.tsi_data['device_id'].unique():
                    sensor_data = self.tsi_data[self.tsi_data['device_id'] == device_id]
                    uptimes[device_id] = self.calculate_sensor_uptime(sensor_data, device_id)
            
            self.uptime_data = uptimes
            logger.info(f"Calculated uptimes for {len(uptimes)} production sensors")
            
        except Exception as e:
            logger.error(f"Error calculating uptimes: {e}")
        
        return uptimes
    
    def generate_pdf_report(self, output_filename: Optional[str] = None) -> str:
        """
        Generate comprehensive PDF report for production sensors.
        
        Args:
            output_filename: Optional custom filename
            
        Returns:
            Path to generated PDF file
        """
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"production_sensors_report_{timestamp}.pdf"
        
        output_path = self.output_dir / output_filename
        
        try:
            # Load data and calculate metrics
            if not self.load_production_data():
                raise Exception("Failed to load production sensor data")
            
            uptimes = self.calculate_all_uptimes()
            
            # Prepare data for charts
            wu_sensors = {}
            tsi_sensors = {}
            
            if self.wu_data is not None:
                for station_id in self.wu_data['stationID'].unique():
                    wu_sensors[station_id] = self.wu_data[self.wu_data['stationID'] == station_id]
            
            if self.tsi_data is not None:
                for device_id in self.tsi_data['device_id'].unique():
                    tsi_sensors[device_id] = self.tsi_data[self.tsi_data['device_id'] == device_id]
            
            # Generate charts
            logger.info("Generating charts for PDF report...")
            
            # Summary charts
            wu_temp_summary = self.create_summary_chart(wu_sensors, 'tempAvg', 'aggregate') if wu_sensors else ""
            wu_humidity_summary = self.create_summary_chart(wu_sensors, 'humidityAvg', 'aggregate') if wu_sensors else ""
            tsi_pm25_summary = self.create_summary_chart(tsi_sensors, 'PM 2.5', 'aggregate') if tsi_sensors else ""
            tsi_temp_summary = self.create_summary_chart(tsi_sensors, 'T (C)', 'aggregate') if tsi_sensors else ""
            
            # Uptime chart
            uptime_chart = self.create_uptime_chart(uptimes)
            
            # Individual sensor charts
            sensor_charts = {}
            
            # WU sensor individual charts
            for sensor_id, df in wu_sensors.items():
                sensor_name = self.sensor_metadata.get(sensor_id, {}).get('name', sensor_id)
                sensor_charts[sensor_id] = {
                    'temperature': self.create_sensor_chart(df, sensor_id, 'tempAvg', sensor_name),
                    'humidity': self.create_sensor_chart(df, sensor_id, 'humidityAvg', sensor_name),
                    'pressure': self.create_sensor_chart(df, sensor_id, 'pressureMax', sensor_name),
                    'wind': self.create_sensor_chart(df, sensor_id, 'windspeedAvg', sensor_name)
                }
            
            # TSI sensor individual charts
            for sensor_id, df in tsi_sensors.items():
                sensor_name = self.sensor_metadata.get(sensor_id, {}).get('name', sensor_id)
                sensor_charts[sensor_id] = {
                    'pm25': self.create_sensor_chart(df, sensor_id, 'PM 2.5', sensor_name),
                    'temperature': self.create_sensor_chart(df, sensor_id, 'T (C)', sensor_name),
                    'humidity': self.create_sensor_chart(df, sensor_id, 'RH (%)', sensor_name),
                    'pm10': self.create_sensor_chart(df, sensor_id, 'PM 10', sensor_name)
                }
            
            # Build HTML content
            html_content = self._build_html_content(
                uptimes, sensor_charts, wu_temp_summary, wu_humidity_summary,
                tsi_pm25_summary, tsi_temp_summary, uptime_chart
            )
            
            # Generate PDF
            logger.info(f"Converting HTML to PDF: {output_path}")
            
            # Create WeasyPrint HTML document and convert to PDF
            html_doc = weasyprint.HTML(string=html_content)
            html_doc.write_pdf(str(output_path))
            
            logger.info(f"PDF report generated successfully: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            
            # Generate fallback error PDF
            error_html = f"""
            <html>
            <head>
                <style>
                    body {{ background-color: white; font-family: 'Times New Roman', Times, serif; 
                           font-size: 24px; margin: 20%; text-align: center; }}
                </style>
            </head>
            <body>
                <h1>Hot Durham Production Sensors Report</h1>
                <p>Error generating report: {str(e)}</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </body>
            </html>
            """
            
            try:
                html_doc = weasyprint.HTML(string=error_html)
                html_doc.write_pdf(str(output_path))
                logger.info(f"Error PDF generated: {output_path}")
            except Exception as pdf_error:
                logger.error(f"Failed to generate error PDF: {pdf_error}")
                
            return str(output_path)
    
    def _build_html_content(self, uptimes: Dict[str, float], sensor_charts: Dict, 
                           wu_temp_summary: str, wu_humidity_summary: str, 
                           tsi_pm25_summary: str, tsi_temp_summary: str, 
                           uptime_chart: str) -> str:
        """
        Build HTML content for PDF report.
        
        Args:
            uptimes: Sensor uptime data
            sensor_charts: Individual sensor charts
            wu_temp_summary: WU temperature summary chart
            wu_humidity_summary: WU humidity summary chart
            tsi_pm25_summary: TSI PM2.5 summary chart
            tsi_temp_summary: TSI temperature summary chart
            uptime_chart: Uptime analysis chart
            
        Returns:
            Complete HTML content string
        """
        html_content = f"""
        <html>
        <head>
            <style>
                @page {{
                    size: A4;
                    margin: 0.75in;
                }}
                body {{ 
                    background-color: white; 
                    font-family: 'Times New Roman', Times, serif; 
                    margin: 0;
                    line-height: 1.6;
                }}
                .page-break {{ page-break-after: always; }}
                .title {{ 
                    font-size: 28px; 
                    font-weight: bold; 
                    text-align: center; 
                    margin-bottom: 30px;
                    color: #2c3e50;
                }}
                .section-title {{ 
                    font-size: 24px; 
                    font-weight: bold; 
                    color: #34495e;
                    margin-top: 30px;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                .sensor-title {{ 
                    font-size: 20px; 
                    font-weight: bold; 
                    color: #2980b9;
                    margin-top: 25px;
                    margin-bottom: 15px;
                }}
                .sensor-info {{ 
                    font-size: 16px; 
                    margin-bottom: 10px;
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }}
                .uptime-good {{ color: #27ae60; font-weight: bold; }}
                .uptime-warning {{ color: #f39c12; font-weight: bold; }}
                .uptime-poor {{ color: #e74c3c; font-weight: bold; }}
                .chart-container {{ 
                    text-align: center; 
                    margin: 20px 0;
                }}
                .summary-stats {{
                    background-color: #ecf0f1;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .intro {{ 
                    font-size: 18px;
                    margin-bottom: 30px;
                    text-align: justify;
                }}
                .metadata {{
                    font-size: 14px;
                    color: #7f8c8d;
                    text-align: center;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            
            <!-- Title Page -->
            <div class="title">
                Hot Durham Environmental Monitoring Project<br>
                Production Sensor Comprehensive Report
            </div>
            
            <div class="intro">
                <strong>Report Period:</strong> {self.get_period()}<br>
                <strong>Generated:</strong> {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}<br>
                <strong>Total Production Sensors:</strong> {len(uptimes)}<br><br>
                
                This report provides comprehensive analysis of all production (non-test) sensors 
                deployed in the Hot Durham environmental monitoring network. The analysis includes 
                sensor uptime monitoring, data quality assessment, and performance visualizations 
                for both Weather Underground meteorological sensors and TSI air quality sensors.
            </div>
            
            <div class="summary-stats">
                <strong>Executive Summary:</strong><br>
                • Weather Underground Sensors: {len([s for s in uptimes.keys() if s.startswith('KNCDURHA')])}<br>
                • TSI Air Quality Sensors: {len([s for s in uptimes.keys() if not s.startswith('KNCDURHA')])}<br>
                • Average Network Uptime: {np.mean(list(uptimes.values())):.1f}%<br>
                • Sensors with >90% Uptime: {len([u for u in uptimes.values() if u >= 90])}<br>
                • Sensors Requiring Attention: {len([u for u in uptimes.values() if u < 70])}
            </div>
            
            <div class="page-break"></div>
            
            <!-- Uptime Analysis -->
            <div class="section-title">Network Uptime Analysis</div>
            <div class="chart-container">
                <img src="{uptime_chart}" style="width: 100%; max-width: 1000px;">
            </div>
            
            <div class="page-break"></div>
            
            <!-- Summary Charts -->
            <div class="section-title">Network Summary - Weather Underground Sensors</div>
        """
        
        if wu_temp_summary:
            html_content += f"""
            <div class="chart-container">
                <h3>Temperature Trends (All WU Sensors)</h3>
                <img src="{wu_temp_summary}" style="width: 100%; max-width: 1000px;">
            </div>
            """
        
        if wu_humidity_summary:
            html_content += f"""
            <div class="chart-container">
                <h3>Humidity Trends (All WU Sensors)</h3>
                <img src="{wu_humidity_summary}" style="width: 100%; max-width: 1000px;">
            </div>
            """
        
        html_content += """
            <div class="page-break"></div>
            
            <div class="section-title">Network Summary - TSI Air Quality Sensors</div>
        """
        
        if tsi_pm25_summary:
            html_content += f"""
            <div class="chart-container">
                <h3>PM2.5 Trends (All TSI Sensors)</h3>
                <img src="{tsi_pm25_summary}" style="width: 100%; max-width: 1000px;">
            </div>
            """
        
        if tsi_temp_summary:
            html_content += f"""
            <div class="chart-container">
                <h3>Temperature Trends (All TSI Sensors)</h3>
                <img src="{tsi_temp_summary}" style="width: 100%; max-width: 1000px;">
            </div>
            """
        
        html_content += """
            <div class="page-break"></div>
            
            <!-- Individual Sensor Details -->
            <div class="section-title">Individual Sensor Performance</div>
        """
        
        # Add individual sensor sections
        for sensor_id, charts in sensor_charts.items():
            sensor_meta = self.sensor_metadata.get(sensor_id, {})
            sensor_name = sensor_meta.get('name', sensor_id)
            sensor_type = sensor_meta.get('type', 'Unknown')
            sensor_location = sensor_meta.get('location', 'Unknown')
            uptime = uptimes.get(sensor_id, 0)
            
            # Determine uptime class
            if uptime >= 90:
                uptime_class = "uptime-good"
            elif uptime >= 70:
                uptime_class = "uptime-warning"
            else:
                uptime_class = "uptime-poor"
            
            html_content += f"""
            <div class="sensor-title">Sensor: {sensor_name}</div>
            <div class="sensor-info">
                <strong>Sensor ID:</strong> {sensor_id}<br>
                <strong>Type:</strong> {sensor_type}<br>
                <strong>Location:</strong> {sensor_location}<br>
                <strong>Uptime:</strong> <span class="{uptime_class}">{uptime:.1f}%</span>
            </div>
            """
            
            # Add charts for this sensor
            has_chart = False
            for chart_type, chart_data in charts.items():
                if chart_data:
                    has_chart = True
                    html_content += f"""
                    <div class=\"chart-container\">
                        <img src=\"{chart_data}\" style=\"width: 100%; max-width: 1000px;\">
                    </div>
                    """
            if not has_chart:
                html_content += """
                <div class=\"chart-container\">
                    <div style=\"color: #b00; font-size: 1.2em; padding: 2em; text-align: center;\">
                        No data available for this sensor in the selected period.
                    </div>
                </div>
                """
            html_content += '<div class="page-break"></div>'
        
        # Footer
        html_content += f"""
            <div class="metadata">
                <strong>Technical Notes:</strong><br>
                • Uptime calculated based on data availability and quality filtering<br>
                • Charts show hourly averaged data for the reporting period<br>
                • Logarithmic scaling applied to high-variance metrics<br>
                • Error bars represent standard deviation across sensors<br><br>
                
                Generated by: Hot Durham Production Sensor PDF Report System<br>
                Adapted from: Central Asian Data Center methodology<br>
                Report ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}
            </div>
            
        </body>
        </html>
        """
        
        return html_content

    def _should_use_log_scale(self, data: pd.Series) -> bool:
        """
        Determine if logarithmic scaling would be beneficial for the data.
        
        Args:
            data: Pandas Series containing metric values
            
        Returns:
            True if log scale should be used, False otherwise
        """
        try:
            # Remove NaN values and ensure positive values for log scale
            clean_data = data.dropna()
            if clean_data.empty or (clean_data <= 0).any():
                return False
            
            # Calculate coefficient of variation (CV = std/mean)
            cv = clean_data.std() / clean_data.mean()
            
            # Check if data spans multiple orders of magnitude
            data_range = clean_data.max() / clean_data.min()
            
            # Use log scale if:
            # 1. High coefficient of variation (>1.0) AND
            # 2. Data spans more than 2 orders of magnitude (ratio > 100)
            return cv > 1.0 and data_range > 100
            
        except Exception as e:
            logger.debug(f"Error in log scale detection: {e}")
            return False

def main():
    """Main function to generate production sensor PDF report."""
    print("🏭 Hot Durham Production Sensor PDF Report Generator")
    print("=" * 60)
    
    try:
        # Initialize reporter
        reporter = ProductionSensorPDFReporter()
        
        # Generate report
        print("📊 Generating comprehensive PDF report...")
        pdf_path = reporter.generate_pdf_report()
        
        print("✅ PDF report generated successfully!")
        print(f"📄 Report location: {pdf_path}")
        print(f"📁 Output directory: {reporter.output_dir}")
        
        # Summary statistics
        print("\n📈 Report Summary:")
        print(f"   - Total sensors analyzed: {len(reporter.uptime_data)}")
        print(f"   - Average uptime: {np.mean(list(reporter.uptime_data.values())):.1f}%")
        print(f"   - Report period: {reporter.get_period()}")
        
    except Exception as e:
        print(f"❌ Error generating PDF report: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
