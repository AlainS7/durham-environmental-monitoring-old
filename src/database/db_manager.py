"""
Database integration for Hot Durham project
"""
import pandas as pd
import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Optional
import logging

log = logging.getLogger(__name__)

class HotDurhamDB:
    """Database manager for PostgreSQL on Google Cloud SQL"""

    def __init__(self):
        """Initializes the database connection and schema."""
        self.engine = self._create_db_engine()
        self._init_database()

    def _create_db_engine(self) -> Engine:
        """Creates and returns a SQLAlchemy engine from environment variables."""
        
        def _get_env_var(var_name: str, default: Optional[str] = None) -> Optional[str]:
            """Helper function to get and clean environment variables."""
            value = os.environ.get(var_name, default)
            if value and f"{var_name}=" in value:
                log.warning(f"Fixing malformed environment variable: {var_name}")
                return value.split("=", 1)[-1]
            return value

        db_user = _get_env_var("DB_USER", "postgres")
        db_pass = _get_env_var("DB_PASS")
        db_host = _get_env_var("DB_HOST", "127.0.0.1")
        db_port = _get_env_var("DB_PORT", "5432")
        db_name = _get_env_var("DB_NAME", "postgres")

        if not db_pass:
            log.error("CRITICAL: Environment variable DB_PASS is not set.")
            raise ValueError("Environment variable DB_PASS must be set for database connection.")

        conn_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        return create_engine(conn_string)

    def _init_database(self):
        """
        Initializes all required database tables if they don't already exist.
        This includes the main sensor data schema and logging tables.
        """
        with self.engine.connect() as connection:
            with connection.begin():
                # Main application schema
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS sensors_master (
                        sensor_pk SERIAL PRIMARY KEY,
                        native_sensor_id VARCHAR(255) NOT NULL,
                        sensor_type VARCHAR(50) NOT NULL,
                        friendly_name VARCHAR(255),
                        CONSTRAINT uq_native_sensor_id_type UNIQUE (native_sensor_id, sensor_type)
                    );
                """))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS deployments (
                        deployment_pk SERIAL PRIMARY KEY,
                        sensor_fk INTEGER NOT NULL REFERENCES sensors_master(sensor_pk) ON DELETE CASCADE,
                        location VARCHAR(255) NOT NULL,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        status VARCHAR(50) NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE
                    );
                """))
                connection.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_deployment_per_sensor
                    ON deployments (sensor_fk, (COALESCE(end_date, '9999-12-31')));
                """))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS sensor_readings (
                        "timestamp" TIMESTAMPTZ NOT NULL,
                        deployment_fk INTEGER NOT NULL REFERENCES deployments(deployment_pk) ON DELETE CASCADE,
                        metric_name VARCHAR(100) NOT NULL,
                        value DOUBLE PRECISION,
                        PRIMARY KEY ("timestamp", deployment_fk, metric_name)
                    );
                """))
                connection.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_sensor_readings_deployment_timestamp 
                    ON sensor_readings(deployment_fk, "timestamp" DESC);
                """))

                # Logging and metadata tables
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS collection_log (
                        log_id SERIAL PRIMARY KEY,
                        collection_date TIMESTAMPTZ DEFAULT NOW(),
                        source VARCHAR(50),
                        records_collected INTEGER,
                        errors_count INTEGER,
                        duration_seconds REAL
                    );
                """))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS collection_metadata (
                        metadata_id SERIAL PRIMARY KEY,
                        collection_time TIMESTAMPTZ DEFAULT NOW(),
                        collection_type VARCHAR(100),
                        metadata_json JSONB
                    );
                """))
    
    # --- NEW RECOMMENDED ---
    def insert_sensor_readings(self, df: pd.DataFrame):
        """
        Inserts a DataFrame of sensor data into the normalized sensor_readings table.
        
        The DataFrame is expected to have the following columns:
        - timestamp
        - deployment_fk
        - metric_name
        - value
        """
        if not all(col in df.columns for col in ['timestamp', 'deployment_fk', 'metric_name', 'value']):
            raise ValueError("DataFrame must contain 'timestamp', 'deployment_fk', 'metric_name', and 'value' columns.")
        
        df.to_sql('sensor_readings', self.engine, if_exists='append', index=False, chunksize=1000)
        log.info(f"Successfully inserted {len(df)} records into sensor_readings.")

    # --- LEGACY METHODS (To be deprecated) ---
    def insert_tsi_data(self, df: pd.DataFrame):
        """DEPRECATED: Insert TSI data into the old 'tsi_data' table."""
        log.warning("Using deprecated method 'insert_tsi_data'. Please migrate to 'insert_sensor_readings'.")
        # df.to_sql('tsi_data', self.engine, if_exists='append', index=False)
    
    def insert_wu_data(self, df: pd.DataFrame):
        """DEPRECATED: Insert WU data into the old 'wu_data' table."""
        log.warning("Using deprecated method 'insert_wu_data'. Please migrate to 'insert_sensor_readings'.")
        # df.to_sql('wu_data', self.engine, if_exists='append', index=False)
    
    def get_latest_readings(self, hours: int = 24) -> pd.DataFrame:
        """Gets the latest data from the sensor_readings table for all deployments."""
        query = text("""
            SELECT s.friendly_name, d.location, r.timestamp, r.metric_name, r.value
            FROM sensor_readings r
            JOIN deployments d ON r.deployment_fk = d.deployment_pk
            JOIN sensors_master s ON d.sensor_fk = s.sensor_pk
            WHERE r."timestamp" >= NOW() - INTERVAL ':hours hours'
            ORDER BY r."timestamp" DESC
        """)
        return pd.read_sql_query(query, self.engine, params={"hours": hours})
    
    def log_collection(self, source: str, records: int, errors: int, duration: float):
        """Logs a data collection event to the collection_log table."""
        query = text("""
            INSERT INTO collection_log 
            (source, records_collected, errors_count, duration_seconds)
            VALUES (:source, :records, :errors, :duration)
        """)
        with self.engine.connect() as connection:
            with connection.begin():
                connection.execute(query, {
                    "source": source, 
                    "records": records, 
                    "errors": errors, 
                    "duration": duration
                })
    
    def get_collection_stats(self, days: int = 7) -> pd.DataFrame:
        """Retrieves collection statistics for a given number of days."""
        query = text("""
            SELECT 
                DATE(collection_date) as collection_day,
                source,
                SUM(records_collected) as total_records,
                SUM(errors_count) as total_errors,
                AVG(duration_seconds) as avg_duration
            FROM collection_log 
            WHERE collection_date >= NOW() - INTERVAL ':days days'
            GROUP BY collection_day, source
            ORDER BY collection_day DESC, source
        """)
        return pd.read_sql_query(query, self.engine, params={"days": days})
    
    def store_collection_metadata(self, collection_type: str, metadata: dict):
        """Stores arbitrary collection metadata as a JSON object."""
        query = text("""
            INSERT INTO collection_metadata (collection_type, metadata_json)
            VALUES (:collection_type, :metadata_json)
        """)
        with self.engine.connect() as connection:
            with connection.begin():
                connection.execute(query, {
                    "collection_type": collection_type,
                    "metadata_json": json.dumps(metadata)
                })

