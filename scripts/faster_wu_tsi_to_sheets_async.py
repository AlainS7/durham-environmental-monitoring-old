import os
import sys
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

nest_asyncio.apply()

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
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    def get_station_data(stationId, date, key, max_retries=2):
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
        timeout_seconds = 15
        backoff_seconds = 1
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.get(url, params=params, timeout=(5,10))
                if r.status_code == 200:
                    return r
                print(f"Non-200 response for station {stationId} on {date}: {r.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Attempt {attempt} failed for {stationId} on {date}: {e}")
            import time
            time.sleep(backoff_seconds)
        return None
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    def fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=20):
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
    all_data = fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=20)
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
        # launch all fetch tasks concurrently
        tasks = [asyncio.create_task(bound_fetch(device)) for device in devices]
        # collect results as they complete with a progress bar
        for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching TSI data", unit="device"):
            results.append(await fut)
    return results

def fetch_tsi_data(start_date, end_date, combine_mode='yes', per_device=False):
    # Use the global ts_creds_abs defined at the top
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

if __name__ == "__main__":
    (
        fetch_wu, fetch_tsi, start_date, end_date, share_email,
        local_download, file_format, download_dir, upload_onedrive, onedrive_folder
    ) = get_user_inputs()
    if fetch_wu:
        wu_df = fetch_wu_data(start_date, end_date)
    else:
        wu_df = None
    if fetch_tsi:
        tsi_df, tsi_per_device = fetch_tsi_data(start_date, end_date)
    else:
        tsi_df, tsi_per_device = None, None
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
                    round(wrow['Min Temp'], 2) if not pd.isna(wrow['Min Temp']) else '',
                    round(wrow['Max Temp'], 2) if not pd.isna(wrow['Max Temp']) else '',
                    round(wrow['Avg RH'], 2) if not pd.isna(wrow['Avg RH']) else ''
                ])
        client = create_gspread_client()
        spreadsheet = client.create(f"TSI/WU Data - {datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print("🔗 Google Sheet URL:", spreadsheet.url)
        if share_email:
            try:
                spreadsheet.share(share_email, perm_type='user', role='writer')
            except Exception as e:
                print(f"❌ Failed to share with {share_email}: {e}")
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
        if weekly_rows:
            weekly_ws = spreadsheet.add_worksheet(title="TSI Weekly Summary", rows=len(weekly_rows)+1, cols=6)
            weekly_ws.update([weekly_headers] + weekly_rows)
        if fetch_wu and wu_df is not None and not wu_df.empty:
            wu_headers = wu_df.columns.tolist()
            wu_ws = spreadsheet.add_worksheet(title="WU Data", rows=len(wu_df)+1, cols=len(wu_headers))
            wu_ws.update([wu_headers] + wu_df.values.tolist())
        add_charts = read_or_fallback("Do you want to add charts to the Google Sheet? (y/n)", "y").lower() == 'y'
        if add_charts:
            creds = create_gspread_client_v2()
            sheets_api = build('sheets', 'v4', credentials=creds)
            sheet_id = spreadsheet.id
            meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
            weekly_id = next((s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == 'TSI Weekly Summary'), None)
            if weekly_id:
                # create TSI weekly charts
                charts_title = 'TSI Weekly Charts'
                charts_ws = spreadsheet.add_worksheet(title=charts_title, rows=20000, cols=20)
                # retrieve chart sheet ID
                meta2 = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                charts_id = next((s['properties']['sheetId'] for s in meta2['sheets'] if s['properties']['title'] == charts_title), None)
                # prepare vertical offset for each chart
                chart_row_offset = 0
                # pivot and chart per-device lines
                data_columns = [
                    ('Avg PM2.5', 'PM2.5 (µg/m³)'),
                    ('Min Temp', 'Min Temp (°C)'),
                    ('Max Temp', 'Max Temp (°C)'),
                    ('Avg RH', 'Avg RH (%)')
                ]
                for col_name, y_label in data_columns:
                    # pivot weekly_summary
                    weeks = sorted({row[0] for rows in weekly_summary.values() for row in rows})
                    devices = list(weekly_summary.keys())
                    pivot_header = ['Week Start'] + devices
                    idx_map = {'Avg PM2.5':1, 'Min Temp':2, 'Max Temp':3, 'Avg RH':4}
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
                    # recreate pivot sheet
                    pivot_title = f"{col_name} Weekly Data"
                    try:
                        old = spreadsheet.worksheet(pivot_title)
                        spreadsheet.del_worksheet(old)
                    except:
                        pass
                    pivot_ws = spreadsheet.add_worksheet(title=pivot_title, rows=len(pivot_rows)+1, cols=len(devices)+1)
                    pivot_ws.update([pivot_header] + pivot_rows)
                    # get pivot sheetId
                    meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    pivot_id = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == pivot_title)
                    # build chart series
                    series = []
                    for i, device in enumerate(devices, start=1):
                        series.append({
                            "series": {"sourceRange": {"sources": [{
                                        "sheetId": pivot_id,
                                        "startRowIndex": 0,  # include header row for legend labels
                                        "endRowIndex": len(weeks)+1,
                                        "startColumnIndex": i,
                                        "endColumnIndex": i+1
                        }]}},
                            "targetAxis": "LEFT_AXIS"
                        })
                    # domain
                    domain = {"domain": {"sourceRange": {"sources": [{
                                "sheetId": pivot_id,
                                "startRowIndex": 1,
                                "endRowIndex": len(weeks)+1,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1
                    }]}}}
                    # add chart for this metric
                    chart = {
                        "requests": [
                            {
                                "addChart": {
                                    "chart": {
                                        "spec": {
                                            "title": f"Weekly {col_name} Trend (By Device)",
                                            "basicChart": {
                                                "chartType": "LINE",
                                                "legendPosition": "BOTTOM_LEGEND",
                                                "axis": [
                                                    {"position": "BOTTOM_AXIS", "title": "Week"},
                                                    {"position": "LEFT_AXIS", "title": y_label}
                                                ],
                                                "domains": [domain],
                                                "series": series
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
                    chart_row_offset += len(weeks) + 3
            # now generate WU charts unconditionally (if data present)
            if fetch_wu and wu_df is not None and not wu_df.empty:
                wu_charts_title = 'WU Charts'
                wu_charts_ws = spreadsheet.add_worksheet(title=wu_charts_title, rows=20000, cols=20)
                meta3 = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                wu_charts_id = next((s['properties']['sheetId'] for s in meta3['sheets'] if s['properties']['title'] == wu_charts_title), None)
                wu_chart_row_offset = 0
                wu_metrics = [
                    ('tempAvg', 'Temp (°C)'),
                    ('humidityAvg', 'Humidity (%)'),
                    ('solarRadiationHigh', 'Solar Radiation (High)'),
                    ('windspeedAvg', 'Wind Speed (Avg)'),
                    ('precipTotal', 'Precipitation (Total)'),
                    ('heatindexAvg', 'Heat Index')
                ]
                # map Weather Underground station IDs to friendly names
                station_name_map = {
                    'KNCDURHA548': 'Duke-MS-01',
                    'KNCDURHA549': 'Duke-MS-02',
                    'KNCDURHA209': 'Duke-MS-03',
                    'KNCDURHA551': 'Duke-MS-05',
                    'KNCDURHA555': 'Duke-MS-06',
                    'KNCDURHA556': 'Duke-MS-07',
                    'KNCDURHA590': 'Duke-Kestrel-01'
                }
                times = sorted(wu_df['obsTimeUtc'].unique())
                # preserve IDs for data lookup but use names for headers
                station_ids = sorted(wu_df['stationId'].unique())
                station_names = [station_name_map.get(s, s) for s in station_ids]
                for metric, y_label in wu_metrics:
                    pivot_header = ['Time'] + station_names
                    pivot_rows = [[t] + [wu_df[(wu_df['obsTimeUtc'] == t) & (wu_df['stationId'] == s)][metric].iloc[0] if not wu_df[(wu_df['obsTimeUtc'] == t) & (wu_df['stationId'] == s)][metric].empty else '' for s in station_ids] for t in times]
                    title = f"WU {metric} Data"
                    try:
                        old = spreadsheet.worksheet(title)
                        spreadsheet.del_worksheet(old)
                    except:
                        pass
                    pivot_ws = spreadsheet.add_worksheet(title=title, rows=len(pivot_rows)+1, cols=len(station_names)+1)
                    pivot_ws.update([pivot_header] + pivot_rows)
                    meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
                    pivot_id = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == title)
                    series = [{'series': {'sourceRange': {'sources': [{'sheetId': pivot_id, 'startRowIndex': 0, 'endRowIndex': len(times)+1, 'startColumnIndex': i, 'endColumnIndex': i+1}]}}, 'targetAxis': 'LEFT_AXIS'} for i, _ in enumerate(station_ids, start=1)]
                    domain = {'domain': {'sourceRange': {'sources': [{'sheetId': pivot_id, 'startRowIndex': 1, 'endRowIndex': len(times)+1, 'startColumnIndex': 0, 'endColumnIndex': 1}]}}}
                    chart = {'requests': [{'addChart': {'chart': {'spec': {'title': f'WU {metric} Trend', 'basicChart': {'chartType': 'LINE', 'legendPosition': 'BOTTOM_LEGEND', 'axis': [{'position': 'BOTTOM_AXIS', 'title': 'Time'}, {'position': 'LEFT_AXIS', 'title': y_label}], 'domains': [domain], 'series': series}}, 'position': {'overlayPosition': {'anchorCell': {'sheetId': wu_charts_id, 'rowIndex': wu_chart_row_offset, 'columnIndex': 0}}}}}}]}
                    sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart).execute()
                    wu_chart_row_offset += 15  # stack charts with fixed 15-row spacing
