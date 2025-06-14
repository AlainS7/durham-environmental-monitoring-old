#!/usr/bin/env python3
"""
Live Sensor Map with Real-time Data
Creates an interactive web map showing all sensors with live data updates
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests
import httpx
import pandas as pd
from flask import Flask, render_template, jsonify, request
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import existing systems
try:
    from src.core.data_manager import DataManager
    from src.data_collection.faster_wu_tsi_to_sheets_async import fetch_wu_data, fetch_tsi_data
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False

class LiveSensorMapServer:
    """Flask server for live sensor map"""
    
    def __init__(self, project_root_path: str):
        self.project_root = Path(project_root_path)
        self.app = Flask(__name__, template_folder=str(self.project_root / "templates"))
        self.setup_routes()
        
        # Load credentials
        self.wu_creds = self.load_wu_credentials()
        self.tsi_creds = self.load_tsi_credentials()
        
        # Sensor configurations with enhanced location data
        self.wu_sensors = [
            {
                "name": "Duke-MS-01", 
                "id": "KNCDURHA548", 
                "lat": 36.0014, 
                "lon": -78.9392,
                "location": "Duke Campus - Main Building",
                "type": "Weather Station"
            },
            {
                "name": "Duke-MS-02", 
                "id": "KNCDURHA549", 
                "lat": 36.0030, 
                "lon": -78.9400,
                "location": "Duke Campus - East Wing", 
                "type": "Weather Station"
            },
            {
                "name": "Duke-MS-03", 
                "id": "KNCDURHA209", 
                "lat": 36.0040, 
                "lon": -78.9380,
                "location": "Duke Campus - Research Area",
                "type": "Weather Station"
            },
            {
                "name": "Duke-MS-05", 
                "id": "KNCDURHA551", 
                "lat": 36.0020, 
                "lon": -78.9370,
                "location": "Duke Campus - South Building",
                "type": "Weather Station"
            },
            {
                "name": "Duke-MS-06", 
                "id": "KNCDURHA555", 
                "lat": 36.0050, 
                "lon": -78.9360,
                "location": "Duke Campus - North Area",
                "type": "Weather Station"
            },
            {
                "name": "Duke-MS-07", 
                "id": "KNCDURHA556", 
                "lat": 36.0010, 
                "lon": -78.9350,
                "location": "Duke Campus - West Wing",
                "type": "Weather Station"
            },
            {
                "name": "Duke-Kestrel-01", 
                "id": "KNCDURHA590", 
                "lat": 36.0025, 
                "lon": -78.9345,
                "location": "Duke Campus - Kestrel Station",
                "type": "Weather Station"
            }
        ]
        
        # TSI sensors will be loaded dynamically from API
        self.tsi_sensors = []
        self.last_tsi_fetch = None
        
    def load_wu_credentials(self):
        """Load Weather Underground API credentials"""
        try:
            creds_path = self.project_root / "creds" / "wu_api_key.json"
            with open(creds_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load WU credentials: {e}")
            return {}
    
    def load_tsi_credentials(self):
        """Load TSI API credentials"""
        try:
            creds_path = self.project_root / "creds" / "tsi_creds.json"
            with open(creds_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load TSI credentials: {e}")
            return {}
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('live_sensor_map.html')
        
        @self.app.route('/api/sensors/all')
        def get_all_sensors():
            """Get all sensors with basic info"""
            try:
                # Refresh TSI sensors if needed
                self.refresh_tsi_sensors()
                
                all_sensors = {
                    'wu_sensors': self.wu_sensors,
                    'tsi_sensors': self.tsi_sensors,
                    'last_updated': datetime.now().isoformat()
                }
                return jsonify(all_sensors)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/wu/<sensor_id>')
        def get_wu_data(sensor_id):
            """Get live Weather Underground data for a specific sensor"""
            try:
                if not self.wu_creds.get('test_api_key'):
                    return jsonify({'error': 'WU API key not available'}), 500
                
                # Get current weather data
                url = f"https://api.weather.com/v2/pws/observations/current"
                params = {
                    'stationId': sensor_id,
                    'format': 'json',
                    'units': 'm',
                    'apiKey': self.wu_creds['test_api_key']
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('observations') and len(data['observations']) > 0:
                        obs = data['observations'][0]
                        
                        # Extract and format data
                        live_data = {
                            'timestamp': obs.get('obsTimeUtc', ''),
                            'temperature': obs.get('metric', {}).get('temp'),
                            'humidity': obs.get('humidity'),
                            'wind_speed': obs.get('metric', {}).get('windSpeed'),
                            'wind_direction': obs.get('windir'),
                            'pressure': obs.get('metric', {}).get('pressure'),
                            'precipitation': obs.get('metric', {}).get('precipRate'),
                            'solar_radiation': obs.get('solarRadiation'),
                            'heat_index': obs.get('metric', {}).get('heatIndex'),
                            'dew_point': obs.get('metric', {}).get('dewpt'),
                            'uv_index': obs.get('uv'),
                            'status': 'online'
                        }
                        return jsonify(live_data)
                    else:
                        return jsonify({'error': 'No observations available', 'status': 'no_data'}), 404
                else:
                    return jsonify({'error': f'API error: {response.status_code}', 'status': 'offline'}), response.status_code
                    
            except Exception as e:
                return jsonify({'error': str(e), 'status': 'offline'}), 500
        
        @self.app.route('/api/tsi/<device_id>')
        def get_tsi_data(device_id):
            """Get live TSI data for a specific device"""
            try:
                if not self.tsi_creds.get('key') or not self.tsi_creds.get('secret'):
                    return jsonify({'error': 'TSI credentials not available'}), 500
                
                # Get TSI auth token
                auth_response = requests.post(
                    'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken',
                    params={'grant_type': 'client_credentials'},
                    data={
                        'client_id': self.tsi_creds['key'],
                        'client_secret': self.tsi_creds['secret']
                    },
                    timeout=10
                )
                
                if auth_response.status_code != 200:
                    return jsonify({'error': 'TSI authentication failed', 'status': 'offline'}), 500
                
                access_token = auth_response.json().get('access_token')
                if not access_token:
                    return jsonify({'error': 'No access token received', 'status': 'offline'}), 500
                
                # Get recent data (last 24 hours)
                end_date = datetime.now()
                start_date = end_date - timedelta(hours=24)
                
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }
                
                params = {
                    'device_id': device_id,
                    'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                }
                
                data_response = requests.get(
                    'https://api-prd.tsilink.com/api/v3/external/telemetry',
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if data_response.status_code == 200:
                    data = data_response.json()
                    
                    if isinstance(data, list) and len(data) > 0:
                        # Get the most recent record
                        latest_record = data[-1]
                        
                        # Extract measurements
                        live_data = {
                            'timestamp': latest_record.get('timestamp', ''),
                            'device_id': device_id,
                            'status': 'online'
                        }
                        
                        # Extract sensor measurements
                        sensors = latest_record.get('sensors', [])
                        if isinstance(sensors, list):
                            for sensor in sensors:
                                measurements = sensor.get('measurements', [])
                                for measurement in measurements:
                                    mtype = measurement.get('type')
                                    value = measurement.get('data', {}).get('value')
                                    
                                    # Map measurement types to friendly names
                                    if mtype == 'mcpm2x5':
                                        live_data['pm25'] = value
                                    elif mtype == 'mcpm10':
                                        live_data['pm10'] = value
                                    elif mtype == 'temp_c':
                                        live_data['temperature'] = value
                                    elif mtype == 'rh_percent':
                                        live_data['humidity'] = value
                                    elif mtype == 'mcpm2x5_aqi':
                                        live_data['aqi'] = value
                        
                        return jsonify(live_data)
                    else:
                        return jsonify({'error': 'No recent data available', 'status': 'no_data'}), 404
                else:
                    return jsonify({'error': f'TSI API error: {data_response.status_code}', 'status': 'offline'}), data_response.status_code
                    
            except Exception as e:
                return jsonify({'error': str(e), 'status': 'offline'}), 500
        
        @self.app.route('/api/tsi/devices')
        def get_tsi_devices():
            """Get list of TSI devices"""
            try:
                self.refresh_tsi_sensors()
                return jsonify(self.tsi_sensors)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/health')
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'wu_sensors': len(self.wu_sensors),
                'tsi_sensors': len(self.tsi_sensors),
                'dependencies': DEPENDENCIES_AVAILABLE
            })
    
    def refresh_tsi_sensors(self):
        """Refresh TSI sensor list from API"""
        try:
            # Only refresh if we haven't fetched recently (cache for 5 minutes)
            if (self.last_tsi_fetch and 
                datetime.now() - self.last_tsi_fetch < timedelta(minutes=5)):
                return
            
            if not self.tsi_creds.get('key') or not self.tsi_creds.get('secret'):
                return
            
            # Get TSI auth token
            auth_response = requests.post(
                'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken',
                params={'grant_type': 'client_credentials'},
                data={
                    'client_id': self.tsi_creds['key'],
                    'client_secret': self.tsi_creds['secret']
                },
                timeout=10
            )
            
            if auth_response.status_code != 200:
                return
            
            access_token = auth_response.json().get('access_token')
            if not access_token:
                return
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Get devices list
            devices_response = requests.get(
                'https://api-prd.tsilink.com/api/v3/external/devices',
                headers=headers,
                timeout=10
            )
            
            if devices_response.status_code == 200:
                devices = devices_response.json()
                
                # Convert to our sensor format
                self.tsi_sensors = []
                for device in devices:
                    device_id = device.get('device_id')
                    metadata = device.get('metadata', {})
                    friendly_name = metadata.get('friendlyName', device_id)
                    
                    # Try to get location from metadata, use defaults if not available
                    lat = metadata.get('latitude')
                    lon = metadata.get('longitude')
                    
                    # If no coordinates in metadata, assign based on device name/ID
                    if not lat or not lon:
                        # Default locations around Durham area for TSI sensors
                        default_locations = {
                            'BS-01': {'lat': 36.0015, 'lon': -78.9385},
                            'BS-05': {'lat': 36.0025, 'lon': -78.9375},
                            'BS-11': {'lat': 36.0035, 'lon': -78.9365},
                            'BS-13': {'lat': 36.0045, 'lon': -78.9355},
                        }
                        
                        # Try to match by friendly name or device ID
                        for key, coords in default_locations.items():
                            if key in friendly_name or key in device_id:
                                lat = coords['lat']
                                lon = coords['lon']
                                break
                        
                        # If still no coordinates, use a default with small offset
                        if not lat or not lon:
                            offset = len(self.tsi_sensors) * 0.001
                            lat = 36.0020 + offset
                            lon = -78.9380 + offset
                    
                    sensor_info = {
                        'name': friendly_name,
                        'id': device_id,
                        'lat': float(lat),
                        'lon': float(lon),
                        'location': metadata.get('location', f'TSI Sensor - {friendly_name}'),
                        'type': 'Air Quality Sensor',
                        'last_seen': metadata.get('lastSeen', '')
                    }
                    
                    self.tsi_sensors.append(sensor_info)
                
                self.last_tsi_fetch = datetime.now()
                
        except Exception as e:
            print(f"Error refreshing TSI sensors: {e}")
    
    def run(self, host='localhost', port=5003, debug=True):
        """Run the Flask server"""
        print(f"🗺️ Starting Live Sensor Map Server on http://{host}:{port}")
        print(f"📍 Weather Underground sensors: {len(self.wu_sensors)}")
        self.refresh_tsi_sensors()
        print(f"🏭 TSI sensors: {len(self.tsi_sensors)}")
        
        self.app.run(host=host, port=port, debug=debug)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Live Sensor Map')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=5003, help='Port to bind to (default: 5003)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    server = LiveSensorMapServer(str(project_root))
    server.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
