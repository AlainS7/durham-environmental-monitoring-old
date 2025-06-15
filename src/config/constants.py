"""
Configuration constants for Hot Durham project
"""

# API Configuration
DEFAULT_RATE_LIMIT = 0.5  # requests per second
API_TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3

# Data Validation Limits
PM25_MIN = 0.0
PM25_MAX = 1000.0
TEMP_MIN = -50.0
TEMP_MAX = 60.0
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0

# File Paths
DEFAULT_DB_PATH = "data/hot_durham.db"
LOG_DIR = "logs"
DATA_DIR = "data"

# Google Sheets Configuration
SHEETS_MAX_ROWS = 1000000
SHEETS_BATCH_SIZE = 1000

# Data Collection
MAX_DAYS_BACK = 90  # TSI API limitation
DEFAULT_COLLECTION_HOURS = 24

# Alert Thresholds
PM25_UNHEALTHY_THRESHOLD = 55.5  # μg/m³
TEMP_EXTREME_LOW = -20.0  # °C
TEMP_EXTREME_HIGH = 45.0  # °C

# Test Sensor Configuration
TEST_SENSOR_PREFIXES = ['AA-', 'TEST-', 'DEBUG-']
PRODUCTION_SENSOR_PREFIXES = ['BS-', 'PROD-']
