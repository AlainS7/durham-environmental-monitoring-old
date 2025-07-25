import asyncio
import httpx
import pandas as pd
import nest_asyncio
import argparse
import logging
from datetime import datetime, timedelta
from sqlalchemy import text, types
from tqdm import tqdm

# --- Correctly use your existing project structure for configuration ---
# These imports fetch credentials and sensor lists from your config files.
from src.config.app_config import app_config
from src.database.db_manager import HotDurhamDB
from src.utils.config_loader import get_wu_stations, get_tsi_devices

# Get the logger instance set up by your project's config
log = logging.getLogger(__name__)

# Apply nest_asyncio to allow running async functions in scripts
nest_asyncio.apply()


# --- Data Fetching Functions ---

async def fetch_wu_data_async(start_date_str, end_date_str, is_backfill=False):
    """Fetches Weather Underground data concurrently using project configs."""
    wu_key = app_config.wu_api_key.get('test_api_key') # Use your config object
    stations = get_wu_stations() # Use your config loader

    if not wu_key or not stations:
        log.error("Weather Underground API key or station list is not configured properly.")
        return pd.DataFrame()

    async def fetch_one(client, station_id, date_str, semaphore):
        async with semaphore:
            endpoint = "history/all" if is_backfill else "observations/all/1day"
            url = f"https://api.weather.com/v2/pws/{endpoint}"
            params = {"stationId": station_id, "format": "json", "apiKey": wu_key, "units": "m"}
            if is_backfill:
                params["date"] = date_str

            try:
                response = await client.get(url, params=params, timeout=60.0)
                if response.status_code == 200:
                    return response.json().get('observations', [])
                if response.status_code == 204:
                    return []
                log.warning(f"WU API non-200 for {station_id}: {response.status_code} - {response.text}")
            except Exception as e:
                log.error(f"WU API request failed for {station_id}: {e}", exc_info=True)
            return None

    semaphore = asyncio.Semaphore(10)
    async with httpx.AsyncClient() as client:
        if is_backfill:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            requests = [(s['stationId'], (start_dt + timedelta(days=d)).strftime("%Y%m%d"))
                        for s in stations if 'stationId' in s
                        for d in range((end_dt - start_dt).days + 1)]
            tasks = [fetch_one(client, station_id, date, semaphore) for station_id, date in requests]
        else:
            tasks = [fetch_one(client, s['stationId'], None, semaphore) for s in stations if 'stationId' in s]

        all_obs = []
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU Data"):
            result = await future
            if result:
                all_obs.extend(result)

    if not all_obs:
        return pd.DataFrame()
        
    flat_obs = [obs.update(obs.pop('metric')) or obs for obs in all_obs if 'metric' in obs]
    return pd.DataFrame(flat_obs or all_obs)


async def fetch_tsi_data_async(start_date, end_date):
    """Fetches TSI data concurrently using project configs."""
    tsi_creds = app_config.tsi_creds
    device_ids = get_tsi_devices()

    if not tsi_creds or not tsi_creds.get('key') or not device_ids:
        log.error("TSI credentials or device IDs are not configured properly.")
        return pd.DataFrame()

    auth_url = 'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken'
    auth_data = {'grant_type': 'client_credentials', 'client_id': tsi_creds['key'], 'client_secret': tsi_creds['secret']}
    try:
        auth_resp = httpx.post(auth_url, data=auth_data)
        auth_resp.raise_for_status()
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}", "Accept": "application/json"}
    except Exception as e:
        log.error(f"Failed to authenticate with TSI API: {e}", exc_info=True)
        return pd.DataFrame()

    async def fetch_one_day(client, device_id, date_iso, semaphore):
        async with semaphore:
            url = "https://api-prd.tsilink.com/api/v3/external/telemetry"
            start_iso = f"{date_iso}T00:00:00Z"
            end_iso = (datetime.strptime(date_iso, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
            params = {'device_id': device_id, 'start_date': start_iso, 'end_date': end_iso}
            try:
                response = await client.get(url, headers=headers, params=params, timeout=90.0)
                if response.status_code == 200:
                    records = response.json()
                    if not records:
                        return None
                    df = pd.DataFrame(records)
                    df['device_id'] = device_id
                    return df
            except Exception as e:
                log.error(f"TSI API request failed for {device_id} on {date_iso}: {e}", exc_info=True)
            return None

    date_range = pd.date_range(start=start_date, end=end_date)
    semaphore = asyncio.Semaphore(3)
    async with httpx.AsyncClient() as client:
        tasks = [fetch_one_day(client, dev_id, d.strftime("%Y-%m-%d"), semaphore)
                 for dev_id in device_ids
                 for d in date_range]
        all_results = await asyncio.gather(*tasks)

    valid_dfs = [df for df in all_results if df is not None and not df.empty]
    return pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()


# --- Data Cleaning and Transformation ---

def clean_and_transform_data(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Cleans and transforms raw data from a given source."""
    if df.empty:
        return df

    if source == 'WU':
        rename_map = {'stationID': 'native_sensor_id', 'obsTimeUtc': 'timestamp', 'tempAvg': 'temperature', 'humidityAvg': 'humidity'}
        df.rename(columns=rename_map, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        return df[['native_sensor_id', 'timestamp', 'temperature', 'humidity']] # Select only relevant columns

    if source == 'TSI':
        # Unpack nested data
        def extract(sensors_list):
            readings = {}
            if isinstance(sensors_list, list):
                for sensor in sensors_list:
                    for m in sensor.get('measurements', []):
                        readings[m.get('type')] = m.get('data', {}).get('value')
            return readings
        
        measurements_df = df['sensors'].apply(extract).apply(pd.Series)
        df = pd.concat([df.drop(columns=['sensors']), measurements_df], axis=1)

        rename_map = {'device_id': 'native_sensor_id', 'timestamp': 'raw_timestamp', 'mcpm2x5': 'pm2_5', 'temp_c': 'temperature', 'rh_percent': 'humidity'}
        df.rename(columns=rename_map, inplace=True)
        df['timestamp'] = pd.to_datetime(df['raw_timestamp'], utc=True)
        return df[['native_sensor_id', 'timestamp', 'temperature', 'humidity', 'pm2_5']] # Select relevant columns

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
    
    # Process DataFrames
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

    # Use the efficient "upsert" method with a temporary table
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
                    dtype={'timestamp': types.TIMESTAMP(timezone=True), 'deployment_fk': types.INTEGER, 'metric_name': types.VARCHAR, 'value': types.DOUBLE_PRECISION} # pyright: ignore[reportArgumentType]
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

    wu_raw_df, tsi_raw_df = await asyncio.gather(
        fetch_wu_data_async(start_date, end_date, is_backfill),
        fetch_tsi_data_async(start_date, end_date)
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
            # Use your project's DB Manager
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

    asyncio.run(run_collection_process(args.start_date, args.end_date, args.dry_run, args.backfill))