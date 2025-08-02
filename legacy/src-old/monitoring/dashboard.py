"""
Real-time monitoring dashboard for Hot Durham project
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.database.db_manager import HotDurhamDB

def main():
    st.set_page_config(
        page_title="Hot Durham Environmental Monitoring",
        page_icon="🌡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🌡️ Hot Durham Environmental Monitoring Dashboard")
    
    # Sidebar controls
    st.sidebar.header("Controls")
    time_range = st.sidebar.selectbox(
        "Time Range",
        ["Last 6 hours", "Last 24 hours", "Last 7 days"],
        index=1
    )
    
    hours_map = {"Last 6 hours": 6, "Last 24 hours": 24, "Last 7 days": 168}
    hours = hours_map[time_range]
    
    # Initialize database
    db = HotDurhamDB()
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🌬️ Air Quality", "🌡️ Weather", "📈 System Stats"])
    
    with tab1:
        show_overview(db, hours)
    
    with tab2:
        show_air_quality(db, hours)
    
    with tab3:
        show_weather(db, hours)
    
    with tab4:
        show_system_stats(db)

def show_overview(db, hours):
    """Show overview metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    # Get latest data
    tsi_data = db.get_latest_data("tsi", hours)
    wu_data = db.get_latest_data("wu", hours)
    
    with col1:
        st.metric("Active TSI Sensors", len(tsi_data['device_name'].unique()) if not tsi_data.empty else 0)
    
    with col2:
        st.metric("Active WU Stations", len(wu_data['station_id'].unique()) if not wu_data.empty else 0)
    
    with col3:
        avg_pm25 = tsi_data['pm25'].mean() if not tsi_data.empty else 0
        st.metric("Avg PM2.5", f"{avg_pm25:.1f} μg/m³")
    
    with col4:
        avg_temp = wu_data['temperature'].mean() if not wu_data.empty else 0
        st.metric("Avg Temperature", f"{avg_temp:.1f}°C")
    
    # Recent data summary
    st.subheader("Recent Data Collection")
    if not tsi_data.empty:
        st.write(f"**TSI Data:** {len(tsi_data)} records from {len(tsi_data['device_name'].unique())} sensors")
    if not wu_data.empty:
        st.write(f"**Weather Data:** {len(wu_data)} records from {len(wu_data['station_id'].unique())} stations")

def show_air_quality(db, hours):
    """Show air quality data"""
    tsi_data = db.get_latest_data("tsi", hours)
    
    if tsi_data.empty:
        st.warning("No air quality data available for the selected time range.")
        return
    
    # PM2.5 time series
    st.subheader("PM2.5 Levels Over Time")
    if 'timestamp' in tsi_data.columns and 'pm25' in tsi_data.columns:
        tsi_data['timestamp'] = pd.to_datetime(tsi_data['timestamp'])
        
        fig = px.line(
            tsi_data, 
            x='timestamp', 
            y='pm25', 
            color='device_name',
            title="PM2.5 Concentrations by Sensor"
        )
        fig.update_layout(xaxis_title="Time", yaxis_title="PM2.5 (μg/m³)")
        st.plotly_chart(fig, use_container_width=True)
    
    # Current air quality status
    st.subheader("Current Air Quality Status")
    if 'pm25' in tsi_data.columns:
        latest_pm25 = tsi_data.groupby('device_name')['pm25'].last()
        
        for sensor, pm25 in latest_pm25.items():
            if pm25 <= 12:
                color = "🟢"
                status = "Good"
            elif pm25 <= 35:
                color = "🟡"
                status = "Moderate"
            elif pm25 <= 55:
                color = "🟠"
                status = "Unhealthy for Sensitive"
            else:
                color = "🔴"
                status = "Unhealthy"
            
            st.write(f"{color} **{sensor}**: {pm25:.1f} μg/m³ ({status})")

def show_weather(db, hours):
    """Show weather data"""
    wu_data = db.get_latest_data("wu", hours)
    
    if wu_data.empty:
        st.warning("No weather data available for the selected time range.")
        return
    
    # Temperature time series
    st.subheader("Temperature Over Time")
    if 'timestamp' in wu_data.columns and 'temperature' in wu_data.columns:
        wu_data['timestamp'] = pd.to_datetime(wu_data['timestamp'])
        
        fig = px.line(
            wu_data, 
            x='timestamp', 
            y='temperature', 
            color='station_id',
            title="Temperature by Weather Station"
        )
        fig.update_layout(xaxis_title="Time", yaxis_title="Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)

def show_system_stats(db):
    """Show system statistics"""
    st.subheader("Data Collection Statistics")
    
    stats = db.get_collection_stats(7)
    if not stats.empty:
        fig = px.bar(
            stats, 
            x='collection_date', 
            y='total_records', 
            color='source',
            title="Daily Data Collection Volume"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Show raw stats
        st.dataframe(stats)
    else:
        st.info("No collection statistics available.")

if __name__ == "__main__":
    main()
