import asyncio
import httpx
import pandas as pd
import json
import os
import sys
import time
import nest_asyncio
import logging
import argparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from tqdm import tqdm

# Setup logging and configuration first
from src.utils.logging_setup import setup_logging
from src.config.app_config import app_config

# Use relative imports for local modules
from config.test_sensors_config import TestSensorConfig
from config.wu_stations_config import get_wu_stations
from config.tsi_stations_config import get_tsi_devices
from src.utils.tsi_date_manager import TSIDateRangeManager

# Initialize logging
setup_logging()

# Create a database engine from the config
engine = create_engine(app_config.database_url)

nest_asyncio.apply()

def clean_and_transform_tsi_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and transforms the raw TSI DataFrame to match the database schema.
    """
    if df.empty:
        return df

    # Define the schema columns
    schema_columns = [
        'device_id', 'reading_time', 'device_name', 'latitude', 'longitude',
        'temperature', 'rh', 'p_bar', 'co2', 'co', 'so2', 'o3', 'no2',
        'pm_1', 'pm_2_5', 'pm_4', 'pm_10', 'nc_pt5', 'nc_1', 'nc_2_5',
        'nc_4', 'nc_10', 'aqi', 'pm_offset', 't_offset', 'rh_offset'
    ]

    # Create a new DataFrame to hold the transformed data
    transformed_df = pd.DataFrame()

    # Rename columns from API names to schema names
    rename_map = {
        'timestamp': 'reading_time',
        'temp_c': 'temperature',
        'rh_percent': 'rh',
        'baro_inhg': 'p_bar',
        'co2_ppm': 'co2',
        'co_ppm': 'co',
        'so2_ppb': 'so2',
        'o3_ppb': 'o3',
        'no2_ppb': 'no2',
        'mcpm1x0': 'pm_1',
        'mcpm2x5': 'pm_2_5',
        'mcpm4x0': 'pm_4',
        'mcpm10': 'pm_10',
        'ncpm0x5': 'nc_pt5',
        'ncpm1x0': 'nc_1',
        'ncpm2x5': 'nc_2_5',
        'ncpm4x0': 'nc_4',
        'ncpm10': 'nc_10',
        'mcpm2x5_aqi': 'aqi'
    }
    df.rename(columns=rename_map, inplace=True)

    # Extract nested data from 'metadata' column
    if 'metadata' in df.columns:
        # Ensure metadata is a dict, not a string
        def to_dict(x):
            if isinstance(x, str):
                try: return json.loads(x)
                except (json.JSONDecodeError, TypeError): return {}
            return x if isinstance(x, dict) else {}

        meta_series = df['metadata'].apply(to_dict)
        df['latitude'] = meta_series.apply(lambda x: x.get('location', {}).get('latitude'))
        df['longitude'] = meta_series.apply(lambda x: x.get('location', {}).get('longitude'))

    # Ensure all schema columns exist, fill missing with None (or np.nan)
    for col in schema_columns:
        if col not in df.columns:
            df[col] = None

    # Select and reorder columns to match the schema
    transformed_df = df[schema_columns]

    # Convert all numeric columns to numeric types, coercing errors
    for col in transformed_df.columns:
        if col not in ['device_id', 'reading_time', 'device_name']:
            transformed_df[col] = pd.to_numeric(transformed_df[col], errors='coerce')

    return transformed_df

def read_or_fallback(prompt, default=None):
    # This function is for interactive use and will not be used in the automated script.
    # It remains for potential local debugging.
    try:
        if sys.stdin.isatty():
            val = input(f"{prompt} [{default}]: ") if default else input(prompt)
            return val if val else (default if default is not None else "")
        try:
            import select
            if select.select([sys.stdin], [], [], 0.1)[0]:
                val = sys.stdin.readline().strip()
                return val if val else (default if default is not None else "")
            else:
                val = input(f"{prompt} [{default}]: ") if default else input(prompt)
                return val if val else (default if default is not None else "")
        except ImportError:
            val = input(f"{prompt} [{default}]: ") if default else input(prompt)
            return val if val else (default if default is not None else "")
    except Exception:
        val = input(f"{prompt} [{default}]: ") if default else input(prompt)
        return val if val else (default if default is not None else "")

def insert_data_to_db(df, table_name):
    """
    Inserts a DataFrame into the specified database table, ignoring duplicates
    based on the table's primary key.
    """
    if df is None or df.empty:
        logging.info(f"No data to insert into {table_name}.")
        return

    # Define the primary key columns for each table
    pk_columns = {
        'wu_data': ['stationid', 'obstimeutc'],
        'tsi_data': ['device_id', 'reading_time']
    }

    if table_name not in pk_columns:
        logging.warning(f"No duplicate prevention strategy for {table_name}. Appending data.")
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
        except Exception as e:
            logging.error(f"Error inserting data into {table_name}: {e}", exc_info=True)
        return

    temp_table_name = f"temp_{table_name}"
    
    try:
        # Step 1: Write all new data to a temporary table
        logging.info(f"Writing {len(df)} rows to temporary table {temp_table_name}...")
        df.to_sql(temp_table_name, engine, if_exists='replace', index=False)

        # Step 2: Construct a SQL query to insert only the new rows from the temp table
        pk_cols_str = ", ".join([f'"{c}"' for c in pk_columns[table_name]])
        all_cols_str = ", ".join([f'"{c}"' for c in df.columns])
        
        # Use lowercase for ON CONFLICT target columns
        pk_cols_conflict = ", ".join(pk_columns[table_name])

        sql = f"""
        INSERT INTO {table_name} ({all_cols_str})
        SELECT {all_cols_str}
        FROM {temp_table_name}
        ON CONFLICT ({pk_cols_conflict}) DO NOTHING;
        """
        
        # Step 3: Execute the SQL to insert the data
        with engine.connect() as connection:
            trans = connection.begin()
            result = connection.execute(text(sql))
            trans.commit()
        logging.info(f"Successfully inserted/updated {result.rowcount} rows in {table_name}.")

    except Exception as e:
        logging.error(f"Error inserting data into {table_name}: {e}", exc_info=True)
    finally:
        # Step 4: Drop the temporary table to clean up
        with engine.connect() as connection:
            trans = connection.begin()
            connection.execute(text(f"DROP TABLE IF EXISTS {temp_table_name};"))
            trans.commit()

def fetch_wu_data(start_date_str, end_date_str):
    wu_key = app_config.wu_api_key.get('test_api_key')
    stations = get_wu_stations()

    def get_station_data_and_process(client, stationId, date, key, max_attempts=4):
        base_url = "https://api.weather.com/v2"
        params = {
            "stationId": stationId,
            "date": date,
            "format": "json",
            "apiKey": key,
            "units": "m",
            "numericPrecision": "decimal",
        }
        url = os.path.join(base_url, "pws", "history/hourly")
        backoff_delays = [1, 3, 5]  # Delays for retries (1s, 3s, 5s)

        for attempt_num in range(1, max_attempts + 1):
            response = None
            try:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        return data.get('observations', [])
                    except json.JSONDecodeError:
                        logging.warning(f"Attempt {attempt_num}/{max_attempts} failed for {stationId} on {date} due to JSON decode error.")
                    except Exception as e:
                        logging.error(f"Attempt {attempt_num}/{max_attempts} failed during processing for {stationId} on {date}: {e}", exc_info=True)
                elif response.status_code == 204:
                    logging.info(f"No content (204) for {stationId} on {date}. Assuming no data.")
                    return []
                else:
                    logging.warning(f"Attempt {attempt_num}/{max_attempts} received non-200 response for {stationId} on {date}: {response.status_code} {response.text[:200]}")

            except httpx.TimeoutException:
                logging.warning(f"Attempt {attempt_num}/{max_attempts} timed out for {stationId} on {date}.")
            except httpx.RequestError as e:
                logging.warning(f"Attempt {attempt_num}/{max_attempts} failed for {stationId} on {date} with httpx.RequestError: {e}")
            except Exception as e:
                logging.error(f"Attempt {attempt_num}/{max_attempts} encountered an unexpected error for {stationId} on {date}: {e}", exc_info=True)

            if attempt_num < max_attempts:
                delay_index = min(attempt_num - 1, len(backoff_delays) - 1)
                delay = backoff_delays[delay_index]
                logging.info(f"Waiting {delay}s before retry {attempt_num + 1} for {stationId} on {date}...")
                time.sleep(delay)
            else:
                logging.error(f"Final attempt {attempt_num}/{max_attempts} failed for {stationId} on {date}.")

        logging.error(f"All {max_attempts} attempts failed to fetch/process data for {stationId} on {date} after exhausting retries (httpx).")
        return None

    start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

    all_rows = []
    total_requests = ((end_date_dt - start_date_dt).days + 1) * len(stations)

    timeout_config = httpx.Timeout(60.0, connect=10.0) # 60s total read/write/pool, 10s for connect
    with httpx.Client(timeout=timeout_config) as client:
        with tqdm(total=total_requests, desc="Fetching & Processing WU data sequentially") as pbar:
            for single_date_offset in range((end_date_dt - start_date_dt).days + 1):
                current_date = start_date_dt + timedelta(days=single_date_offset)
                date_str = current_date.strftime("%Y%m%d")
                for station in stations:
                    stationId = station['stationId']
                    processed_rows_for_single_request = get_station_data_and_process(client, stationId, date_str, wu_key)
                    if processed_rows_for_single_request is not None:
                        all_rows.extend(processed_rows_for_single_request)
                    pbar.update(1)

    columns = [
        'stationID', 'obsTimeUtc', 'tempAvg', 'humidityAvg', 'solarRadiationHigh',
        'precipRate', 'precipTotal', 'winddirAvg', 'windspeedAvg', 'windgustAvg',
        'pressureMax', 'pressureMin', 'pressureTrend', 'heatindexAvg', 'dewptAvg'
    ]

    df = pd.DataFrame(all_rows, columns=columns)

    if not df.empty:
        df.columns = [c.lower() for c in df.columns] # Lowercase all column names
        df['obstimeutc'] = df['obstimeutc'].astype(str)
        # Replace problematic values safely
        df = df.replace({float('inf'): '', float('-inf'): ''})
        df = df.fillna('')
    else:
        df = pd.DataFrame(columns=columns)

    return df

async def fetch_wu_data_async(start_date_str, end_date_str):
    """
    Fetches Weather Underground data concurrently for a given date range.
    """
    wu_key = app_config.wu_api_key.get('test_api_key')
    if not wu_key:
        logging.error("Weather Underground API key not found in configuration.")
        return pd.DataFrame()
        
    stations = get_wu_stations()
    start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

    # Create a list of all requests to be made
    dates_to_fetch = [start_date_dt + timedelta(days=d) for d in range((end_date_dt - start_date_dt).days + 1)]
    requests_to_make = [(station['stationId'], date.strftime("%Y%m%d")) for station in stations for date in dates_to_fetch]

    all_rows = []
    
    async def fetch_one_station_day(client, station_id, date_str, semaphore):
        """Fetches and processes data for a single station on a single day."""
        async with semaphore:
            base_url = "https://api.weather.com/v2/pws/history/hourly"
            params = {
                "stationId": station_id,
                "date": date_str,
                "format": "json",
                "apiKey": wu_key,
                "units": "m",
                "numericPrecision": "decimal",
            }
            backoff_delays = [1, 3, 5]  # Delays for retries

            for attempt in range(1, 4):
                try:
                    response = await client.get(base_url, params=params, timeout=60.0)
                    if response.status_code == 200:
                        data = response.json()
                        return data.get('observations', [])
                    elif response.status_code == 204:
                        logging.info(f"No content (204) for {station_id} on {date_str}.")
                        return []
                    else:
                        logging.warning(f"Attempt {attempt}/3 received non-200 response for {station_id} on {date_str}: {response.status_code}")
                except httpx.TimeoutException:
                    logging.warning(f"Attempt {attempt}/3 timed out for {station_id} on {date_str}.")
                except httpx.RequestError as e:
                    logging.warning(f"Attempt {attempt}/3 failed for {station_id} on {date_str} with RequestError: {e}")
                except json.JSONDecodeError:
                    logging.warning(f"Attempt {attempt}/3 failed for {station_id} on {date_str} due to JSON decode error.")
                except Exception as e:
                    logging.error(f"An unexpected error occurred in attempt {attempt}/3 for {station_id} on {date_str}: {e}", exc_info=True)

                if attempt < 3:
                    delay = backoff_delays[min(attempt - 1, len(backoff_delays) - 1)]
                    await asyncio.sleep(delay)
            
            logging.error(f"All 3 attempts failed for {station_id} on {date_str}.")
            return None

    # Limit concurrency to 10 requests at a time to avoid rate-limiting
    semaphore = asyncio.Semaphore(10)
    timeout_config = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        tasks = [fetch_one_station_day(client, station_id, date_str, semaphore) for station_id, date_str in requests_to_make]
        
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU data"):
            result = await future
            if result is not None:
                all_rows.extend(result)

    columns = [
        'stationID', 'obsTimeUtc', 'tempAvg', 'humidityAvg', 'solarRadiationHigh',
        'precipRate', 'precipTotal', 'winddirAvg', 'windspeedAvg', 'windgustAvg',
        'pressureMax', 'pressureMin', 'pressureTrend', 'heatindexAvg', 'dewptAvg'
    ]
    
    df = pd.DataFrame(all_rows, columns=columns)
    if not df.empty:
        df.columns = [c.lower() for c in df.columns] # Lowercase all column names
        df['obstimeutc'] = df['obstimeutc'].astype(str)
        df = df.replace({float('inf'): '', float('-inf'): ''})
        df = df.fillna('')
    else:
        df = pd.DataFrame(columns=columns)
        
    return df

def to_iso8601(date_str):
    """Convert date string to ISO8601 format, supporting both YYYY-MM-DD and YYYYMMDD formats."""
    try:
        # Try YYYY-MM-DD format first
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        try:
            # Try YYYYMMDD format
            dt = datetime.strptime(date_str, "%Y%m%d")
            return dt.strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            # If neither format works, return original string
            logging.warning(f"Could not parse date {date_str}, using as-is")
            return date_str

async def fetch_device_data_async(client, device, start_date_iso, end_date_iso, headers, per_device):
    device_id = device.get('device_id')
    device_name = device.get('metadata', {}).get('friendlyName') or device_id
    data_url = "https://api-prd.tsilink.com/api/v3/external/telemetry"
    params = {
        'device_id': device_id,
        'start_date': start_date_iso,
        'end_date': end_date_iso
    }
    response = None
    for attempt in range(3):
        try:
            response = await client.get(data_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                break
        except Exception:
            pass
        await asyncio.sleep(2)
    if response is None or response.status_code != 200:
        logging.warning(f"Failed to fetch data for device {device_name}. Status code: {getattr(response, 'status_code', 'N/A')}")
        return None, device_name
    data_json = response.json()
    records = data_json if isinstance(data_json, list) else data_json.get('data', [])
    if not records:
        return None, device_name
    df = pd.DataFrame(records)
    def extract_measurements(sensors):
        result = {}
        if isinstance(sensors, list):
            for sensor in sensors:
                for m in sensor.get('measurements', []):
                    mtype = m.get('type')
                    value = m.get('data', {}).get('value')
                    timestamp = m.get('data', {}).get('timestamp')
                    if mtype is not None:
                        if mtype in result:
                            prev_timestamp = result.get(mtype + '_ts')
                            if prev_timestamp and timestamp and timestamp > prev_timestamp:
                                result[mtype] = value
                                result[mtype + '_ts'] = timestamp
                        else:
                            result[mtype] = value
                            result[mtype + '_ts'] = timestamp
        return {k: v for k, v in result.items() if not k.endswith('_ts')}
    if 'sensors' in df.columns:
        measurements_df = df['sensors'].apply(extract_measurements).apply(pd.Series)
        df = pd.concat([df.drop(columns=['sensors']), measurements_df], axis=1)
    df['device_id'] = device_id
    df['device_name'] = device_name
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        # Keep 15-minute intervals instead of hourly aggregation for higher accuracy
        df['timestamp_15min'] = df['timestamp'].dt.floor('15min')
        df = df.sort_values('timestamp').drop_duplicates(['timestamp_15min'], keep='first')
        df = df.drop(columns=['timestamp_15min'])
    return df, device_name

async def fetch_all_devices(devices, start_date_iso, end_date_iso, headers, per_device):
    semaphore = asyncio.Semaphore(5)
    results = []
    async def bound_fetch(device):
        async with semaphore:
            return await fetch_device_data_async(client, device, start_date_iso, end_date_iso, headers, per_device)
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(bound_fetch(device)) for device in devices]
        for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching TSI data", unit="device"):
            results.append(await fut)
    return results

async def fetch_tsi_data_async(start_date, end_date, combine_mode='yes', per_device=False):
    if TSIDateRangeManager is not None:
        days_back = TSIDateRangeManager.get_days_back_from_start(start_date)
        days_span = TSIDateRangeManager.get_days_difference(start_date, end_date)
        
        if not TSIDateRangeManager.is_within_limit(start_date, end_date):
            logging.warning(f"Start date {start_date} is {days_back} days back, which exceeds TSI's 90-day historical limit.")
            # For automated systems, default to most recent data
            adjusted_start, adjusted_end, was_adjusted = TSIDateRangeManager.adjust_date_range_for_tsi(
                start_date, end_date, prefer_recent=True
            )
            
            if was_adjusted:
                start_date, end_date = adjusted_start, adjusted_end
                new_days_back = TSIDateRangeManager.get_days_back_from_start(start_date)
                new_days_span = TSIDateRangeManager.get_days_difference(start_date, end_date)
                logging.info(f"Automatically adjusted date range to: {start_date} to {end_date}")
                logging.info(f"New range: {new_days_span} days span, starting {new_days_back} days back")
        else:
            logging.info(f"TSI date range valid: {start_date} to {end_date}")
            logging.info(f"Range: {days_span} days span, starting {days_back} days back")
    else:
        logging.warning(f"Using basic date handling: {start_date} to {end_date}")
    
    
    tsi_creds = app_config.tsi_creds
    auth_resp = httpx.post(
        'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken',
        params={'grant_type': 'client_credentials'},
        data={'client_id': tsi_creds['key'], 'client_secret': tsi_creds['secret']}
    )
    
    if auth_resp.status_code != 200:
        logging.error(f"Failed to authenticate with TSI API. Status: {auth_resp.status_code}, Response: {auth_resp.text}")
        return pd.DataFrame(), {}
        
    access_token = auth_resp.json().get('access_token')
    if not access_token:
        logging.error("Failed to get access_token from TSI API.")
        return pd.DataFrame(), {}
        
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    devices_url = "https://api-prd.tsilink.com/api/v3/external/devices"
    devices_resp = httpx.get(devices_url, headers=headers)
    if devices_resp.status_code != 200:
        logging.error(f"Failed to fetch TSI devices. Status code: {devices_resp.status_code}")
        return pd.DataFrame(), {}
    devices_json = devices_resp.json()
    if not devices_json or not isinstance(devices_json, list):
        logging.warning("No TSI devices found or unexpected format.")
        return pd.DataFrame(), {}
    
    # Filter devices based on the configuration file
    configured_device_ids = get_tsi_devices()
    if configured_device_ids and "placeholder_device_1" in configured_device_ids:
        logging.warning("Using placeholder TSI device IDs. Please update config/tsi_stations_config.py with your actual device IDs.")

    if configured_device_ids:
        all_devices_from_api = {d['device_id']: d for d in devices_json}
        selected_devices = [all_devices_from_api[dev_id] for dev_id in configured_device_ids if dev_id in all_devices_from_api]
        
        found_ids = {d['device_id'] for d in selected_devices}
        not_found_ids = set(configured_device_ids) - found_ids
        if not_found_ids:
            logging.warning(f"The following configured TSI device IDs were not found in your account: {', '.join(not_found_ids)}")
        
        if not selected_devices:
            logging.error("None of the configured TSI devices were found. Aborting TSI data fetch.")
            return pd.DataFrame(), {}
        logging.info(f"Found {len(selected_devices)} configured TSI devices to process.")
    else:
        selected_devices = devices_json
        logging.info(f"No specific TSI devices configured. Processing all {len(selected_devices)} devices found in account.")

    start_date_iso = to_iso8601(start_date)
    end_date_iso = to_iso8601(end_date)
    results = await fetch_all_devices(selected_devices, start_date_iso, end_date_iso, headers, per_device)
    all_rows = []
    per_device_dfs = {}
    for df, device_name in results:
        if df is not None:
            all_rows.append(df)
            if per_device:
                per_device_dfs[device_name] = df.copy()
    if not all_rows:
        return pd.DataFrame(), per_device_dfs
    combined_df = pd.concat(all_rows, ignore_index=True)
    return combined_df, per_device_dfs

def separate_sensor_data_by_type(wu_df, tsi_df):
    """
    Enhanced sensor data separation with improved error handling and logging.
    
    Separates sensor data into test and production categories based on configured
    test sensor IDs, with comprehensive validation and detailed reporting.
    
    Args:
        wu_df: Weather Underground DataFrame
        tsi_df: TSI sensor DataFrame  
        
    Returns:
        tuple: (test_data, prod_data) dictionaries with separated DataFrames
    """
    # Initialize TestSensorConfig
    try:
        test_config = TestSensorConfig()
        if 'is_test_sensor' not in dir(test_config):
            logging.warning("TestSensorConfig is missing 'is_test_sensor' method. Cannot separate test/prod data.")
            return {'wu': None, 'tsi': None}, {'wu': wu_df, 'tsi': tsi_df}
    except Exception as e:
        logging.warning(f"Could not initialize TestSensorConfig: {e}. Cannot separate test/prod data.")
        return {'wu': None, 'tsi': None}, {'wu': wu_df, 'tsi': tsi_df}

    # Initialize return dictionaries with proper typing
    test_data: dict = {'wu': None, 'tsi': None}
    prod_data: dict = {'wu': None, 'tsi': None}
    
    # Statistics tracking
    separation_stats = {
        'wu_test_count': 0,
        'wu_prod_count': 0,
        'wu_unknown_count': 0,
        'tsi_test_count': 0,
        'tsi_prod_count': 0,
        'tsi_unknown_count': 0,
        'wu_test_sensors': set(),
        'wu_prod_sensors': set(),
        'tsi_test_sensors': set(),
        'tsi_prod_sensors': set()
    }
    
    # Separate Weather Underground data
    if wu_df is not None and not wu_df.empty:
        logging.info(f"Processing {len(wu_df)} Weather Underground records...")
        test_wu_rows = []
        prod_wu_rows = []
        
        for idx, row in wu_df.iterrows():
            try:
                station_id = row.get('stationID', '').strip()
                
                # Skip rows with missing station IDs
                if not station_id:
                    separation_stats['wu_unknown_count'] += 1
                    continue
                
                # Classify sensor
                if test_config.is_test_sensor(station_id):
                    test_wu_rows.append(row)
                    separation_stats['wu_test_count'] += 1
                    separation_stats['wu_test_sensors'].add(station_id)
                else:
                    prod_wu_rows.append(row)
                    separation_stats['wu_prod_count'] += 1
                    separation_stats['wu_prod_sensors'].add(station_id)
                    
            except Exception as e:
                logging.warning(f"Error processing WU row {idx}: {e}")
                separation_stats['wu_unknown_count'] += 1
                continue
        
        # Create DataFrame if we have test data
        if test_wu_rows:
            test_data['wu'] = pd.DataFrame(test_wu_rows)
            logging.info(f"Separated {len(test_wu_rows)} WU test sensor records from {len(separation_stats['wu_test_sensors'])} sensors")
            if len(separation_stats['wu_test_sensors']) <= 5:
                logging.info(f"Test sensors: {', '.join(sorted(separation_stats['wu_test_sensors']))}")
        
        # Create DataFrame if we have production data
        if prod_wu_rows:
            prod_data['wu'] = pd.DataFrame(prod_wu_rows)
            logging.info(f"Separated {len(prod_wu_rows)} WU production sensor records from {len(separation_stats['wu_prod_sensors'])} sensors")
            if len(separation_stats['wu_prod_sensors']) <= 5:
                logging.info(f"Production sensors: {', '.join(sorted(separation_stats['wu_prod_sensors']))}")
        
        if separation_stats['wu_unknown_count'] > 0:
            logging.warning(f"Skipped {separation_stats['wu_unknown_count']} WU records with missing/invalid station IDs")
    
    # Separate TSI data with enhanced field detection
    if tsi_df is not None and not tsi_df.empty:
        logging.info(f"Processing {len(tsi_df)} TSI sensor records...")
        test_tsi_rows = []
        prod_tsi_rows = []
        
        # Identify available ID fields in the TSI data
        available_id_fields = []
        potential_id_fields = ['device_id', 'device_name', 'Device Name', 'deviceId', 'deviceName', 'sensor_id', 'id']
        for field in potential_id_fields:
            if field in tsi_df.columns:
                available_id_fields.append(field)
        
        if not available_id_fields:
            logging.warning("No recognizable TSI sensor ID fields found in data")
            logging.warning(f"Available columns: {', '.join(tsi_df.columns.tolist())}")
            prod_data['tsi'] = tsi_df.copy() # Assume all are production if no ID
        else:
            logging.info(f"Using TSI ID fields: {', '.join(available_id_fields)}")
        
            for idx, row in tsi_df.iterrows():
                try:
                    # Extract all possible sensor identifiers
                    sensor_ids = set()
                    for field in available_id_fields:
                        field_value = str(row.get(field, '')).strip()
                        if field_value and field_value.lower() not in ['nan', 'none', '']:
                            sensor_ids.add(field_value)
                    
                    # Skip if no valid sensor IDs found
                    if not sensor_ids:
                        separation_stats['tsi_unknown_count'] += 1
                        continue
                    
                    # Check if any of the identifiers match test sensors
                    is_test_sensor = any(test_config.is_test_sensor(sensor_id) for sensor_id in sensor_ids)
                    
                    # Get the primary sensor ID for tracking (prefer device_id, then device_name)
                    primary_id = None
                    for field in ['device_id', 'device_name', 'Device Name']:
                        if field in row and str(row[field]).strip():
                            primary_id = str(row[field]).strip()
                            break
                    if not primary_id:
                        primary_id = next(iter(sensor_ids)) if sensor_ids else 'unknown'
                    
                    # Classify sensor
                    if is_test_sensor:
                        test_tsi_rows.append(row)
                        separation_stats['tsi_test_count'] += 1
                        separation_stats['tsi_test_sensors'].add(primary_id)
                    else:
                        prod_tsi_rows.append(row)
                        separation_stats['tsi_prod_count'] += 1
                        separation_stats['tsi_prod_sensors'].add(primary_id)
                        
                except Exception as e:
                    logging.warning(f"Error processing TSI row {idx}: {e}")
                    separation_stats['tsi_unknown_count'] += 1
                    continue
            
            # Create DataFrame if we have test data
            if test_tsi_rows:
                test_data['tsi'] = pd.DataFrame(test_tsi_rows)
                logging.info(f"Separated {len(test_tsi_rows)} TSI test sensor records from {len(separation_stats['tsi_test_sensors'])} sensors")
                if len(separation_stats['tsi_test_sensors']) <= 5:
                    logging.info(f"Test sensors: {', '.join(sorted(separation_stats['tsi_test_sensors']))}")
            
            # Create DataFrame if we have production data
            if prod_tsi_rows:
                prod_data['tsi'] = pd.DataFrame(prod_tsi_rows)
                logging.info(f"Separated {len(prod_tsi_rows)} TSI production sensor records from {len(separation_stats['tsi_prod_sensors'])} sensors")
                if len(separation_stats['tsi_prod_sensors']) <= 5:
                    logging.info(f"Production sensors: {', '.join(sorted(separation_stats['tsi_prod_sensors']))}")
            
            if separation_stats['tsi_unknown_count'] > 0:
                logging.warning(f"Skipped {separation_stats['tsi_unknown_count']} TSI records with missing/invalid sensor IDs")
    
    # Print separation summary
    total_test_records = separation_stats['wu_test_count'] + separation_stats['tsi_test_count']
    total_prod_records = separation_stats['wu_prod_count'] + separation_stats['tsi_prod_count']
    total_unknown_records = separation_stats['wu_unknown_count'] + separation_stats['tsi_unknown_count']
    
    logging.info("--- Data Separation Summary ---")
    logging.info(f"Test sensors: {total_test_records} records from {len(separation_stats['wu_test_sensors']) + len(separation_stats['tsi_test_sensors'])} sensors")
    logging.info(f"Production sensors: {total_prod_records} records from {len(separation_stats['wu_prod_sensors']) + len(separation_stats['tsi_prod_sensors'])} sensors")
    if total_unknown_records > 0:
        logging.warning(f"Unknown/invalid: {total_unknown_records} records")
    
    # Validate separation results
    if total_test_records == 0 and total_prod_records == 0 and ( (wu_df is not None and not wu_df.empty) or (tsi_df is not None and not tsi_df.empty) ):
        logging.warning("No valid sensor data was separated. Check sensor ID configurations and data quality.")
    elif total_test_records == 0 and total_prod_records > 0:
        logging.info("No test sensor data found. All data classified as production.")
    elif total_prod_records == 0 and total_test_records > 0:
        logging.info("No production sensor data found. All data classified as test.")
    
    return test_data, prod_data

async def run_collection_process(start_date_str, end_date_str, tsi_end_date_str, dry_run):
    logging.info("Starting concurrent data fetch for Weather Underground and TSI...")
    
    # Concurrently fetch both data sources
    wu_task = asyncio.create_task(fetch_wu_data_async(start_date_str, end_date_str))
    tsi_task = asyncio.create_task(fetch_tsi_data_async(start_date_str, tsi_end_date_str))
    
    wu_df, (tsi_df, _) = await asyncio.gather(wu_task, tsi_task)

    if wu_df is not None and not wu_df.empty:
        logging.info(f"Found {len(wu_df)} records from Weather Underground.")
    else:
        logging.warning("No data returned from Weather Underground.")

    if tsi_df is not None and not tsi_df.empty:
        logging.info(f"Found {len(tsi_df)} raw records from TSI. Cleaning and transforming...")
        tsi_df = clean_and_transform_tsi_data(tsi_df)
        logging.info(f"Successfully transformed {len(tsi_df)} TSI records.")
    else:
        logging.warning("No data returned from TSI.")

    logging.info("Separating test and production data...")
    test_data, prod_data = separate_sensor_data_by_type(wu_df, tsi_df)

    if dry_run:
        logging.info("--- DRY RUN MODE ENABLED ---")
        
        # Handle WU data
        if prod_data['wu'] is not None and not prod_data['wu'].empty:
            logging.info("--- WU Production Data Summary ---")
            logging.info(f"Shape: {prod_data['wu'].shape}")
            logging.info(f"Head:\n{prod_data['wu'].head().to_string()}")
            prod_data['wu'].to_csv('wu_dry_run_output.csv', index=False)
            logging.info("Full WU production data saved to 'wu_dry_run_output.csv'")
        else:
            logging.info("No WU production data to display.")

        # Handle TSI data
        if prod_data['tsi'] is not None and not prod_data['tsi'].empty:
            logging.info("--- TSI Production Data Summary ---")
            logging.info(f"Shape: {prod_data['tsi'].shape}")
            logging.info(f"Head:\n{prod_data['tsi'].head().to_string()}")
            prod_data['tsi'].to_csv('tsi_dry_run_output.csv', index=False)
            logging.info("Full TSI production data saved to 'tsi_dry_run_output.csv'")
        else:
            logging.info("No TSI production data to display.")
            
        logging.info("Dry run finished. Exiting before database insertion.")
    else:
        logging.info("--- LIVE RUN MODE ---")
        logging.info("Inserting production data into the database...")
        insert_data_to_db(prod_data['wu'], 'wu_data')
        insert_data_to_db(prod_data['tsi'], 'tsi_data')
        logging.info("Database insertion process complete.")

async def main():
    """
    Main async function to fetch data from TSI and WU, then upload to database.
    This version is non-interactive and concurrent, designed for automated execution.
    """
    parser = argparse.ArgumentParser(description="Fetch weather data for a specified date range.")
    parser.add_argument('--start-date', help="Start date in YYYY-MM-DD format.")
    parser.add_argument('--end-date', type=str, help='End date for data fetching (YYYY-MM-DD). Defaults to start date.')
    parser.add_argument('--dry-run', action='store_true', help='Run script without inserting data into DB, saving to CSV instead.')
    args = parser.parse_args()

    start_date_str = args.start_date
    end_date_str = args.end_date

    # If no start date is provided, default to yesterday
    if not start_date_str:
        start_date_dt = datetime.now() - timedelta(days=1)
        start_date_str = start_date_dt.strftime("%Y-%m-%d")
        logging.info(f"Automatically setting date range to previous day: {start_date_str} to {start_date_str}")
    
    # If no end date is provided, default to the start date
    if not end_date_str:
        end_date_str = start_date_str

    # For TSI, the end date needs to be the day after to include the full day's data.
    start_date_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    tsi_end_date_dt = end_date_dt + timedelta(days=1)
    tsi_end_date_str = tsi_end_date_dt.strftime("%Y-%m-%d")

    logging.info("Starting data collection process...")
    
    # Run the main collection process
    await run_collection_process(start_date_str, end_date_str, tsi_end_date_str, args.dry_run)

if __name__ == "__main__":
    asyncio.run(main())
