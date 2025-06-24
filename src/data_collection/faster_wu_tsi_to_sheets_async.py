import sys
import os

# Add project root to path FIRST, before importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src', 'core'))
sys.path.insert(0, os.path.join(project_root, 'config'))

# Now we can import the data manager and test sensor config
try:
    from data_manager import DataManager
except ImportError:
    try:
        from src.core.data_manager import DataManager
    except ImportError:
        DataManager = None

try:
    from test_sensors_config import TestSensorConfig, is_test_sensor, get_data_path, get_log_path
except ImportError:
    try:
        from config.test_sensors_config import TestSensorConfig, is_test_sensor, get_data_path, get_log_path
    except ImportError:
        TestSensorConfig = None
        is_test_sensor = None
        get_data_path = None
        get_log_path = None

# Import enhanced utilities
try:
    from src.utils.enhanced_logging import HotDurhamLogger
    from src.validation.data_validator import SensorDataValidator
    from src.database.db_manager import HotDurhamDB
    from src.utils.error_handler import ErrorHandler
    from src.config.config_manager import ConfigManager
    from src.monitoring.performance_monitor import PerformanceMonitor
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False
    print("💡 Enhanced features not available - using basic functionality")

import json
import pandas as pd
from datetime import datetime, timedelta
import re
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import nest_asyncio
import asyncio
import httpx
import time
import select

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials as GCreds
from googleapiclient.discovery import build

# Could add support for OneDrive upload here
try:
    import msal
except ImportError:
    msal = None

# Import data management system
# Already imported above

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
# project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ts_creds_abs = os.path.join(project_root, 'creds', 'tsi_creds.json')
google_creds_abs = os.path.join(project_root, 'creds', 'google_creds.json')
wu_api_key_abs = os.path.join(project_root, 'creds', 'wu_api_key.json')

if not os.path.exists(ts_creds_abs):
    print(f"❌ ERROR: TSI credentials not found at {ts_creds_abs}. Please upload or place your tsi_creds.json in the creds/ folder.")
    input("Press Enter to exit...")
    sys.exit(1)
if not os.path.exists(google_creds_abs):
    print(f"❌ ERROR: Google credentials not found at {google_creds_abs}. Please upload or place your google_creds.json in the creds/ folder.")
    input("Press Enter to exit...")
    sys.exit(1)
if not os.path.exists(wu_api_key_abs):
    print(f"❌ ERROR: WU API key not found at {wu_api_key_abs}. Please upload or place your wu_api_key.json in the creds/ folder.")
    input("Press Enter to exit...")
    sys.exit(1)

def get_user_inputs():
    print("Select data sources to fetch:")
    print("1. Weather Underground (WU)")
    print("2. TSI")
    print("3. Both")
    source_choice = read_or_fallback("Enter 1, 2, or 3", "3")
    fetch_wu = source_choice in ("1", "3")
    fetch_tsi = source_choice in ("2", "3")
    start_date = read_or_fallback("Enter the start date (YYYY-MM-DD):", "2025-04-01")
    end_date = read_or_fallback("Enter the end date (YYYY-MM-DD):", "2025-05-30")
    while True:
        share_email = read_or_fallback("Enter the email address to share the Google Sheet with:", "hotdurham@gmail.com").strip()
        if re.match(r"[^@]+@[^@]+\.[^@]+", share_email):
            break
        print("Invalid email address. Please enter a valid Google email address.")
    local_download = read_or_fallback("Do you want to save the data locally as well? (y/n)", "n").lower() == 'y'
    if local_download:
        file_format = read_or_fallback("Choose file format: 1 for CSV, 2 for Excel", "1")
        file_format = 'csv' if file_format == '1' else 'excel'
        download_dir = read_or_fallback("Enter directory to save files (leave blank for ./data):", "data").strip() or "data"
    else:
        file_format = None
        download_dir = None
    upload_onedrive = read_or_fallback("Do you want to upload the exported files to OneDrive? (y/n)", "n").lower() == 'y'
    if upload_onedrive:
        onedrive_folder = read_or_fallback("Enter OneDrive folder path (e.g. /Documents/HotDurham):", "/Documents/HotDurham")
    else:
        onedrive_folder = None
    return fetch_wu, fetch_tsi, start_date, end_date, share_email, local_download, file_format, download_dir, upload_onedrive, onedrive_folder

def create_gspread_client():
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = GCreds.from_service_account_file(google_creds_abs, scopes=scope)
    return gspread.authorize(creds)

def create_gspread_client_v2():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    return GCreds.from_service_account_file(google_creds_abs, scopes=scope)

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
                # print(f"DEBUG: WU API Request (httpx) to {url} with params {{'stationId': '{stationId}', 'date': '{date}'}} using timeout={client.timeout} (Attempt: {attempt_num})")
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
                            # print(f"No observations found for {stationId} on {date}.")
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
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent / "utils"))
        try:
            from tsi_date_manager import TSIDateRangeManager
        except ImportError:
            print("⚠️ Warning: TSI date manager not available, using basic date handling")
            TSIDateRangeManager = None
    
    # Check and adjust date range for TSI API limitation
    original_start, original_end = start_date, end_date
    
    if TSIDateRangeManager is not None:
        days_back = TSIDateRangeManager.get_days_back_from_start(start_date)
        days_span = TSIDateRangeManager.get_days_difference(start_date, end_date)
        
        if not TSIDateRangeManager.is_within_limit(start_date, end_date):
            print(f"⚠️ WARNING: Start date {start_date} is {days_back} days back, exceeds TSI's 90-day historical limit")
            print(f"   TSI API Error: 'start_date cannot be more than 90 days in the past'")
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
            if len(separation_stats['wu_test_sensors']) <= 5:  # Show sensor IDs if not too many
                print(f"   Test sensors: {', '.join(sorted(separation_stats['wu_test_sensors']))}")
        
        if prod_wu_rows:
            prod_data['wu'] = pd.DataFrame(prod_wu_rows)
            print(f"🏭 Separated {len(prod_wu_rows)} WU production sensor records from {len(separation_stats['wu_prod_sensors'])} sensors")
            if len(separation_stats['wu_prod_sensors']) <= 5:  # Show sensor IDs if not too many
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
            if len(separation_stats['tsi_test_sensors']) <= 5:  # Show sensor IDs if not too many
                print(f"   Test sensors: {', '.join(sorted(separation_stats['tsi_test_sensors']))}")
        
        if prod_tsi_rows:
            prod_data['tsi'] = pd.DataFrame(prod_tsi_rows)
            print(f"🏭 Separated {len(prod_tsi_rows)} TSI production sensor records from {len(separation_stats['tsi_prod_sensors'])} sensors")
            if len(separation_stats['tsi_prod_sensors']) <= 5:  # Show sensor IDs if not too many
                print(f"   Production sensors: {', '.join(sorted(separation_stats['tsi_prod_sensors']))}")
        
        if separation_stats['tsi_unknown_count'] > 0:
            print(f"⚠️ Skipped {separation_stats['tsi_unknown_count']} TSI records with missing/invalid sensor IDs")
    
    # Print separation summary
    total_test_records = separation_stats['wu_test_count'] + separation_stats['tsi_test_count']
    total_prod_records = separation_stats['wu_prod_count'] + separation_stats['tsi_prod_count']
    total_unknown_records = separation_stats['wu_unknown_count'] + separation_stats['tsi_unknown_count']
    
    print(f"\n📊 Data Separation Summary:")
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

def save_separated_sensor_data(data_manager, test_data, prod_data, start_date, end_date, pull_type, file_format='csv'):
    """
    Enhanced saving of separated sensor data with improved error handling and validation.
    
    Args:
        data_manager: DataManager instance for handling file operations
        test_data: Dictionary containing test sensor DataFrames
        prod_data: Dictionary containing production sensor DataFrames
        start_date: Start date string
        end_date: End date string
        pull_type: Type of data pull (weekly, monthly, etc.)
        file_format: File format for saving ('csv', 'json', etc.)
        
    Returns:
        dict: Dictionary with lists of saved file paths for test and production data
    """
    saved_files = {'test': [], 'production': []}
    save_stats = {'test_files': 0, 'production_files': 0, 'errors': 0}
    
    print(f"💾 Saving separated sensor data (format: {file_format})...")
    
    # Save test data with individual sensor files
    print("🧪 Processing test sensor data...")
    for data_type, df in test_data.items():
        if df is not None and not df.empty:
            try:
                # Get unique sensor IDs from test data
                sensor_id_field = 'stationID' if data_type == 'wu' else None
                
                # For TSI data, determine the appropriate ID field
                if data_type == 'tsi':
                    for field in ['device_id', 'device_name', 'Device Name']:
                        if field in df.columns:
                            sensor_id_field = field
                            break
                    
                    if not sensor_id_field:
                        print(f"⚠️ Warning: No recognizable sensor ID field found in TSI test data")
                        print(f"   Available columns: {', '.join(df.columns.tolist())}")
                        continue
                
                sensor_ids = df[sensor_id_field].unique()
                print(f"🔍 Processing {len(sensor_ids)} test {data_type.upper()} sensors...")
                
                for sensor_id in sensor_ids:
                    try:
                        # Filter data for this specific sensor
                        sensor_df = df[df[sensor_id_field] == sensor_id].copy()
                        
                        if sensor_df.empty:
                            print(f"⚠️ Warning: No data found for test sensor {sensor_id}")
                            continue
                        
                        # Validate sensor data before saving
                        if data_type == 'wu':
                            # Basic validation for WU data
                            required_cols = ['stationID', 'obsTimeUtc']
                            missing_cols = [col for col in required_cols if col not in sensor_df.columns]
                            if missing_cols:
                                print(f"⚠️ Warning: Test sensor {sensor_id} missing required columns: {missing_cols}")
                        
                        elif data_type == 'tsi':
                            # Basic validation for TSI data
                            required_cols = ['timestamp']
                            missing_cols = [col for col in required_cols if col not in sensor_df.columns]
                            if missing_cols:
                                print(f"⚠️ Warning: Test sensor {sensor_id} missing required columns: {missing_cols}")
                        
                        # Save individual sensor data
                        saved_path = data_manager.save_sensor_data(
                            sensor_id=sensor_id,
                            data_type=data_type,
                            df=sensor_df,
                            start_date=start_date,
                            end_date=end_date,
                            file_format=file_format
                        )
                        
                        if saved_path:
                            saved_files['test'].append(saved_path)
                            save_stats['test_files'] += 1
                            print(f"   ✅ Saved test {data_type.upper()} sensor {sensor_id}: {sensor_df.shape[0]} records → {saved_path}")
                        else:
                            print(f"   ❌ Failed to save test sensor {sensor_id}")
                            save_stats['errors'] += 1
                            
                    except Exception as e:
                        print(f"   ❌ Error saving test sensor {sensor_id}: {e}")
                        save_stats['errors'] += 1
                        continue
                        
            except Exception as e:
                print(f"❌ Error processing test {data_type.upper()} data: {e}")
                save_stats['errors'] += 1
                continue
    
    # Save production data using existing batch method
    print("🏭 Processing production sensor data...")
    for data_type, df in prod_data.items():
        if df is not None and not df.empty:
            try:
                print(f"🔍 Saving production {data_type.upper()} data: {df.shape[0]} records...")
                
                # Validate production data before saving
                if data_type == 'wu' and 'stationID' in df.columns:
                    unique_sensors = df['stationID'].nunique()
                    print(f"   📊 Production data contains {unique_sensors} unique WU sensors")
                elif data_type == 'tsi':
                    # Try to identify unique TSI sensors
                    sensor_count = 0
                    for field in ['device_id', 'device_name', 'Device Name']:
                        if field in df.columns:
                            sensor_count = df[field].nunique()
                            print(f"   📊 Production data contains {sensor_count} unique TSI sensors")
                            break
                
                # Use existing data manager method for production data
                # For WU data, keep the date format as YYYY-MM-DD; for TSI, convert to YYYYMMDD
                wu_start_date = start_date if data_type == 'wu' else start_date.replace('-', '')
                wu_end_date = end_date if data_type == 'wu' else end_date.replace('-', '')
                saved_path = data_manager.pull_and_store_data(
                    data_type=data_type,
                    start_date=wu_start_date,
                    end_date=wu_end_date,
                    file_format=file_format
                )
                
                if saved_path:
                    saved_files['production'].append(saved_path)
                    save_stats['production_files'] += 1
                    print(f"   ✅ Saved production {data_type.upper()} data → {saved_path}")
                else:
                    print(f"   ❌ Failed to save production {data_type.upper()} data")
                    save_stats['errors'] += 1
                    
            except Exception as e:
                print(f"❌ Error saving production {data_type.upper()} data: {e}")
                save_stats['errors'] += 1
                continue
    
    # Print save summary
    print(f"\n📊 Data Save Summary:")
    print(f"   🧪 Test sensor files saved: {save_stats['test_files']}")
    print(f"   🏭 Production data files saved: {save_stats['production_files']}")
    if save_stats['errors'] > 0:
        print(f"   ❌ Save errors encountered: {save_stats['errors']}")
    
    total_files = len(saved_files['test']) + len(saved_files['production'])
    if total_files > 0:
        print(f"   ✅ Total files successfully saved: {total_files}")
    else:
        print(f"   ⚠️ Warning: No files were saved")
    
    return saved_files

# ========== CHART CONFIGURATION ==========
# CHART IMPROVEMENTS:
# 1. Set ENABLE_OUTLIER_REMOVAL = False to disable outlier removal completely
# 2. Adjust CHART_WIDTH and CHART_HEIGHT to change chart dimensions
# 3. Modify outlier detection method in remove_outliers() function ('iqr' or 'zscore')
# 4. Set ENABLE_DISCONNECTED_POINTS = True to show data points without connecting lines

ENABLE_OUTLIER_REMOVAL = True  # Set to False to disable outlier removal
CHART_WIDTH = 1200  # Chart width in pixels (default is ~600)
CHART_HEIGHT = 400  # Chart height in pixels (default is ~300)
ENABLE_DISCONNECTED_POINTS = False  # Set to True to show data points without connecting lines

def remove_outliers(df, column, method='iqr', z_threshold=3, iqr_multiplier=1.5):
    """
    Remove outliers from a DataFrame column using IQR or Z-score method.
    
    Args:
        df: DataFrame containing the data
        column: Column name to remove outliers from
        method: 'iqr' for Interquartile Range or 'zscore' for Z-score method
        z_threshold: Z-score threshold for outlier detection (default: 3)
        iqr_multiplier: IQR multiplier for outlier detection (default: 1.5)
    
    Returns:
        DataFrame with outliers removed
    """
    if not ENABLE_OUTLIER_REMOVAL:
        return df
    
    if column not in df.columns:
        return df
    
    # Special handling: Skip outlier removal for Duke-Kestrel-01 entirely
    # This station has different measurement ranges than the other WU stations
    if 'stationID' in df.columns:
        kestrel_only = (df['stationID'] == 'KNCDURHA590').all()
        if kestrel_only:
            print(f"   📊 Skipping outlier removal for Duke-Kestrel-01 {column} (different station type)")
            return df
        
        # If mixed data, do per-station outlier removal
        if 'KNCDURHA590' in df['stationID'].values:
            return remove_outliers_per_station(df, column, method, z_threshold, iqr_multiplier)
    elif 'Station Name' in df.columns:
        kestrel_only = (df['Station Name'] == 'Duke-Kestrel-01').all()
        if kestrel_only:
            print(f"   📊 Skipping outlier removal for Duke-Kestrel-01 {column} (different station type)")
            return df
        
        # If mixed data, do per-station outlier removal
        if 'Duke-Kestrel-01' in df['Station Name'].values:
            return remove_outliers_per_station(df, column, method, z_threshold, iqr_multiplier)
    
    # Convert to numeric, replacing non-numeric values with NaN
    numeric_data = pd.to_numeric(df[column], errors='coerce')
    
    if method == 'iqr':
        # Interquartile Range method
        Q1 = numeric_data.quantile(0.25)
        Q3 = numeric_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - iqr_multiplier * IQR
        upper_bound = Q3 + iqr_multiplier * IQR
        outlier_mask = (numeric_data >= lower_bound) & (numeric_data <= upper_bound)
    elif method == 'zscore':
        # Z-score method
        mean = numeric_data.mean()
        std = numeric_data.std()
        z_scores = abs((numeric_data - mean) / std)
        outlier_mask = z_scores <= z_threshold
    else:
        # Invalid method, return original DataFrame
        return df
    
    # Filter out outliers
    filtered_df = df[outlier_mask.fillna(True)]  # Keep NaN values
    
    if len(filtered_df) != len(df):
        removed_count = len(df) - len(filtered_df)
        print(f"   📊 Outlier removal: Removed {removed_count} outliers from {column} using {method} method")
    
    return filtered_df

def remove_outliers_per_station(df, column, method='iqr', z_threshold=3, iqr_multiplier=1.5):
    """
    Remove outliers separately for each station to avoid cross-station contamination.
    
    Args:
        df: DataFrame containing the data
        column: Column name to remove outliers from
        method: 'iqr' for Interquartile Range or 'zscore' for Z-score method
        z_threshold: Z-score threshold for outlier detection (default: 3)
        iqr_multiplier: IQR multiplier for outlier detection (default: 1.5)
    
    Returns:
        DataFrame with outliers removed per station
    """
    station_col = 'stationID' if 'stationID' in df.columns else 'Station Name'
    filtered_dfs = []
    
    for station, station_df in df.groupby(station_col):
        # Skip Duke-Kestrel-01 entirely for outlier removal
        if station in ['KNCDURHA590', 'Duke-Kestrel-01']:
            print(f"   📊 Skipping outlier removal for {station} {column} (different station type)")
            filtered_dfs.append(station_df)
            continue
        
        # Apply outlier removal to this station's data only
        station_df_copy = station_df.copy()
        numeric_data = pd.to_numeric(station_df_copy[column], errors='coerce')
        
        if len(numeric_data.dropna()) < 5:  # Need at least 5 data points for outlier detection
            filtered_dfs.append(station_df_copy)
            continue
        
        if method == 'iqr':
            # Interquartile Range method
            Q1 = numeric_data.quantile(0.25)
            Q3 = numeric_data.quantile(0.75)
            IQR = Q3 - Q1
            if IQR == 0:  # All values are the same
                filtered_dfs.append(station_df_copy)
                continue
            lower_bound = Q1 - iqr_multiplier * IQR
            upper_bound = Q3 + iqr_multiplier * IQR
            outlier_mask = (numeric_data >= lower_bound) & (numeric_data <= upper_bound)
        elif method == 'zscore':
            # Z-score method
            mean = numeric_data.mean()
            std = numeric_data.std()
            if std == 0:  # All values are the same
                filtered_dfs.append(station_df_copy)
                continue
            z_scores = abs((numeric_data - mean) / std)
            outlier_mask = z_scores <= z_threshold
        else:
            # Invalid method, keep original data
            filtered_dfs.append(station_df_copy)
            continue
        
        # Filter out outliers for this station
        filtered_station_df = station_df_copy[outlier_mask.fillna(True)]
        
        if len(filtered_station_df) != len(station_df_copy):
            removed_count = len(station_df_copy) - len(filtered_station_df)
            print(f"   📊 Outlier removal for {station}: Removed {removed_count} outliers from {column} using {method} method")
        
        filtered_dfs.append(filtered_station_df)
    
    return pd.concat(filtered_dfs, ignore_index=True)

def get_chart_dimensions():
    """
    Get chart dimensions for Google Sheets charts.
    
    Returns:
        dict: Chart dimensions configuration
    """
    return {
        'width': CHART_WIDTH,
        'height': CHART_HEIGHT
    }

if __name__ == "__main__":
    (
        fetch_wu, fetch_tsi, start_date, end_date, share_email,
        local_download, file_format, download_dir, upload_onedrive, onedrive_folder
    ) = get_user_inputs()
    
    # Initialize enhanced features if available
    if ENHANCED_FEATURES_AVAILABLE:
        enhanced_logger = HotDurhamLogger("data_collection")
        data_validator = SensorDataValidator()
        db_manager = HotDurhamDB()
        error_handler = ErrorHandler()
        config_manager = ConfigManager()
        performance_monitor = PerformanceMonitor("data_collection")
        print("✨ Enhanced features initialized: logging, validation, database, error handling, config management, performance monitoring")
    else:
        enhanced_logger = None
        data_validator = None
        db_manager = None
        error_handler = None
        config_manager = None
        performance_monitor = None
    
    # Initialize data manager for organized data storage and Google Drive sync
    print("🗂️ Initializing data management system...")
    if DataManager is not None:
        data_manager = DataManager(project_root)
    else:
        print("⚠️ Warning: DataManager not available, skipping data management setup")
        data_manager = None
    
    # Initialize test sensor configuration
    print("🧪 Initializing test sensor configuration...")
    if TestSensorConfig is not None:
        test_config = TestSensorConfig(project_root)
        
        # Validate test sensor configuration
        validation_result = test_config.validate_configuration()
        
        # Display test sensor configuration status
        print(f"📋 Test sensor configuration loaded:")
        print(f"   - Total test sensors: {validation_result['stats']['total_test_sensors']}")
    else:
        print("⚠️ Warning: TestSensorConfig not available, skipping test sensor configuration")
        test_config = None
    print(f"   - WU test sensors: {validation_result['stats']['wu_test_sensors']}")
    print(f"   - TSI test sensors: {validation_result['stats']['tsi_test_sensors']}")
    print(f"   - Test data path: {test_config.test_data_path}")
    print(f"   - Production data path: {test_config.prod_data_path}")
    
    # Show validation warnings and recommendations
    if validation_result['warnings']:
        print(f"⚠️ Configuration warnings:")
        for warning in validation_result['warnings']:
            print(f"   - {warning}")
    
    if validation_result['recommendations']:
        print(f"💡 Configuration recommendations:")
        for rec in validation_result['recommendations']:
            print(f"   - {rec}")
    
    if not validation_result['is_valid']:
        print("❌ Critical configuration errors found. Please fix before proceeding:")
        for error in validation_result['errors']:
            print(f"   - {error}")
        exit(1)  # Exit with error code instead of return
    
    # Determine pull type for naming (weekly, bi-weekly, etc.)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    days_diff = (end_dt - start_dt).days
    
    if days_diff <= 7:
        pull_type = "weekly"
    elif days_diff <= 14:
        pull_type = "bi_weekly"
    elif days_diff <= 31:
        pull_type = "monthly"
    else:
        pull_type = "custom"

    if fetch_wu:
        wu_df = fetch_wu_data(start_date, end_date)
    else:
        wu_df = None
    if fetch_tsi:
        tsi_df, tsi_per_device = fetch_tsi_data(start_date, end_date)
    else:
        tsi_df, tsi_per_device = None, None

    # Separate sensor data by type (test vs production)
    print("🔍 Separating sensor data by type...")
    test_data, prod_data = separate_sensor_data_by_type(wu_df, tsi_df, test_config)
    
    # Save data using appropriate routing
    print("💾 Saving sensor data...")
    saved_files = save_separated_sensor_data(data_manager, test_data, prod_data, start_date, end_date, pull_type, file_format or 'csv')
    
    # Calculate record counts for summary (define variables in scope)
    test_wu_count = len(test_data.get('wu', pd.DataFrame())) if test_data.get('wu') is not None else 0
    test_tsi_count = len(test_data.get('tsi', pd.DataFrame())) if test_data.get('tsi') is not None else 0
    prod_wu_count = len(prod_data.get('wu', pd.DataFrame())) if prod_data.get('wu') is not None else 0
    prod_tsi_count = len(prod_data.get('tsi', pd.DataFrame())) if prod_data.get('tsi') is not None else 0

    # Display save summary with enhanced details
    print("\n" + "="*60)
    print("📊 DATA COLLECTION AND SEPARATION SUMMARY")
    print("="*60)
    
    if saved_files['test']:
        print(f"🧪 TEST SENSOR DATA ({len(saved_files['test'])} files saved):")
        for path in saved_files['test']:
            print(f"   ✅ {path}")
        
        # Display test sensor statistics
        if test_wu_count > 0 or test_tsi_count > 0:
            print(f"   📈 Records: {test_wu_count} WU + {test_tsi_count} TSI = {test_wu_count + test_tsi_count} total")
    else:
        print("🧪 TEST SENSOR DATA: No test sensor data found")
    
    print()
    if saved_files['production']:
        print(f"🏭 PRODUCTION SENSOR DATA ({len(saved_files['production'])} files saved):")
        for path in saved_files['production']:
            print(f"   ✅ {path}")
        
        # Display production sensor statistics
        if prod_wu_count > 0 or prod_tsi_count > 0:
            print(f"   📈 Records: {prod_wu_count} WU + {prod_tsi_count} TSI = {prod_wu_count + prod_tsi_count} total")
    else:
        print("🏭 PRODUCTION SENSOR DATA: No production sensor data found")
    
    # Display enhanced test sensor summary
    print(f"\n🔧 TEST SENSOR CONFIGURATION STATUS:")
    summary = data_manager.get_test_sensor_summary()
    for key, value in summary.items():
        if key == 'test_sensors':
            if value:
                print(f"   - Configured test sensors ({len(value)}): {', '.join(value)}")
            else:
                print(f"   - Configured test sensors: None")
        else:
            print(f"   - {key}: {value}")
    
    # Show separation effectiveness
    total_records = (test_wu_count + test_tsi_count + prod_wu_count + prod_tsi_count)
    if total_records > 0:
        test_percentage = ((test_wu_count + test_tsi_count) / total_records) * 100
        print(f"\n📊 DATA SEPARATION EFFECTIVENESS:")
        print(f"   - Total records processed: {total_records:,}")
        print(f"   - Test sensor data: {test_percentage:.1f}% ({test_wu_count + test_tsi_count:,} records)")
        print(f"   - Production sensor data: {100-test_percentage:.1f}% ({prod_wu_count + prod_tsi_count:,} records)")
    
    print("="*60)

    spreadsheet = None
    sheet_id = None

    # Use production data for Google Sheets (exclude test sensors from charts/tables)
    prod_wu_df = prod_data.get('wu')
    prod_tsi_df = prod_data.get('tsi')
    
    print("📊 Preparing Google Sheets with production sensor data only...")
    if prod_wu_df is not None and not prod_wu_df.empty:
        print(f"   📈 Including {len(prod_wu_df)} WU production records")
    if prod_tsi_df is not None and not prod_tsi_df.empty:
        print(f"   📈 Including {len(prod_tsi_df)} TSI production records")

    if (fetch_wu and prod_wu_df is not None and not prod_wu_df.empty) or \
       (fetch_tsi and prod_tsi_df is not None and not prod_tsi_df.empty):
        client = create_gspread_client()
        spreadsheet = client.create(f"Production_TSI_WU_Data - {datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print("🔗 Google Sheet URL:", spreadsheet.url)
        print("📋 Note: This sheet contains PRODUCTION sensors only (test sensors excluded)")
        sheet_id = spreadsheet.id
        if share_email:
            try:
                spreadsheet.share(share_email, perm_type='user', role='writer')
            except Exception as e:
                print(f"❌ Failed to share with {share_email}: {e}")

    if fetch_tsi and prod_tsi_df is not None and not prod_tsi_df.empty:
        col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)', 'NC (4)', 'NC (10)', 'PM 2.5 AQI']
        rename_map = {
            'mcpm2x5': 'PM 2.5',
            'temp_c': 'T (C)',
            'rh_percent': 'RH (%)',
            'mcpm1x0': 'PM 1',
            'mcpm4x0': 'PM 4',
            'mcpm10': 'PM 10',
            'ncpm0x5': 'NC (0.5)',
            'ncpm1x0': 'NC (1)',
            'ncpm2x5': 'NC (2.5)',
            'ncpm4x0': 'NC (4)',
            'ncpm10': 'NC (10)',
            'mcpm2x5_aqi': 'PM 2.5 AQI',
            'timestamp': 'timestamp',
            'device_name': 'Device Name',
        }
        # Rename columns in production TSI data for Google Sheets
        for k, v in rename_map.items():
            if k in prod_tsi_df.columns:
                prod_tsi_df.rename(columns={k: v}, inplace=True)
        combined_data = []
        summary_data = []
        daily_summary = {}
        seen = set()
        raw_data_for_daily = []  # Store raw data with datetime objects for daily summaries
        
        print(f"📊 Processing {len(prod_tsi_df)} production TSI records for Google Sheets...")
        
        for _, row in prod_tsi_df.iterrows():
            name = row.get('Device Name', row.get('device_name', 'Unknown'))
            
            # Skip test sensors - double check using test_config
            sensor_ids = []
            for field in ['device_id', 'device_name', 'Device Name']:
                if field in row and str(row[field]).strip():
                    sensor_ids.append(str(row[field]).strip())
            
            # Skip if any of the sensor IDs match test sensors (safety check)
            if any(test_config.is_test_sensor(sensor_id) for sensor_id in sensor_ids):
                continue
            
            ts = row.get('timestamp')
            try:
                if pd.isna(ts) or ts is None:
                    continue
                hour = pd.to_datetime(str(ts)).replace(minute=0, second=0, microsecond=0)
            except:
                continue
            if (name, hour) in seen:
                continue
            seen.add((name, hour))
            
            # Store raw data with datetime for daily summaries
            raw_data_for_daily.append({
                'Device Name': name,
                'timestamp': hour,
                'PM 2.5': row.get('PM 2.5', ''),
                'T (C)': row.get('T (C)', ''),
                'RH (%)': row.get('RH (%)', ''),
            })
            
            values = [
                hour.strftime('%m-%d %H:%M'),
                row.get('PM 2.5', ''),
                row.get('T (C)', ''),
                row.get('RH (%)', ''),
                row.get('PM 1', ''),
                row.get('PM 4', ''),
                row.get('PM 10', ''),
                row.get('NC (0.5)', ''),
                row.get('NC (1)', ''),
                row.get('NC (2.5)', ''),
                row.get('NC (4)', ''),
                row.get('NC (10)', ''),
                row.get('PM 2.5 AQI', '')
            ]
            combined_data.append([name] + values)
        def sanitize_for_gs(data):
            def safe(x):
                if isinstance(x, float):
                    if pd.isna(x) or x == float('inf') or x == float('-inf'):
                        return ''
                return x
            return [[safe(v) for v in row] for row in data]
        combined_data = sanitize_for_gs(combined_data)
        summary_data = sanitize_for_gs(summary_data)
        for k in daily_summary:
            daily_summary[k] = sanitize_for_gs(daily_summary[k])
        combined_df = pd.DataFrame(combined_data, columns=["Device Name"] + col)
        
        # Create daily summaries from raw data with datetime objects
        raw_df = pd.DataFrame(raw_data_for_daily)
        print(f"📊 Creating daily summaries from {len(raw_df)} raw records...")
        
        for name, group in raw_df.groupby('Device Name'):
            group = group.copy()
            # Convert numeric columns
            for key in ['PM 2.5', 'T (C)', 'RH (%)']:
                group[key] = pd.to_numeric(group[key], errors='coerce')
            
            # Create summary data for overview sheet
            summary_data.append([
                name,
                round(group['PM 2.5'].mean(), 2) if not pd.isna(group['PM 2.5'].mean()) else '',
                round(group['T (C)'].max(), 2) if not pd.isna(group['T (C)'].max()) else '',
                round(group['T (C)'].min(), 2) if not pd.isna(group['T (C)'].min()) else '',
                round(group['RH (%)'].mean(), 2) if not pd.isna(group['RH (%)'].mean()) else ''
            ])
            
            # Create daily aggregations using datetime objects
            group['day'] = group['timestamp'].dt.date
            
            # Apply outlier removal to each metric if enabled
            if ENABLE_OUTLIER_REMOVAL:
                print(f"   📊 Applying outlier removal for device {name}")
                group = remove_outliers(group, 'PM 2.5', method='iqr')
                group = remove_outliers(group, 'T (C)', method='iqr')
                group = remove_outliers(group, 'RH (%)', method='iqr')
            
            daily = group.groupby('day').agg({
                'PM 2.5': 'mean', 'T (C)': ['min', 'max'], 'RH (%)': 'mean'
            }).reset_index()
            daily.columns = ['Day', 'Avg PM2.5', 'Min Temp', 'Max Temp', 'Avg RH']
            
            print(f"📊 Device {name}: {len(daily)} daily records")
            
            for _, drow in daily.iterrows():
                daily_summary.setdefault(name, []).append([
                    drow['Day'].strftime('%m-%d'),
                    round(drow['Avg PM2.5'], 2) if not pd.isna(drow['Avg PM2.5']) else '',
                    round(drow['Min Temp'], 1) if not pd.isna(drow['Min Temp']) else '',
                    round(drow['Max Temp'], 1) if not pd.isna(drow['Max Temp']) else '',
                    round(drow['Avg RH'], 2) if not pd.isna(drow['Avg RH']) else ''
                ])
        
        print(f"📊 Daily summary created for {len(daily_summary)} devices:")
        for device, data in daily_summary.items():
            print(f"   📊 {device}: {len(data)} daily records")
        
        # Only update Google Sheets if spreadsheet was created successfully
        if spreadsheet is not None:
            ws = spreadsheet.sheet1
            ws.update([['Device Name'] + col] + combined_data)
            ws.update_title(f"Production_TSI_{start_date}_to_{end_date}")
            if summary_data:
                summary_headers = ['Device Name', 'Avg PM2.5 (µg/m³)', 'Max Temp (°C)', 'Min Temp (°C)', 'Avg RH (%)']
                ws_summary = spreadsheet.add_worksheet(title="Production TSI Summary", rows=len(summary_data)+1, cols=5)
                ws_summary.update([summary_headers] + summary_data)
        daily_headers = ['Device Name', 'Day', 'Avg PM2.5 (µg/m³)', 'Min Temp (°C)', 'Max Temp (°C)', 'Avg RH (%)']
        daily_rows = []
        for device, rows in daily_summary.items():
            for row in rows:
                daily_rows.append([device] + row)
        if daily_rows and spreadsheet is not None:
            daily_ws = spreadsheet.add_worksheet(title="Production TSI Daily Summary", rows=len(daily_rows)+1, cols=6)
            daily_ws.update([daily_headers] + daily_rows)
        if fetch_wu and prod_wu_df is not None and not prod_wu_df.empty and spreadsheet is not None:
            print(f"📊 Adding {len(prod_wu_df)} production WU records to Google Sheet...")
            wu_headers = prod_wu_df.columns.tolist()
            wu_ws = spreadsheet.add_worksheet(title="Production WU Data", rows=len(prod_wu_df)+1, cols=len(wu_headers))
            wu_ws.update([wu_headers] + prod_wu_df.values.tolist())
        add_charts = read_or_fallback("Do you want to add charts to the Google Sheet? (y/n)", "y").lower() == 'y'
        if add_charts and spreadsheet is not None:
            print(f"🔧 Starting chart creation process...")
            print(f"📊 Daily summary data available for {len(daily_summary)} devices: {list(daily_summary.keys())}")
            creds = create_gspread_client_v2()
            sheets_api = build('sheets', 'v4', credentials=creds)
            sheet_id = spreadsheet.id
            meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
            print(f"📋 Available sheets: {[s['properties']['title'] for s in meta['sheets']]}")
            weekly_id = next((s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == 'Production TSI Summary'), None)
            print(f"🔍 Found 'Production TSI Summary' sheet ID: {weekly_id}")
            if weekly_id:
                print("✅ Found TSI Summary sheet, proceeding with chart creation...")
                charts_title = 'Production TSI and WU Weekly Charts'
                charts_ws = spreadsheet.add_worksheet(title=charts_title, rows=20000, cols=20)
                meta2 = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                charts_id = next((s['properties']['sheetId'] for s in meta2['sheets'] if s['properties']['title'] == charts_title), None)
                chart_row_offset = 0
                data_columns = [
                    ('Avg PM2.5', 'PM2.5 (µg/m³)'),
                    ('Min Temp', 'Min Temp (°C)'),
                    ('Max Temp', 'Max Temp (°C)'),
                    ('Avg RH', 'Avg RH (%)')
                ]
                for col_name, y_label in data_columns:
                    # Change from weeks to days for daily data analysis
                    days = sorted({row[0] for rows in daily_summary.values() for row in rows})
                    devices = list(daily_summary.keys())
                    
                    # Extract year from days for chart title
                    current_year = datetime.now().year
                    if days:
                        try:
                            first_day_date = datetime.strptime(days[0], '%Y-%m-%d')
                            current_year = first_day_date.year
                        except:
                            pass
                    
                    pivot_header = ['Day'] + devices
                    idx_map = {'Avg PM2.5':1, 'Min Temp':2, 'Max Temp':3, 'Avg RH':4}
                    # Build wide-format pivot: each row is [day, dev1_val, dev2_val, ...]
                    pivot_rows = []
                    for day in days:
                        row = [day]
                        for device in devices:
                            val = ''
                            for r in daily_summary.get(device, []):
                                if r[0] == day:
                                    val = r[idx_map[col_name]]
                                    break
                            row.append(val)
                        pivot_rows.append(row)
                    def safe_gs_value(x):
                        import pandas as pd
                        import numpy as np
                        if isinstance(x, (pd.Timestamp,)):
                            return str(x)
                        if isinstance(x, float):
                            if pd.isna(x) or x == float('inf') or x == float('-inf'):
                                return ''
                            return x  # Keep numeric values as numbers
                        if isinstance(x, (int, np.integer)):
                            return x  # Keep integers as numbers
                        if x is None:
                            return ''
                        # Try to convert string representations of numbers to float
                        try:
                            float_val = float(x)
                            return float_val
                        except (ValueError, TypeError):
                            return str(x)
                    pivot_header_safe = [safe_gs_value(v) for v in pivot_header]
                    pivot_rows_safe = [[safe_gs_value(v) for v in row] for row in pivot_rows]
                    pivot_title = f"{col_name} Daily Data"
                    
                    print(f"📊 Creating {pivot_title} sheet with {len(pivot_rows_safe)} data rows and {len(devices)} devices")
                    print(f"📊 Days available: {len(days)}, Sample days: {days[:3] if len(days) >= 3 else days}")
                    
                    # Skip if no data
                    if not days or not devices or not pivot_rows_safe:
                        print(f"⚠️ Skipping {pivot_title} - no data available")
                        continue
                    
                    try:
                        old = spreadsheet.worksheet(pivot_title)
                        spreadsheet.del_worksheet(old)
                    except Exception:
                        pass
                    pivot_ws = spreadsheet.add_worksheet(title=pivot_title, rows=len(pivot_rows_safe)+1, cols=len(devices)+1)
                    pivot_ws.update([pivot_header_safe] + pivot_rows_safe)
                    meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    pivot_id = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == pivot_title)
                    series = []
                    for i, device in enumerate(devices, start=1):
                        series_config = {
                            "series": {"sourceRange": {"sources": [{
                                        "sheetId": pivot_id,
                                        "startRowIndex": 0,
                                        "endRowIndex": len(days)+1,
                                        "startColumnIndex": i,
                                        "endColumnIndex": i+1
                            }]}},
                            "targetAxis": "LEFT_AXIS"
                        }
                        # Add disconnected points style if enabled
                        if ENABLE_DISCONNECTED_POINTS:
                            # For disconnected points, we use SCATTER chart type instead of line styles
                            # This will be handled at the chart level, not series level
                            series_config["pointStyle"] = {"shape": "CIRCLE", "size": 5}
                        else:
                            # Default connected line chart
                            series_config["lineStyle"] = {"type": "SOLID"}
                        series.append(series_config)
                    domain = {"domain": {"sourceRange": {"sources": [{
                                "sheetId": pivot_id,
                                "startRowIndex": 1,
                                "endRowIndex": len(days)+1,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1
                    }]}}}
                    chart = {
                        "requests": [
                            {
                                "addChart": {
                                    "chart": {
                                        "spec": {
                                            "title": f"Daily {col_name} Trend - {current_year} (By Device)",
                                            "basicChart": {
                                                "chartType": "LINE",
                                                "legendPosition": "BOTTOM_LEGEND",
                                                "axis": [
                                                    {"position": "BOTTOM_AXIS", "title": "Day"},
                                                    {"position": "LEFT_AXIS", "title": y_label}
                                                ],
                                                "domains": [domain],
                                                "series": series,
                                                "headerCount": 1
                                            }
                                        },
                                        "position": {
                                            "overlayPosition": {
                                                "anchorCell": {
                                                    "sheetId": charts_id,
                                                    "rowIndex": chart_row_offset,
                                                    "columnIndex": 0
                                                },
                                                "widthPixels": CHART_WIDTH,
                                                "heightPixels": CHART_HEIGHT
                                            }
                                        }
                                    }
                                }
                            }
                        ]
                    }
                    try:
                        result = sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                        print(f"✅ Created chart for {col_name} (ID: {result.get('replies', [{}])[0].get('addChart', {}).get('chart', {}).get('chartId', 'unknown')})")
                    except Exception as chart_error:
                        print(f"❌ Failed to create chart for {col_name}: {chart_error}")
                    chart_row_offset += 20  # Use a fixed offset to prevent overlap

                # Add charts for WU data if available (PRODUCTION ONLY)
                if fetch_wu and prod_wu_df is not None and not prod_wu_df.empty:
                    wu_metrics = [
                        ('tempAvg', 'Temperature (C)'),
                        ('humidityAvg', 'Humidity (%)'),
                        ('heatindexAvg', 'Heat Index (C)'),  # Prioritize this version first
                        ('solarRadiationHigh', 'Solar Radiation'),
                        ('precipTotal', 'Precipitation (mm)'),
                        ('windspeedAvg', 'Wind Speed (Avg)'),
                        ('dewptAvg', 'Dew Point (C)')  # Additional useful metric
                    ]
                    # Parse obsTimeUtc back to datetime for proper time handling (PRODUCTION data)
                    prod_wu_df['obsTimeUtc'] = pd.to_datetime(prod_wu_df['obsTimeUtc'], errors='coerce')
                    # Remove any rows where obsTimeUtc couldn't be parsed
                    prod_wu_df = prod_wu_df.dropna(subset=['obsTimeUtc'])
                    
                    # Keep hourly data but create day-only labels for cleaner chart display
                    prod_wu_df['date_display'] = prod_wu_df['obsTimeUtc'].dt.strftime('%m-%d')
                    
                    station_id_to_name = {
                        "KNCDURHA548": "Duke-MS-01",
                        "KNCDURHA549": "Duke-MS-02",
                        "KNCDURHA209": "Duke-MS-03",
                        "KNCDURHA551": "Duke-MS-05",
                        "KNCDURHA555": "Duke-MS-06",
                        "KNCDURHA556": "Duke-MS-07",
                        "KNCDURHA590": "Duke-Kestrel-01"
                    }
                    prod_wu_df['Station Name'] = prod_wu_df['stationID'].map(station_id_to_name).fillna(prod_wu_df['stationID'])
                    station_names = sorted(prod_wu_df['Station Name'].unique())
                    
                    print(f"📊 WU Station Names found: {station_names}")
                    for station in station_names:
                        count = len(prod_wu_df[prod_wu_df['Station Name'] == station])
                        print(f"   📈 {station}: {count} records")
                    
                    # Ensure all metric columns are numeric for pivot_table, skip if column missing
                    for metric, _ in wu_metrics:
                        if metric in prod_wu_df.columns:
                            prod_wu_df[metric] = pd.to_numeric(prod_wu_df[metric], errors='coerce')
                    
                    # Apply outlier removal to WU metrics if enabled
                    if ENABLE_OUTLIER_REMOVAL:
                        print(f"📊 Applying outlier removal to WU data...")
                        for metric, _ in wu_metrics:
                            if metric in prod_wu_df.columns:
                                prod_wu_df = remove_outliers(prod_wu_df, metric, method='iqr')
                    
                    # Get unique timestamps for the time axis (keep hourly frequency)
                    all_times = sorted(prod_wu_df['obsTimeUtc'].unique())
                    
                    for metric, y_label in wu_metrics:
                        # Skip if metric column doesn't exist
                        if metric not in prod_wu_df.columns:
                            continue
                            
                        # Create pivot table with timestamps as index and stations as columns (hourly data)
                        pivot = prod_wu_df.pivot_table(index='obsTimeUtc', columns='Station Name', values=metric, aggfunc='mean')
                        pivot = pivot.reindex(all_times)  # Ensure all times are present
                        pivot.reset_index(inplace=True)
                        
                        # Extract year for chart title and format timestamps for display (day-month only)
                        year = pivot['obsTimeUtc'].dt.year.iloc[0] if len(pivot) > 0 else datetime.now().year
                        pivot['time_display'] = pivot['obsTimeUtc'].dt.strftime('%m-%d')
                        
                        # Skip if there's no data (all NaN values except timestamp column)
                        data_columns = [col for col in pivot.columns if col not in ['obsTimeUtc', 'time_display']]
                        if not data_columns or pivot[data_columns].isna().all().all():
                            continue
                        
                        # Filter out columns (stations) that have ALL NaN values for this metric
                        # But be more lenient - keep stations with at least some valid data
                        stations_with_data = []
                        for col in data_columns:
                            non_null_count = pivot[col].count()  # Count non-NaN values
                            total_count = len(pivot)
                            if non_null_count > 0:  # Keep stations with any valid data
                                stations_with_data.append(col)
                                # Extra debug for Duke-Kestrel-01
                                if col == 'Duke-Kestrel-01':
                                    print(f"   📊 Duke-Kestrel-01 {metric}: {non_null_count}/{total_count} non-null values in pivot table")
                        
                        # Use stations with data instead of all data columns
                        actual_station_names = stations_with_data
                        
                        # Convert to safe format for Google Sheets
                        def safe_gs_value(x):
                            import pandas as pd
                            import numpy as np
                            if isinstance(x, (pd.Timestamp,)):
                                return x.strftime('%m-%d')
                            if isinstance(x, float):
                                if pd.isna(x) or x == float('inf') or x == float('-inf'):
                                    return ''
                                return x  # Keep numeric values as numbers
                            if isinstance(x, (int, np.integer)):
                                return x  # Keep integers as numbers
                            if x is None:
                                return ''
                            # Try to convert string representations of numbers to float
                            try:
                                float_val = float(x)
                                return float_val
                            except (ValueError, TypeError):
                                return str(x)
                        
                        title = f"WU {metric} Data"
                        try:
                            old = spreadsheet.worksheet(title)
                            spreadsheet.del_worksheet(old)
                        except:
                            pass
                        
                        # Get actual station columns from pivot table (some stations might not have data for this metric)
                        # actual_station_names = [col for col in pivot.columns if col not in ['obsTimeUtc', 'time_display']]
                        # Use the filtered list from above that excludes all-NaN columns
                        
                        print(f"📊 WU {metric} chart - Stations with data: {actual_station_names}")
                        if 'Duke-Kestrel-01' not in actual_station_names:
                            print(f"⚠️ Duke-Kestrel-01 missing from {metric} data!")
                            # Check if Duke-Kestrel-01 has any non-null values for this metric
                            kestrel_data = prod_wu_df[prod_wu_df['Station Name'] == 'Duke-Kestrel-01'][metric].dropna()
                            print(f"   📊 Duke-Kestrel-01 {metric} records: {len(kestrel_data)} non-null values in source data")
                        else:
                            print(f"✅ Duke-Kestrel-01 successfully included in {metric} chart!")
                        
                        ws = spreadsheet.add_worksheet(title=title, rows=len(pivot)+1, cols=len(actual_station_names)+1)
                        # Convert pivot to safe format, use time_display for x-axis labels
                        pivot_safe = pivot.fillna('')
                        pivot_safe['time_display'] = pivot_safe['time_display'].apply(safe_gs_value)
                        for col in pivot_safe.columns:
                            if col not in ['obsTimeUtc', 'time_display']:
                                pivot_safe[col] = pivot_safe[col].apply(safe_gs_value)
                        
                        # Create sheet data with day-month labels but keep all hourly data points
                        sheet_data = []
                        for _, row in pivot_safe.iterrows():
                            sheet_row = [row['time_display']] + [row[station] for station in actual_station_names]
                            sheet_data.append(sheet_row)
                        
                        ws.update([['Date'] + actual_station_names] + sheet_data)
                        meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                        pivot_id = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == title)
                        # Build series with optional disconnected points styling
                        series = []
                        for i, _ in enumerate(actual_station_names, start=1):
                            series_config = {
                                'series': {
                                    'sourceRange': {
                                        'sources': [{
                                            'sheetId': pivot_id,
                                            'startRowIndex': 0,
                                            'endRowIndex': len(all_times)+1,
                                            'startColumnIndex': i,
                                            'endColumnIndex': i+1
                                        }]
                                    }
                                },
                                'targetAxis': 'LEFT_AXIS'
                            }
                            # Add disconnected points style if enabled
                            if ENABLE_DISCONNECTED_POINTS:
                                # For disconnected points, use SCATTER chart type instead of line style
                                series_config['pointStyle'] = {'shape': 'CIRCLE', 'size': 5}
                            else:
                                # Default connected line chart
                                series_config['lineStyle'] = {'type': 'SOLID'}
                            series.append(series_config)
                        domain = {
                            'domain': {
                                'sourceRange': {
                                    'sources': [{
                                        'sheetId': pivot_id,
                                        'startRowIndex': 1,  # Corrected from 0
                                        'endRowIndex': len(all_times)+1,
                                        'startColumnIndex': 0,
                                        'endColumnIndex': 1
                                    }]
                                }
                            }
                        }
                        chart = {
                            'requests': [{
                                'addChart': {
                                    'chart': {
                                        'spec': {
                                            'title': f'WU {metric} Trend - {year}',
                                            'basicChart': {
                                                'chartType': 'LINE',
                                                'legendPosition': 'BOTTOM_LEGEND',
                                                'axis': [
                                                    {'position': 'BOTTOM_AXIS', 'title': 'Date'},
                                                    {'position': 'LEFT_AXIS', 'title': y_label}
                                                ],
                                                'domains': [domain],
                                                'series': series,
                                                'headerCount': 1
                                            }
                                        },
                                        'position': {
                                            'overlayPosition': {
                                                'anchorCell': {
                                                    'sheetId': charts_id,
                                                    'rowIndex': chart_row_offset,
                                                    'columnIndex': 0
                                                },
                                                'widthPixels': CHART_WIDTH,
                                                'heightPixels': CHART_HEIGHT
                                            }
                                        }
                                    }
                                }
                            }]
                        }
                        try:
                            result = sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                            print(f"✅ Created WU {metric} chart (ID: {result.get('replies', [{}])[0].get('addChart', {}).get('chart', {}).get('chartId', 'unknown')})")
                        except Exception as chart_error:
                            print(f"❌ Failed to create WU {metric} chart: {chart_error}")
                        chart_row_offset += 20  # Use a fixed offset to prevent overlap

                # --- NEW: Add full time-series (hourly) sheets and charts for TSI (PRODUCTION ONLY) ---
                if fetch_tsi and prod_tsi_df is not None and not prod_tsi_df.empty:
                    # Prepare TSI time-series pivot tables and charts using PRODUCTION data only
                    tsi_metrics = [
                        ('PM 2.5', 'PM2.5 (µg/m³)'),
                        ('T (C)', 'Temperature (C)'),
                        ('RH (%)', 'Humidity (%)'),
                        ('PM 10', 'PM10 (µg/m³)')
                    ]
                    # Get all unique device names and all unique timestamps from PRODUCTION data
                    prod_tsi_df['timestamp'] = pd.to_datetime(prod_tsi_df['timestamp'], errors='coerce')
                    device_names = sorted(prod_tsi_df['Device Name'].unique())
                    
                    # Apply outlier removal to TSI time-series data if enabled
                    if ENABLE_OUTLIER_REMOVAL:
                        print(f"📊 Applying outlier removal to TSI time-series data...")
                        for metric, _ in tsi_metrics:
                            if metric in prod_tsi_df.columns:
                                prod_tsi_df = remove_outliers(prod_tsi_df, metric, method='iqr')
                    
                    all_times = sorted(prod_tsi_df['timestamp'].dropna().unique())
                    for metric, y_label in tsi_metrics:
                        # Pivot: rows = timestamp, columns = device, values = metric (PRODUCTION data only)
                        pivot = prod_tsi_df.pivot_table(index='timestamp', columns='Device Name', values=metric, aggfunc='mean')
                        pivot = pivot.reindex(all_times)  # Ensure all times are present
                        pivot.reset_index(inplace=True)
                        
                        # Extract year for chart title and format timestamp without hours/minutes for cleaner display
                        year = pivot['timestamp'].dt.year.iloc[0] if len(pivot) > 0 else datetime.now().year
                        pivot['timestamp'] = pivot['timestamp'].dt.strftime('%m-%d')
                        
                        # Skip if there's no data (all NaN values except timestamp column)
                        data_columns = [col for col in pivot.columns if col != 'timestamp']
                        if not data_columns or pivot[data_columns].isna().all().all():
                            continue
                        
                        # Filter device names to only include those with data for this metric
                        devices_with_data = []
                        for device in device_names:
                            if device in pivot.columns and pivot[device].count() > 0:
                                devices_with_data.append(device)
                        
                        print(f"📊 TSI {metric} chart - Devices with data: {devices_with_data}")
                        
                        if not devices_with_data:
                            print(f"⚠️ No devices have data for {metric}, skipping chart creation")
                            continue
                        sheet_title = f"TSI {metric} Time Series"
                        try:
                            old = spreadsheet.worksheet(sheet_title)
                            spreadsheet.del_worksheet(old)
                        except:
                            pass
                        ws = spreadsheet.add_worksheet(title=sheet_title, rows=len(pivot)+1, cols=len(devices_with_data)+1)
                        
                        # Create sheet data with only devices that have data
                        sheet_data = []
                        for _, row in pivot.iterrows():
                            sheet_row = [row['timestamp']]
                            for device in devices_with_data:
                                value = row[device] if device in row else ''
                                # Convert NaN to empty string for Google Sheets
                                if str(value).lower() in ['nan', 'none'] or value is None:
                                    value = ''
                                sheet_row.append(value)
                            sheet_data.append(sheet_row)
                        
                        ws.update([['Time'] + devices_with_data] + sheet_data)
                        # Add chart for this metric
                        meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                        sheet_id_pivot = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == sheet_title)
                        
                        # Build series with optional disconnected points styling
                        series = []
                        for i, device in enumerate(devices_with_data, start=1):
                            series_config = {
                                "series": {"sourceRange": {"sources": [{
                                    "sheetId": sheet_id_pivot,
                                    "startRowIndex": 0,
                                    "endRowIndex": len(pivot)+1,
                                    "startColumnIndex": i,
                                    "endColumnIndex": i+1
                                }]}},
                                "targetAxis": "LEFT_AXIS"
                            }
                            # Add disconnected points style if enabled
                            if ENABLE_DISCONNECTED_POINTS:
                                # For disconnected points, use point styling with no lines
                                series_config["pointStyle"] = {"shape": "CIRCLE", "size": 5}
                            else:
                                # Default connected line chart
                                series_config["lineStyle"] = {"type": "SOLID"}
                            series.append(series_config)
                        domain = {"domain": {"sourceRange": {"sources": [{
                            "sheetId": sheet_id_pivot,
                            "startRowIndex": 1,
                            "endRowIndex": len(pivot)+1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1
                        }]}}}
                        chart = {
                            "requests": [
                                {
                                    "addChart": {
                                        "chart": {
                                            "spec": {
                                                "title": f"TSI {metric} Over Time - {year}",
                                                "basicChart": {
                                                    "chartType": "LINE",
                                                    "legendPosition": "BOTTOM_LEGEND",
                                                    "axis": [
                                                        {"position": "BOTTOM_AXIS", "title": "Date & Time"},
                                                        {"position": "LEFT_AXIS", "title": y_label}
                                                    ],
                                                    "domains": [domain],
                                                    "series": series,
                                                    "headerCount": 1
                                                }
                                            },
                                            "position": {
                                                "overlayPosition": {
                                                    "anchorCell": {
                                                        "sheetId": charts_id,
                                                        "rowIndex": chart_row_offset,
                                                        "columnIndex": 0
                                                    },
                                                    "widthPixels": CHART_WIDTH,
                                                    "heightPixels": CHART_HEIGHT
                                                }
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                        try:
                            result = sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                            print(f"✅ Created TSI time-series chart for {metric} (ID: {result.get('replies', [{}])[0].get('addChart', {}).get('chart', {}).get('chartId', 'unknown')})")
                        except Exception as chart_error:
                            print(f"❌ Failed to create TSI time-series chart for {metric}: {chart_error}")
                        chart_row_offset += 20
            else:
                print("❌ 'Production TSI Summary' sheet not found - charts will not be created")
                print(f"📋 Available sheets: {[s['properties']['title'] for s in meta['sheets']]}")
        else:
            if not add_charts:
                print("⏭️ Chart creation skipped by user choice")
            if spreadsheet is None:
                print("❌ No spreadsheet available for chart creation")

    print("✅ All data processing and Google Sheet export complete!")
    
    # Add summary about test sensor exclusion
    print("\n" + "="*60)
    print("📊 GOOGLE SHEETS SUMMARY")
    print("="*60)
    if spreadsheet is not None:
        print("✅ Google Sheet created successfully with PRODUCTION data only")
        print("🔗 Sheet URL:", spreadsheet.url)
        print("📋 Sheet Contents:")
        print("   ✅ Production TSI sensor data (test sensors excluded)")
        print("   ✅ Production WU sensor data (test sensors excluded)")
        print("   ✅ Production-only charts and summaries")
        print("   🧪 Test sensor data excluded from all sheets and charts")
        
        if test_wu_count > 0 or test_tsi_count > 0:
            print(f"\n📊 Excluded from Google Sheets:")
            if test_wu_count > 0:
                print(f"   🧪 {test_wu_count} test WU sensor records")
            if test_tsi_count > 0:
                print(f"   🧪 {test_tsi_count} test TSI sensor records")
            print("   💾 Test data saved separately for internal analysis")
    else:
        print("⚠️ No Google Sheet created - no production data available")
    print("="*60)
    
    # Save data using the data manager for organized storage
    print("💾 Saving data with organized folder structure...")
    if fetch_wu and wu_df is not None and not wu_df.empty:
        wu_saved_path = data_manager.save_raw_data(
            data=wu_df,
            source='wu',
            start_date=start_date,
            end_date=end_date,
            pull_type=pull_type,
            file_format=file_format if file_format else 'csv'
        )
        print(f"📁 WU data saved to: {wu_saved_path}")
    
    if fetch_tsi and tsi_df is not None and not tsi_df.empty:
        tsi_saved_path = data_manager.save_raw_data(
            data=tsi_df,
            source='tsi',
            start_date=start_date,
            end_date=end_date,
            pull_type=pull_type,
            file_format=file_format if file_format else 'csv'
        )
        print(f"📁 TSI data saved to: {tsi_saved_path}")
    
    # Save Google Sheet info for tracking
    if spreadsheet is not None:
        sheet_info = {
            'sheet_id': sheet_id,
            'sheet_url': spreadsheet.url,
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range': f"{start_date} to {end_date}",
            'pull_type': pull_type,
            'data_sources': []
        }
        if fetch_wu:
            sheet_info['data_sources'].append('Weather Underground')
        if fetch_tsi:
            sheet_info['data_sources'].append('TSI')
        
        data_manager.save_sheet_metadata(sheet_info, start_date, end_date, pull_type)
        print(f"📋 Google Sheet metadata saved")
    
    # Sync to Google Drive if enabled
    print("☁️ Syncing data to Google Drive...")
    try:
        data_manager.sync_to_drive()
        print("✅ Google Drive sync completed successfully!")
    except Exception as e:
        print(f"⚠️ Google Drive sync failed: {e}")
        print("Data is still saved locally in the organized folder structure.")
    
    # Legacy local download support (for backward compatibility)
    if local_download and download_dir and download_dir != "data":
        print(f"📦 Also saving to legacy download directory: {download_dir}")
        if download_dir is not None:
            os.makedirs(download_dir, exist_ok=True)
            if fetch_wu and wu_df is not None and not wu_df.empty:
                wu_path = os.path.join(download_dir, f"WU_{start_date}_to_{end_date}.{file_format if file_format else 'csv'}")
                if file_format == 'excel':
                    wu_df.to_excel(wu_path, index=False)
                else:
                    wu_df.to_csv(wu_path, index=False)
                print(f"WU data also saved to {wu_path}")
            if fetch_tsi and tsi_df is not None and not tsi_df.empty:
                tsi_path = os.path.join(download_dir, f"TSI_{start_date}_to_{end_date}.{file_format if file_format else 'csv'}")
                if file_format == 'excel':
                    tsi_df.to_excel(tsi_path, index=False)
                else:
                    tsi_df.to_csv(tsi_path, index=False)
                print(f"TSI data also saved to {tsi_path}")
    
    if upload_onedrive and msal is not None:
        print("OneDrive upload not implemented in this script. Please use a separate tool or script for OneDrive uploads.")
    
    print("🎉 Done! Data has been organized, saved locally, and synced to Google Drive.")
