#!/usr/bin/env python3
"""
Enhanced Multi-Category Visualization Script for Hot Durham
Creates combined plots with multiple data categories on the same chart
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'scripts'))

from src.core.data_manager import DataManager

def create_combined_visualizations(days_back=30):
    """Create visualizations combining multiple data categories"""
    
    # Initialize data manager
    dm = DataManager(project_root)
    
    # Load recent data
    print("📊 Loading recent data for visualization...")
    wu_data = dm.load_recent_data('wu', days=days_back)
    tsi_data = dm.load_recent_data('tsi', days=days_back)
    
    if wu_data.empty and tsi_data.empty:
        print("⚠️ No recent data found for visualization")
        return
    
    # Create output directory
    charts_dir = project_root / "reports" / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # 1. Temperature Comparison: WU vs TSI
    if not wu_data.empty and not tsi_data.empty:
        print("🌡️ Creating temperature comparison chart...")
        create_temperature_comparison(wu_data, tsi_data, charts_dir)
    
    # 2. Air Quality vs Weather Correlation
    if not wu_data.empty and not tsi_data.empty:
        print("🌬️ Creating air quality vs weather correlation...")
        create_air_quality_weather_correlation(wu_data, tsi_data, charts_dir)
    
    # 3. Multi-metric Time Series
    if not wu_data.empty:
        print("📈 Creating multi-metric weather time series...")
        create_multi_metric_timeseries(wu_data, tsi_data, charts_dir)
    
    # 4. Device-Specific Multi-Category Charts
    if not tsi_data.empty:
        print("🔬 Creating device-specific multi-category charts...")
        create_device_multi_category(tsi_data, charts_dir)
    
    print(f"✅ Charts saved to: {charts_dir}")

def create_temperature_comparison(wu_data, tsi_data, output_dir):
    """Compare temperature readings between WU and TSI sensors"""
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Process WU temperature data
    if 'date' in wu_data.columns and 'temperature' in wu_data.columns:
        wu_data['datetime'] = pd.to_datetime(wu_data['date'])
        wu_temp = wu_data.groupby(['datetime', 'station_name'])['temperature'].mean().reset_index()
        
        for station in wu_temp['station_name'].unique():
            station_data = wu_temp[wu_temp['station_name'] == station]
            ax.plot(station_data['datetime'], station_data['temperature'], 
                   label=f'WU-{station}', linewidth=2, alpha=0.8)
    
    # Process TSI temperature data
    if 'date' in tsi_data.columns and 'temperature' in tsi_data.columns:
        tsi_data['datetime'] = pd.to_datetime(tsi_data['date'])
        tsi_temp = tsi_data.groupby(['datetime', 'device'])['temperature'].mean().reset_index()
        
        for device in tsi_temp['device'].unique():
            device_data = tsi_temp[tsi_temp['device'] == device]
            ax.plot(device_data['datetime'], device_data['temperature'], 
                   label=f'TSI-{device}', linewidth=2, alpha=0.8, linestyle='--')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Temperature (°F)', fontsize=12)
    ax.set_title('Temperature Comparison: Weather Underground vs TSI Sensors', fontsize=14, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / f'temperature_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
                dpi=300, bbox_inches='tight')
    plt.close()

def create_air_quality_weather_correlation(wu_data, tsi_data, output_dir):
    """Create scatter plots showing air quality vs weather metrics"""
    
    # Prepare data
    if 'date' in wu_data.columns and 'date' in tsi_data.columns:
        wu_data['date'] = pd.to_datetime(wu_data['date']).dt.date
        tsi_data['date'] = pd.to_datetime(tsi_data['date']).dt.date
        
        # Aggregate by date
        wu_daily = wu_data.groupby('date').agg({
            'temperature': 'mean',
            'humidity': 'mean',
            'wind_speed': 'mean',
            'pressure': 'mean'
        }).reset_index()
        
        tsi_daily = tsi_data.groupby('date').agg({
            'pm2_5': 'mean',
            'temperature': 'mean',
            'humidity': 'mean'
        }).reset_index()
        
        # Merge datasets
        combined = pd.merge(wu_daily, tsi_daily, on='date', suffixes=('_wu', '_tsi'), how='inner')
        
        if not combined.empty:
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            
            # PM2.5 vs Temperature
            axes[0,0].scatter(combined['temperature_wu'], combined['pm2_5'], alpha=0.7, c='red')
            axes[0,0].set_xlabel('Temperature (°F) - WU')
            axes[0,0].set_ylabel('PM2.5 (μg/m³) - TSI')
            axes[0,0].set_title('Air Quality vs Temperature')
            axes[0,0].grid(True, alpha=0.3)
            
            # PM2.5 vs Humidity
            axes[0,1].scatter(combined['humidity_wu'], combined['pm2_5'], alpha=0.7, c='blue')
            axes[0,1].set_xlabel('Humidity (%) - WU')
            axes[0,1].set_ylabel('PM2.5 (μg/m³) - TSI')
            axes[0,1].set_title('Air Quality vs Humidity')
            axes[0,1].grid(True, alpha=0.3)
            
            # PM2.5 vs Wind Speed
            if 'wind_speed' in combined.columns:
                axes[1,0].scatter(combined['wind_speed'], combined['pm2_5'], alpha=0.7, c='green')
                axes[1,0].set_xlabel('Wind Speed (mph) - WU')
                axes[1,0].set_ylabel('PM2.5 (μg/m³) - TSI')
                axes[1,0].set_title('Air Quality vs Wind Speed')
                axes[1,0].grid(True, alpha=0.3)
            
            # Temperature Correlation WU vs TSI
            axes[1,1].scatter(combined['temperature_wu'], combined['temperature_tsi'], alpha=0.7, c='orange')
            axes[1,1].set_xlabel('Temperature (°F) - WU')
            axes[1,1].set_ylabel('Temperature (°F) - TSI')
            axes[1,1].set_title('Temperature: WU vs TSI Correlation')
            axes[1,1].grid(True, alpha=0.3)
            
            # Add correlation line
            if len(combined) > 1:
                z = np.polyfit(combined['temperature_wu'].dropna(), combined['temperature_tsi'].dropna(), 1)
                p = np.poly1d(z)
                axes[1,1].plot(combined['temperature_wu'], p(combined['temperature_wu']), "r--", alpha=0.8)
            
            plt.suptitle('Air Quality vs Weather Correlations', fontsize=16, fontweight='bold')
            plt.tight_layout()
            plt.savefig(output_dir / f'air_quality_weather_correlation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()

def create_multi_metric_timeseries(wu_data, tsi_data, output_dir):
    """Create multi-axis time series with different metrics"""
    
    fig, ax1 = plt.subplots(figsize=(15, 10))
    
    # Process WU data
    if not wu_data.empty and 'date' in wu_data.columns:
        wu_data['datetime'] = pd.to_datetime(wu_data['date'])
        wu_daily = wu_data.groupby('datetime').agg({
            'temperature': 'mean',
            'humidity': 'mean',
            'pressure': 'mean'
        }).reset_index()
        
        # Primary axis: Temperature
        color = 'tab:red'
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Temperature (°F)', color=color, fontsize=12)
        line1 = ax1.plot(wu_daily['datetime'], wu_daily['temperature'], color=color, linewidth=2, label='Temperature')
        ax1.tick_params(axis='y', labelcolor=color)
        
        # Secondary axis: Humidity
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Humidity (%)', color=color, fontsize=12)
        line2 = ax2.plot(wu_daily['datetime'], wu_daily['humidity'], color=color, linewidth=2, label='Humidity')
        ax2.tick_params(axis='y', labelcolor=color)
        
        # Third axis: PM2.5 if TSI data available
        if not tsi_data.empty and 'date' in tsi_data.columns and 'pm2_5' in tsi_data.columns:
            tsi_data['datetime'] = pd.to_datetime(tsi_data['date'])
            tsi_daily = tsi_data.groupby('datetime')['pm2_5'].mean().reset_index()
            
            ax3 = ax1.twinx()
            ax3.spines['right'].set_position(('outward', 60))
            color = 'tab:green'
            ax3.set_ylabel('PM2.5 (μg/m³)', color=color, fontsize=12)
            line3 = ax3.plot(tsi_daily['datetime'], tsi_daily['pm2_5'], color=color, linewidth=2, label='PM2.5')
            ax3.tick_params(axis='y', labelcolor=color)
        
        # Combine legends
        lines = line1 + line2
        if not tsi_data.empty and 'pm2_5' in tsi_data.columns:
            lines += line3
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')
        
        ax1.grid(True, alpha=0.3)
        plt.title('Multi-Metric Environmental Monitoring', fontsize=14, fontweight='bold', pad=20)
        plt.xticks(rotation=45)
        
    plt.tight_layout()
    plt.savefig(output_dir / f'multi_metric_timeseries_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
               dpi=300, bbox_inches='tight')
    plt.close()

def create_device_multi_category(tsi_data, output_dir):
    """Create device-specific charts with multiple categories"""
    
    if 'device' not in tsi_data.columns:
        return
    
    devices = tsi_data['device'].unique()
    
    for device in devices:
        device_data = tsi_data[tsi_data['device'] == device].copy()
        
        if device_data.empty:
            continue
            
        device_data['datetime'] = pd.to_datetime(device_data['date'])
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # PM2.5 over time
        if 'pm2_5' in device_data.columns:
            axes[0,0].plot(device_data['datetime'], device_data['pm2_5'], color='red', linewidth=2)
            axes[0,0].set_title(f'{device} - PM2.5 Levels')
            axes[0,0].set_ylabel('PM2.5 (μg/m³)')
            axes[0,0].grid(True, alpha=0.3)
            
        # Temperature over time
        if 'temperature' in device_data.columns:
            axes[0,1].plot(device_data['datetime'], device_data['temperature'], color='orange', linewidth=2)
            axes[0,1].set_title(f'{device} - Temperature')
            axes[0,1].set_ylabel('Temperature (°F)')
            axes[0,1].grid(True, alpha=0.3)
            
        # Humidity over time
        if 'humidity' in device_data.columns:
            axes[1,0].plot(device_data['datetime'], device_data['humidity'], color='blue', linewidth=2)
            axes[1,0].set_title(f'{device} - Humidity')
            axes[1,0].set_ylabel('Humidity (%)')
            axes[1,0].set_xlabel('Date')
            axes[1,0].grid(True, alpha=0.3)
            
        # Combined metrics (normalized)
        metrics_to_plot = []
        if 'pm2_5' in device_data.columns:
            pm25_norm = (device_data['pm2_5'] - device_data['pm2_5'].min()) / (device_data['pm2_5'].max() - device_data['pm2_5'].min())
            axes[1,1].plot(device_data['datetime'], pm25_norm, label='PM2.5 (norm)', linewidth=2)
            
        if 'temperature' in device_data.columns:
            temp_norm = (device_data['temperature'] - device_data['temperature'].min()) / (device_data['temperature'].max() - device_data['temperature'].min())
            axes[1,1].plot(device_data['datetime'], temp_norm, label='Temperature (norm)', linewidth=2)
            
        if 'humidity' in device_data.columns:
            hum_norm = (device_data['humidity'] - device_data['humidity'].min()) / (device_data['humidity'].max() - device_data['humidity'].min())
            axes[1,1].plot(device_data['datetime'], hum_norm, label='Humidity (norm)', linewidth=2)
            
        axes[1,1].set_title(f'{device} - Normalized Metrics Comparison')
        axes[1,1].set_ylabel('Normalized Value (0-1)')
        axes[1,1].set_xlabel('Date')
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in axes.flat:
            ax.tick_params(axis='x', rotation=45)
        
        plt.suptitle(f'Multi-Category Analysis: {device}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_dir / f'device_multi_category_{device}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()

if __name__ == "__main__":
    import numpy as np
    
    print("🎨 Hot Durham Multi-Category Visualization Generator")
    print("=" * 50)
    
    try:
        create_combined_visualizations(days_back=30)
        print("✅ Multi-category visualizations created successfully!")
    except Exception as e:
        print(f"❌ Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()
