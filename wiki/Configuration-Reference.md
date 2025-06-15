# Configuration Reference

This document provides a comprehensive reference for all configuration options in the Hot Durham Environmental Monitoring System.

## Configuration Files

### 1. Environment Variables (`.env`)

The primary configuration method using environment variables.

```env
# =============================================================================
# Hot Durham Environmental Monitoring System Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
DEBUG=True                          # Enable debug mode (True/False)
LOG_LEVEL=INFO                      # Logging level (DEBUG/INFO/WARNING/ERROR)
PORT=8080                          # Server port number
HOST=localhost                     # Server host address
ENVIRONMENT=development            # Environment (development/staging/production)

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------
DATABASE_URL=sqlite:///data/hot_durham.db  # Database connection string
DATABASE_POOL_SIZE=5                       # Connection pool size
DATABASE_TIMEOUT=30                        # Query timeout in seconds
DATABASE_ECHO=False                        # Echo SQL queries (True/False)

# Production MySQL example:
# DATABASE_URL=mysql+pymysql://user:password@localhost/hotdurham

# -----------------------------------------------------------------------------
# API Keys and External Services
# -----------------------------------------------------------------------------
WEATHER_UNDERGROUND_API_KEY=your_wu_key_here    # Weather Underground API key
GOOGLE_SHEETS_CREDENTIALS_PATH=creds/service_account.json  # Google creds file

# Optional API keys
OPENWEATHER_API_KEY=your_openweather_key        # OpenWeather API (backup)
TSI_API_ENDPOINT=https://tsi.example.com/api    # TSI sensor endpoint
TSI_API_KEY=your_tsi_key                        # TSI API key

# -----------------------------------------------------------------------------
# Data Collection Settings
# -----------------------------------------------------------------------------
DATA_COLLECTION_INTERVAL=300       # Collection interval in seconds (5 minutes)
MAX_RETRIES=3                      # Maximum retry attempts for failed requests
REQUEST_TIMEOUT=30                 # HTTP request timeout in seconds
BATCH_SIZE=100                     # Batch size for bulk operations
RATE_LIMIT_REQUESTS=100            # API requests per minute limit
RATE_LIMIT_WINDOW=60               # Rate limit window in seconds

# -----------------------------------------------------------------------------
# Data Processing
# -----------------------------------------------------------------------------
DATA_VALIDATION_ENABLED=True       # Enable data validation (True/False)
ANOMALY_DETECTION_ENABLED=True     # Enable anomaly detection (True/False)
ML_MODEL_PATH=models/anomaly_detection.pkl  # ML model file path
DATA_RETENTION_DAYS=365            # Data retention period in days
AGGREGATION_INTERVALS=1h,6h,1d     # Comma-separated aggregation intervals

# -----------------------------------------------------------------------------
# Caching
# -----------------------------------------------------------------------------
CACHE_ENABLED=True                 # Enable caching (True/False)
CACHE_TYPE=memory                  # Cache type (memory/redis/file)
CACHE_TTL=300                      # Cache time-to-live in seconds
CACHE_MAX_SIZE=1000                # Maximum cache entries

# Redis cache (if using CACHE_TYPE=redis)
# REDIS_URL=redis://localhost:6379/0
# REDIS_PASSWORD=your_redis_password

# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
SECRET_KEY=your-super-secret-key-change-this    # JWT secret key
JWT_EXPIRATION_HOURS=24                         # JWT token expiration
ALLOWED_HOSTS=localhost,127.0.0.1,*.hotdurham.org  # Allowed hostnames
CORS_ORIGINS=http://localhost:3000,https://hotdurham.org  # CORS origins

# -----------------------------------------------------------------------------
# Monitoring and Alerts
# -----------------------------------------------------------------------------
MONITORING_ENABLED=True            # Enable system monitoring (True/False)
HEALTH_CHECK_INTERVAL=60           # Health check interval in seconds
ALERT_EMAIL_ENABLED=False          # Enable email alerts (True/False)
ALERT_EMAIL_SMTP_SERVER=smtp.gmail.com  # SMTP server
ALERT_EMAIL_SMTP_PORT=587          # SMTP port
ALERT_EMAIL_USERNAME=alerts@hotdurham.org    # SMTP username
ALERT_EMAIL_PASSWORD=your_email_password     # SMTP password
ALERT_EMAIL_TO=admin@hotdurham.org           # Alert recipient email

# -----------------------------------------------------------------------------
# File Storage
# -----------------------------------------------------------------------------
UPLOAD_FOLDER=uploads              # Upload directory
MAX_FILE_SIZE=10485760            # Max file size in bytes (10MB)
ALLOWED_EXTENSIONS=csv,json,xlsx  # Allowed file extensions
BACKUP_FOLDER=backups             # Backup directory
EXPORT_FOLDER=exports             # Export directory

# -----------------------------------------------------------------------------
# Google Sheets Integration
# -----------------------------------------------------------------------------
GOOGLE_SHEETS_ENABLED=True         # Enable Google Sheets integration
GOOGLE_SHEETS_FOLDER_ID=your_folder_id      # Google Drive folder ID
GOOGLE_SHEETS_TEMPLATE_ID=your_template_id  # Sheet template ID
GOOGLE_SHEETS_BATCH_SIZE=1000      # Batch size for sheet operations

# -----------------------------------------------------------------------------
# Weather Underground Settings
# -----------------------------------------------------------------------------
WU_BASE_URL=https://api.weather.com/v1     # Weather Underground base URL
WU_STATIONS=KNCRTP12,KNCDURHM5             # Comma-separated station IDs
WU_REQUEST_DELAY=1                          # Delay between requests (seconds)
WU_RETRY_DELAY=5                           # Retry delay (seconds)

# -----------------------------------------------------------------------------
# TSI Sensor Settings
# -----------------------------------------------------------------------------
TSI_ENABLED=True                   # Enable TSI sensor integration
TSI_POLL_INTERVAL=300              # TSI polling interval (seconds)
TSI_SENSOR_IDS=TSI001,TSI002,TSI003  # Comma-separated sensor IDs
TSI_TIMEOUT=15                     # TSI request timeout (seconds)

# -----------------------------------------------------------------------------
# Development and Testing
# -----------------------------------------------------------------------------
TESTING=False                      # Testing mode (True/False)
MOCK_EXTERNAL_APIS=False          # Mock external APIs for testing
SAMPLE_DATA_ENABLED=True          # Include sample data (True/False)
DEV_TOOLBAR_ENABLED=True          # Enable development toolbar
PROFILING_ENABLED=False           # Enable performance profiling
```

### 2. Application Configuration (`config/config.yaml`)

YAML-based configuration for complex settings.

```yaml
# Application Configuration
app:
  name: "Hot Durham Environmental Monitoring"
  version: "2.0.0"
  description: "Environmental monitoring and analysis system for Durham, NC"
  timezone: "America/New_York"
  
database:
  # Connection settings
  pool_size: 5
  pool_timeout: 30
  pool_recycle: 3600
  echo: false
  
  # Migration settings
  auto_migrate: true
  migration_path: "migrations/"
  
data_collection:
  # Collection schedules
  schedules:
    weather_underground:
      interval: 300  # 5 minutes
      enabled: true
      priority: high
    
    tsi_sensors:
      interval: 60   # 1 minute
      enabled: true
      priority: high
    
    google_sheets:
      interval: 900  # 15 minutes
      enabled: true
      priority: medium
  
  # Data validation rules
  validation:
    temperature:
      min: -40.0
      max: 60.0
      unit: "celsius"
    
    humidity:
      min: 0.0
      max: 100.0
      unit: "percent"
    
    pressure:
      min: 800.0
      max: 1100.0
      unit: "hPa"

monitoring:
  # Health check configuration
  health_checks:
    database:
      enabled: true
      timeout: 5
      interval: 60
    
    external_apis:
      enabled: true
      timeout: 10
      interval: 300
    
    disk_space:
      enabled: true
      threshold: 90  # percentage
      interval: 600
  
  # Performance monitoring
  performance:
    track_response_times: true
    track_memory_usage: true
    track_cpu_usage: true
    sample_rate: 0.1  # 10% sampling

alerts:
  # Alert thresholds
  thresholds:
    temperature_high: 35.0
    temperature_low: -10.0
    humidity_high: 95.0
    humidity_low: 10.0
    data_age_minutes: 30
  
  # Notification channels
  channels:
    email:
      enabled: false
      template: "alert_email.html"
    
    webhook:
      enabled: false
      url: "https://hooks.slack.com/your-webhook"
    
    log:
      enabled: true
      level: "WARNING"

export:
  # Export formats
  formats:
    csv:
      enabled: true
      delimiter: ","
      include_headers: true
    
    json:
      enabled: true
      indent: 2
      include_metadata: true
    
    pdf:
      enabled: true
      template: "report_template.html"
      page_size: "A4"
  
  # File retention
  retention:
    temp_files_hours: 24
    export_files_days: 7
    backup_files_days: 30
```

### 3. Logging Configuration (`config/logging.yaml`)

```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  
  json:
    class: 'pythonjsonlogger.jsonlogger.JsonFormatter'
    format: '%(asctime)s %(name)s %(levelname)s %(module)s %(lineno)d %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/application.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
  
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: detailed
    filename: logs/errors.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  src:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  src.data_collection:
    level: INFO
    handlers: [console, file]
    propagate: false
  
  src.api:
    level: INFO
    handlers: [console, file]
    propagate: false
  
  urllib3:
    level: WARNING
    handlers: [console]
    propagate: false

root:
  level: INFO
  handlers: [console, file, error_file]
```

## Configuration Management

### Environment-Specific Configurations

#### Development (`config/environments/development.py`)

```python
import os

# Development-specific settings
DEBUG = True
TESTING = False

# Database
DATABASE_URL = "sqlite:///data/hot_durham_dev.db"

# External APIs
MOCK_EXTERNAL_APIS = True
SAMPLE_DATA_ENABLED = True

# Caching
CACHE_TYPE = "memory"
CACHE_TTL = 60  # Short TTL for development

# Security (relaxed for development)
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Monitoring
MONITORING_ENABLED = False
ALERT_EMAIL_ENABLED = False
```

#### Production (`config/environments/production.py`)

```python
import os

# Production settings
DEBUG = False
TESTING = False

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://user:pass@localhost/hotdurham")
DATABASE_POOL_SIZE = 20

# Security
SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Caching
CACHE_TYPE = "redis"
CACHE_TTL = 3600

# Monitoring
MONITORING_ENABLED = True
ALERT_EMAIL_ENABLED = True

# Performance
REQUEST_TIMEOUT = 10  # Shorter timeout for production
MAX_RETRIES = 5  # More retries for production
```

### Dynamic Configuration

#### Feature Flags (`config/features.json`)

```json
{
  "features": {
    "google_sheets_integration": {
      "enabled": true,
      "description": "Google Sheets data sync",
      "rollout_percentage": 100
    },
    "ml_anomaly_detection": {
      "enabled": true,
      "description": "Machine learning anomaly detection",
      "rollout_percentage": 50
    },
    "real_time_alerts": {
      "enabled": false,
      "description": "Real-time alert notifications",
      "rollout_percentage": 0
    },
    "advanced_analytics": {
      "enabled": true,
      "description": "Advanced data analytics features",
      "rollout_percentage": 100
    }
  }
}
```

## Configuration Validation

### Schema Validation

The system validates configuration using JSON Schema:

```python
# config/schema.py
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "database": {
            "type": "object",
            "properties": {
                "pool_size": {"type": "integer", "minimum": 1, "maximum": 100},
                "timeout": {"type": "integer", "minimum": 1}
            },
            "required": ["pool_size"]
        },
        "data_collection": {
            "type": "object",
            "properties": {
                "interval": {"type": "integer", "minimum": 60},
                "max_retries": {"type": "integer", "minimum": 1, "maximum": 10}
            }
        }
    },
    "required": ["database", "data_collection"]
}
```

### Configuration Loading Priority

1. **Command line arguments** (highest priority)
2. **Environment variables**
3. **Configuration files** (`.env`, `config.yaml`)
4. **Default values** (lowest priority)

### Example: Loading Configuration

```python
from src.config import ConfigManager

# Initialize configuration manager
config = ConfigManager()

# Load configuration with priority order
config.load_from_file('config/config.yaml')
config.load_from_env()
config.load_from_args(sys.argv)

# Access configuration values
database_url = config.get('database.url')
api_key = config.get('api.weather_underground.key')
debug_mode = config.get('app.debug', default=False)
```

## Configuration Best Practices

### 1. Security

- ✅ **Never commit sensitive data** to version control
- ✅ **Use environment variables** for secrets
- ✅ **Rotate API keys regularly**
- ✅ **Use strong secret keys** for JWT tokens

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Environment Separation

- ✅ **Separate configs** for development/staging/production
- ✅ **Use different databases** for each environment
- ✅ **Mock external APIs** in development
- ✅ **Enable monitoring** only in production

### 3. Documentation

- ✅ **Document all configuration options**
- ✅ **Provide example values**
- ✅ **Explain impacts** of configuration changes
- ✅ **Keep documentation updated**

### 4. Validation

- ✅ **Validate configuration** on startup
- ✅ **Provide clear error messages**
- ✅ **Use type hints** and schemas
- ✅ **Test configuration changes**

## Troubleshooting Configuration

### Common Issues

#### Invalid Database URL
```bash
# Check database connectivity
python scripts/test_database.py

# Reset database
rm data/hot_durham.db
python scripts/init_database.py
```

#### Missing API Keys
```bash
# Validate API keys
python scripts/validate_api_keys.py

# Test individual APIs
python scripts/test_wu_connection.py
python scripts/test_google_sheets.py
```

#### Configuration Loading Errors
```bash
# Validate configuration syntax
python scripts/validate_config.py

# Check environment variables
python scripts/check_env.py
```

### Debugging Configuration

```python
# Debug configuration loading
from src.config import ConfigManager

config = ConfigManager(debug=True)
config.load_all()

# Print loaded configuration (sanitized)
config.print_config(hide_secrets=True)

# Validate configuration
errors = config.validate()
if errors:
    print("Configuration errors:", errors)
```

---

*This configuration reference is maintained with the system. Last updated: June 15, 2025*
