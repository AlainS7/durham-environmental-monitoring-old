import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta

import httpx
import nest_asyncio
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from tqdm import tqdm

# Add project root to path FIRST, before importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src', 'core'))
sys.path.insert(0, os.path.join(project_root, 'config'))

# Now we can import the data manager and test sensor config
try:
    from test_sensors_config import TestSensorConfig
except ImportError:
    try:
        from config.test_sensors_config import TestSensorConfig
    except ImportError:
        TestSensorConfig = None

# Load environment variables from .env file
load_dotenv()

# Database connection
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    print("❌ ERROR: Database environment variables not set. Please create a .env file with DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, and DB_NAME.")
    sys.exit(1)

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

nest_asyncio.apply()

def read_or_fallback(prompt, default=None):
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

# Use robust file path gathering for creds
ts_creds_abs = os.path.join(project_root, 'creds', 'tsi_creds.json')
wu_api_key_abs = os.path.join(project_root, 'creds', 'wu_api_key.json')

if not os.path.exists(ts_creds_abs):
    print(f"❌ ERROR: TSI credentials not found at {ts_creds_abs}. Please upload or place your tsi_creds.json in the creds/ folder.")
    input("Press Enter to exit...")
    sys.exit(1)
if not os.path.exists(wu_api_key_abs):
    print(f"❌ ERROR: WU API key not found at {wu_api_key_abs}. Please upload or place your wu_api_key.json in the creds/ folder.")
    input("Press Enter to exit...")
    sys.exit(1)

def insert_data_to_db(df, table_name):
    """Inserts a DataFrame into the specified database table."""
    if df is None or df.empty:
        print(f"No data to insert into {table_name}.")
        return
    try:
        print(f"Inserting {len(df)} rows into {table_name}...")
        df.to_sql(table_name, engine, if_exists='append', index=False)
        print(f"✅ Successfully inserted data into {table_name}.")
    except Exception as e:
        print(f"❌ ERROR inserting data into {table_name}: {e}")

def fetch_wu_data(start_date_str, end_date_str):
    with open(wu_api_key_abs) as f:
        wu_key = json.load(f)['test_api_key']
    stations = [
        {"name": "Duke-MS-01", "stationId": "KNCDURHA548"},
        {"name": "Duke-MS-02", "stationId": "KNCDURHA549"},
        {"name": "Duke-MS-03", "stationId": "KNCDURHA209"},
        {"name": "Duke-MS-05", "stationId": "KNCDURHA551"},
        {"name": "Duke-MS-06", "stationId": "KNCDURHA555"},
        {"name": "Duke-MS-07", "stationId": "KNCDURHA556"},
        {"name": "Duke-Kestrel-01", "stationId": "KNCDURHA590"}
    ]

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
                        processed_rows = []
                        for obs in data.get('observations', []):
                            obs_time = pd.to_datetime(obs.get('obsTimeUtc'), errors='coerce').round('h')
                            row = [
                                obs.get('stationID'),
                                obs_time,
                                obs.get('metric', {}).get('tempAvg'),
                                obs.get('humidityAvg'),
                                obs.get('solarRadiationHigh'),
                                obs.get('metric', {}).get('precipRate'),
                                obs.get('metric', {}).get('precipTotal'),
                                obs.get('winddirAvg'),
                                obs.get('metric', {}).get('windspeedAvg'),
                                obs.get('metric', {}).get('windgustAvg'),
                                obs.get('metric', {}).get('pressureMax'),
                                obs.get('metric', {}).get('pressureMin'),
                                obs.get('metric', {}).get('pressureTrend'),
                                obs.get('metric', {}).get('heatindexAvg'),
                                obs.get('metric', {}).get('dewptAvg')
                            ]
                            processed_rows.append(row)
                        if not processed_rows:
                            return []
                        return processed_rows
                    except json.JSONDecodeError:
                        print(f"JSONDecodeError for {stationId} on {date}. Response: {response.text[:200]}")
                    except Exception as e:
                        print(f"Error processing data for {stationId} on {date}: {e}")
                elif response.status_code == 204:
                    print(f"No content (204) for {stationId} on {date}. Assuming no data.")
                    return []
                else:
                    print(f"Attempt {attempt_num}/{max_attempts} received non-200 response (httpx) for {stationId} on {date}: {response.status_code} {response.text[:200]}")

            except httpx.TimeoutException:
                print(f"Attempt {attempt_num}/{max_attempts} timed out (httpx) for {stationId} on {date}.")
            except httpx.RequestError as e:
                print(f"Attempt {attempt_num}/{max_attempts} failed for {stationId} on {date} with httpx.RequestError: {e}")
            except Exception as e:
                print(f"Attempt {attempt_num}/{max_attempts} encountered an unexpected error for {stationId} on {date}: {e}")

            if attempt_num < max_attempts:
                delay_index = min(attempt_num - 1, len(backoff_delays) - 1)
                delay = backoff_delays[delay_index]
                print(f"Waiting {delay}s before retry {attempt_num + 1} for {stationId} on {date}...")
                time.sleep(delay)
            else:
                print(f"Final attempt {attempt_num}/{max_attempts} failed for {stationId} on {date}.")

        print(f"All {max_attempts} attempts failed to fetch/process data for {stationId} on {date} after exhausting retries (httpx).")
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
        df['obsTimeUtc'] = df['obsTimeUtc'].astype(str)
        # Replace problematic values safely
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
            print(f"⚠️ Warning: Could not parse date {date_str}, using as-is")
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
        print(f"Failed to fetch data for device {device_name}. Status code: {getattr(response, 'status_code', 'N/A')}")
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

def fetch_tsi_data(start_date, end_date, combine_mode='yes', per_device=False):
    # Import TSI date range manager
    try:
        from src.utils.tsi_date_manager import TSIDateRangeManager
    except ImportError:
        # Fallback for direct path import
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent / "utils"))
        try:
            from tsi_date_manager import TSIDateRangeManager
        except ImportError:
            print("⚠️ Warning: TSI date manager not available, using basic date handling")
            TSIDateRangeManager = None
    
    if TSIDateRangeManager is not None:
        days_back = TSIDateRangeManager.get_days_back_from_start(start_date)
        days_span = TSIDateRangeManager.get_days_difference(start_date, end_date)
        
        if not TSIDateRangeManager.is_within_limit(start_date, end_date):
            print(f"⚠️ WARNING: Start date {start_date} is {days_back} days back, exceeds TSI's 90-day historical limit")
            print("   TSI API Error: 'start_date cannot be more than 90 days in the past'")
            print("   Options:")
            print("   1. Use most recent valid date range")
            print("   2. Skip TSI data collection") 
            print("   3. Split into multiple API calls (advanced)")
            
            # For automated systems, default to most recent data
            adjusted_start, adjusted_end, was_adjusted = TSIDateRangeManager.adjust_date_range_for_tsi(
                start_date, end_date, prefer_recent=True
            )
            
            if was_adjusted:
                start_date, end_date = adjusted_start, adjusted_end
                new_days_back = TSIDateRangeManager.get_days_back_from_start(start_date)
                new_days_span = TSIDateRangeManager.get_days_difference(start_date, end_date)
                print(f"   🔄 Automatically adjusted to: {start_date} to {end_date}")
                print(f"   📊 New range: {new_days_span} days span, starting {new_days_back} days back")
        else:
            print(f"✅ TSI date range valid: {start_date} to {end_date}")
            print(f"   📊 Range: {days_span} days span, starting {days_back} days back")
    else:
        print(f"⚠️ Using basic date handling: {start_date} to {end_date}")
    
    
    if not os.path.exists(ts_creds_abs):
        print(f"❌ ERROR: TSI credentials not found at {ts_creds_abs}. Please upload or place your tsi_creds.json in the creds/ folder.")
        return pd.DataFrame(), {}
    with open(ts_creds_abs) as f:
        tsi_creds = json.load(f)
    auth_resp = httpx.post(
        'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken',
        params={'grant_type': 'client_credentials'},
        data={'client_id': tsi_creds['key'], 'client_secret': tsi_creds['secret']}
    )
    access_token = auth_resp.json().get('access_token', None)
    if not access_token:
        print("Failed to authenticate with TSI API.")
        return pd.DataFrame(), {}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    devices_url = "https://api-prd.tsilink.com/api/v3/external/devices"
    devices_resp = httpx.get(devices_url, headers=headers)
    if devices_resp.status_code != 200:
        print(f"Failed to fetch TSI devices. Status code: {devices_resp.status_code}")
        return pd.DataFrame(), {}
    devices_json = devices_resp.json()
    if not devices_json or not isinstance(devices_json, list):
        print("No TSI devices found.")
        return pd.DataFrame(), {}
    selected_devices = devices_json
    start_date_iso = to_iso8601(start_date)
    end_date_iso = to_iso8601(end_date)
    results = asyncio.run(fetch_all_devices(selected_devices, start_date_iso, end_date_iso, headers, per_device))
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

def separate_sensor_data_by_type(wu_df, tsi_df, test_config):
    """
    Enhanced sensor data separation with improved error handling and logging.
    
    Separates sensor data into test and production categories based on configured
    test sensor IDs, with comprehensive validation and detailed reporting.
    
    Args:
        wu_df: Weather Underground DataFrame
        tsi_df: TSI sensor DataFrame  
        test_config: TestSensorConfig instance
        
    Returns:
        tuple: (test_data, prod_data) dictionaries with separated DataFrames
    """
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
        print(f"🔍 Processing {len(wu_df)} Weather Underground records...")
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
                print(f"⚠️ Error processing WU row {idx}: {e}")
                separation_stats['wu_unknown_count'] += 1
                continue
        
        # Create DataFrames if we have data
        if test_wu_rows:
            test_data['wu'] = pd.DataFrame(test_wu_rows)
            print(f"🧪 Separated {len(test_wu_rows)} WU test sensor records from {len(separation_stats['wu_test_sensors'])} sensors")
            if len(separation_stats['wu_test_sensors']) <= 5:
                print(f"   Test sensors: {', '.join(sorted(separation_stats['wu_test_sensors']))}")
        
        if prod_wu_rows:
            prod_data['wu'] = pd.DataFrame(prod_wu_rows)
            print(f"🏭 Separated {len(prod_wu_rows)} WU production sensor records from {len(separation_stats['wu_prod_sensors'])} sensors")
            if len(separation_stats['wu_prod_sensors']) <= 5:
                print(f"   Production sensors: {', '.join(sorted(separation_stats['wu_prod_sensors']))}")
        
        if separation_stats['wu_unknown_count'] > 0:
            print(f"⚠️ Skipped {separation_stats['wu_unknown_count']} WU records with missing/invalid station IDs")
    
    # Separate TSI data with enhanced field detection
    if tsi_df is not None and not tsi_df.empty:
        print(f"🔍 Processing {len(tsi_df)} TSI sensor records...")
        test_tsi_rows = []
        prod_tsi_rows = []
        
        # Identify available ID fields in the TSI data
        available_id_fields = []
        potential_id_fields = ['device_id', 'device_name', 'Device Name', 'deviceId', 'deviceName', 'sensor_id', 'id']
        for field in potential_id_fields:
            if field in tsi_df.columns:
                available_id_fields.append(field)
        
        if not available_id_fields:
            print("⚠️ No recognizable TSI sensor ID fields found in data")
            print(f"   Available columns: {', '.join(tsi_df.columns.tolist())}")
        else:
            print(f"🔍 Using TSI ID fields: {', '.join(available_id_fields)}")
        
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
                print(f"⚠️ Error processing TSI row {idx}: {e}")
                separation_stats['tsi_unknown_count'] += 1
                continue
        
        # Create DataFrames if we have data
        if test_tsi_rows:
            test_data['tsi'] = pd.DataFrame(test_tsi_rows)
            print(f"🧪 Separated {len(test_tsi_rows)} TSI test sensor records from {len(separation_stats['tsi_test_sensors'])} sensors")
            if len(separation_stats['tsi_test_sensors']) <= 5:
                print(f"   Test sensors: {', '.join(sorted(separation_stats['tsi_test_sensors']))}")
        
        if prod_tsi_rows:
            prod_data['tsi'] = pd.DataFrame(prod_tsi_rows)
            print(f"🏭 Separated {len(prod_tsi_rows)} TSI production sensor records from {len(separation_stats['tsi_prod_sensors'])} sensors")
            if len(separation_stats['tsi_prod_sensors']) <= 5:
                print(f"   Production sensors: {', '.join(sorted(separation_stats['tsi_prod_sensors']))}")
        
        if separation_stats['tsi_unknown_count'] > 0:
            print(f"⚠️ Skipped {separation_stats['tsi_unknown_count']} TSI records with missing/invalid sensor IDs")
    
    # Print separation summary
    total_test_records = separation_stats['wu_test_count'] + separation_stats['tsi_test_count']
    total_prod_records = separation_stats['wu_prod_count'] + separation_stats['tsi_prod_count']
    total_unknown_records = separation_stats['wu_unknown_count'] + separation_stats['tsi_unknown_count']
    
    print("\n📊 Data Separation Summary:")
    print(f"   🧪 Test sensors: {total_test_records} records from {len(separation_stats['wu_test_sensors']) + len(separation_stats['tsi_test_sensors'])} sensors")
    print(f"   🏭 Production sensors: {total_prod_records} records from {len(separation_stats['wu_prod_sensors']) + len(separation_stats['tsi_prod_sensors'])} sensors")
    if total_unknown_records > 0:
        print(f"   ⚠️ Unknown/invalid: {total_unknown_records} records")
    
    # Validate separation results
    if total_test_records == 0 and total_prod_records == 0:
        print("⚠️ Warning: No valid sensor data was separated. Check sensor ID configurations.")
    elif total_test_records == 0:
        print("💡 Info: No test sensor data found. All data classified as production.")
    elif total_prod_records == 0:
        print("💡 Info: No production sensor data found. All data classified as test.")
    
    return test_data, prod_data

def main():
    """
    Main function to fetch data from TSI and WU, then upload to database.
    """
    print("Starting data collection process...")

    # 1. GET USER INPUT FOR DATE RANGE
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    start_date_def = yesterday.strftime("%Y-%m-%d")
    end_date_def = yesterday.strftime("%Y-%m-%d")

    start_date = read_or_fallback("Enter start date (YYYY-MM-DD)", start_date_def)
    end_date = read_or_fallback("Enter end date (YYYY-MM-DD)", end_date_def)

    # 2. FETCH DATA
    print("\nFetching Weather Underground data...")
    wu_df = fetch_wu_data(start_date, end_date)
    print(f"Found {len(wu_df)} records from Weather Underground.")

    print("\nFetching TSI data...")
    tsi_df, _ = fetch_tsi_data(start_date, end_date)
    print(f"Found {len(tsi_df)} records from TSI.")

    # 3. SEPARATE DATA (IF NEEDED)
    prod_wu_df = wu_df
    prod_tsi_df = tsi_df
    if TestSensorConfig:
        try:
            test_config = TestSensorConfig()
            if 'is_test_sensor' in dir(test_config):
                test_data, prod_data = separate_sensor_data_by_type(wu_df, tsi_df, test_config)
                prod_wu_df = prod_data.get('wu')
                prod_tsi_df = prod_data.get('tsi')
            else:
                print("TestSensorConfig does not have 'is_test_sensor' method. Skipping data separation.")

        except Exception as e:
            print(f"Could not separate test/prod data: {e}")
    else:
        print("TestSensorConfig not available. Skipping data separation.")


    # 4. INSERT DATA INTO DATABASE
    print("\nUploading data to PostgreSQL...")
    insert_data_to_db(prod_wu_df, 'wu_data')
    insert_data_to_db(prod_tsi_df, 'tsi_data')

    print("\nData collection and upload process finished.")


if __name__ == '__main__':
    main()
