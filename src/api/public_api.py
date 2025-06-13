#!/usr/bin/env python3
"""
Hot Durham System - Feature 3: Public API & Developer Portal
RESTful API for public access to Durham air quality data
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, render_template_string
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import pandas as pd
import sqlite3
import hashlib
import secrets

class PublicAPI:
    """Public API for Hot Durham air quality data."""
    
    def __init__(self, base_dir: str = None):
        """Initialize the Public API system."""
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.config_file = self.base_dir / "config" / "public_api_config.json"
        self.api_keys_db = self.base_dir / "data" / "api_keys.db"
        self.usage_db = self.base_dir / "data" / "api_usage.db"
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = secrets.token_hex(32)
        
        # Enable CORS for public API
        CORS(self.app)
        
        # Setup rate limiting
        self.limiter = Limiter(
            key_func=get_remote_address,
            app=self.app,
            default_limits=["1000 per hour"]
        )
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self._load_config()
        
        # Initialize databases
        self._init_databases()
        
        # Setup API routes
        self._setup_routes()
        
        print("🌐 Hot Durham Public API & Developer Portal initialized")
        print(f"📂 Base directory: {self.base_dir}")
        
    def _load_config(self):
        """Load API configuration."""
        default_config = {
            "api_version": "v1",
            "rate_limits": {
                "public": "1000 per hour",
                "premium": "10000 per hour",
                "developer": "5000 per hour"
            },
            "endpoints": {
                "sensors": "/api/v1/sensors",
                "current": "/api/v1/sensors/{sensor_id}/current",
                "historical": "/api/v1/sensors/{sensor_id}/historical",
                "forecasts": "/api/v1/forecasts",
                "alerts": "/api/v1/alerts"
            },
            "data_retention": {
                "current": "7 days",
                "historical": "1 year",
                "forecasts": "7 days"
            }
        }
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        
        print(f"📋 API configuration loaded: {len(self.config['endpoints'])} endpoints")
        
    def _init_databases(self):
        """Initialize API keys and usage tracking databases."""
        # Create data directory
        self.api_keys_db.parent.mkdir(parents=True, exist_ok=True)
        
        # API Keys database
        conn = sqlite3.connect(str(self.api_keys_db))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                tier TEXT DEFAULT 'public',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
        # Usage tracking database
        conn = sqlite3.connect(str(self.usage_db))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT,
                endpoint TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time REAL,
                status_code INTEGER,
                ip_address TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
        print("🗄️ API databases initialized")
        
    def _setup_routes(self):
        """Setup all API routes."""
        
        # Root endpoint - API documentation
        @self.app.route('/')
        def api_docs():
            return self._render_api_docs()
        
        # API status
        @self.app.route('/api/v1/status')
        @self.limiter.limit("100 per minute")
        def api_status():
            return jsonify({
                "status": "operational",
                "version": self.config["api_version"],
                "timestamp": datetime.now().isoformat(),
                "endpoints": len(self.config["endpoints"])
            })
        
        # List all sensors
        @self.app.route('/api/v1/sensors')
        @self.limiter.limit("200 per hour")
        def list_sensors():
            api_key = request.headers.get('X-API-Key')
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401
            
            self._log_usage(api_key, '/api/v1/sensors', request.remote_addr)
            
            sensors = self._get_sensors_list()
            return jsonify({
                "sensors": sensors,
                "count": len(sensors),
                "timestamp": datetime.now().isoformat()
            })
        
        # Current sensor data
        @self.app.route('/api/v1/sensors/<sensor_id>/current')
        @self.limiter.limit("500 per hour")
        def get_current_data(sensor_id):
            api_key = request.headers.get('X-API-Key')
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401
            
            self._log_usage(api_key, f'/api/v1/sensors/{sensor_id}/current', request.remote_addr)
            
            data = self._get_current_sensor_data(sensor_id)
            if not data:
                return jsonify({"error": "Sensor not found"}), 404
            
            return jsonify(data)
        
        # Historical sensor data
        @self.app.route('/api/v1/sensors/<sensor_id>/historical')
        @self.limiter.limit("100 per hour")
        def get_historical_data(sensor_id):
            api_key = request.headers.get('X-API-Key')
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401
            
            # Get query parameters
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            limit = min(int(request.args.get('limit', 1000)), 10000)  # Max 10k records
            
            self._log_usage(api_key, f'/api/v1/sensors/{sensor_id}/historical', request.remote_addr)
            
            data = self._get_historical_sensor_data(sensor_id, start_date, end_date, limit)
            if not data:
                return jsonify({"error": "No data found"}), 404
            
            return jsonify({
                "sensor_id": sensor_id,
                "data": data,
                "count": len(data),
                "timestamp": datetime.now().isoformat()
            })
        
        # Air quality forecasts
        @self.app.route('/api/v1/forecasts')
        @self.limiter.limit("200 per hour")
        def get_forecasts():
            api_key = request.headers.get('X-API-Key')
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401
            
            hours_ahead = min(int(request.args.get('hours', 24)), 48)  # Max 48 hours
            
            self._log_usage(api_key, '/api/v1/forecasts', request.remote_addr)
            
            forecasts = self._get_air_quality_forecasts(hours_ahead)
            return jsonify({
                "forecasts": forecasts,
                "hours_ahead": hours_ahead,
                "timestamp": datetime.now().isoformat()
            })
        
        # Active alerts
        @self.app.route('/api/v1/alerts')
        @self.limiter.limit("300 per hour")
        def get_alerts():
            api_key = request.headers.get('X-API-Key')
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401
            
            self._log_usage(api_key, '/api/v1/alerts', request.remote_addr)
            
            alerts = self._get_active_alerts()
            return jsonify({
                "alerts": alerts,
                "count": len(alerts),
                "timestamp": datetime.now().isoformat()
            })
        
        # Developer portal - register API key
        @self.app.route('/api/v1/register', methods=['POST'])
        @self.limiter.limit("10 per hour")
        def register_api_key():
            data = request.get_json()
            if not data or 'email' not in data:
                return jsonify({"error": "Email is required"}), 400
            
            api_key = self._generate_api_key(data['email'])
            return jsonify({
                "api_key": api_key,
                "tier": "public",
                "rate_limit": self.config["rate_limits"]["public"],
                "documentation": f"{request.url_root}",
                "message": "API key generated successfully"
            })
        
        # API usage stats (for registered users)
        @self.app.route('/api/v1/usage')
        @self.limiter.limit("50 per hour")
        def get_usage_stats():
            api_key = request.headers.get('X-API-Key')
            if not self._validate_api_key(api_key):
                return jsonify({"error": "Invalid or missing API key"}), 401
            
            stats = self._get_usage_stats(api_key)
            return jsonify(stats)
        
        print("🛣️ API routes configured")
        
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        if not api_key:
            return False
        
        conn = sqlite3.connect(str(self.api_keys_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM api_keys WHERE api_key = ? AND is_active = 1",
            (api_key,)
        )
        result = cursor.fetchone()
        
        if result:
            # Update last used timestamp
            cursor.execute(
                "UPDATE api_keys SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1 WHERE api_key = ?",
                (api_key,)
            )
            conn.commit()
        
        conn.close()
        return result is not None
        
    def _generate_api_key(self, email: str) -> str:
        """Generate a new API key."""
        api_key = f"hd_{secrets.token_urlsafe(32)}"
        
        conn = sqlite3.connect(str(self.api_keys_db))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_keys (api_key, email) VALUES (?, ?)",
            (api_key, email)
        )
        conn.commit()
        conn.close()
        
        return api_key
        
    def _log_usage(self, api_key: str, endpoint: str, ip_address: str):
        """Log API usage."""
        conn = sqlite3.connect(str(self.usage_db))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_usage (api_key, endpoint, ip_address) VALUES (?, ?, ?)",
            (api_key, endpoint, ip_address)
        )
        conn.commit()
        conn.close()
        
    def _get_sensors_list(self) -> List[Dict]:
        """Get list of all sensors."""
        # This would integrate with existing sensor data
        sensors = [
            {
                "id": "tsi_001",
                "name": "TSI AirAssure",
                "type": "PM2.5/PM10",
                "location": "Durham, NC",
                "status": "active",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "wu_001", 
                "name": "Weather Underground",
                "type": "Weather",
                "location": "Durham, NC",
                "status": "active",
                "last_updated": datetime.now().isoformat()
            }
        ]
        return sensors
        
    def _get_current_sensor_data(self, sensor_id: str) -> Optional[Dict]:
        """Get current sensor data."""
        # This would integrate with existing data collection
        if sensor_id == "tsi_001":
            return {
                "sensor_id": sensor_id,
                "timestamp": datetime.now().isoformat(),
                "pm25": 8.5,
                "pm10": 12.3,
                "temperature": 22.5,  # Always 1 decimal place
                "humidity": 65,
                "aqi": 35,
                "health_category": "Good"
            }
        elif sensor_id == "wu_001":
            return {
                "sensor_id": sensor_id,
                "timestamp": datetime.now().isoformat(),
                "temperature": 24.7,  # Always 1 decimal place
                "humidity": 68,
                "pressure": 1013.2,
                "wind_speed": 5.2,
                "wind_direction": "NW"
            }
        return None
        
    def _get_historical_sensor_data(self, sensor_id: str, start_date: str, end_date: str, limit: int) -> List[Dict]:
        """Get historical sensor data."""
        # This would integrate with existing historical data
        data = []
        now = datetime.now()
        
        for i in range(min(limit, 24)):  # Sample last 24 hours
            timestamp = now - timedelta(hours=i)
            if sensor_id == "tsi_001":
                data.append({
                    "timestamp": timestamp.isoformat(),
                    "pm25": 8.5 + (i * 0.1),
                    "pm10": 12.3 + (i * 0.2),
                    "temperature": 22.5 + (i * 0.1),
                    "humidity": 65 + i,
                    "aqi": 35 + i
                })
        
        return data
        
    def _get_air_quality_forecasts(self, hours_ahead: int) -> List[Dict]:
        """Get air quality forecasts."""
        # This would integrate with Feature 2 ML predictions
        forecasts = []
        now = datetime.now()
        
        for i in range(hours_ahead):
            forecast_time = now + timedelta(hours=i+1)
            forecasts.append({
                "timestamp": forecast_time.isoformat(),
                "pm25_forecast": 8.5 + (i * 0.05),
                "aqi_forecast": 35 + i,
                "health_category": "Good",
                "confidence": 0.85
            })
        
        return forecasts
        
    def _get_active_alerts(self) -> List[Dict]:
        """Get active alerts."""
        # This would integrate with alert system
        return [
            {
                "id": "alert_001",
                "type": "air_quality",
                "severity": "moderate",
                "message": "PM2.5 levels slightly elevated",
                "timestamp": datetime.now().isoformat(),
                "sensor_id": "tsi_001"
            }
        ]
        
    def _get_usage_stats(self, api_key: str) -> Dict:
        """Get usage statistics for API key."""
        conn = sqlite3.connect(str(self.usage_db))
        cursor = conn.cursor()
        
        # Get usage count for last 30 days
        cursor.execute('''
            SELECT COUNT(*) as total_requests,
                   COUNT(DISTINCT DATE(timestamp)) as active_days
            FROM api_usage 
            WHERE api_key = ? AND timestamp > datetime('now', '-30 days')
        ''', (api_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            "total_requests_30_days": result[0] if result else 0,
            "active_days_30_days": result[1] if result else 0,
            "rate_limit": self.config["rate_limits"]["public"]
        }
        
    def _render_api_docs(self) -> str:
        """Render API documentation."""
        docs_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Hot Durham Public API - Developer Portal</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #d73027; border-bottom: 3px solid #d73027; padding-bottom: 10px; }
        h2 { color: #2b83ba; margin-top: 30px; }
        .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #2b83ba; border-radius: 4px; }
        .method { display: inline-block; background: #28a745; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px; margin-right: 10px; }
        .method.post { background: #ffc107; color: black; }
        code { background: #e9ecef; padding: 2px 4px; border-radius: 3px; font-family: monospace; }
        .example { background: #f1f3f4; padding: 15px; border-radius: 4px; margin: 10px 0; }
        .register-form { background: #e7f3ff; padding: 20px; border-radius: 4px; margin: 20px 0; }
        input, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #d73027; color: white; border: none; cursor: pointer; }
        button:hover { background: #b71c1c; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 Hot Durham Public API</h1>
        <p><strong>Developer Portal & Documentation</strong></p>
        <p>Access real-time and historical air quality data for Durham, NC. All temperature data is formatted to 1 decimal place for consistency.</p>
        
        <div class="register-form">
            <h3>🔑 Get Your API Key</h3>
            <p>Register for free API access:</p>
            <input type="email" id="email" placeholder="your-email@example.com" style="width: 300px;">
            <button onclick="registerApiKey()">Generate API Key</button>
            <div id="api-key-result" style="margin-top: 10px;"></div>
        </div>
        
        <h2>📋 API Endpoints</h2>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/status</strong>
            <p>Check API status and version information.</p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/sensors</strong>
            <p>List all available sensors with their current status.</p>
            <p><strong>Headers:</strong> <code>X-API-Key: your_api_key</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/sensors/{sensor_id}/current</strong>
            <p>Get current readings from a specific sensor.</p>
            <p><strong>Headers:</strong> <code>X-API-Key: your_api_key</code></p>
            <div class="example">
                <strong>Example Response:</strong>
                <pre>{
  "sensor_id": "tsi_001",
  "timestamp": "2025-06-13T17:30:00",
  "pm25": 8.5,
  "temperature": 22.5,
  "humidity": 65,
  "aqi": 35,
  "health_category": "Good"
}</pre>
            </div>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/sensors/{sensor_id}/historical</strong>
            <p>Get historical data from a specific sensor.</p>
            <p><strong>Headers:</strong> <code>X-API-Key: your_api_key</code></p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>start_date</code> - Start date (YYYY-MM-DD)</li>
                <li><code>end_date</code> - End date (YYYY-MM-DD)</li>
                <li><code>limit</code> - Max records (default: 1000, max: 10000)</li>
            </ul>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/forecasts</strong>
            <p>Get air quality forecasts (powered by ML models).</p>
            <p><strong>Headers:</strong> <code>X-API-Key: your_api_key</code></p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>hours</code> - Hours ahead (default: 24, max: 48)</li>
            </ul>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/alerts</strong>
            <p>Get active air quality alerts.</p>
            <p><strong>Headers:</strong> <code>X-API-Key: your_api_key</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span>
            <strong>/api/v1/register</strong>
            <p>Register for an API key.</p>
            <p><strong>Body:</strong> <code>{"email": "your-email@example.com"}</code></p>
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span>
            <strong>/api/v1/usage</strong>
            <p>Get your API usage statistics.</p>
            <p><strong>Headers:</strong> <code>X-API-Key: your_api_key</code></p>
        </div>
        
        <h2>🔒 Rate Limits</h2>
        <ul>
            <li><strong>Public Tier:</strong> 1,000 requests per hour</li>
            <li><strong>Developer Tier:</strong> 5,000 requests per hour</li>
            <li><strong>Premium Tier:</strong> 10,000 requests per hour</li>
        </ul>
        
        <h2>💡 Example Usage</h2>
        <div class="example">
            <strong>JavaScript:</strong>
            <pre>
fetch('/api/v1/sensors/tsi_001/current', {
  headers: {
    'X-API-Key': 'your_api_key_here'
  }
})
.then(response => response.json())
.then(data => {
  console.log(`Temperature: ${data.temperature}°C`);
  console.log(`PM2.5: ${data.pm25} μg/m³`);
});
            </pre>
        </div>
        
        <div class="example">
            <strong>Python:</strong>
            <pre>
import requests

headers = {'X-API-Key': 'your_api_key_here'}
response = requests.get('/api/v1/sensors/tsi_001/current', headers=headers)
data = response.json()

print(f"Temperature: {data['temperature']}°C")
print(f"PM2.5: {data['pm25']} μg/m³")
            </pre>
        </div>
        
        <div class="footer">
            <p><strong>Hot Durham Public API</strong> | Version 1.0 | Contact: admin@hotdurham.com</p>
            <p>🌱 Supporting environmental awareness in Durham, NC</p>
        </div>
    </div>
    
    <script>
        async function registerApiKey() {
            const email = document.getElementById('email').value;
            if (!email) {
                alert('Please enter your email address');
                return;
            }
            
            try {
                const response = await fetch('/api/v1/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({email: email})
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('api-key-result').innerHTML = 
                        `<div style="background: #d4edda; color: #155724; padding: 10px; border-radius: 4px;">
                            <strong>Success!</strong> Your API Key: <code>${data.api_key}</code><br>
                            <small>Save this key - you'll need it for API requests.</small>
                        </div>`;
                } else {
                    document.getElementById('api-key-result').innerHTML = 
                        `<div style="background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px;">
                            <strong>Error:</strong> ${data.error}
                        </div>`;
                }
            } catch (error) {
                document.getElementById('api-key-result').innerHTML = 
                    `<div style="background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px;">
                        <strong>Error:</strong> Failed to register API key
                    </div>`;
            }
        }
    </script>
</body>
</html>
        """
        return docs_html
        
    def run_server(self, host: str = '0.0.0.0', port: int = 5002, debug: bool = False):
        """Run the API server."""
        print(f"🚀 Starting Hot Durham Public API server on http://{host}:{port}")
        print(f"📖 API Documentation: http://{host}:{port}/")
        self.app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    api = PublicAPI()
    api.run_server(debug=True)
