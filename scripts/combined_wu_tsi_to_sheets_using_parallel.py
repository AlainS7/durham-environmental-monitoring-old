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
    # Local download prompt
    local_download = read_or_fallback("Do you want to save the data locally as well? (y/n)", "n").lower() == 'y'
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
    def fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=30):
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
    all_data = fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=30)
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
    import pandas as pd
    import requests
    import time
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm
    # Ensure ISO 8601 format for TSI API
    def to_iso8601(date_str):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT00:00:00Z")
        except Exception:
            return date_str  # fallback if already in correct format
    start_date_iso = to_iso8601(start_date)
    end_date_iso = to_iso8601(end_date)
    with open(ts_creds_abs) as f:
        tsi_creds = json.load(f)
    auth_resp = requests.post(
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
    # 1. Get device list
    devices_url = "https://api-prd.tsilink.com/api/v3/external/devices"
    devices_resp = requests.get(devices_url, headers=headers)
    if devices_resp.status_code != 200:
        print(f"Failed to fetch TSI devices. Status code: {devices_resp.status_code}")
        print(f"Response: {devices_resp.text}")
        return pd.DataFrame(), {}
    try:
        devices_json = devices_resp.json()
        # Fetch a sample device's data to inspect available fields
        if devices_json and isinstance(devices_json, list):
            sample_device = devices_json[0]
            device_id = sample_device.get('device_id')
            if device_id:
                data_url = "https://api-prd.tsilink.com/api/v3/external/telemetry"
                params = {
                    'device_id': device_id,
                    'start_date': start_date_iso,
                    'end_date': end_date_iso
                }
                data_resp = requests.get(data_url, headers=headers, params=params)
                if data_resp.status_code == 200:
                    data_json = data_resp.json()
                    if isinstance(data_json, list) and data_json:
                        pass  # No print
                    else:
                        pass  # No print
                else:
                    pass  # No print
    except Exception as e:
        print("Failed to parse TSI devices response as JSON:", e)
        return pd.DataFrame(), {}
    devices = devices_json  # FIX: API returns a list, not a dict
    if not devices:
        print("No TSI devices found.")
        return pd.DataFrame(), {}
    # Always include all devices, no prompt
    selected_devices = devices

    def fetch_device_data(device):
        device_id = device.get('device_id')
        device_name = device.get('metadata', {}).get('friendlyName') or device_id
        data_url = "https://api-prd.tsilink.com/api/v3/external/telemetry"
        params = {
            'device_id': device_id,
            'start_date': start_date_iso,
            'end_date': end_date_iso
        }
        for attempt in range(3):
            data_resp = requests.get(data_url, headers=headers, params=params)
            if data_resp.status_code == 200:
                break
            time.sleep(2)
        if data_resp.status_code != 200:
            print(f"Failed to fetch data for device {device_name}. Status code: {data_resp.status_code}")
            print(f"Response: {data_resp.text}")
            return None, device_name
        data_json = data_resp.json()
        records = data_json if isinstance(data_json, list) else data_json.get('data', [])
        if not records:
            return None, device_name
        df = pd.DataFrame(records)
        # Extract measurement values from sensors
        def extract_measurements(sensors):
            result = {}
            if isinstance(sensors, list):
                for sensor in sensors:
                    for m in sensor.get('measurements', []):
                        mtype = m.get('type')
                        value = m.get('data', {}).get('value')
                        # If multiple measurements of the same type, keep the latest (by timestamp)
                        timestamp = m.get('data', {}).get('timestamp')
                        if mtype is not None:
                            # If already present, compare timestamps
                            if mtype in result:
                                prev_timestamp = result[mtype + '_ts'] if mtype + '_ts' in result else None
                                if prev_timestamp and timestamp and timestamp > prev_timestamp:
                                    result[mtype] = value
                                    result[mtype + '_ts'] = timestamp
                            else:
                                result[mtype] = value
                                result[mtype + '_ts'] = timestamp
            # Remove timestamp helper keys
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

    all_rows = []
    per_device_dfs = {}
    max_workers = min(10, len(selected_devices)) if len(selected_devices) > 1 else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_device_data, device): device for device in selected_devices}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching TSI data (parallel)", unit="device"):
            df, device_name = future.result()
            if df is not None:
                all_rows.append(df)
                if per_device:
                    per_device_dfs[device_name] = df.copy()
    if not all_rows:
        return pd.DataFrame(), per_device_dfs
    combined_df = pd.concat(all_rows, ignore_index=True)
    return combined_df, per_device_dfs

if __name__ == "__main__":
    # Get user options interactively
    (
        fetch_wu, fetch_tsi, start_date, end_date, share_email,
        local_download, file_format, download_dir, upload_onedrive, onedrive_folder
    ) = get_user_inputs()
    # You can now call fetch_wu_data, fetch_tsi_data, etc. as needed
    if fetch_wu:
        wu_df = fetch_wu_data(start_date, end_date)
    else:
        wu_df = None
    if fetch_tsi:
        tsi_df, tsi_per_device = fetch_tsi_data(start_date, end_date)
    else:
        tsi_df, tsi_per_device = None, None

    # Gather and organize TSI data like tsi_to_google_sheets.py
    if fetch_tsi and tsi_df is not None and not tsi_df.empty:
        # Ensure columns exist and are named as expected
        col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)', 'NC (4)', 'NC (10)', 'PM 2.5 AQI']
        # Rename columns if needed
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
        # Combine data for all devices
        combined_data = []
        summary_data = []
        weekly_summary = {}
        seen = set()
        for _, row in tsi_df.iterrows():
            name = row.get('Device Name', row.get('device_name', 'Unknown'))
            ts = row.get('timestamp')
            try:
                hour = pd.to_datetime(ts).replace(minute=0, second=0, microsecond=0)
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
        # Sanitize summary_data, weekly_summary, and combined_data for Google Sheets
        def sanitize_for_gs(data):
            # Recursively replace NaN, inf, -inf with '' in lists of lists
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
        # Create DataFrame for combined data
        combined_df = pd.DataFrame(combined_data, columns=["Device Name"] + col)
        # Summary statistics per device
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
                    round(wrow['Min Temp'], 2) if not pd.isna(wrow['Min Temp']) else '',
                    round(wrow['Max Temp'], 2) if not pd.isna(wrow['Max Temp']) else '',
                    round(wrow['Avg RH'], 2) if not pd.isna(wrow['Avg RH']) else ''
                ])
        # At this point, combined_df, summary_data, and weekly_summary are ready for export
        # Export to Google Sheets (like tsi_to_google_sheets.py)
        client = create_gspread_client()
        spreadsheet = client.create(f"TSI/WU Data - {datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print("🔗 Google Sheet URL:", spreadsheet.url)
        if share_email:
            try:
                spreadsheet.share(share_email, perm_type='user', role='writer')
            except Exception as e:
                print(f"❌ Failed to share with {share_email}: {e}")
        # Combined TSI data
        ws = spreadsheet.sheet1
        ws.update([['Device Name'] + col] + combined_data)
        ws.update_title(f"Combined_TSI_{start_date}_to_{end_date}")
        # Summary sheet
        if summary_data:
            summary_headers = ['Device Name', 'Avg PM2.5 (µg/m³)', 'Max Temp (°C)', 'Min Temp (°C)', 'Avg RH (%)']
            ws_summary = spreadsheet.add_worksheet(title="TSI Summary", rows=str(len(summary_data)+1), cols="5")
            ws_summary.update([summary_headers] + summary_data)
        # Weekly summary sheet
        weekly_headers = ['Device Name', 'Week Start', 'Avg PM2.5 (µg/m³)', 'Min Temp (°C)', 'Max Temp (°C)', 'Avg RH (%)']
        weekly_rows = []
        for device, rows in weekly_summary.items():
            for row in rows:
                weekly_rows.append([device] + row)
        if weekly_rows:
            weekly_ws = spreadsheet.add_worksheet(title="TSI Weekly Summary", rows=str(len(weekly_rows)+1), cols="6")
            weekly_ws.update([weekly_headers] + weekly_rows)

        # Export Weather Underground data if available
        if fetch_wu and wu_df is not None and not wu_df.empty:
            wu_headers = wu_df.columns.tolist()
            wu_ws = spreadsheet.add_worksheet(title="WU Data", rows=str(len(wu_df)+1), cols=str(len(wu_headers)))
            wu_ws.update([wu_headers] + wu_df.values.tolist())

        # Ask user if they want to add charts
        add_charts = read_or_fallback("Do you want to add charts to the Google Sheet? (y/n)", "y").lower() == 'y'
        if add_charts:
            import time
            time.sleep(5)
            creds = create_gspread_client_v2()
            sheets_api = build('sheets', 'v4', credentials=creds)
            sheet_id = spreadsheet.id
            meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
            weekly_id = next((s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == 'TSI Weekly Summary'), None)
            anchor_col = len(weekly_headers) - 1
            if weekly_id:
                # For each data column (e.g., PM2.5, Min Temp, Max Temp, Avg RH), create a chart with all devices as series
                data_columns = [
                    (2, 'Avg PM2.5', 'PM2.5 (µg/m³)'),
                    (3, 'Min Temp', 'Min Temp (°C)'),
                    (4, 'Max Temp', 'Max Temp (°C)'),
                    (5, 'Avg RH', 'Avg RH (%)')
                ]
                for col_idx, col_name, y_label in data_columns:
                    device_row_ranges = []
                    row_idx = 1
                    for device, rows in weekly_summary.items():
                        device_row_ranges.append((device, row_idx, row_idx + len(rows)))
                        row_idx += len(rows)
                    chart_series = []
                    for device, start_row, end_row in device_row_ranges:
                        chart_series.append({
                            "series": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": weekly_id,
                                        "startRowIndex": start_row,
                                        "endRowIndex": end_row,
                                        "startColumnIndex": col_idx,
                                        "endColumnIndex": col_idx + 1
                                    }]
                                }
                            },
                            "targetAxis": "LEFT_AXIS",
                            "seriesOverride": {"pointShape": "CIRCLE"}
                        })
                    chart_req = {
                        "requests": [
                            {
                                "addChart": {
                                    "chart": {
                                        "spec": {
                                            "title": f"Weekly {col_name} Trend (All Devices)",
                                            "basicChart": {
                                                "chartType": "LINE",
                                                "legendPosition": "BOTTOM_LEGEND",
                                                "axis": [
                                                    {"position": "BOTTOM_AXIS", "title": "Week"},
                                                    {"position": "LEFT_AXIS", "title": y_label}
                                                ],
                                                "domains": [{
                                                    "domain": {
                                                        "sourceRange": {
                                                            "sources": [{
                                                                "sheetId": weekly_id,
                                                                "startRowIndex": 1,
                                                                "endRowIndex": row_idx,
                                                                "startColumnIndex": 1,
                                                                "endColumnIndex": 2
                                                            }]
                                                        }
                                                    }
                                                }],
                                                "series": chart_series
                                            }
                                        },
                                        "position": {
                                            "overlayPosition": {
                                                "anchorCell": {
                                                    "sheetId": weekly_id,
                                                    "rowIndex": 0,
                                                    "columnIndex": anchor_col + col_idx
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        ]
                    }
                    sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart_req).execute()
