"""
Database integration for Hot Durham project
"""
import pandas as pd
import json
import os
from sqlalchemy import create_engine, text

class HotDurhamDB:
    """Database manager for PostgreSQL on Google Cloud SQL"""
    
    def __init__(self):
        # Database connection parameters should be loaded from environment variables
        # These are typically set when running with the Cloud SQL Auth Proxy
        self.db_name = os.getenv("DB_NAME", "postgres")
        self.db_user = os.getenv("DB_USER", "postgres")
        self.db_pass = os.getenv("DB_PASS")
        self.db_host = os.getenv("DB_HOST", "127.0.0.1")
        self.db_port = os.getenv("DB_PORT", "5432")
        
        self.conn_string = f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_engine(self.conn_string)
        self._init_database()

    def _init_database(self):
        """Initialize database tables using SQLAlchemy Engine."""
        with self.engine.connect() as connection:
            with connection.begin():  # Automatically commits or rolls back
                # WU data table from DBeaver script, with lowercase column names
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS wu_data (
                        stationid VARCHAR(255) NOT NULL,
                        obstimeutc TIMESTAMPTZ NOT NULL,
                        tempavg REAL,
                        humidityavg REAL,
                        solarradiationhigh REAL,
                        preciprate REAL,
                        preciptotal REAL,
                        winddiravg REAL,
                        windspeedavg REAL,
                        windgustavg REAL,
                        pressuremax REAL,
                        pressuremin REAL,
                        pressuretrend REAL,
                        heatindexavg REAL,
                        dewptavg REAL,
                        PRIMARY KEY (stationid, obstimeutc)
                    )
                """))
                
                # TSI data table from DBeaver script, with lowercase column names
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS tsi_data (
                        device_id VARCHAR(255) NOT NULL,
                        reading_time TIMESTAMPTZ NOT NULL,
                        device_name VARCHAR(255),
                        latitude REAL,
                        longitude REAL,
                        temperature REAL,
                        rh REAL,
                        p_bar REAL,
                        co2 REAL,
                        co REAL,
                        so2 REAL,
                        o3 REAL,
                        no2 REAL,
                        pm_1 REAL,
                        pm_2_5 REAL,
                        pm_4 REAL,
                        pm_10 REAL,
                        nc_pt5 REAL,
                        nc_1 REAL,
                        nc_2_5 REAL,
                        nc_4 REAL,
                        nc_10 REAL,
                        aqi REAL,
                        pm_offset REAL,
                        t_offset REAL,
                        rh_offset REAL,
                        PRIMARY KEY (device_id, reading_time)
                    )
                """))
                
                # Data collection log (useful for monitoring)
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS collection_log (
                        id SERIAL PRIMARY KEY,
                        collection_date DATE,
                        source TEXT,
                        records_collected INTEGER,
                        errors_count INTEGER,
                        duration_seconds REAL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Metadata collection (useful for monitoring)
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS collection_metadata (
                        id SERIAL PRIMARY KEY,
                        collection_type TEXT,
                        metadata_json JSONB,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes with lowercase column names
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tsi_reading_time ON tsi_data(reading_time)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_tsi_device_id ON tsi_data(device_id)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_wu_obstimeutc ON wu_data(obstimeutc)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_wu_stationid ON wu_data(stationid)"))
    
    def insert_tsi_data(self, df: pd.DataFrame):
        """Insert TSI data into database"""
        df.to_sql('tsi_data', self.engine, if_exists='append', index=False)
    
    def insert_wu_data(self, df: pd.DataFrame):
        """Insert WU data into database"""
        df.to_sql('wu_data', self.engine, if_exists='append', index=False)
    
    def get_latest_data(self, source: str, hours: int = 24) -> pd.DataFrame:
        """Get latest data from specified source"""
        if source.lower() == 'tsi':
            table_name = 'tsi_data'
            timestamp_col = 'reading_time'
        elif source.lower() == 'wu':
            table_name = 'wu_data'
            timestamp_col = 'obstimeutc'
        else:
            raise ValueError("Invalid source specified. Must be 'tsi' or 'wu'.")

        query = text(f"""
            SELECT * FROM {table_name} 
            WHERE {timestamp_col} >= NOW() - INTERVAL '{hours} hours'
            ORDER BY {timestamp_col} DESC
        """)
        return pd.read_sql_query(query, self.engine)
    
    def log_collection(self, source: str, records: int, errors: int, duration: float):
        """Log data collection event"""
        query = text("""
            INSERT INTO collection_log 
            (collection_date, source, records_collected, errors_count, duration_seconds)
            VALUES (CURRENT_DATE, :source, :records, :errors, :duration)
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
        """Get collection statistics"""
        query = text(f"""
            SELECT 
                collection_date,
                source,
                SUM(records_collected) as total_records,
                SUM(errors_count) as total_errors,
                AVG(duration_seconds) as avg_duration
            FROM collection_log 
            WHERE collection_date >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY collection_date, source
            ORDER BY collection_date DESC
        """)
        return pd.read_sql_query(query, self.engine)
    
    def store_collection_metadata(self, collection_type: str, metadata: dict):
        """Store collection metadata"""
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
