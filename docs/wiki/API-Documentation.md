# API Documentation

The Hot Durham Environmental Monitoring System provides a comprehensive REST API for accessing environmental data, managing sensors, and integrating with external systems.

## Base URL

```plaintext
Production: https://api.hotdurham.org/v1
Development: http://localhost:8080/api/v1
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Include your token in the Authorization header:

```http
Authorization: Bearer your_jwt_token_here
```

### Getting an API Token

```bash
# Request a token
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Rate Limiting

- **Standard Users**: 100 requests per minute
- **Premium Users**: 1000 requests per minute
- **Admin Users**: No limits

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## API Endpoints

### Health Check

Check if the API is operational.

```http
GET /api/v1/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-06-15T10:30:00Z",
  "database": "connected",
  "external_apis": {
    "weather_underground": "operational",
    "google_sheets": "operational"
  }
}
```

### Sensors

#### List All Sensors

```http
GET /api/v1/sensors
```

**Query Parameters:**

- `type` (optional): Filter by sensor type (`temperature`, `humidity`, `pressure`)
- `status` (optional): Filter by status (`active`, `inactive`, `maintenance`)
- `limit` (optional): Number of results (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response:**

```json
{
  "sensors": [
    {
      "id": "sensor_001",
      "name": "Downtown Temperature",
      "type": "temperature",
      "location": {
        "latitude": 35.9940,
        "longitude": -78.8986,
        "address": "Downtown Durham, NC"
      },
      "status": "active",
      "last_reading": "2025-06-15T10:25:00Z",
      "metadata": {
        "installation_date": "2024-01-15",
        "model": "TSI-4000",
        "accuracy": "±0.1°C"
      }
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

#### Get Sensor Details

```http
GET /api/v1/sensors/{sensor_id}
```

**Response:**

```json
{
  "id": "sensor_001",
  "name": "Downtown Temperature",
  "type": "temperature",
  "location": {
    "latitude": 35.9940,
    "longitude": -78.8986,
    "address": "Downtown Durham, NC"
  },
  "status": "active",
  "configuration": {
    "sampling_rate": 300,
    "units": "celsius",
    "precision": 2
  },
  "calibration": {
    "last_calibrated": "2025-05-01T09:00:00Z",
    "next_calibration": "2025-08-01T09:00:00Z",
    "offset": 0.0,
    "scale": 1.0
  },
  "statistics": {
    "total_readings": 15420,
    "uptime_percentage": 99.7,
    "average_daily_readings": 288
  }
}
```

### Data Retrieval

#### Get Latest Readings

```http
GET /api/v1/data/latest
```

**Query Parameters:**

- `sensors` (optional): Comma-separated sensor IDs
- `types` (optional): Comma-separated data types

**Response:**

```json
{
  "readings": [
    {
      "sensor_id": "sensor_001",
      "timestamp": "2025-06-15T10:25:00Z",
      "value": 24.5,
      "unit": "celsius",
      "quality": "good",
      "flags": []
    },
    {
      "sensor_id": "sensor_002",
      "timestamp": "2025-06-15T10:25:00Z",
      "value": 65.2,
      "unit": "percent",
      "quality": "good",
      "flags": []
    }
  ],
  "timestamp": "2025-06-15T10:25:30Z"
}
```

#### Get Historical Data

```http
GET /api/v1/data/historical
```

**Query Parameters:**

- `sensors` (required): Comma-separated sensor IDs
- `start_time` (required): ISO 8601 timestamp
- `end_time` (required): ISO 8601 timestamp
- `interval` (optional): Aggregation interval (`1m`, `5m`, `1h`, `1d`)
- `aggregation` (optional): Aggregation function (`avg`, `min`, `max`, `sum`)

**Example:**

```http
GET /api/v1/data/historical?sensors=sensor_001,sensor_002&start_time=2025-06-14T00:00:00Z&end_time=2025-06-15T00:00:00Z&interval=1h&aggregation=avg
```

**Response:**

```json
{
  "data": [
    {
      "sensor_id": "sensor_001",
      "readings": [
        {
          "timestamp": "2025-06-14T00:00:00Z",
          "value": 22.1,
          "count": 12,
          "quality": "good"
        },
        {
          "timestamp": "2025-06-14T01:00:00Z",
          "value": 21.8,
          "count": 12,
          "quality": "good"
        }
      ]
    }
  ],
  "metadata": {
    "total_points": 576,
    "interval": "1h",
    "aggregation": "avg",
    "time_range": {
      "start": "2025-06-14T00:00:00Z",
      "end": "2025-06-15T00:00:00Z"
    }
  }
}
```

### Data Export

#### Export Data

```http
POST /api/v1/data/export
```

**Request Body:**

```json
{
  "sensors": ["sensor_001", "sensor_002"],
  "start_time": "2025-06-14T00:00:00Z",
  "end_time": "2025-06-15T00:00:00Z",
  "format": "csv",
  "options": {
    "include_metadata": true,
    "timezone": "America/New_York"
  }
}
```

**Response:**

```json
{
  "export_id": "export_12345",
  "status": "processing",
  "estimated_completion": "2025-06-15T10:32:00Z",
  "download_url": null
}
```

#### Check Export Status

```http
GET /api/v1/data/export/{export_id}
```

**Response:**

```json
{
  "export_id": "export_12345",
  "status": "completed",
  "created_at": "2025-06-15T10:30:00Z",
  "completed_at": "2025-06-15T10:31:45Z",
  "download_url": "https://api.hotdurham.org/v1/data/download/export_12345",
  "expires_at": "2025-06-16T10:31:45Z",
  "file_size": 2048576
}
```

### Statistics and Analytics

#### Get Sensor Statistics

```http
GET /api/v1/sensors/{sensor_id}/stats
```

**Query Parameters:**

- `period` (optional): Time period (`24h`, `7d`, `30d`, `1y`)

**Response:**

```json
{
  "sensor_id": "sensor_001",
  "period": "24h",
  "statistics": {
    "count": 288,
    "min": 18.2,
    "max": 28.7,
    "mean": 23.4,
    "median": 23.2,
    "std_dev": 2.1,
    "percentiles": {
      "p25": 21.8,
      "p75": 25.1,
      "p95": 27.2
    }
  },
  "trends": {
    "direction": "stable",
    "change_rate": 0.02,
    "correlation": 0.85
  }
}
```

#### Get System Analytics

```http
GET /api/v1/analytics/summary
```

**Response:**

```json
{
  "overview": {
    "total_sensors": 42,
    "active_sensors": 40,
    "total_readings_today": 12096,
    "data_quality_score": 98.5
  },
  "performance": {
    "api_response_time_avg": 145,
    "data_collection_success_rate": 99.2,
    "uptime_percentage": 99.8
  },
  "alerts": {
    "active_alerts": 2,
    "resolved_today": 5,
    "pending_maintenance": 1
  }
}
```

### Configuration Management

#### Update Sensor Configuration

```http
PUT /api/v1/sensors/{sensor_id}/config
```

**Request Body:**

```json
{
  "sampling_rate": 300,
  "alert_thresholds": {
    "min": 0.0,
    "max": 40.0
  },
  "calibration": {
    "offset": 0.1,
    "scale": 1.0
  }
}
```

**Response:**

```json
{
  "sensor_id": "sensor_001",
  "configuration": {
    "sampling_rate": 300,
    "alert_thresholds": {
      "min": 0.0,
      "max": 40.0
    },
    "calibration": {
      "offset": 0.1,
      "scale": 1.0
    }
  },
  "updated_at": "2025-06-15T10:35:00Z"
}
```

## Error Handling

The API uses standard HTTP status codes and provides detailed error messages:

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_SENSOR_ID",
    "message": "Sensor with ID 'invalid_sensor' not found",
    "details": {
      "requested_id": "invalid_sensor",
      "available_sensors": ["sensor_001", "sensor_002"]
    },
    "timestamp": "2025-06-15T10:30:00Z",
    "request_id": "req_12345"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request or invalid parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

## Code Examples

### Python Example

```python
import requests
import json

# Authentication
auth_response = requests.post(
    'http://localhost:8080/api/v1/auth/login',
    json={'username': 'user', 'password': 'pass'}
)
token = auth_response.json()['access_token']

# Headers for authenticated requests
headers = {'Authorization': f'Bearer {token}'}

# Get latest sensor data
response = requests.get(
    'http://localhost:8080/api/v1/data/latest',
    headers=headers,
    params={'sensors': 'sensor_001,sensor_002'}
)

if response.status_code == 200:
    data = response.json()
    for reading in data['readings']:
        print(f"Sensor {reading['sensor_id']}: {reading['value']} {reading['unit']}")
```

### JavaScript Example

```javascript
// Authentication
const authResponse = await fetch('http://localhost:8080/api/v1/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'user', password: 'pass'})
});
const {access_token} = await authResponse.json();

// Get sensor list
const sensorsResponse = await fetch('http://localhost:8080/api/v1/sensors', {
  headers: {'Authorization': `Bearer ${access_token}`}
});
const sensors = await sensorsResponse.json();

console.log(`Found ${sensors.total} sensors`);
```

### curl Examples

```bash
# Get API health
curl http://localhost:8080/api/v1/health

# Get latest readings (authenticated)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/v1/data/latest

# Export data
curl -X POST http://localhost:8080/api/v1/data/export \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"sensors": ["sensor_001"], "start_time": "2025-06-14T00:00:00Z", "end_time": "2025-06-15T00:00:00Z", "format": "csv"}'
```

## API Versioning

The API uses semantic versioning with the version specified in the URL path:

- `/api/v1/` - Current stable version
- `/api/v2/` - Next major version (in development)

### Deprecation Policy

- Minor versions are backward compatible
- Major versions may introduce breaking changes
- Deprecated endpoints receive 6 months notice
- Legacy versions supported for 1 year after deprecation

## SDK and Libraries

### Official SDKs

- **Python**: `pip install hotdurham-sdk`
- **JavaScript**: `npm install hotdurham-client`
- **R**: `install.packages("hotdurham")`

### Community Libraries

- **Go**: `github.com/community/hotdurham-go`
- **PHP**: `composer require community/hotdurham-php`

---

*For additional API support, see the [FAQ](FAQ.md) or contact the development team.*
