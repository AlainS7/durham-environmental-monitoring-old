
from datetime import datetime
import os
import requests
import json
import pandas as pd

def safe_float(val):
    try:
        if pd.isna(val) or not pd.api.types.is_number(val) or abs(val) > 1e100:
            return ""
        return round(float(val), 2)
    except:
        return ""

from zoneinfo import ZoneInfo
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load TSI API credentials
with open('tsi_creds.json') as f:
    creds = json.load(f)

tsi_key = creds['key']
tsi_secret = creds['secret']

# Get access token
base_url = 'https://api-prd.tsilink.com/api/v3/external'
authorize_url = base_url + '/oauth/client_credential/accesstoken'

params = {
    'grant_type': 'client_credentials',
    'Content-Type': "application/x-www-form-urlencoded"
}
data = {
    'client_id': tsi_key,
    'client_secret': tsi_secret,
}
response = requests.post(authorize_url, params=params, data=data)
access_token = response.json()['access_token']

# Get list of devices
device_url = "https://api-prd.tsilink.com/api/v3/external/devices"
header = {
    "Accept": "application/json",
    "Authorization": 'Bearer ' + access_token
}
response = requests.get(device_url, headers=header)
devices = response.json()

# Google Sheets setup
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google_creds.json', scope)
client = gspread.authorize(creds)
sheet_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
spreadsheet = client.create(f"TSI Data - {sheet_timestamp}")
spreadsheet.share('email@gmail.com', perm_type='user', role='writer')  # replace with your email
print("🔗 Google Sheet URL:", spreadsheet.url)

# Columns for data
col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)',
       'NC (4)', 'NC (10)', 'PM 2.5 AQI', 'PM Cal', 'T cal', 'RH cal']

# Ask user for options
import re

def get_valid_date(prompt):
    while True:
        user_input = input(prompt)
        try:
            # Check basic format and parse
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", user_input):
                raise ValueError("Date must be in YYYY-MM-DD format.")
            dt = datetime.fromisoformat(user_input)
            return dt.strftime('%Y-%m-%d')
        except ValueError as e:
            print(f"❌ Invalid date: {e}")


sheet_mode = input("Combine all data into one sheet? (yes/no): ").strip().lower()
start_date_str = get_valid_date('Enter start date (YYYY-MM-DD): ')
end_date_str = get_valid_date('Enter end date (YYYY-MM-DD): ')
start_dt = datetime.fromisoformat(start_date_str).strftime('%Y-%m-%dT00:00:00Z')
end_dt = datetime.fromisoformat(end_date_str).strftime('%Y-%m-%dT23:59:59Z')

# Prepare combined data if needed
combined_data = []

# Loop through devices
for device in devices:
    cloud_device_id = device['device_id']
    friendly_name = device['metadata']['friendlyName']

    params = {
        'start_date': start_dt,
        'end_date': end_dt,
        'device_id': cloud_device_id
    }

    device_data_url = "https://api-prd.tsilink.com/api/v3/external/telemetry"
    response = requests.get(device_data_url, headers=header, params=params)
    print(f"Status code for device {friendly_name}: {response.status_code}")

    if response.status_code == 200:
        data = []
        hourly_seen = set()

        for row in response.json():
            tz_utc = row['cloud_timestamp'].replace('T', ' ').replace('Z', '+00:00')
            from dateutil import parser
            tz_utc = parser.isoparse(tz_utc)
            tz_est = tz_utc.astimezone(ZoneInfo('America/New_York'))
            timestamp_hour = tz_est.replace(minute=0, second=0, microsecond=0)

            if timestamp_hour in hourly_seen:
                continue
            hourly_seen.add(timestamp_hour)

            values = [
                timestamp_hour.strftime('%Y-%m-%d %H:%M:%S'),
                row.get('pm2_5', ''),
                row.get('temperature', ''),
                row.get('humidity', ''),
                row.get('pm1_0', ''),
                row.get('pm4_0', ''),
                row.get('pm10_0', ''),
                row.get('nc0_5', ''),
                row.get('nc1_0', ''),
                row.get('nc2_5', ''),
                row.get('nc4_0', ''),
                row.get('nc10_0', ''),
                row.get('pm2_5_aqi', ''),
                row.get('pm_calibrated', ''),
                row.get('temperature_calibrated', ''),
                row.get('humidity_calibrated', '')
            ]

            if sheet_mode == "yes":
                combined_data.append([friendly_name] + values)
            else:
                data.append(values)

        if sheet_mode != "yes":
            df = pd.DataFrame(data, columns=col)
            worksheet = spreadsheet.add_worksheet(title=friendly_name[:50], rows=str(len(df)+1), cols=str(len(col)))
            worksheet.update([col] + data)

    else:
        print(f"❌ Failed to retrieve data for device {friendly_name}. Status code: {response.status_code}")

# If using combined mode, write one sheet
if sheet_mode == "yes" and combined_data:
    headers = ["Device Name"] + col
    worksheet = spreadsheet.sheet1
    worksheet.update([headers] + combined_data)


# Rename combined sheet
if sheet_mode == "yes":
    worksheet.update_title(f"Combined_{start_date_str}_to_{end_date_str}")

# Add summary sheet
summary_data = []
for device in devices:
    device_name = device['metadata']['friendlyName']
    if sheet_mode == "yes":
        device_rows = [row for row in combined_data if row[0] == device_name]
        if not device_rows:
            continue
        df = pd.DataFrame(device_rows, columns=["Device Name"] + col)
    else:
        try:
            worksheet = spreadsheet.worksheet(device_name[:50])
            records = worksheet.get_all_values()[1:]  # skip header
            df = pd.DataFrame(records, columns=col)
        except:
            continue

    # Convert columns to numeric if possible
    for key in ['PM 2.5', 'T (C)', 'RH (%)']:
        df[key] = pd.to_numeric(df[key], errors='coerce')

    avg_pm25 = round(df['PM 2.5'].mean(skipna=True), 2)
    max_temp = round(df['T (C)'].max(skipna=True), 2)
    min_temp = round(df['T (C)'].min(skipna=True), 2)
    avg_humidity = round(df['RH (%)'].mean(skipna=True), 2)

    summary_data.append([
        device_name,
        safe_float(avg_pm25),
        safe_float(max_temp),
        safe_float(min_temp),
        safe_float(avg_humidity)
    ])

if summary_data:
    summary_headers = ['Device Name', 'Avg PM2.5 (µg/m³)', 'Max Temp (°C)', 'Min Temp (°C)', 'Avg RH (%)']
    summary_ws = spreadsheet.add_worksheet(title="Summary", rows=str(len(summary_data)+1), cols="5")
    summary_ws.update([summary_headers] + summary_data)


from datetime import timedelta

# Helper to get week start date
def get_week_start(dt_str):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    start = dt - timedelta(days=dt.weekday())
    return start.strftime("%Y-%m-%d")

# Weekly summary data
weekly_summary = {}

for device in devices:
    device_name = device['metadata']['friendlyName']
    if sheet_mode == "yes":
        device_rows = [row for row in combined_data if row[0] == device_name]
        if not device_rows:
            continue
        df = pd.DataFrame(device_rows, columns=["Device Name"] + col)
    else:
        try:
            worksheet = spreadsheet.worksheet(device_name[:50])
            records = worksheet.get_all_values()[1:]  # skip header
            df = pd.DataFrame(records, columns=col)
        except:
            continue

    # Convert needed columns
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    for key in ['PM 2.5', 'T (C)', 'RH (%)']:
        df[key] = pd.to_numeric(df[key], errors='coerce')

    df['week_start'] = df['timestamp'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))

    weekly = df.groupby('week_start').agg({
        'PM 2.5': 'mean',
        'T (C)': ['min', 'max'],
        'RH (%)': 'mean'
    }).reset_index()

    weekly.columns = ['Week Start', 'Avg PM2.5', 'Min Temp', 'Max Temp', 'Avg RH']
    for _, row in weekly.iterrows():
        weekly_summary.setdefault(device_name, []).append([
            row['Week Start'],  # keep this as a string
            safe_float(row['Avg PM2.5']),
            safe_float(row['Min Temp']),
            safe_float(row['Max Temp']),
            safe_float(row['Avg RH'])
        ])

# Add weekly summary sheet
weekly_headers = ['Device Name', 'Week Start', 'Avg PM2.5 (µg/m³)', 'Min Temp (°C)', 'Max Temp (°C)', 'Avg RH (%)']
weekly_rows = []
for device, rows in weekly_summary.items():
    for row in rows:
        weekly_rows.append([device] + row)

if weekly_rows:
    weekly_ws = spreadsheet.add_worksheet(title="Weekly Summary", rows=str(len(weekly_rows)+1), cols="6")
    weekly_ws.update([weekly_headers] + weekly_rows)


# Add charts to Weekly Summary sheet
import time
import google.auth
from googleapiclient.discovery import build

# Wait briefly to ensure sheet sync
time.sleep(5)

# Authenticate with Google Sheets API for charts
creds_gspread = ServiceAccountCredentials.from_json_keyfile_name('google_creds.json', scope)
scoped_creds = creds_gspread.with_scopes(['https://www.googleapis.com/auth/spreadsheets'])
authed_session = scoped_creds.authorize(http=None)
sheets_api = build('sheets', 'v4', credentials=scoped_creds)

spreadsheet_id = spreadsheet.id
weekly_sheet_id = None

# Get the sheet ID for "Weekly Summary"
sheets_meta = sheets_api.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
for sheet in sheets_meta['sheets']:
    if sheet['properties']['title'] == 'Weekly Summary':
        weekly_sheet_id = sheet['properties']['sheetId']
        break

if weekly_sheet_id:
    device_names = list(weekly_summary.keys())
    start_row = 1
    for i, device in enumerate(device_names):
        # Find rows for this device
        count = len(weekly_summary[device])
        chart_request = {
            "requests": [
                {
                    "addChart": {
                        "chart": {
                            "spec": {
                                "title": f"Weekly PM2.5 Trend - {device}",
                                "basicChart": {
                                    "chartType": "LINE",
                                    "legendPosition": "BOTTOM_LEGEND",
                                    "axis": [
                                        {"position": "BOTTOM_AXIS", "title": "Week"},
                                        {"position": "LEFT_AXIS", "title": "PM2.5 (µg/m³)"}
                                    ],
                                    "domains": [
                                        {
                                            "domain": {
                                                "sourceRange": {
                                                    "sources": [
                                                        {
                                                            "sheetId": weekly_sheet_id,
                                                            "startRowIndex": start_row,
                                                            "endRowIndex": start_row + count,
                                                            "startColumnIndex": 1,
                                                            "endColumnIndex": 2
                                                        }
                                                    ]
                                                }
                                            }
                                        }
                                    ],
                                    "series": [
                                        {
                                            "series": {
                                                "sourceRange": {
                                                    "sources": [
                                                        {
                                                            "sheetId": weekly_sheet_id,
                                                            "startRowIndex": start_row,
                                                            "endRowIndex": start_row + count,
                                                            "startColumnIndex": 3,
                                                            "endColumnIndex": 4
                                                        }
                                                    ]
                                                }
                                            },
                                            "targetAxis": "LEFT_AXIS"
                                        },
                                        {
                                            "series": {
                                                "sourceRange": {
                                                    "sources": [
                                                        {
                                                            "sheetId": weekly_sheet_id,
                                                            "startRowIndex": start_row,
                                                            "endRowIndex": start_row + count,
                                                            "startColumnIndex": 5,
                                                            "endColumnIndex": 6
                                                        }
                                                    ]
                                                }
                                            },
                                            "targetAxis": "LEFT_AXIS"
                                        },
                                        {
                                            "series": {
                                                "sourceRange": {
                                                    "sources": [
                                                        {
                                                            "sheetId": weekly_sheet_id,
                                                            "startRowIndex": start_row,
                                                            "endRowIndex": start_row + count,
                                                            "startColumnIndex": 2,
                                                            "endColumnIndex": 3
                                                        }
                                                    ]
                                                }
                                            },
                                            "targetAxis": "LEFT_AXIS"
                                        }
                                    ]
                                }
                            },
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": weekly_sheet_id,
                                        "rowIndex": start_row,
                                        "columnIndex": 7
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
        sheets_api.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=chart_request).execute()
        start_row += count
