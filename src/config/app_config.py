import os
import json
import sys
import logging
from google.cloud import secretmanager
from dotenv import load_dotenv

# Import to configure logging for the entire application
import src.utils.logging_setup

# Load environment variables from .env file for local development
load_dotenv()

class Config:
    """
    A centralized configuration class for the application.
    Handles loading secrets and environment variables.
    """
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID")
        self.db_creds_secret_id = os.getenv("DB_CREDS_SECRET_ID")
        self.tsi_creds_secret_id = os.getenv("TSI_CREDS_SECRET_ID")
        self.wu_api_key_secret_id = os.getenv("WU_API_KEY_SECRET_ID")

        self._validate_env_vars()
        
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Load secrets
        self.db_creds = self._get_json_secret(self.db_creds_secret_id)
        self.tsi_creds = self._get_json_secret(self.tsi_creds_secret_id)
        self.wu_api_key = self._get_json_secret(self.wu_api_key_secret_id)

        self._validate_secrets()

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
            "TSI_CREDS_SECRET_ID", "WU_API_KEY_SECRET_ID"
        ]
        missing_vars = [var for var in required_vars if not getattr(self, var.lower())]
        if missing_vars:
            logging.critical(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)

    def _get_json_secret(self, secret_id):
        """Fetches and decodes a JSON secret from Google Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
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
