import sys
import os

# Add project root to path FIRST, before importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src', 'core'))
sys.path.insert(0, os.path.join(project_root, 'config'))

# Now we can import the data manager and test sensor config
from data_manager import DataManager
from test_sensors_config import TestSensorConfig, is_test_sensor, get_data_path, get_log_path
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
    start_date = read_or_fallback("Enter the start date (YYYY-MM-DD):", "2025-03-01")
    end_date = read_or_fallback("Enter the end date (YYYY-MM-DD):", "2025-04-30")
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
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT00:00:00Z")
    except Exception:
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
        df['timestamp_hour'] = df['timestamp'].dt.floor('h')
        df = df.sort_values('timestamp').drop_duplicates(['timestamp_hour'], keep='first')
        df = df.drop(columns=['timestamp_hour'])
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
    """Separate sensor data into test and production based on sensor IDs."""
    test_data = {'wu': None, 'tsi': None}
    prod_data = {'wu': None, 'tsi': None}
    
    # Separate Weather Underground data
    if wu_df is not None and not wu_df.empty:
        test_wu_rows = []
        prod_wu_rows = []
        
        for _, row in wu_df.iterrows():
            station_id = row.get('stationID', '')
            if test_config.is_test_sensor(station_id):
                test_wu_rows.append(row)
            else:
                prod_wu_rows.append(row)
        
        if test_wu_rows:
            test_data['wu'] = pd.DataFrame(test_wu_rows)
            print(f"🧪 Found {len(test_wu_rows)} WU test sensor records")
        if prod_wu_rows:
            prod_data['wu'] = pd.DataFrame(prod_wu_rows)
            print(f"🏭 Found {len(prod_wu_rows)} WU production sensor records")
    
    # Separate TSI data
    if tsi_df is not None and not tsi_df.empty:
        test_tsi_rows = []
        prod_tsi_rows = []
        
        for _, row in tsi_df.iterrows():
            # Check multiple possible ID fields
            device_id = row.get('device_id', '')
            device_name = row.get('device_name', '')
            friendly_name = row.get('Device Name', device_name)
            
            # Check if any of the identifiers match test sensors
            is_test = (test_config.is_test_sensor(device_id) or 
                      test_config.is_test_sensor(device_name) or 
                      test_config.is_test_sensor(friendly_name))
            
            if is_test:
                test_tsi_rows.append(row)
            else:
                prod_tsi_rows.append(row)
        
        if test_tsi_rows:
            test_data['tsi'] = pd.DataFrame(test_tsi_rows)
            print(f"🧪 Found {len(test_tsi_rows)} TSI test sensor records")
        if prod_tsi_rows:
            prod_data['tsi'] = pd.DataFrame(prod_tsi_rows)
            print(f"🏭 Found {len(prod_tsi_rows)} TSI production sensor records")
    
    return test_data, prod_data

def save_separated_sensor_data(data_manager, test_data, prod_data, start_date, end_date, pull_type, file_format='csv'):
    """Save separated sensor data to appropriate locations."""
    saved_files = {'test': [], 'production': []}
    
    # Save test data
    for data_type, df in test_data.items():
        if df is not None and not df.empty:
            # Get unique sensor IDs from test data
            if data_type == 'wu':
                sensor_ids = df['stationID'].unique()
            else:  # tsi
                sensor_ids = df['device_id'].unique() if 'device_id' in df.columns else df['device_name'].unique()
            
            for sensor_id in sensor_ids:
                if data_type == 'wu':
                    sensor_df = df[df['stationID'] == sensor_id]
                else:
                    if 'device_id' in df.columns:
                        sensor_df = df[df['device_id'] == sensor_id]
                    else:
                        sensor_df = df[df['device_name'] == sensor_id]
                
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
    
    # Save production data using existing method
    for data_type, df in prod_data.items():
        if df is not None and not df.empty:
            saved_path = data_manager.pull_and_store_data(
                data_type=data_type,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                file_format=file_format
            )
            if saved_path:
                saved_files['production'].append(saved_path)
    
    return saved_files

if __name__ == "__main__":
    (
        fetch_wu, fetch_tsi, start_date, end_date, share_email,
        local_download, file_format, download_dir, upload_onedrive, onedrive_folder
    ) = get_user_inputs()
    
    # Initialize data manager for organized data storage and Google Drive sync
    print("🗂️ Initializing data management system...")
    data_manager = DataManager(project_root)
    
    # Initialize test sensor configuration
    print("🧪 Initializing test sensor configuration...")
    test_config = TestSensorConfig(project_root)
    
    # Display test sensor configuration status
    print(f"📋 Test sensor configuration loaded:")
    print(f"   - Test sensors configured: {len(test_config.get_test_sensor_ids())}")
    print(f"   - Test data path: {test_config.test_data_path}")
    print(f"   - Production data path: {test_config.prod_data_path}")
    
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
    
    # Display save summary
    if saved_files['test']:
        print(f"🧪 Test sensor data saved to {len(saved_files['test'])} files:")
        for path in saved_files['test']:
            print(f"   - {path}")
    
    if saved_files['production']:
        print(f"🏭 Production sensor data saved to {len(saved_files['production'])} files:")
        for path in saved_files['production']:
            print(f"   - {path}")
    
    # Display test sensor summary
    print("📊 Test sensor configuration summary:")
    summary = data_manager.get_test_sensor_summary()
    for key, value in summary.items():
        if key == 'test_sensors':
            print(f"   - {key}: {', '.join(value) if value else 'None'}")
        else:
            print(f"   - {key}: {value}")

    spreadsheet = None
    sheet_id = None

    if (fetch_wu and wu_df is not None and not wu_df.empty) or \
       (fetch_tsi and tsi_df is not None and not tsi_df.empty):
        client = create_gspread_client()
        spreadsheet = client.create(f"TSI_WU_Data - {datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print("🔗 Google Sheet URL:", spreadsheet.url)
        sheet_id = spreadsheet.id
        if share_email:
            try:
                spreadsheet.share(share_email, perm_type='user', role='writer')
            except Exception as e:
                print(f"❌ Failed to share with {share_email}: {e}")

    if fetch_tsi and tsi_df is not None and not tsi_df.empty:
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
        for k, v in rename_map.items():
            if k in tsi_df.columns:
                tsi_df.rename(columns={k: v}, inplace=True)
        combined_data = []
        summary_data = []
        weekly_summary = {}
        seen = set()
        for _, row in tsi_df.iterrows():
            name = row.get('Device Name', row.get('device_name', 'Unknown'))
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
            values = [
                hour.strftime('%Y-%m-%d %H:%M:%S'),
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
        for k in weekly_summary:
            weekly_summary[k] = sanitize_for_gs(weekly_summary[k])
        combined_df = pd.DataFrame(combined_data, columns=["Device Name"] + col)
        for name, group in combined_df.groupby('Device Name'):
            group = group.copy()
            for key in ['PM 2.5', 'T (C)', 'RH (%)']:
                group[key] = pd.to_numeric(group[key], errors='coerce')
            summary_data.append([
                name,
                round(group['PM 2.5'].mean(), 2) if not pd.isna(group['PM 2.5'].mean()) else '',
                round(group['T (C)'].max(), 2) if not pd.isna(group['T (C)'].max()) else '',
                round(group['T (C)'].min(), 2) if not pd.isna(group['T (C)'].min()) else '',
                round(group['RH (%)'].mean(), 2) if not pd.isna(group['RH (%)'].mean()) else ''
            ])
            group['timestamp'] = pd.to_datetime(group['timestamp'], errors='coerce')
            group['week_start'] = group['timestamp'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
            weekly = group.groupby('week_start').agg({
                'PM 2.5': 'mean', 'T (C)': ['min', 'max'], 'RH (%)': 'mean'
            }).reset_index()
            weekly.columns = ['Week Start', 'Avg PM2.5', 'Min Temp', 'Max Temp', 'Avg RH']
            for _, wrow in weekly.iterrows():
                weekly_summary.setdefault(name, []).append([
                    wrow['Week Start'],
                    round(wrow['Avg PM2.5'], 2) if not pd.isna(wrow['Avg PM2.5']) else '',
                    round(wrow['Min Temp'], 1) if not pd.isna(wrow['Min Temp']) else '',
                    round(wrow['Max Temp'], 1) if not pd.isna(wrow['Max Temp']) else '',
                    round(wrow['Avg RH'], 2) if not pd.isna(wrow['Avg RH']) else ''
                ])
        
        # Only update Google Sheets if spreadsheet was created successfully
        if spreadsheet is not None:
            ws = spreadsheet.sheet1
            ws.update([['Device Name'] + col] + combined_data)
            ws.update_title(f"Combined_TSI_{start_date}_to_{end_date}")
            if summary_data:
                summary_headers = ['Device Name', 'Avg PM2.5 (µg/m³)', 'Max Temp (°C)', 'Min Temp (°C)', 'Avg RH (%)']
                ws_summary = spreadsheet.add_worksheet(title="TSI Summary", rows=len(summary_data)+1, cols=5)
                ws_summary.update([summary_headers] + summary_data)
        weekly_headers = ['Device Name', 'Week Start', 'Avg PM2.5 (µg/m³)', 'Min Temp (°C)', 'Max Temp (°C)', 'Avg RH (%)']
        weekly_rows = []
        for device, rows in weekly_summary.items():
            for row in rows:
                weekly_rows.append([device] + row)
        if weekly_rows and spreadsheet is not None:
            weekly_ws = spreadsheet.add_worksheet(title="TSI Weekly Summary", rows=len(weekly_rows)+1, cols=6)
            weekly_ws.update([weekly_headers] + weekly_rows)
        if fetch_wu and wu_df is not None and not wu_df.empty and spreadsheet is not None:
            wu_headers = wu_df.columns.tolist()
            wu_ws = spreadsheet.add_worksheet(title="WU Data", rows=len(wu_df)+1, cols=len(wu_headers))
            wu_ws.update([wu_headers] + wu_df.values.tolist())
        add_charts = read_or_fallback("Do you want to add charts to the Google Sheet? (y/n)", "y").lower() == 'y'
        if add_charts and spreadsheet is not None:
            creds = create_gspread_client_v2()
            sheets_api = build('sheets', 'v4', credentials=creds)
            sheet_id = spreadsheet.id
            meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
            weekly_id = next((s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == 'TSI Weekly Summary'), None)
            if weekly_id:
                charts_title = 'TSI and WU Weekly Charts'
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
                    weeks = sorted({row[0] for rows in weekly_summary.values() for row in rows})
                    devices = list(weekly_summary.keys())
                    
                    # Extract year from weeks for chart title
                    current_year = datetime.now().year
                    if weeks:
                        try:
                            first_week_date = datetime.strptime(weeks[0], '%Y-%m-%d')
                            current_year = first_week_date.year
                        except:
                            pass
                    
                    pivot_header = ['Week Start'] + devices
                    idx_map = {'Avg PM2.5':1, 'Min Temp':2, 'Max Temp':3, 'Avg RH':4}
                    # Build wide-format pivot: each row is [week, dev1_val, dev2_val, ...]
                    pivot_rows = []
                    for week in weeks:
                        row = [week]
                        for device in devices:
                            val = ''
                            for r in weekly_summary.get(device, []):
                                if r[0] == week:
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
                    pivot_title = f"{col_name} Weekly Data"
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
                        series.append({
                            "series": {"sourceRange": {"sources": [{
                                        "sheetId": pivot_id,
                                        "startRowIndex": 0,
                                        "endRowIndex": len(weeks)+1,
                                        "startColumnIndex": i,
                                        "endColumnIndex": i+1
                            }]}},
                            "targetAxis": "LEFT_AXIS"
                        })
                    domain = {"domain": {"sourceRange": {"sources": [{
                                "sheetId": pivot_id,
                                "startRowIndex": 1,
                                "endRowIndex": len(weeks)+1,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1
                    }]}}}
                    chart = {
                        "requests": [
                            {
                                "addChart": {
                                    "chart": {
                                        "spec": {
                                            "title": f"Weekly {col_name} Trend - {current_year} (By Device)",
                                            "basicChart": {
                                                "chartType": "LINE",
                                                "legendPosition": "BOTTOM_LEGEND",
                                                "axis": [
                                                    {"position": "BOTTOM_AXIS", "title": "Week Start"},
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
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        ]
                    }
                    sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                    chart_row_offset += 20  # Use a fixed offset to prevent overlap

                # Add charts for WU data if available
                if fetch_wu and wu_df is not None and not wu_df.empty:
                    wu_metrics = [
                        ('tempAvg', 'Temperature (C)'),
                        ('humidityAvg', 'Humidity (%)'),
                        ('heatindexAvg', 'Heat Index (C)'),  # Prioritize this version first
                        ('solarRadiationHigh', 'Solar Radiation'),
                        ('precipTotal', 'Precipitation (mm)'),
                        ('windspeedAvg', 'Wind Speed (Avg)'),
                        ('dewptAvg', 'Dew Point (C)')  # Additional useful metric
                    ]
                    # Parse obsTimeUtc back to datetime for proper time handling
                    wu_df['obsTimeUtc'] = pd.to_datetime(wu_df['obsTimeUtc'], errors='coerce')
                    # Remove any rows where obsTimeUtc couldn't be parsed
                    wu_df = wu_df.dropna(subset=['obsTimeUtc'])
                    
                    station_id_to_name = {
                        "KNCDURHA548": "Duke-MS-01",
                        "KNCDURHA549": "Duke-MS-02",
                        "KNCDURHA209": "Duke-MS-03",
                        "KNCDURHA551": "Duke-MS-05",
                        "KNCDURHA555": "Duke-MS-06",
                        "KNCDURHA556": "Duke-MS-07",
                        "KNCDURHA590": "Duke-Kestrel-01"
                    }
                    wu_df['Station Name'] = wu_df['stationID'].map(station_id_to_name).fillna(wu_df['stationID'])
                    station_names = sorted(wu_df['Station Name'].unique())
                    
                    # Create a consistent time string column for lookup
                    wu_df['obsTimeUtc_str'] = wu_df['obsTimeUtc'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    all_times = sorted(wu_df['obsTimeUtc'].unique())
                    
                    # Ensure all metric columns are numeric for pivot_table, skip if column missing
                    for metric, _ in wu_metrics:
                        if metric in wu_df.columns:
                            wu_df[metric] = pd.to_numeric(wu_df[metric], errors='coerce')
                    for metric, y_label in wu_metrics:
                        # Skip if metric column doesn't exist
                        if metric not in wu_df.columns:
                            continue
                            
                        # Use pivot_table for cleaner data reshaping
                        pivot = wu_df.pivot_table(index='obsTimeUtc', columns='Station Name', values=metric, aggfunc='mean')
                        pivot = pivot.reindex(all_times)  # Ensure all times are present
                        pivot.reset_index(inplace=True)
                        
                        # Extract year for chart title and format timestamp without year for better readability
                        year = pivot['obsTimeUtc'].dt.year.iloc[0] if len(pivot) > 0 else datetime.now().year
                        pivot['obsTimeUtc'] = pivot['obsTimeUtc'].dt.strftime('%m-%d %H:%M')
                        
                        # Skip if there's no data (all NaN values except timestamp column)
                        data_columns = [col for col in pivot.columns if col != 'obsTimeUtc']
                        if not data_columns or pivot[data_columns].isna().all().all():
                            continue
                        
                        # Convert to safe format for Google Sheets
                        def safe_gs_value(x):
                            import pandas as pd
                            import numpy as np
                            if isinstance(x, (pd.Timestamp,)):
                                return x.strftime('%Y-%m-%d %H:%M:%S')
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
                        ws = spreadsheet.add_worksheet(title=title, rows=len(pivot)+1, cols=len(station_names)+1)
                        # Convert pivot to safe format
                        pivot_safe = pivot.fillna('')
                        for col in pivot_safe.columns:
                            if col != 'obsTimeUtc':
                                pivot_safe[col] = pivot_safe[col].apply(safe_gs_value)
                        ws.update([['Time'] + station_names] + pivot_safe.values.tolist())
                        meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                        pivot_id = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == title)
                        series = [
                            {
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
                            for i, _ in enumerate(station_names, start=1)
                        ]
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
                                                    {'position': 'BOTTOM_AXIS', 'title': 'Date & Time'},
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
                                                }
                                            }
                                        }
                                    }
                                }
                            }]
                        }
                        sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                        chart_row_offset += 20  # Use a fixed offset to prevent overlap

                # --- NEW: Add full time-series (hourly) sheets and charts for TSI ---
                if fetch_tsi and tsi_df is not None and not tsi_df.empty:
                    # Prepare TSI time-series pivot tables and charts
                    tsi_metrics = [
                        ('PM 2.5', 'PM2.5 (µg/m³)'),
                        ('T (C)', 'Temperature (C)'),
                        ('RH (%)', 'Humidity (%)'),
                        ('PM 10', 'PM10 (µg/m³)')
                    ]
                    # Get all unique device names and all unique timestamps
                    tsi_df['timestamp'] = pd.to_datetime(tsi_df['timestamp'], errors='coerce')
                    device_names = sorted(tsi_df['Device Name'].unique())
                    all_times = sorted(tsi_df['timestamp'].dropna().unique())
                    for metric, y_label in tsi_metrics:
                        # Pivot: rows = timestamp, columns = device, values = metric
                        pivot = tsi_df.pivot_table(index='timestamp', columns='Device Name', values=metric, aggfunc='mean')
                        pivot = pivot.reindex(all_times)  # Ensure all times are present
                        pivot.reset_index(inplace=True)
                        
                        # Extract year for chart title and format timestamp without year for better readability
                        year = pivot['timestamp'].dt.year.iloc[0] if len(pivot) > 0 else datetime.now().year
                        pivot['timestamp'] = pivot['timestamp'].dt.strftime('%m-%d %H:%M')
                        
                        # Skip if there's no data (all NaN values except timestamp column)
                        data_columns = [col for col in pivot.columns if col != 'timestamp']
                        if not data_columns or pivot[data_columns].isna().all().all():
                            continue
                        sheet_title = f"TSI {metric} Time Series"
                        try:
                            old = spreadsheet.worksheet(sheet_title)
                            spreadsheet.del_worksheet(old)
                        except:
                            pass
                        ws = spreadsheet.add_worksheet(title=sheet_title, rows=len(pivot)+1, cols=len(device_names)+1)
                        ws.update([['Time'] + device_names] + pivot.fillna('').values.tolist())
                        # Add chart for this metric
                        meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                        sheet_id_pivot = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == sheet_title)
                        series = []
                        for i, device in enumerate(device_names, start=1):
                            series.append({
                                "series": {"sourceRange": {"sources": [{
                                    "sheetId": sheet_id_pivot,
                                    "startRowIndex": 0,
                                    "endRowIndex": len(pivot)+1,
                                    "startColumnIndex": i,
                                    "endColumnIndex": i+1
                                }]}},
                                "targetAxis": "LEFT_AXIS"
                            })
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
                                                "title": f"TSI {metric} Over Time - {year} (By Device)",
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
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                        sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                        chart_row_offset += 20

    print("✅ All data processing and Google Sheet export complete!")
    
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
