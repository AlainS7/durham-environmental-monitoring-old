"""
Database integration for Hot Durham project
"""
import psycopg2
import pandas as pd
import json
import os
from sqlalchemy import create_engine

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
    
    def _get_connection(self):
        return psycopg2.connect(
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_pass,
            host=self.db_host,
            port=self.db_port
        )

    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # WU data table from DBeaver script
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS wu_data (
                        stationID VARCHAR(255) NOT NULL,
                        obsTimeUtc TIMESTAMPTZ NOT NULL,
                        tempAvg REAL,
                        humidityAvg REAL,
                        solarRadiationHigh REAL,
                        precipRate REAL,
                        precipTotal REAL,
                        winddirAvg REAL,
                        windspeedAvg REAL,
                        windgustAvg REAL,
                        pressureMax REAL,
                        pressureMin REAL,
                        pressureTrend REAL,
                        heatindexAvg REAL,
                        dewptAvg REAL,
                        PRIMARY KEY (stationID, obsTimeUtc)
                    )
                """)
                
                # TSI data table from DBeaver script
                cur.execute("""
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
                """)
                
                # Data collection log (useful for monitoring)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS collection_log (
                        id SERIAL PRIMARY KEY,
                        collection_date DATE,
                        source TEXT,
                        records_collected INTEGER,
                        errors_count INTEGER,
                        duration_seconds REAL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Metadata collection (useful for monitoring)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS collection_metadata (
                        id SERIAL PRIMARY KEY,
                        collection_type TEXT,
                        metadata_json JSONB,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tsi_reading_time ON tsi_data(reading_time)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tsi_device_id ON tsi_data(device_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wu_obsTimeUtc ON wu_data(obsTimeUtc)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_wu_stationID ON wu_data(stationID)")
            conn.commit()
    
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
            timestamp_col = 'obsTimeUtc'
        else:
            raise ValueError("Invalid source specified. Must be 'tsi' or 'wu'.")

        query = f"""
            SELECT * FROM {table_name} 
            WHERE {timestamp_col} >= NOW() - INTERVAL '{hours} hours'
            ORDER BY {timestamp_col} DESC
        """
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)
    
    def log_collection(self, source: str, records: int, errors: int, duration: float):
        """Log data collection event"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO collection_log 
                    (collection_date, source, records_collected, errors_count, duration_seconds)
                    VALUES (CURRENT_DATE, %s, %s, %s, %s)
                """, (source, records, errors, duration))
            conn.commit()
    
    def get_collection_stats(self, days: int = 7) -> pd.DataFrame:
        """Get collection statistics"""
        query = f"""
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
        """
        
        with self._get_connection() as conn:
            return pd.read_sql_query(query, conn)
    
    def store_collection_metadata(self, collection_type: str, metadata: dict):
        """Store collection metadata"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO collection_metadata (collection_type, metadata_json)
                    VALUES (%s, %s)
                """, (collection_type, json.dumps(metadata)))
            conn.commit()
