#!/usr/bin/env python3
"""
Enhanced Streamlit GUI for Hot Durham Project
Supports both Weather Underground and TSI data with improved live preview capabilities
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import subprocess
import os
import json
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'scripts'))

from src.core.data_manager import DataManager

# Configure Streamlit
st.set_page_config(
    page_title="Hot Durham Weather Monitoring Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-good { color: #28a745; }
    .status-warning { color: #ffc107; }
    .status-danger { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

def initialize_data_manager():
    """Initialize the data manager"""
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager(project_root)
    return st.session_state.data_manager

def load_recent_data(source, days=7):
    """Load recent data for preview"""
    dm = initialize_data_manager()
    return dm.load_recent_data(source, days=days)

def create_interactive_charts(wu_data, tsi_data):
    """Create interactive Plotly charts"""
    charts = {}
    
    # Temperature comparison chart
    if not wu_data.empty and not tsi_data.empty:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Temperature Comparison', 'Humidity Comparison', 'PM2.5 Levels', 'Multi-Metric Overview'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": True}]]
        )
        
        # Temperature comparison
        if 'date' in wu_data.columns and 'temperature' in wu_data.columns:
            wu_data['datetime'] = pd.to_datetime(wu_data['date'])
            wu_temp = wu_data.groupby('datetime')['temperature'].mean()
            fig.add_trace(
                go.Scatter(x=wu_temp.index, y=wu_temp.values, name='WU Temperature', line=dict(color='red')),
                row=1, col=1
            )
        
        if 'date' in tsi_data.columns and 'temperature' in tsi_data.columns:
            tsi_data['datetime'] = pd.to_datetime(tsi_data['date'])
            tsi_temp = tsi_data.groupby('datetime')['temperature'].mean()
            fig.add_trace(
                go.Scatter(x=tsi_temp.index, y=tsi_temp.values, name='TSI Temperature', line=dict(color='orange')),
                row=1, col=1
            )
        
        # Humidity comparison
        if 'humidity' in wu_data.columns:
            wu_humidity = wu_data.groupby('datetime')['humidity'].mean()
            fig.add_trace(
                go.Scatter(x=wu_humidity.index, y=wu_humidity.values, name='WU Humidity', line=dict(color='blue')),
                row=1, col=2
            )
        
        if 'humidity' in tsi_data.columns:
            tsi_humidity = tsi_data.groupby('datetime')['humidity'].mean()
            fig.add_trace(
                go.Scatter(x=tsi_humidity.index, y=tsi_humidity.values, name='TSI Humidity', line=dict(color='cyan')),
                row=1, col=2
            )
        
        # PM2.5 levels
        if 'pm2_5' in tsi_data.columns:
            pm25_data = tsi_data.groupby('datetime')['pm2_5'].mean()
            fig.add_trace(
                go.Scatter(x=pm25_data.index, y=pm25_data.values, name='PM2.5', line=dict(color='green')),
                row=2, col=1
            )
        
        # Multi-metric overview
        if not wu_data.empty:
            wu_temp_norm = (wu_temp - wu_temp.min()) / (wu_temp.max() - wu_temp.min())
            fig.add_trace(
                go.Scatter(x=wu_temp_norm.index, y=wu_temp_norm.values, name='Temperature (norm)', line=dict(color='red')),
                row=2, col=2
            )
        
        if 'humidity' in wu_data.columns:
            wu_humidity_norm = (wu_humidity - wu_humidity.min()) / (wu_humidity.max() - wu_humidity.min())
            fig.add_trace(
                go.Scatter(x=wu_humidity_norm.index, y=wu_humidity_norm.values, name='Humidity (norm)', line=dict(color='blue')),
                row=2, col=2
            )
        
        if 'pm2_5' in tsi_data.columns:
            pm25_norm = (pm25_data - pm25_data.min()) / (pm25_data.max() - pm25_data.min())
            fig.add_trace(
                go.Scatter(x=pm25_norm.index, y=pm25_norm.values, name='PM2.5 (norm)', line=dict(color='green')),
                row=2, col=2
            )
        
        fig.update_layout(height=800, title_text="Hot Durham Environmental Monitoring Dashboard")
        charts['overview'] = fig
    
    return charts

def run_data_pull(sources, start_date, end_date, pull_type):
    """Run automated data pull"""
    try:
        cmd = [
            sys.executable,
            str(project_root / "src" / "data_collection" / "automated_data_pull.py"),
            f"--{pull_type}"
        ]
        
        if 'wu' not in sources:
            cmd.append("--tsi-only")
        elif 'tsi' not in sources:
            cmd.append("--wu-only")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

# Main App
def main():
    st.markdown('<h1 class="main-header">🔥 Hot Durham Weather Monitoring Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")
    
    # Data source selection
    st.sidebar.subheader("📊 Data Sources")
    wu_enabled = st.sidebar.checkbox("Weather Underground", value=True)
    tsi_enabled = st.sidebar.checkbox("TSI Air Quality Sensors", value=True)
    
    # Date range selection
    st.sidebar.subheader("📅 Date Range")
    days_back = st.sidebar.slider("Days of data to load", min_value=1, max_value=90, value=14)
    
    # Pull type
    st.sidebar.subheader("🔄 Data Pull Options")
    pull_type = st.sidebar.selectbox("Pull Type", ["weekly", "bi_weekly", "monthly", "custom"])
    
    if pull_type == "custom":
        start_date = st.sidebar.date_input("Start Date", value=datetime.now() - timedelta(days=7))
        end_date = st.sidebar.date_input("End Date", value=datetime.now())
    
    # Chart options
    st.sidebar.subheader("📈 Visualization Options")
    chart_type = st.sidebar.selectbox("Chart Type", 
                                     ["Interactive Dashboard", "Static Charts", "Both"])
    show_device_breakdown = st.sidebar.checkbox("Show Device Breakdown", value=True)
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Dashboard", "🔄 Data Pull", "📈 Analysis", "⚙️ System Status"])
    
    with tab1:
        st.header("Live Environmental Monitoring Dashboard")
        
        # Load recent data
        if st.button("🔄 Refresh Data"):
            with st.spinner("Loading recent data..."):
                wu_data = load_recent_data('wu', days=days_back) if wu_enabled else pd.DataFrame()
                tsi_data = load_recent_data('tsi', days=days_back) if tsi_enabled else pd.DataFrame()
                
                st.session_state.wu_data = wu_data
                st.session_state.tsi_data = tsi_data
        
        # Display data if available
        if hasattr(st.session_state, 'wu_data') or hasattr(st.session_state, 'tsi_data'):
            wu_data = getattr(st.session_state, 'wu_data', pd.DataFrame())
            tsi_data = getattr(st.session_state, 'tsi_data', pd.DataFrame())
            
            # Data summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("WU Records", len(wu_data), delta=None)
            with col2:
                st.metric("TSI Records", len(tsi_data), delta=None)
            with col3:
                if not wu_data.empty and 'temperature' in wu_data.columns:
                    avg_temp = wu_data['temperature'].mean()
                    st.metric("Avg Temperature", f"{avg_temp:.1f}°F")
            with col4:
                if not tsi_data.empty and 'pm2_5' in tsi_data.columns:
                    avg_pm25 = tsi_data['pm2_5'].mean()
                    status = "🟢" if avg_pm25 < 12 else "🟡" if avg_pm25 < 35 else "🔴"
                    st.metric("Avg PM2.5", f"{avg_pm25:.1f} μg/m³", delta=status)
            
            # Interactive charts
            if chart_type in ["Interactive Dashboard", "Both"]:
                charts = create_interactive_charts(wu_data, tsi_data)
                for chart_name, chart in charts.items():
                    st.plotly_chart(chart, use_container_width=True)
            
            # Device breakdown
            if show_device_breakdown and not tsi_data.empty:
                st.subheader("🔬 Device-Specific Data")
                if 'device' in tsi_data.columns:
                    devices = tsi_data['device'].unique()
                    selected_devices = st.multiselect("Select devices to view", devices, default=devices[:3])
                    
                    for device in selected_devices:
                        device_data = tsi_data[tsi_data['device'] == device]
                        if not device_data.empty:
                            st.write(f"**{device}**")
                            device_cols = st.columns(3)
                            
                            if 'pm2_5' in device_data.columns:
                                with device_cols[0]:
                                    st.metric(f"{device} PM2.5", f"{device_data['pm2_5'].mean():.1f}")
                            if 'temperature' in device_data.columns:
                                with device_cols[1]:
                                    st.metric(f"{device} Temp", f"{device_data['temperature'].mean():.1f}°F")
                            if 'humidity' in device_data.columns:
                                with device_cols[2]:
                                    st.metric(f"{device} Humidity", f"{device_data['humidity'].mean():.1f}%")
        else:
            st.info("Click 'Refresh Data' to load recent environmental data")
    
    with tab2:
        st.header("🔄 Automated Data Pull")
        
        sources = []
        if wu_enabled:
            sources.append('wu')
        if tsi_enabled:
            sources.append('tsi')
        
        st.write(f"**Selected Sources:** {', '.join(sources) if sources else 'None'}")
        st.write(f"**Pull Type:** {pull_type}")
        
        if pull_type == "custom":
            st.write(f"**Date Range:** {start_date} to {end_date}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Run Data Pull", disabled=not sources):
                with st.spinner("Running data pull..."):
                    success, stdout, stderr = run_data_pull(sources, 
                                                          start_date if pull_type == "custom" else None,
                                                          end_date if pull_type == "custom" else None,
                                                          pull_type)
                    if success:
                        st.success("✅ Data pull completed successfully!")
                        st.text_area("Output", stdout, height=200)
                    else:
                        st.error("❌ Data pull failed!")
                        st.text_area("Error", stderr, height=200)
        
        with col2:
            if st.button("📊 Generate Reports"):
                with st.spinner("Generating reports..."):
                    try:
                        result = subprocess.run([
                            sys.executable,
                            str(project_root / "src" / "analysis" / "enhanced_data_analysis.py")
                        ], capture_output=True, text=True, cwd=project_root)
                        
                        if result.returncode == 0:
                            st.success("✅ Reports generated successfully!")
                        else:
                            st.error("❌ Report generation failed!")
                            st.text_area("Error", result.stderr, height=100)
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
    
    with tab3:
        st.header("📈 Multi-Category Analysis")
        
        if st.button("🎨 Generate Multi-Category Visualizations"):
            with st.spinner("Creating visualizations..."):
                try:
                    result = subprocess.run([
                        sys.executable,
                        str(project_root / "src" / "analysis" / "multi_category_visualization.py")
                    ], capture_output=True, text=True, cwd=project_root)
                    
                    if result.returncode == 0:
                        st.success("✅ Visualizations created successfully!")
                        
                        # Display generated charts
                        charts_dir = project_root / "reports" / "charts"
                        if charts_dir.exists():
                            chart_files = list(charts_dir.glob("*.png"))
                            chart_files.sort(key=os.path.getmtime, reverse=True)
                            
                            for chart_file in chart_files[:5]:  # Show last 5 charts
                                st.subheader(chart_file.stem.replace('_', ' ').title())
                                st.image(str(chart_file))
                    else:
                        st.error("❌ Visualization generation failed!")
                        st.text_area("Error", result.stderr, height=100)
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    with tab4:
        st.header("⚙️ System Status")
        
        dm = initialize_data_manager()
        
        # System health check
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📁 Data Inventory")
            
            # Check raw data
            raw_wu_count = len(list((project_root / "raw_pulls" / "wu").rglob("*.csv"))) if (project_root / "raw_pulls" / "wu").exists() else 0
            raw_tsi_count = len(list((project_root / "raw_pulls" / "tsi").rglob("*.csv"))) if (project_root / "raw_pulls" / "tsi").exists() else 0
            
            st.metric("WU Raw Files", raw_wu_count)
            st.metric("TSI Raw Files", raw_tsi_count)
            
            # Check processed data
            processed_count = len(list((project_root / "processed").rglob("*.csv"))) if (project_root / "processed").exists() else 0
            st.metric("Processed Files", processed_count)
        
        with col2:
            st.subheader("☁️ Google Drive Status")
            
            drive_status = "✅ Connected" if dm.drive_service else "❌ Not Connected"
            st.write(f"**Status:** {drive_status}")
            
            if st.button("🔄 Test Google Drive Sync"):
                try:
                    if dm.drive_service:
                        dm.sync_to_drive()
                        st.success("✅ Google Drive sync successful!")
                    else:
                        st.error("❌ Google Drive not configured")
                except Exception as e:
                    st.error(f"❌ Sync failed: {e}")
        
        # Recent activity
        st.subheader("📊 Recent Activity")
        
        # Check for recent log files
        logs_dir = project_root / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            if log_files:
                latest_log = max(log_files, key=os.path.getmtime)
                st.write(f"**Latest Log:** {latest_log.name}")
                
                if st.button("📄 View Recent Log Entries"):
                    try:
                        with open(latest_log, 'r') as f:
                            lines = f.readlines()
                            recent_lines = lines[-20:] if len(lines) > 20 else lines
                            st.text_area("Recent Log Entries", ''.join(recent_lines), height=200)
                    except Exception as e:
                        st.error(f"Error reading log: {e}")

if __name__ == "__main__":
    main()
