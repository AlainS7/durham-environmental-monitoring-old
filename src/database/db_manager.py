"""
Database integration for Hot Durham project
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json

class HotDurhamDB:
    """Lightweight SQLite database for sensor data"""
    
    def __init__(self, db_path: str = "data/hot_durham.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # TSI data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tsi_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    device_id TEXT,
                    device_name TEXT,
                    pm25 REAL,
                    pm10 REAL,
                    temperature REAL,
                    humidity REAL,
                    is_test_sensor BOOLEAN,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # WU data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wu_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    station_id TEXT,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    wind_speed REAL,
                    is_test_sensor BOOLEAN,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Data collection log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_date DATE,
                    source TEXT,
                    records_collected INTEGER,
                    errors_count INTEGER,
                    duration_seconds REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Metadata collection
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_type TEXT,
                    metadata_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tsi_timestamp ON tsi_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tsi_device ON tsi_data(device_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wu_timestamp ON wu_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wu_station ON wu_data(station_id)")
    
    def insert_tsi_data(self, df: pd.DataFrame, is_test: bool = False):
        """Insert TSI data into database"""
        df['is_test_sensor'] = is_test
        df.to_sql('tsi_data', sqlite3.connect(self.db_path), 
                 if_exists='append', index=False)
    
    def insert_wu_data(self, df: pd.DataFrame, is_test: bool = False):
        """Insert WU data into database"""
        df['is_test_sensor'] = is_test
        df.to_sql('wu_data', sqlite3.connect(self.db_path), 
                 if_exists='append', index=False)
    
    def get_latest_data(self, source: str, hours: int = 24) -> pd.DataFrame:
        """Get latest data from specified source"""
        table_name = f"{source}_data"
        query = f"""
            SELECT * FROM {table_name} 
            WHERE timestamp >= datetime('now', '-{hours} hours')
            AND is_test_sensor = 0
            ORDER BY timestamp DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn)
    
    def log_collection(self, source: str, records: int, errors: int, duration: float):
        """Log data collection event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO collection_log 
                (collection_date, source, records_collected, errors_count, duration_seconds)
                VALUES (date('now'), ?, ?, ?, ?)
            """, (source, records, errors, duration))
    
    def get_collection_stats(self, days: int = 7) -> pd.DataFrame:
        """Get collection statistics"""
        query = """
            SELECT 
                collection_date,
                source,
                SUM(records_collected) as total_records,
                SUM(errors_count) as total_errors,
                AVG(duration_seconds) as avg_duration
            FROM collection_log 
            WHERE collection_date >= date('now', '-{} days')
            GROUP BY collection_date, source
            ORDER BY collection_date DESC
        """.format(days)
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn)
    
    def store_collection_metadata(self, collection_type: str, metadata: dict):
        """Store collection metadata"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO collection_metadata (collection_type, metadata_json)
                VALUES (?, ?)
            """, (collection_type, json.dumps(metadata)))
