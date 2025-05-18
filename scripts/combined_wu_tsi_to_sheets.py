import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
import re
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo
from dateutil import parser
import time

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials as GCreds
from googleapiclient.discovery import build

# Add for OneDrive upload
try:
    import msal
except ImportError:
    msal = None

def read_or_fallback(prompt, default=None):
    try:
        if sys.stdin.isatty():
            val = input(f"{prompt} [{default}]: ") if default else input(prompt)
            return val if val else (default if default is not None else "")
        import select
        if select.select([sys.stdin], [], [], 0.1)[0]:
            val = sys.stdin.readline().strip()
            return val if val else (default if default is not None else "")
        else:
            val = input(f"{prompt} [{default}]: ") if default else input(prompt)
            return val if val else (default if default is not None else "")
    except Exception:
        val = input(f"{prompt} [{default}]: ") if default else input(prompt)
        return val if val else (default if default is not None else "")

# Use robust file path gathering for creds
script_dir = os.path.dirname(os.path.abspath(__file__))
tsi_creds_path = os.path.join(script_dir, '..', 'creds', 'tsi_creds.json')
google_creds_path = os.path.join(script_dir, '..', 'creds', 'google_creds.json')
wu_api_key_path = os.path.join(script_dir, '..', 'creds', 'wu_api_key.json')

# Normalize to absolute paths
ts_creds_abs = os.path.abspath(tsi_creds_path)
google_creds_abs = os.path.abspath(google_creds_path)
wu_api_key_abs = os.path.abspath(wu_api_key_path)

if not os.path.exists(ts_creds_abs):
    print(f"❌ ERROR: TSI credentials not found at {ts_creds_abs}. Please upload or place your tsi_creds.json in the creds/ folder.")
    sys.exit(1)
if not os.path.exists(google_creds_abs):
    print(f"❌ ERROR: Google credentials not found at {google_creds_abs}. Please upload or place your google_creds.json in the creds/ folder.")
    sys.exit(1)
if not os.path.exists(wu_api_key_abs):
    print(f"❌ ERROR: WU API key not found at {wu_api_key_abs}. Please upload or place your wu_api_key.json in the creds/ folder.")
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
    # Local download prompt
    local_download = read_or_fallback("Do you want to save the data locally as well? (y/n)", "y").lower() == 'y'
    if local_download:
        file_format = read_or_fallback("Choose file format: 1 for CSV, 2 for Excel", "1")
        file_format = 'csv' if file_format == '1' else 'excel'
        download_dir = read_or_fallback("Enter directory to save files (leave blank for ./data):", "data").strip() or "data"
    else:
        file_format = None
        download_dir = None
    # OneDrive upload prompt
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
    creds = ServiceAccountCredentials.from_json_keyfile_name(google_creds_abs, scope)
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
    def get_station_data(stationId, date, key):
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
        try:
            r = requests.get(url, params=params, timeout=30)
            return r
        except requests.exceptions.Timeout:
            print(f"Timeout occurred for station {stationId} on {date}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed for station {stationId} on {date}: {e}")
            return None
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    def fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=10):
        all_data = []
        total_requests = ((end_date - start_date).days + 1) * len(stations)
        tasks = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for single_date in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
                date_str = single_date.strftime("%Y%m%d")
                for station in stations:
                    stationId = station['stationId']
                    tasks.append(executor.submit(get_station_data, stationId, date_str, wu_key))
            with tqdm(total=total_requests, desc="Fetching WU data (parallel)") as pbar:
                for future in as_completed(tasks):
                    result = future.result()
                    if result is not None:
                        all_data.append(result)
                    pbar.update(1)
        return all_data
    all_data = fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=10)
    collected_data = []
    columns = [
        'stationId', 'obsTimeUtc', 'tempAvg', 'humidityAvg', 'solarRadiationHigh',
        'winddirAvg', 'windspeedAvg', 'precipTotal', 'heatindexAvg'
    ]
    for response in all_data:
        try:
            if response.status_code != 200:
                continue
            data = response.json()
            for obs in data['observations']:
                obs_time = pd.to_datetime(obs['obsTimeUtc']).round('h')
                row = [
                    obs['stationID'],
                    obs_time,
                    obs['metric']['tempAvg'],
                    obs['humidityAvg'],
                    obs['solarRadiationHigh'],
                    obs['winddirAvg'],
                    obs['metric']['windspeedAvg'],
                    obs['metric']['precipTotal'],
                    obs['metric']['heatindexAvg']
                ]
                collected_data.append(row)
        except Exception:
            continue
    df = pd.DataFrame(collected_data, columns=columns)
    df['obsTimeUtc'] = df['obsTimeUtc'].astype(str)
    df = df.replace([pd.NA, pd.NaT, float('inf'), float('-inf')], '')
    df = df.fillna('')
    return df

def fetch_tsi_data(start_date, end_date, combine_mode='yes', per_device=False):
    with open(ts_creds_abs) as f:
        tsi_creds = json.load(f)
    auth_resp = requests.post(
        'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken',
        params={'grant_type': 'client_credentials'},
        data={'client_id': tsi_creds['key'], 'client_secret': tsi_creds['secret']}
    )
    access_token = auth_resp.json()['access_token']
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    devices = requests.get("https://api-prd.tsilink.com/api/v3/external/devices", headers=headers).json()
    col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)', 'NC (4)', 'NC (10)', 'PM 2.5 AQI']
    combined_data = []
    per_device_dfs = {}
    def extract_value(row, t):
        for s in row.get('sensors', []):
            for m in s.get('measurements', []):
                if m.get('type') == t and 'data' in m and 'value' in m['data']:
                    return m['data']['value']
        return ""
    start_dt = datetime.fromisoformat(start_date).strftime('%Y-%m-%dT00:00:00Z')
    end_dt = datetime.fromisoformat(end_date).strftime('%Y-%m-%dT23:59:59Z')
    for d in devices:
        device_id = d['device_id']
        name = d['metadata']['friendlyName']
        params = {'start_date': start_dt, 'end_date': end_dt, 'device_id': device_id}
        r = requests.get("https://api-prd.tsilink.com/api/v3/external/telemetry", headers=headers, params=params)
        if r.status_code != 200:
            continue
        seen = set()
        device_data = []
        for row in r.json():
            try:
                ts = parser.isoparse(row['cloud_timestamp']).astimezone(ZoneInfo('America/New_York'))
                hour = ts.replace(minute=0, second=0, microsecond=0)
            except:
                continue
            if hour in seen: continue
            seen.add(hour)
            values = [
                hour.strftime('%Y-%m-%d %H:%M:%S'),
                extract_value(row, 'mcpm2x5'),
                extract_value(row, 'temp_c'),
                extract_value(row, 'rh_percent'),
                extract_value(row, 'mcpm1x0'),
                extract_value(row, 'mcpm4x0'),
                extract_value(row, 'mcpm10'),
                extract_value(row, 'ncpm0x5'),
                extract_value(row, 'ncpm1x0'),
                extract_value(row, 'ncpm2x5'),
                extract_value(row, 'ncpm4x0'),
                extract_value(row, 'ncpm10'),
                extract_value(row, 'mcpm2x5_aqi')
            ]
            combined_data.append([name] + values)
            device_data.append([name] + values)
        if per_device:
            headers = ["Device Name"] + col
            per_device_dfs[name] = pd.DataFrame(device_data, columns=headers)
    headers = ["Device Name"] + col
    df = pd.DataFrame(combined_data, columns=headers)
    df = df.replace([pd.NA, pd.NaT, float('inf'), float('-inf')], '')
    df = df.fillna('')
    return df, per_device_dfs if per_device else None

# OneDrive upload helper

def upload_to_onedrive(local_path, remote_folder, filename):
    """
    Uploads a file to OneDrive using Microsoft Graph API.
    Requires creds/onedrive_creds.json with client_id, client_secret, tenant_id.
    """
    if msal is None:
        print("msal library not installed. Please install it with 'pip install msal'. Skipping OneDrive upload.")
        return
    import json
    with open('creds/onedrive_creds.json') as f:
        creds = json.load(f)
    client_id = creds['client_id']
    client_secret = creds['client_secret']
    tenant_id = creds['tenant_id']
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://graph.microsoft.com/.default"]
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    result = app.acquire_token_for_client(scopes=scope)
    if "access_token" not in result:
        print("Failed to get access token for OneDrive upload.")
        return
    access_token = result["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
    # Remove leading slash for API
    remote_folder = remote_folder.lstrip('/')
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{remote_folder}/{filename}:/content"
    with open(local_path, 'rb') as f:
        resp = requests.put(upload_url, headers=headers, data=f)
    if resp.status_code in (200, 201):
        print(f"Uploaded {filename} to OneDrive folder {remote_folder}")
    else:
        print(f"Failed to upload {filename} to OneDrive: {resp.status_code} {resp.text}")

def main():
    fetch_wu, fetch_tsi, start_date, end_date, share_email, local_download, file_format, download_dir, upload_onedrive, onedrive_folder = get_user_inputs()
    client = create_gspread_client()
    spreadsheet = client.create(f"Combined WU & TSI Data - {start_date} to {end_date}")
    spreadsheet.share(share_email, perm_type='user', role='writer')
    print("🔗 Google Sheet URL:", spreadsheet.url)
    exported_files = []
    if local_download and not os.path.exists(download_dir):
        os.makedirs(download_dir)
    if fetch_wu:
        print("Fetching Weather Underground data...")
        wu_df = fetch_wu_data(start_date, end_date)
        ws_wu = spreadsheet.sheet1
        ws_wu.update_title('WU')
        ws_wu.update([wu_df.columns.values.tolist()] + wu_df.values.tolist())
        print("WU data uploaded to sheet 'WU'.")
        if local_download:
            wu_filename = os.path.join(download_dir, f"WU_{start_date}_to_{end_date}.{ 'csv' if file_format == 'csv' else 'xlsx'}")
            if file_format == 'csv':
                wu_df.to_csv(wu_filename, index=False)
            else:
                wu_df.to_excel(wu_filename, index=False)
            print(f"WU data also saved locally to {wu_filename}")
            exported_files.append(wu_filename)
    if fetch_tsi:
        print("Fetching TSI data...")
        tsi_df, per_device_dfs = fetch_tsi_data(start_date, end_date, per_device=True)
        if fetch_wu:
            ws_tsi = spreadsheet.add_worksheet(title='TSI', rows=str(len(tsi_df)+1), cols=str(len(tsi_df.columns)))
        else:
            ws_tsi = spreadsheet.sheet1
            ws_tsi.update_title('TSI')
        ws_tsi.update([tsi_df.columns.values.tolist()] + tsi_df.values.tolist())
        print("TSI data uploaded to sheet 'TSI'.")
        if local_download:
            tsi_filename = os.path.join(download_dir, f"TSI_{start_date}_to_{end_date}.{ 'csv' if file_format == 'csv' else 'xlsx'}")
            if file_format == 'csv':
                tsi_df.to_csv(tsi_filename, index=False)
            else:
                tsi_df.to_excel(tsi_filename, index=False)
            print(f"TSI data also saved locally to {tsi_filename}")
            exported_files.append(tsi_filename)
            # Per-device export
            for device_name, device_df in per_device_dfs.items():
                safe_name = re.sub(r'[^\w\-_\. ]', '_', device_name)
                device_file = os.path.join(download_dir, f"TSI_{safe_name}_{start_date}_to_{end_date}.{ 'csv' if file_format == 'csv' else 'xlsx'}")
                if file_format == 'csv':
                    device_df.to_csv(device_file, index=False)
                else:
                    device_df.to_excel(device_file, index=False)
                print(f"TSI per-device data saved to {device_file}")
                exported_files.append(device_file)
    # Upload to OneDrive if requested
    if upload_onedrive:
        for fpath in exported_files:
            fname = os.path.basename(fpath)
            upload_to_onedrive(fpath, onedrive_folder, fname)
    print("Done.")

