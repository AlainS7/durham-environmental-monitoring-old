import asyncio
import httpx
import pandas as pd
import json
import numpy as np
import nest_asyncio
import argparse
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from tqdm import tqdm

# Configuration and DB access are imported, which handle logging setup
from src.config.app_config import app_config
from src.database.db_manager import HotDurhamDB
from src.utils.config_loader import get_wu_stations, get_tsi_devices, load_sensor_configs

# Get the logger instance
log = logging.getLogger(__name__)

# Apply nest_asyncio to allow running async functions in scripts
nest_asyncio.apply()

def clean_and_transform_tsi_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and transforms the raw TSI DataFrame to match the database schema.
    """
    if df.empty:
        return df

    schema_columns = [
        'device_id', 'reading_time', 'device_name', 'latitude', 'longitude',
        'temperature', 'rh', 'p_bar', 'co2', 'co', 'so2', 'o3', 'no2',
        'pm_1', 'pm_2_5', 'pm_4', 'pm_10', 'nc_pt5', 'nc_1', 'nc_2_5',
        'nc_4', 'nc_10', 'aqi', 'pm_offset', 't_offset', 'rh_offset'
    ]

    rename_map = {
        'timestamp': 'reading_time', 'temp_c': 'temperature', 'rh_percent': 'rh',
        'baro_inhg': 'p_bar', 'co2_ppm': 'co2', 'co_ppm': 'co', 'so2_ppb': 'so2',
        'o3_ppb': 'o3', 'no2_ppb': 'no2', 'mcpm1x0': 'pm_1', 'mcpm2x5': 'pm_2_5',
        'mcpm4x0': 'pm_4', 'mcpm10': 'pm_10', 'ncpm0x5': 'nc_pt5', 'ncpm1x0': 'nc_1',
        'ncpm2x5': 'nc_2_5', 'ncpm4x0': 'nc_4', 'ncpm10': 'nc_10', 'mcpm2x5_aqi': 'aqi'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'metadata' in df.columns:
        def to_dict(x):
            if isinstance(x, str):
                try:
                    return json.loads(x)
                except (json.JSONDecodeError, TypeError):
                    return {}
            return x if isinstance(x, dict) else {}

        meta_series = df['metadata'].apply(to_dict)
        df['latitude'] = meta_series.apply(lambda x: x.get('location', {}).get('latitude'))
        df['longitude'] = meta_series.apply(lambda x: x.get('location', {}).get('longitude'))

    for col in schema_columns:
        if col not in df.columns:
            df[col] = None

    transformed_df = df[schema_columns].copy()

    for col in transformed_df.columns:
        if col not in ['device_id', 'reading_time', 'device_name']:
            transformed_df.loc[:, col] = pd.to_numeric(transformed_df.loc[:, col], errors='coerce')
    
    # Ensure reading_time is a timezone-aware datetime object
    transformed_df['reading_time'] = pd.to_datetime(transformed_df['reading_time'], utc=True)

    return transformed_df

def separate_data(wu_df: pd.DataFrame, tsi_df: pd.DataFrame, prod_sensors: dict):
    """
    Filters dataframes to include only records from production sensors.
    """
    wu_prod_df = pd.DataFrame()
    if not wu_df.empty:
        # The config under 'wu' is a list of dictionaries, each with a 'stationId'.
        wu_prod_ids = [s['stationId'] for s in prod_sensors.get('wu', []) if isinstance(s, dict) and 'stationId' in s]
        if wu_prod_ids:
            wu_prod_df = wu_df[wu_df['stationid'].isin(wu_prod_ids)].copy()
            num_skipped = len(wu_df) - len(wu_prod_df)
            if num_skipped > 0:
                log.warning(f"Skipped {num_skipped} WU records with station IDs not in production config.")
        else:
            log.warning("No production WU sensors configured. Skipping all WU records.")

    tsi_prod_df = pd.DataFrame()
    if not tsi_df.empty:
        # The config under 'tsi' is a list of dictionaries, each with an 'id'.
        tsi_prod_ids = [s['id'] for s in prod_sensors.get('tsi', []) if isinstance(s, dict) and 'id' in s]
        if tsi_prod_ids:
            tsi_prod_df = tsi_df[tsi_df['device_id'].isin(tsi_prod_ids)].copy()
            num_skipped = len(tsi_df) - len(tsi_prod_df)
            if num_skipped > 0:
                log.warning(f"Skipped {num_skipped} TSI records with device IDs not in production config.")
        else:
            log.warning("No production TSI sensors configured. Skipping all TSI records.")

    return wu_prod_df, tsi_prod_df

def insert_data_to_db(db: HotDurhamDB, df: pd.DataFrame, table_name: str):
    """
    Inserts a DataFrame into the specified database table using an
    efficient and robust INSERT...ON CONFLICT...DO UPDATE strategy.
    """
    if df is None or df.empty:
        log.info(f"No data to insert into {table_name}.")
        return

    pk_columns = {'wu_data': ['stationid', 'obstimeutc'], 'tsi_data': ['device_id', 'reading_time']}
    if table_name not in pk_columns:
        log.error(f"Unknown table for insertion: {table_name}. Aborting.")
        return

    temp_table = f"temp_{table_name}"
    pk_cols = pk_columns[table_name]
    update_cols = [c for c in df.columns if c not in pk_cols]
    
    all_cols_str = ", ".join([f'"{c}"' for c in df.columns])
    pk_cols_str = ", ".join(pk_cols)
    set_clause = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in update_cols])

    query = text(f"""
        INSERT INTO {table_name} ({all_cols_str})
        SELECT {all_cols_str} FROM {temp_table}
        ON CONFLICT ({pk_cols_str}) DO UPDATE 
        SET {set_clause};
    """)

    try:
        with db.engine.connect() as connection:
            with connection.begin() as transaction:
                try:
                    log.info(f"Writing {len(df)} rows to temporary table {temp_table}...")
                    df.to_sql(temp_table, connection, if_exists='replace', index=False)
                    
                    log.info(f"Executing INSERT...ON CONFLICT for {table_name}...")
                    result = connection.execute(query)
                    
                    log.info(f"Database operation for {table_name} affected {result.rowcount} rows.")
                    
                    connection.execute(text(f"DROP TABLE {temp_table}"))
                except Exception as e:
                    log.error(f"Error during transaction for {table_name}, rolling back. Error: {e}", exc_info=True)
                    transaction.rollback()
                    raise
    except Exception as e:
        log.error(f"Database connection failed for {table_name}: {e}", exc_info=True)

async def fetch_wu_data_async(start_date_str, end_date_str):
    """ Fetches Weather Underground data concurrently. """
    wu_key = app_config.wu_api_key.get('test_api_key')
    if not wu_key:
        log.error("Weather Underground API key not found.")
        return pd.DataFrame()
        
    stations = get_wu_stations()
    if not stations:
        log.warning("No WU stations found in the configuration. Skipping WU data fetch.")
        return pd.DataFrame()

    start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

    requests_to_make = [(s['stationId'], (start_date_dt + timedelta(days=d)).strftime("%Y%m%d")) for s in stations if isinstance(s, dict) and 'stationId' in s for d in range((end_date_dt - start_date_dt).days + 1)]

    async def fetch_one(client, station_id, date_str, semaphore):
        async with semaphore:
            params = {"stationId": station_id, "date": date_str, "format": "json", "apiKey": wu_key, "units": "m", "numericPrecision": "decimal"}
            try:
                response = await client.get("https://api.weather.com/v2/pws/history/hourly", params=params, timeout=60.0)
                if response.status_code == 200:
                    return response.json().get('observations', [])
                if response.status_code == 204:
                    return []
                log.warning(f"WU API non-200 response for {station_id} on {date_str}: {response.status_code}")
            except Exception as e:
                log.error(f"WU API request failed for {station_id} on {date_str}: {e}", exc_info=True)
            return None

    semaphore = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = [fetch_one(client, station_id, date_str, semaphore) for station_id, date_str in requests_to_make]
        results = []
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU data"):
            result = await future
            if result is not None:
                results.extend(result)

    cols = ['stationID', 'obsTimeUtc', 'tempAvg', 'humidityAvg', 'solarRadiationHigh', 'precipRate', 'precipTotal', 'winddirAvg', 'windspeedAvg', 'windgustAvg', 'pressureMax', 'pressureMin', 'pressureTrend', 'heatindexAvg', 'dewptAvg']
    df = pd.DataFrame(results, columns=cols)
    if not df.empty:
        df.columns = [c.lower() for c in df.columns]
        # Ensure obstimeutc is a timezone-aware datetime object
        df['obstimeutc'] = pd.to_datetime(df['obstimeutc'], utc=True)
        df = df.replace([np.inf, -np.inf], np.nan).fillna(pd.NA)
    return df

def to_iso8601(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y-%m-%dT00:00:00Z")

async def fetch_device_data_async(client, device, start_date_iso, end_date_iso, headers):
    device_id = device.get('device_id')
    device_name = device.get('metadata', {}).get('friendlyName') or device_id
    params = {'device_id': device_id, 'start_date': start_date_iso, 'end_date': end_date_iso}
    try:
        response = await client.get("https://api-prd.tsilink.com/api/v3/external/telemetry", headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            records = response.json()
            if not records:
                return None
            df = pd.DataFrame(records)
            def extract(sensors):
                res = {}
                if isinstance(sensors, list):
                    for s in sensors:
                        for m in s.get('measurements', []):
                            res[m.get('type')] = m.get('data', {}).get('value')
                return res
            if 'sensors' in df.columns:
                measurements_df = df['sensors'].apply(extract).apply(pd.Series)
                df = pd.concat([df.drop(columns=['sensors']), measurements_df], axis=1)
            df['device_id'] = device_id
            df['device_name'] = device_name
            return df
    except Exception as e:
        log.warning(f"Failed to fetch data for TSI device {device_name}: {e}", exc_info=True)
    return None

async def fetch_tsi_data_async(start_date, end_date):
    log.info(f"TSI fetching data for range: {start_date} to {end_date}")
    tsi_creds = app_config.tsi_creds
    auth_resp = httpx.post('https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken', params={'grant_type': 'client_credentials'}, data={'client_id': tsi_creds['key'], 'client_secret': tsi_creds['secret']})
    if auth_resp.status_code != 200:
        log.error(f"Failed to authenticate with TSI API: {auth_resp.text}")
        return pd.DataFrame()
    headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}", "Accept": "application/json"}
    
    devices_resp = httpx.get("https://api-prd.tsilink.com/api/v3/external/devices", headers=headers)
    if devices_resp.status_code != 200:
        log.error(f"Failed to fetch TSI devices: {devices_resp.status_code}")
        return pd.DataFrame()
    
    configured_ids = get_tsi_devices()
    api_devices = {d['device_id']: d for d in devices_resp.json()}
    selected_devices = [api_devices[dev_id] for dev_id in configured_ids if dev_id in api_devices] if configured_ids else list(api_devices.values())
    log.info(f"Processing {len(selected_devices)} TSI devices.")

    start_iso = to_iso8601(start_date)
    end_iso = to_iso8601((datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"))

    async with httpx.AsyncClient() as client:
        tasks = [fetch_device_data_async(client, d, start_iso, end_iso, headers) for d in selected_devices]
        results = []
        for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching TSI data"):
            results.append(await fut)

    all_dfs = [df for df in results if df is not None]
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

async def run_collection_process(start_date_str=None, end_date_str=None, is_dry_run=False):
    if not start_date_str or not end_date_str:
        yesterday = (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        start_date_str = end_date_str = yesterday
        log.info(f"Date range not specified. Defaulting to yesterday: {start_date_str}")

    log.info(f"Starting data collection for {start_date_str} to {end_date_str}...")
    
    wu_task = asyncio.create_task(fetch_wu_data_async(start_date_str, end_date_str))
    tsi_task = asyncio.create_task(fetch_tsi_data_async(start_date_str, end_date_str))
    wu_df, tsi_df = await asyncio.gather(wu_task, tsi_task)

    log.info(f"Found {len(wu_df)} records from WU and {len(tsi_df)} raw records from TSI.")
    
    if not tsi_df.empty:
        tsi_df = clean_and_transform_tsi_data(tsi_df)
        log.info(f"Successfully transformed {len(tsi_df)} TSI records.")

    prod_sensors, _ = load_sensor_configs()
    wu_prod_df, tsi_prod_df = separate_data(wu_df, tsi_df, prod_sensors)
    log.info(f"Separated {len(wu_prod_df)} WU and {len(tsi_prod_df)} TSI production records.")

    if is_dry_run:
        log.info("--- DRY RUN MODE ---")
        log.info("WU Production Data (first 5):")
        log.info(wu_prod_df.head())
        log.info("TSI Production Data (first 5):")
        log.info(tsi_prod_df.head())
    else:
        log.info("--- LIVE RUN MODE ---")
        try:
            db = HotDurhamDB()
            insert_data_to_db(db, wu_prod_df, 'wu_data')
            insert_data_to_db(db, tsi_prod_df, 'tsi_data')
            log.info("Database insertion process complete.")
        except Exception as e:
            log.error(f"An error occurred during database operations: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data collection script for Hot Durham project.")
    parser.add_argument("--start_date", type=str, default=None, help="Start date (YYYY-MM-DD). Defaults to yesterday.")
    parser.add_argument("--end_date", type=str, default=None, help="End date (YYYY-MM-DD). Defaults to yesterday.")
    parser.add_argument("--dry_run", action="store_true", help="Enable dry run mode (no data insertion).")
    args = parser.parse_args()
    
    asyncio.run(run_collection_process(args.start_date, args.end_date, args.dry_run))
