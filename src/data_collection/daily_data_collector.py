import asyncio
import pandas as pd
import argparse
import logging
from datetime import datetime, timedelta
from sqlalchemy import text

from src.config.app_config import app_config
from src.database.db_manager import HotDurhamDB
from src.data_collection.clients.wu_client import WUClient
from src.data_collection.clients.tsi_client import TSIClient

log = logging.getLogger(__name__)

# --- Database Connection Check ---
def check_db_connection(db: HotDurhamDB) -> bool:
    """Checks if the database connection is valid."""
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        log.info("Database connection successful.")
        return True
    except Exception as e:
        log.error(f"Database connection failed: {e}")
        return False

# --- Data Cleaning and Transformation ---
def clean_and_transform_data(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Cleans and standardizes column names for WU and TSI data sources.
    This prepares the DataFrame for the later melting/unpivoting step.
    """
    if df.empty:
        return df

    log.info(f"Cleaning {len(df)} raw records from {source}.")
    
    # Standardize column names across both sources
    if source == 'WU':
        # This mapping defines all the fields we want to capture from the WU API.
        # It renames them to standardized, database-friendly names.
        rename_map = {
            # Core identifiers
            'stationID': 'native_sensor_id', 
            'obsTimeUtc': 'timestamp', 
            
            # Temperature and Humidity
            'tempAvg': 'temperature', 
            'tempHigh': 'temperature_high',
            'tempLow': 'temperature_low',
            'humidityAvg': 'humidity',
            'humidityHigh': 'humidity_high',
            'humidityLow': 'humidity_low',

            # Precipitation
            'precipRate': 'precip_rate',
            'precipTotal': 'precip_total',

            # Wind
            'windspeedAvg': 'wind_speed_avg',
            'windspeedHigh': 'wind_speed_high',
            'windspeedLow': 'wind_speed_low',
            'windgustAvg': 'wind_gust_avg',
            'windgustHigh': 'wind_gust_high',
            'windgustLow': 'wind_gust_low',
            'winddirAvg': 'wind_direction_avg',

            # Pressure
            'pressureMax': 'pressure_max',
            'pressureMin': 'pressure_min',
            'pressureTrend': 'pressure_trend',

            # Radiation and UV
            'solarRadiationHigh': 'solar_radiation',
            'uvHigh': 'uv_high',

            # Other derived metrics
            'windchillAvg': 'wind_chill_avg',
            'windchillHigh': 'wind_chill_high',
            'windchillLow': 'wind_chill_low',
            'heatindexAvg': 'heat_index_avg',
            'heatindexHigh': 'heat_index_high',
            'heatindexLow': 'heat_index_low',
            'dewptAvg': 'dew_point_avg',
            'dewptHigh': 'dew_point_high',
            'dewptLow': 'dew_point_low',

            # Quality Control
            'qcStatus': 'qc_status'
        }
        # Only keep columns that exist in the DataFrame to avoid errors
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    elif source == 'TSI':
        # Flattening and renaming for TSI data
        rename_map = {
            'device_id': 'native_sensor_id',
            'timestamp': 'timestamp', # The TSI client now provides a clean 'timestamp'
            'mcpm2x5': 'pm2_5', 
            'temp_c': 'temperature', 
            'rh_percent': 'humidity',
            'co2': 'co2',
            'o3': 'o3',
            'no2': 'no2'
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    return df


# --- Database Insertion ---
def insert_data_to_db(db: HotDurhamDB, wu_df: pd.DataFrame, tsi_df: pd.DataFrame):
    """
    Transforms wide-format DataFrames into a long format and upserts them
    into the sensor_readings table.
    """
    if wu_df.empty and tsi_df.empty:
        log.info("No data to insert.")
        return

    # 1. Get a map of all active deployments from the database
    try:
        with db.engine.connect() as connection:
            deployment_map_sql = text("""
                SELECT d.deployment_pk, sm.native_sensor_id, sm.sensor_type
                FROM deployments d
                JOIN sensors_master sm ON d.sensor_fk = sm.sensor_pk
                WHERE d.end_date IS NULL;
            """)
            deployment_map_df = pd.read_sql(deployment_map_sql, connection)
    except Exception as e:
        log.error(f"Failed to fetch deployment map: {e}", exc_info=True)
        return

    if deployment_map_df.empty:
        log.error("No active deployments found in the database. Cannot map data.")
        return

    all_readings = []
    
    # 2. Process each DataFrame (WU and TSI)
    for df, df_type in [(wu_df, 'WU'), (tsi_df, 'TSI')]:
        if df.empty:
            continue

        # Filter deployment map for the current sensor type
        type_map = deployment_map_df[deployment_map_df['sensor_type'] == df_type]
        
        # Join the data with its deployment key
        merged_df = df.merge(type_map, on='native_sensor_id', how='inner')
        
        if merged_df.empty:
            log.warning(f"No {df_type} data matched an active deployment.")
            continue
        
        merged_df.rename(columns={'deployment_pk': 'deployment_fk'}, inplace=True)
        
        # 3. Unpivot (melt) the data from wide to long format
        id_vars = ['timestamp', 'deployment_fk']
        # Dynamically find all metric columns to melt
        value_vars = [col for col in merged_df.columns if col not in id_vars + ['native_sensor_id', 'sensor_type']]
        
        if not value_vars:
            log.warning(f"No metric columns found for {df_type} after merging.")
            continue

        long_df = pd.melt(merged_df, id_vars=id_vars, value_vars=value_vars, var_name='metric_name', value_name='value')
        all_readings.append(long_df)

    if not all_readings:
        log.warning("No data matched an active deployment. Nothing to insert.")
        return

    # 4. Combine, clean, and prepare the final DataFrame
    final_df = pd.concat(all_readings, ignore_index=True)
    final_df.dropna(subset=['value'], inplace=True)
    final_df.drop_duplicates(subset=['timestamp', 'deployment_fk', 'metric_name'], keep='last', inplace=True)

    if final_df.empty:
        log.info("Final DataFrame is empty after cleaning and de-duplication.")
        return
        
    # 5. Use the robust upsert method from your db_manager
    try:
        db.insert_sensor_readings(final_df)
        log.info(f"Successfully processed and upserted {len(final_df)} records.")
    except Exception as e:
        log.error(f"Database insertion failed during final step: {e}", exc_info=True)
        raise

# --- Main Execution Logic ---
async def run_collection_process(start_date, end_date, is_dry_run=False):
    """Main process to fetch, clean, and store sensor data."""
    log.info(f"Starting data collection for {start_date} to {end_date}. Dry Run: {is_dry_run}")
    
    # Initialize API clients
    wu_client = WUClient(**app_config.wu_api_config)
    tsi_client = TSIClient(**app_config.tsi_api_config)

    # Fetch data concurrently
    wu_raw_df, tsi_raw_df = await asyncio.gather(
        wu_client.fetch_data(start_date, end_date),
        tsi_client.fetch_data(start_date, end_date)
    )
    log.info(f"Fetched {len(wu_raw_df)} raw WU records and {len(tsi_raw_df)} raw TSI records.")

    # Clean and standardize both dataframes
    wu_df = clean_and_transform_data(wu_raw_df, 'WU')
    tsi_df = clean_and_transform_data(tsi_raw_df, 'TSI')

    if is_dry_run:
        log.info("--- DRY RUN MODE ---")
        print("\n--- Cleaned WU Data (first 5) ---")
        print(wu_df.head().to_markdown(index=False))
        print("\n--- Cleaned TSI Data (first 5) ---")
        print(tsi_df.head().to_markdown(index=False))
        log.info("Dry run complete. No data was written.")
        return

    # --- LIVE RUN MODE ---
    log.info("--- LIVE RUN MODE ---")
    try:
        db = HotDurhamDB()
        if not check_db_connection(db):
            log.critical("Database connection failed. Aborting live run.")
            return

        # The single, robust insertion function
        insert_data_to_db(db, wu_df, tsi_df)
        
        log.info("Live run complete.")

    except Exception as e:
        log.error(f"An error occurred during the live run: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data collection script for Hot Durham project.")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    parser.add_argument("--start_date", type=str, default=yesterday, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=yesterday, help="End date (YYYY-MM-DD).")
    parser.add_argument("--dry_run", action="store_true", help="Fetches and cleans but does not write to the database.")
    args = parser.parse_args()

    try:
        asyncio.run(run_collection_process(args.start_date, args.end_date, args.dry_run))
    except Exception as e:
        log.critical(f"An unhandled error occurred in the main process: {e}", exc_info=True)