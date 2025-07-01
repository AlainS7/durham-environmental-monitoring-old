# Production environment
DEBUG = False
LOG_LEVEL = "INFO"
API_RATE_LIMIT = 0.5  # requests per second

# Data sources
TSI_API_ENABLED = True
WU_API_ENABLED = True
GOOGLE_SHEETS_ENABLED = True

# Storage
USE_DATABASE = True

BACKUP_ENABLED = True

# Test sensors
INCLUDE_TEST_SENSORS_IN_LOGS = False
