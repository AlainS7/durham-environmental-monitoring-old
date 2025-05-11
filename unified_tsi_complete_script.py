
from datetime import datetime, timedelta
import os
import requests
import json
import pandas as pd
from zoneinfo import ZoneInfo
from dateutil import parser
import re
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import time

def safe_float(val):
    try:
        if pd.isna(val) or not pd.api.types.is_number(val) or abs(val) > 1e100:
            return ""
        return round(float(val), 2)
    except:
        return ""

def extract_value(row, target_type):
    for sensor in row.get('sensors', []):
        for m in sensor.get('measurements', []):
            if m.get('type') == target_type and 'data' in m and 'value' in m['data']:
                return m['data']['value']
    return ""

# Load TSI API credentials
with open('tsi_creds.json') as f:
    creds = json.load(f)

tsi_key = creds['key']
tsi_secret = creds['secret']

# Get access token
base_url = 'https://api-prd.tsilink.com/api/v3/external'
authorize_url = base_url + '/oauth/client_credential/accesstoken'
params = {'grant_type': 'client_credentials', 'Content-Type': "application/x-www-form-urlencoded"}
data = {'client_id': tsi_key, 'client_secret': tsi_secret}
response = requests.post(authorize_url, params=params, data=data)
access_token = response.json()['access_token']

# Get list of devices
device_url = f"{base_url}/devices"
header = {"Accept": "application/json", "Authorization": 'Bearer ' + access_token}
response = requests.get(device_url, headers=header)
devices = response.json()

# Google Sheets setup
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('google_creds.json', scopes=scope)
client = gspread.authorize(creds)
sheet_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
spreadsheet = client.create(f"TSI Data - {sheet_timestamp}")
user_email = input("Enter email to share the sheet with: ").strip()
if user_email:
    spreadsheet.share(user_email, perm_type='user', role='writer')
else:
    print("⚠️ No email entered — sheet will not be shared.")
print("🔗 Google Sheet URL:", spreadsheet.url)

col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)', 'NC (4)', 'NC (10)', 'PM 2.5 AQI']

def get_valid_date(prompt):
    while True:
        user_input = input(prompt)
        try:
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
combined_data = []

# Fetch data from each device
for device in devices:
    cloud_device_id = device['device_id']
    friendly_name = device['metadata']['friendlyName']
    params = {'start_date': start_dt, 'end_date': end_dt, 'device_id': cloud_device_id}
    response = requests.get(f"{base_url}/telemetry", headers=header, params=params)
    print(f"Status code for device {friendly_name}: {response.status_code}")

    if response.status_code == 200:
        data = []
        hourly_seen = set()

        for row in response.json():
            tz_utc = row['cloud_timestamp'].replace('T', ' ').replace('Z', '+00:00')
            tz_utc = parser.isoparse(tz_utc)
            tz_est = tz_utc.astimezone(ZoneInfo('America/New_York'))
            timestamp_hour = tz_est.replace(minute=0, second=0, microsecond=0)

            if timestamp_hour in hourly_seen:
                continue
            hourly_seen.add(timestamp_hour)

            values = [
                timestamp_hour.strftime('%Y-%m-%d %H:%M:%S'),
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

            if sheet_mode == "yes":
                combined_data.append([friendly_name] + values)
            else:
                data.append(values)

        if sheet_mode != "yes":
            df = pd.DataFrame(data, columns=col)
            worksheet = spreadsheet.add_worksheet(title=friendly_name[:50], rows=str(len(df)+1), cols=str(len(col)))
            worksheet.update([col] + data)

if sheet_mode == "yes" and combined_data:
    headers = ["Device Name"] + col
    worksheet = spreadsheet.sheet1
    worksheet.update([headers] + combined_data)
    worksheet.update_title(f"Combined_{start_date_str}_to_{end_date_str}")

# Summary Sheet
summary_data = []
for device in devices:
    name = device['metadata']['friendlyName']
    if sheet_mode == "yes":
        device_rows = [row for row in combined_data if row[0] == name]
        if not device_rows:
            continue
        df = pd.DataFrame(device_rows, columns=["Device Name"] + col)
    else:
        try:
            worksheet = spreadsheet.worksheet(name[:50])
            df = pd.DataFrame(worksheet.get_all_values()[1:], columns=col)
        except:
            continue

    for k in ['PM 2.5', 'T (C)', 'RH (%)']:
        df[k] = pd.to_numeric(df[k], errors='coerce')

    summary_data.append([name, safe_float(df['PM 2.5'].mean()), safe_float(df['T (C)'].max()), safe_float(df['T (C)'].min()), safe_float(df['RH (%)'].mean())])

if summary_data:
    spreadsheet.add_worksheet("Summary", rows="100", cols="5").update([['Device Name', 'Avg PM2.5 (µg/m³)', 'Max Temp (°C)', 'Min Temp (°C)', 'Avg RH (%)']] + summary_data)

# Weekly Summary
weekly_summary = {}
for device in devices:
    name = device['metadata']['friendlyName']
    if sheet_mode == "yes":
        rows = [row for row in combined_data if row[0] == name]
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=["Device Name"] + col)
    else:
        try:
            worksheet = spreadsheet.worksheet(name[:50])
            df = pd.DataFrame(worksheet.get_all_values()[1:], columns=col)
        except:
            continue

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    for k in ['PM 2.5', 'T (C)', 'RH (%)']:
        df[k] = pd.to_numeric(df[k], errors='coerce')

    df['week'] = df['timestamp'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
    grouped = df.groupby('week').agg({'PM 2.5': 'mean', 'T (C)': ['min', 'max'], 'RH (%)': 'mean'}).reset_index()
    grouped.columns = ['Week', 'Avg PM2.5', 'Min Temp', 'Max Temp', 'Avg RH']
    for _, row in grouped.iterrows():
        weekly_summary.setdefault(name, []).append([row['Week'], safe_float(row['Avg PM2.5']), safe_float(row['Min Temp']), safe_float(row['Max Temp']), safe_float(row['Avg RH'])])

weekly_data = []
for dev, rows in weekly_summary.items():
    for row in rows:
        weekly_data.append([dev] + row)

if weekly_data:
    weekly_ws = spreadsheet.add_worksheet("Weekly Summary", rows="100", cols="6")
    weekly_ws.update([['Device Name', 'Week Start', 'Avg PM2.5 (µg/m³)', 'Min Temp (°C)', 'Max Temp (°C)', 'Avg RH (%)']] + weekly_data)

    # Add Charts
    sheets_api = build('sheets', 'v4', credentials=creds)
    meta = sheets_api.spreadsheets().get(spreadsheetId=spreadsheet.id).execute()
    weekly_sheet_id = next(s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == "Weekly Summary")
    time.sleep(5)
    start = 1
    for dev in weekly_summary:
        count = len(weekly_summary[dev])
        chart_req = {
            "requests": [{
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": f"Weekly Trend - {dev}",
                            "basicChart": {
                                "chartType": "LINE",
                                "axis": [{"position": "BOTTOM_AXIS", "title": "Week"}, {"position": "LEFT_AXIS", "title": "Values"}],
                                "domains": [{"domain": {"sourceRange": {"sources": [{"sheetId": weekly_sheet_id, "startRowIndex": start, "endRowIndex": start+count, "startColumnIndex": 1, "endColumnIndex": 2}]}}}],
                                "series": [
                                    {"series": {"sourceRange": {"sources": [{"sheetId": weekly_sheet_id, "startRowIndex": start, "endRowIndex": start+count, "startColumnIndex": 2, "endColumnIndex": 3}]}}, "targetAxis": "LEFT_AXIS"},
                                    {"series": {"sourceRange": {"sources": [{"sheetId": weekly_sheet_id, "startRowIndex": start, "endRowIndex": start+count, "startColumnIndex": 3, "endColumnIndex": 4}]}}, "targetAxis": "LEFT_AXIS"},
                                    {"series": {"sourceRange": {"sources": [{"sheetId": weekly_sheet_id, "startRowIndex": start, "endRowIndex": start+count, "startColumnIndex": 5, "endColumnIndex": 6}]}}, "targetAxis": "LEFT_AXIS"}
                                ]
                            }
                        },
                        "position": {"overlayPosition": {"anchorCell": {"sheetId": weekly_sheet_id, "rowIndex": start, "columnIndex": 3}}}
                    }
                }
            }]
        }
        sheets_api.spreadsheets().batchUpdate(spreadsheetId=spreadsheet.id, body=chart_req).execute()
        start += count
