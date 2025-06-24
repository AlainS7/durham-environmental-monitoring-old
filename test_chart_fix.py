#!/usr/bin/env python3
"""
Test script to simulate the Duke-Kestrel-01 chart creation with our fix
"""

import pandas as pd
import os
import numpy as np

# Load the existing WU data
wu_data_path = "/Users/alainsoto/Developer/work/github.com/AlainS7/tsi-data-uploader/raw_pulls/wu/2025/week_14/wu_data_2025-04-01_to_2025-05-30.csv"

if not os.path.exists(wu_data_path):
    print(f"❌ WU data file not found at {wu_data_path}")
    exit(1)

print("📊 Loading and processing WU data for chart creation test...")
wu_df = pd.read_csv(wu_data_path)

# Apply the same transformations as the main script
wu_df['obsTimeUtc'] = pd.to_datetime(wu_df['obsTimeUtc'], errors='coerce')
wu_df = wu_df.dropna(subset=['obsTimeUtc'])
wu_df['date_display'] = wu_df['obsTimeUtc'].dt.strftime('%m-%d')

# Apply station name mapping
station_id_to_name = {
    "KNCDURHA548": "Duke-MS-01",
    "KNCDURHA549": "Duke-MS-02", 
    "KNCDURHA209": "Duke-MS-03",
    "KNCDURHA551": "Duke-MS-05",
    "KNCDURHA555": "Duke-MS-06", 
    "KNCDURHA556": "Duke-MS-07",
    "KNCDURHA590": "Duke-Kestrel-01"
}
wu_df['Station Name'] = wu_df['stationID'].map(station_id_to_name).fillna(wu_df['stationID'])

# Ensure metric columns are numeric
wu_metrics = [
    ('tempAvg', 'Temperature (C)'),
    ('humidityAvg', 'Humidity (%)'),
    ('heatindexAvg', 'Heat Index (C)'),
    ('solarRadiationHigh', 'Solar Radiation'),
    ('precipTotal', 'Precipitation (mm)'),
    ('windspeedAvg', 'Wind Speed (Avg)'),
    ('dewptAvg', 'Dew Point (C)')
]

for metric, _ in wu_metrics:
    if metric in wu_df.columns:
        wu_df[metric] = pd.to_numeric(wu_df[metric], errors='coerce')

# Simulate outlier removal (simplified - just for demo)
def simple_outlier_removal(df, column):
    if column not in df.columns:
        return df
    
    numeric_data = pd.to_numeric(df[column], errors='coerce')
    Q1 = numeric_data.quantile(0.25)
    Q3 = numeric_data.quantile(0.75)
    IQR = Q3 - Q1
    
    # Use lenient parameters for Duke-Kestrel-01 data
    kestrel_count = len(df[df['Station Name'] == 'Duke-Kestrel-01'])
    total_count = len(df)
    is_kestrel_heavy = (kestrel_count / max(total_count, 1)) > 0.3
    
    iqr_multiplier = 2.5 if is_kestrel_heavy else 1.5
    
    lower_bound = Q1 - iqr_multiplier * IQR
    upper_bound = Q3 + iqr_multiplier * IQR
    outlier_mask = (numeric_data >= lower_bound) & (numeric_data <= upper_bound)
    
    filtered_df = df[outlier_mask.fillna(True)]
    if len(filtered_df) != len(df):
        removed_count = len(df) - len(filtered_df)
        lenient_note = " (lenient for Kestrel)" if is_kestrel_heavy else ""
        print(f"   📊 Outlier removal: Removed {removed_count} outliers from {column}{lenient_note}")
    
    return filtered_df

print(f"\n📊 Testing chart creation for each metric...")
all_times = sorted(wu_df['obsTimeUtc'].unique())

for metric, y_label in wu_metrics:
    if metric not in wu_df.columns:
        print(f"⏭️ Skipping {metric} - column not found")
        continue
    
    print(f"\n🔍 Testing {metric} chart creation:")
    
    # Apply outlier removal
    metric_df = simple_outlier_removal(wu_df, metric)
    
    # Create pivot table 
    pivot = metric_df.pivot_table(index='obsTimeUtc', columns='Station Name', values=metric, aggfunc='mean')
    pivot = pivot.reindex(all_times)
    pivot.reset_index(inplace=True)
    
    # Check which stations have data - implementing our fix
    data_columns = [col for col in pivot.columns if col != 'obsTimeUtc']
    
    # Filter out columns (stations) that have ALL NaN values for this metric
    stations_with_data = []
    for col in data_columns:
        non_null_count = pivot[col].count()
        total_count = len(pivot)
        if non_null_count > 0:
            stations_with_data.append(col)
            if col == 'Duke-Kestrel-01':
                print(f"   📊 Duke-Kestrel-01 {metric}: {non_null_count}/{total_count} non-null values in pivot table")
    
    print(f"   📊 Stations with data: {stations_with_data}")
    
    if 'Duke-Kestrel-01' in stations_with_data:
        print(f"   ✅ Duke-Kestrel-01 successfully included in {metric} chart!")
    else:
        print(f"   ⚠️ Duke-Kestrel-01 missing from {metric} chart")
        # Additional debug
        kestrel_raw_data = wu_df[wu_df['Station Name'] == 'Duke-Kestrel-01'][metric].dropna()
        print(f"   📊 Duke-Kestrel-01 {metric} source data: {len(kestrel_raw_data)} non-null values")

print(f"\n✅ Chart creation test completed!")
