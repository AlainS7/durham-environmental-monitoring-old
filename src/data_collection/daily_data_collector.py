

import asyncio
import pandas as pd
import argparse
import logging
from datetime import datetime, timedelta
from sqlalchemy import text, types

from src.config.app_config import app_config
from src.database.db_manager import HotDurhamDB
from src.data_collection.clients.wu_client import WUClient
from src.data_collection.clients.tsi_client import TSIClient

log = logging.getLogger(__name__)

# --- Data Cleaning and Transformation ---

def clean_and_transform_data(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Cleans and transforms raw data from a given source."""
    if df.empty:
        return df

    if source == 'WU':
        rename_map = {'stationID': 'native_sensor_id', 'obsTimeUtc': 'timestamp', 'tempAvg': 'temperature', 'humidityAvg': 'humidity'}
        df.rename(columns=rename_map, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        return df[['native_sensor_id', 'timestamp', 'temperature', 'humidity']]

    if source == 'TSI':
        rename_map = {'device_id': 'native_sensor_id', 'timestamp': 'raw_timestamp', 'mcpm2x5': 'pm2_5', 'temp_c': 'temperature', 'rh_percent': 'humidity'}
        df.rename(columns=rename_map, inplace=True)
        df['timestamp'] = pd.to_datetime(df['raw_timestamp'], utc=True)
        return df[['native_sensor_id', 'timestamp', 'temperature', 'humidity', 'pm2_5']]

    return pd.DataFrame()


# --- Database Insertion ---

def insert_data_to_db(db: HotDurhamDB, wu_df: pd.DataFrame, tsi_df: pd.DataFrame):
    """Transforms and inserts cleaned data into sensor_readings via deployments."""
    if wu_df.empty and tsi_df.empty:
        log.info("No data to insert.")
        return

    with db.engine.connect() as connection:
        deployment_map_sql = """
            SELECT d.deployment_pk, sm.native_sensor_id, sm.sensor_type
            FROM deployments d
            JOIN sensors_master sm ON d.sensor_fk = sm.sensor_pk
            WHERE d.end_date IS NULL;
        """
        deployment_map_df = pd.read_sql(deployment_map_sql, connection)
        if deployment_map_df.empty:
            log.error("No active deployments found. Cannot insert data.")
            return

    all_readings = []
    
    for df, df_type in [(wu_df, 'WU'), (tsi_df, 'TSI')]:
        if not df.empty:
            type_map = deployment_map_df[deployment_map_df['sensor_type'] == df_type]
            merged_df = df.merge(type_map, on='native_sensor_id', how='inner')
            if merged_df.empty:
                log.warning(f"No {df_type} data matched an active deployment.")
                continue
            
            merged_df.rename(columns={'deployment_pk': 'deployment_fk'}, inplace=True)
            id_vars = ['timestamp', 'deployment_fk']
            value_vars = [col for col in merged_df.columns if col not in ['native_sensor_id', 'sensor_type'] + id_vars]
            long_df = pd.melt(merged_df, id_vars=id_vars, value_vars=value_vars, var_name='metric_name', value_name='value')
            all_readings.append(long_df)

    if not all_readings:
        log.warning("No data records matched an active deployment after processing. Nothing to insert.")
        return

    final_df = pd.concat(all_readings, ignore_index=True)
    final_df.dropna(subset=['value'], inplace=True)
    final_df.drop_duplicates(subset=['timestamp', 'deployment_fk', 'metric_name'], keep='last', inplace=True)

    if final_df.empty:
        log.info("Final DataFrame is empty after cleaning. Nothing to insert.")
        return

    temp_table_name = "temp_sensor_readings"
    pk_cols_str = '"timestamp", deployment_fk, metric_name'
    query = text(f"""
        INSERT INTO sensor_readings ("timestamp", deployment_fk, metric_name, value)
        SELECT "timestamp", deployment_fk, metric_name, value FROM {temp_table_name}
        ON CONFLICT ({pk_cols_str}) DO UPDATE SET value = EXCLUDED.value;
    """)

    try:
        with db.engine.connect() as connection:
            with connection.begin():
                log.info(f"Writing {len(final_df)} unique records to database...")
                final_df.to_sql(
                    temp_table_name, connection, if_exists='replace', index=False,
                    dtype=
                    {
                        'timestamp': types.TIMESTAMP(timezone=True),
                        'deployment_fk': types.INTEGER,
                        'metric_name': types.VARCHAR,
                        'value': types.DOUBLE_PRECISION
                    } # pyright: ignore[reportArgumentType]
                )
                result = connection.execute(query)
                log.info(f"Database upsert complete. {result.rowcount} rows affected.")
                connection.execute(text(f"DROP TABLE {temp_table_name}"))
    except Exception as e:
        log.error(f"Database insertion failed: {e}", exc_info=True)
        raise


# --- Main Execution Logic ---

async def run_collection_process(start_date, end_date, is_dry_run=False, is_backfill=False):
    """Main process to fetch, clean, and store sensor data."""
    log.info(f"Starting data collection for {start_date} to {end_date}. Dry Run: {is_dry_run}, Backfill: {is_backfill}")

    wu_client = WUClient(**app_config.wu_api_config)
    tsi_client = TSIClient(**app_config.tsi_api_config)

    wu_raw_df, tsi_raw_df = await asyncio.gather(
        wu_client.fetch_data(start_date, end_date, is_backfill),
        tsi_client.fetch_data(start_date, end_date)
    )
    log.info(f"Fetched {len(wu_raw_df)} raw WU records and {len(tsi_raw_df)} raw TSI records.")

    wu_df = clean_and_transform_data(wu_raw_df, 'WU')
    tsi_df = clean_and_transform_data(tsi_raw_df, 'TSI')
    log.info(f"Cleaned data: {len(wu_df)} WU records, {len(tsi_df)} TSI records.")

    if is_dry_run:
        log.info("--- DRY RUN MODE ---")
        print("Cleaned WU Data (first 5):\n", wu_df.head().to_markdown(index=False))
        print("\nCleaned TSI Data (first 5):\n", tsi_df.head().to_markdown(index=False))
        log.info("Dry run complete. No data was written.")
    else:
        log.info("--- LIVE RUN MODE ---")
        try:
            db = HotDurhamDB()
            insert_data_to_db(db, wu_df, tsi_df)
            log.info("Live run complete.")
        except Exception as e:
            log.error(f"An error occurred during live run database operations: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data collection script for Hot Durham project.")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    parser.add_argument("--start_date", type=str, default=yesterday, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=yesterday, help="End date (YYYY-MM-DD).")
    parser.add_argument("--dry_run", action="store_true", help="Fetches and cleans but does not write to the database.")
    parser.add_argument("--backfill", action="store_true", help="Enables backfill mode for fetching historical dates.")
    args = parser.parse_args()

    try:
        asyncio.run(run_collection_process(args.start_date, args.end_date, args.dry_run, args.backfill))
    except Exception as e:
        log.critical(f"An unhandled error occurred during data collection: {e}", exc_info=True)
