#!/usr/bin/env python3
"""
Test Weather Underground Historical API Access

Quick test to verify we can access historical data from Weather Underground
for the test sensors before running the full collection.
"""

import os
import sys
import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime, date, timedelta

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "config"))

try:
    from config.test_sensors_config import TEST_SENSOR_IDS, WU_TO_MS_MAPPING
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

import nest_asyncio
nest_asyncio.apply()

async def test_wu_api():
    """Test Weather Underground API access for historical data."""
    
    # Load API credentials
    try:
        wu_api_key_path = project_root / "creds" / "wu_api_key.json"
        with open(wu_api_key_path, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('test_api_key') or creds.get('api_key')
    except Exception as e:
        print(f"❌ Error loading API credentials: {e}")
        return
    
    # Test sensor
    test_sensor = TEST_SENSOR_IDS[0]  # Use first sensor
    print(f"🧪 Testing API access with sensor: {test_sensor}")
    print(f"📍 Mapped to: {WU_TO_MS_MAPPING.get(test_sensor, 'Unknown')}")
    print()
    
    # Test current conditions
    print("1️⃣ Testing current conditions API...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.weather.com/v2/pws/observations/current",
                params={
                    "stationId": test_sensor,
                    "format": "json",
                    "apiKey": api_key,
                    "units": "m",
                    "numericPrecision": "decimal"
                }
            )
            response.raise_for_status()
            current_data = response.json()
            
            if "observations" in current_data and current_data["observations"]:
                obs = current_data["observations"][0]
                print(f"✅ Current conditions: {obs.get('metric', {}).get('temp', 'N/A')}°C")
                print(f"   Timestamp: {obs.get('obsTimeLocal', 'N/A')}")
            else:
                print("⚠️ No current observations available")
                
    except Exception as e:
        print(f"❌ Current conditions API error: {e}")
    
    print()
    
    # Test historical daily data
    print("2️⃣ Testing historical daily API...")
    test_date = date.today() - timedelta(days=1)  # Yesterday
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.weather.com/v2/pws/history/daily",
                params={
                    "stationId": test_sensor,
                    "format": "json",
                    "apiKey": api_key,
                    "units": "m",
                    "date": test_date.strftime('%Y%m%d'),
                    "numericPrecision": "decimal"
                }
            )
            response.raise_for_status()
            historical_data = response.json()
            
            if "observations" in historical_data:
                obs_count = len(historical_data["observations"])
                print(f"✅ Historical data for {test_date}: {obs_count} observations")
                
                if obs_count > 0:
                    sample_obs = historical_data["observations"][0]
                    print(f"   Sample observation keys: {list(sample_obs.keys())}")
            else:
                print(f"⚠️ No historical data available for {test_date}")
                
    except Exception as e:
        print(f"❌ Historical API error: {e}")
    
    print()
    
    # Test historical hourly data (if available)
    print("3️⃣ Testing historical hourly API...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.weather.com/v2/pws/history/hourly",
                params={
                    "stationId": test_sensor,
                    "format": "json",
                    "apiKey": api_key,
                    "units": "m",
                    "date": test_date.strftime('%Y%m%d'),
                    "numericPrecision": "decimal"
                }
            )
            response.raise_for_status()
            hourly_data = response.json()
            
            if "observations" in hourly_data:
                obs_count = len(hourly_data["observations"])
                print(f"✅ Hourly historical data for {test_date}: {obs_count} observations")
                
                if obs_count > 0:
                    sample_obs = hourly_data["observations"][0]
                    print(f"   Sample hourly observation: {sample_obs.get('obsTimeLocal', 'N/A')}")
            else:
                print(f"⚠️ No hourly historical data available for {test_date}")
                
    except Exception as e:
        print(f"❌ Hourly historical API error: {e}")
    
    print()
    print("🔍 API Test Complete!")
    print()
    print("💡 Notes:")
    print("   - Weather Underground may have different data retention policies")
    print("   - Personal weather stations might not have continuous data")
    print("   - 15-minute intervals may need to be reconstructed from available data")

if __name__ == "__main__":
    asyncio.run(test_wu_api())
