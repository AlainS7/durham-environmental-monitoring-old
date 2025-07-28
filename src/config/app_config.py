import os
import json
import sys
import logging
from google.cloud import secretmanager
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

class Config:
    """
    A centralized configuration class for the application.
    Handles loading secrets and environment variables.
    """
    # temporary
    def _parse_env_var_value(self, env_var_name):
        value = os.getenv(env_var_name)
        if value is None:
            return None
        # Check if it's in KEY=VALUE format and extract VALUE
        if '=' in value and value.startswith(env_var_name + '='):
            return value.split('=', 1)[1].strip()
        return value.strip() # Just strip if not in KEY=VALUE format

    def __init__(self):
        self.project_id = self._parse_env_var_value("PROJECT_ID")
        self.db_creds_secret_id = self._parse_env_var_value("DB_CREDS_SECRET_ID")
        self.tsi_creds_secret_id = self._parse_env_var_value("TSI_CREDS_SECRET_ID")
        self.wu_api_key_secret_id = self._parse_env_var_value("WU_API_KEY_SECRET_ID")

        self._validate_env_vars()
        
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Load secrets
        self.db_creds = self._get_json_secret(self.db_creds_secret_id)
        self.tsi_creds = self._get_json_secret(self.tsi_creds_secret_id)
        self.wu_api_key = self._get_json_secret(self.wu_api_key_secret_id)

        self._validate_secrets()

        # API configurations
        self.wu_api_config = {
            "base_url": "https://api.weather.com/v2/pws",
            "api_key": self.wu_api_key.get("test_api_key")
        }
        self.tsi_api_config = {
            "base_url": "https://api-prd.tsilink.com/api/v3/external",
            "auth_url": "https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken",
            "client_id": self.tsi_creds.get("key"),
            "client_secret": self.tsi_creds.get("secret")
        }

        # Define paths to sensor configuration files
        self.sensor_config_paths = {
            'production': os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'environments', 'production.json'),
            'test': os.path.join(os.path.dirname(__file__), '..', '..', 'test_data', 'test_sensors.json')
        }

        # Database URL
        self.database_url = self._build_database_url()

    def _validate_env_vars(self):
        """Ensure all required environment variables are set."""
        required_vars = [
            "PROJECT_ID", "DB_CREDS_SECRET_ID", 
            "WU_API_KEY_SECRET_ID"
        ]
        missing_vars = [var for var in required_vars if not getattr(self, var.lower())]
        if missing_vars:
            logging.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

    def _get_json_secret(self, secret_id):
        """Fetches and decodes a JSON secret from Google Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id.strip()}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            return json.loads(payload)
        except Exception as e:
            logging.critical(f"Fatal: Could not access or parse secret '{secret_id}'. Error: {e}")
            sys.exit(1)

    def _validate_secrets(self):
        """Validate the contents of the fetched secrets."""
        db_keys = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
        if not all(key in self.db_creds for key in db_keys):
            logging.critical("Database credentials secret is missing one or more required keys.")
            sys.exit(1)
            
        if "key" not in self.tsi_creds or "secret" not in self.tsi_creds:
            logging.critical("TSI credentials secret is missing 'key' or 'secret'.")
            sys.exit(1)

        if "test_api_key" not in self.wu_api_key:
            logging.critical("Weather Underground API key secret is missing 'test_api_key'.")
            sys.exit(1)

    def _build_database_url(self):
        """Constructs the database connection string."""
        return (
            f"postgresql://{self.db_creds['DB_USER']}:{self.db_creds['DB_PASSWORD']}"
            f"@{self.db_creds['DB_HOST']}:{self.db_creds['DB_PORT']}"
            f"/{self.db_creds['DB_NAME']}"
        )

# A single, global instance of the configuration
try:
    app_config = Config()
except Exception as e:
    logging.critical(f"Failed to initialize configuration: {e}", exc_info=True)
    sys.exit(1)
