import asyncio
import pandas as pd
import argparse
import logging
import sys
from datetime import datetime, timedelta
from sqlalchemy import text

from src.config.app_config import app_config
from src.database.db_manager import HotDurhamDB
from src.storage.gcs_uploader import GCSUploader
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
        log.info(f"No raw records from {source} to clean.")
        return df

    log.info(f"Cleaning {len(df)} raw records from {source}.")
    log.debug(f"{source} raw columns: {list(df.columns)}")
    log.debug(f"{source} raw sample:\n{df.head().to_string(index=False)}")
    
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
        # Renaming for TSI flat-format data (expanded to match all provided fields)
        rename_map = {
            # 'cloud_account_id': 'account_id', # account the sensor belongs to
            'cloud_device_id': 'native_sensor_id',
            'device_id': 'native_sensor_id',
            'cloud_timestamp': 'timestamp',
            # 'is_indoor': 'is_indoor',
            # 'is_public': 'is_public',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'mcpm10': 'pm10',
            'mcpm10_aqi': 'pm10_aqi',
            'mcpm1x0': 'pm1_0',
            'mcpm2x5': 'pm2_5',
            'mcpm2x5_aqi': 'pm2_5_aqi',
            'mcpm4x0': 'pm4_0',
            # 'model': 'model',
            'ncpm0x5': 'ncpm0_5',
            'ncpm10': 'ncpm10',
            'ncpm1x0': 'ncpm1_0',
            'ncpm2x5': 'ncpm2_5',
            'ncpm4x0': 'ncpm4_0',
            'rh': 'humidity',
            # 'serial': 'serial',
            'temperature': 'temperature',
            'tpsize': 'tpsize',
            'co2_ppm': 'co2_ppm',
            'co_ppm': 'co_ppm',
            'baro_inhg': 'baro_inhg',
            'o3_ppb': 'o3_ppb',
            'no2_ppb': 'no2_ppb',
            'so2_ppb': 'so2_ppb',
            'ch2o_ppb': 'ch2o_ppb',
            'voc_mgm3': 'voc_mgm3'
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    # Consolidate duplicate column names (can happen when multiple source fields
    # are mapped to the same target name). PyArrow will error on duplicate
    # column labels, so coalesce duplicates by taking the first non-null value
    # across the duplicate columns for each row and preserve the original column
    # ordering.
    if df.columns.duplicated().any():
        dup_names = [name for name in df.columns[df.columns.duplicated()].unique()]
        log.warning(f"Duplicate column names after rename: {dup_names}. Consolidating duplicates by first non-null value.")
        names = list(df.columns)
        seen = set()
        new_df = pd.DataFrame(index=df.index)
        for name in names:
            if name in seen:
                continue
            # find all positions with this column label
            indices = [i for i, n in enumerate(names) if n == name]
            if len(indices) == 1:
                new_df[name] = df.iloc[:, indices[0]]
            else:
                tmp = df.iloc[:, indices]
                # forward-fill across columns (axis=1) then take first column
                new_df[name] = tmp.bfill(axis=1).iloc[:, 0]
            seen.add(name)
        df = new_df

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
async def run_collection_process(start_date, end_date, is_dry_run=False, aggregate=False, agg_interval='h', sink='gcs', source='all'):
    """Main process to fetch, clean, and store sensor data.

    The `source` parameter controls which data sources to fetch: 'all', 'wu', or 'tsi'.
    Passing it explicitly avoids attaching attributes to the coroutine function.
    """
    log.info(f"Starting data collection for {start_date} to {end_date}. Dry Run: {is_dry_run}. Aggregate: {aggregate} interval={agg_interval} sink={sink}")
    


    wu_raw_df = pd.DataFrame()
    tsi_raw_df = pd.DataFrame()

    # Fetch only the selected sources (concurrently when 'all')
    source_sel = source
    if source_sel == "all":
        async with WUClient(**app_config.wu_api_config) as wu_client, TSIClient(**app_config.tsi_api_config) as tsi_client:
            if aggregate or agg_interval != 'h':
                wu_task = wu_client.fetch_data(start_date, end_date, aggregate=aggregate, agg_interval=agg_interval)
                tsi_task = tsi_client.fetch_data(start_date, end_date, aggregate=aggregate, agg_interval=agg_interval)
            else:
                wu_task = wu_client.fetch_data(start_date, end_date)
                tsi_task = tsi_client.fetch_data(start_date, end_date)
            wu_raw_df, tsi_raw_df = await asyncio.gather(wu_task, tsi_task)
    elif source_sel == "wu":
        async with WUClient(**app_config.wu_api_config) as wu_client:
            if aggregate or agg_interval != 'h':
                wu_raw_df = await wu_client.fetch_data(start_date, end_date, aggregate=aggregate, agg_interval=agg_interval)
            else:
                wu_raw_df = await wu_client.fetch_data(start_date, end_date)
        tsi_raw_df = pd.DataFrame()
    elif source_sel == "tsi":
        async with TSIClient(**app_config.tsi_api_config) as tsi_client:
            if aggregate or agg_interval != 'h':
                tsi_raw_df = await tsi_client.fetch_data(start_date, end_date, aggregate=aggregate, agg_interval=agg_interval)
            else:
                tsi_raw_df = await tsi_client.fetch_data(start_date, end_date)
        wu_raw_df = pd.DataFrame()

    log.info(f"Fetched {len(wu_raw_df)} raw WU records and {len(tsi_raw_df)} raw TSI records.")

    wu_df = clean_and_transform_data(wu_raw_df, 'WU') if not wu_raw_df.empty else pd.DataFrame()
    tsi_df = clean_and_transform_data(tsi_raw_df, 'TSI') if not tsi_raw_df.empty else pd.DataFrame()

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
        wrote_any = False
        # GCS sink
        if sink in ("gcs", "both"):
            gcs_cfg = app_config.gcs_config
            if not gcs_cfg.get("bucket"):
                log.error("GCS bucket not configured (env GCS_BUCKET). Skipping GCS upload.")
            else:
                uploader = GCSUploader(bucket=gcs_cfg["bucket"], prefix=gcs_cfg.get("prefix", "sensor_readings"))
                if not wu_df.empty:
                    uploader.upload_parquet(wu_df, source="WU", aggregated=aggregate, interval=agg_interval, ts_column="timestamp")
                    wrote_any = True
                if not tsi_df.empty:
                    uploader.upload_parquet(tsi_df, source="TSI", aggregated=aggregate, interval=agg_interval, ts_column="timestamp")
                    wrote_any = True

        # DB sink (legacy path) or fallback when GCS not configured
        if sink in ("db", "both") or (sink == "gcs" and not wrote_any):
            db = HotDurhamDB()
            if not check_db_connection(db):
                log.critical("Database connection failed. Skipping DB sink.")
            else:
                insert_data_to_db(db, wu_df, tsi_df)
                wrote_any = True

        if not wrote_any:
            log.warning("Nothing was written; no sink active or dataframes empty.")
        log.info("Live run complete.")
    except Exception as e:
        log.error(f"An error occurred during the live run: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data collection script for Hot Durham project.")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    parser.add_argument("--start_date", type=str, default=yesterday, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end_date", type=str, default=yesterday, help="End date (YYYY-MM-DD).")
    parser.add_argument("--dry_run", action="store_true", help="Fetches and cleans but does not write to any sink.")
    parser.add_argument("--source", type=str, choices=["all", "wu", "tsi"], default="all", help="Which data source(s) to fetch: all, wu, tsi.")
    parser.add_argument("--aggregate", dest="aggregate", action="store_true", help="Aggregate data to a time interval before sinking.")
    parser.add_argument("--no-aggregate", dest="aggregate", action="store_false", help="Do not aggregate; keep raw data.")
    parser.set_defaults(aggregate=False)
    parser.add_argument("--agg-interval", type=str, default="h", help="Pandas offset alias for aggregation (e.g., 'h', '15min').")
    parser.add_argument("--sink", type=str, choices=["gcs", "db", "both"], default="gcs", help="Destination sink: Google Cloud Storage (gcs), database (db), or both.")
    args = parser.parse_args()

    try:
        asyncio.run(run_collection_process(args.start_date, args.end_date, args.dry_run, args.aggregate, args.agg_interval, args.sink, args.source))
    except Exception as e:
        log.critical(f"An unhandled error occurred in the main process: {e}", exc_info=True)
        sys.exit(1) # Exit with a non-zero status code to indicate failure