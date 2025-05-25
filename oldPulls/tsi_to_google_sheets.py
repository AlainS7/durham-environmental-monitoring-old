from datetime import datetime, timedelta
import os
import sys
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

def read_or_fallback(prompt, default=None):
    import sys
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

combine_mode = read_or_fallback("Combine all data into one sheet? (y/n):", "n").lower()
start_date = read_or_fallback("Enter start date (YYYY-MM-DD):", "2025-03-01")
end_date = read_or_fallback("Enter end date (YYYY-MM-DD):", "2025-04-30")
user_email = read_or_fallback("Enter email to share the sheet with:", "hotdurham@gmail.com")

make_charts = read_or_fallback("Include charts in Google Sheet? (y/n): ").strip().lower()
include_pm25 = include_temp_min = include_temp_max = include_rh = False
if make_charts == "y":
    include_pm25 = read_or_fallback("Include PM2.5 chart? (y/n): ").strip().lower() == "y"
    include_temp_min = read_or_fallback("Include Min Temperature chart? (y/n): ").strip().lower() == "y"
    include_temp_max = read_or_fallback("Include Max Temperature chart? (y/n): ").strip().lower() == "y"
    include_rh = read_or_fallback("Include Relative Humidity chart? (y/n): ").strip().lower() == "y"

start_dt = datetime.fromisoformat(start_date).strftime('%Y-%m-%dT00:00:00Z')
end_dt = datetime.fromisoformat(end_date).strftime('%Y-%m-%dT23:59:59Z')

script_dir = os.path.dirname(os.path.abspath(__file__))
tsi_creds_path = os.path.join(script_dir, '../creds/tsi_creds.json')
google_creds_path = os.path.join(script_dir, '../creds/google_creds.json')

ts_creds_abs = os.path.abspath(tsi_creds_path)
google_creds_abs = os.path.abspath(google_creds_path)


if not os.path.exists(ts_creds_abs):
    print(f"❌ ERROR: TSI credentials not found at {ts_creds_abs}. Please upload or place your tsi_creds.json in the creds/ folder.")
    sys.exit(1)
if not os.path.exists(google_creds_abs):
    print(f"❌ ERROR: Google credentials not found at {google_creds_abs}. Please upload or place your google_creds.json in the creds/ folder.")
    sys.exit(1)

with open(ts_creds_abs) as f:
    tsi_creds = json.load(f)

with open(google_creds_abs) as f:
    pass  # google_creds_path is already set above

auth_resp = requests.post(
    'https://api-prd.tsilink.com/api/v3/external/oauth/client_credential/accesstoken',
    params={'grant_type': 'client_credentials'},
    data={'client_id': tsi_creds['key'], 'client_secret': tsi_creds['secret']}
)
access_token = auth_resp.json()['access_token']
headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

devices = requests.get("https://api-prd.tsilink.com/api/v3/external/devices", headers=headers).json()

scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(google_creds_path, scopes=scope)
client = gspread.authorize(creds)

spreadsheet = client.create(f"TSI Data - {datetime.now().strftime('%Y%m%d_%H%M%S')}")

print("🔗 Google Sheet URL:", spreadsheet.url)

if user_email:
    try:
        spreadsheet.share(user_email, perm_type='user', role='writer')
        print(f"✅ Shared with {user_email}")
    except Exception as e:
        print(f"❌ Failed to share with {user_email}: {e}")

col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)', 'NC (4)', 'NC (10)', 'PM 2.5 AQI']
combined_data = []

def extract_value(row, t):
    for s in row.get('sensors', []):
        for m in s.get('measurements', []):
            if m.get('type') == t and 'data' in m and 'value' in m['data']:
                return m['data']['value']
    return ""

summary_data = []
weekly_summary = {}

for d in devices:
    device_id = d['device_id']
    name = d['metadata']['friendlyName']
    params = {'start_date': start_dt, 'end_date': end_dt, 'device_id': device_id}
    r = requests.get("https://api-prd.tsilink.com/api/v3/external/telemetry", headers=headers, params=params)

    if r.status_code != 200:
        print(f"❌ Failed: {name}")
        continue

    seen = set()
    data = []
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

        if combine_mode == "y":
            combined_data.append([name] + values)
        else:
            data.append(values)

    if combine_mode != "y" and data:
        df = pd.DataFrame(data, columns=col)
        ws = spreadsheet.add_worksheet(title=name[:50], rows=str(len(df)+1), cols=str(len(col)))
        ws.update([col] + data)

        for key in ['PM 2.5', 'T (C)', 'RH (%)']:
            df[key] = pd.to_numeric(df[key], errors='coerce')
        summary_data.append([
            name,
            round(df['PM 2.5'].mean(), 2),
            round(df['T (C)'].max(), 2),
            round(df['T (C)'].min(), 2),
            round(df['RH (%)'].mean(), 2)
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['week_start'] = df['timestamp'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
        weekly = df.groupby('week_start').agg({
            'PM 2.5': 'mean', 'T (C)': ['min', 'max'], 'RH (%)': 'mean'
        }).reset_index()
        weekly.columns = ['Week Start', 'Avg PM2.5', 'Min Temp', 'Max Temp', 'Avg RH']
        for _, row in weekly.iterrows():
            weekly_summary.setdefault(name, []).append([
                row['Week Start'],
                round(row['Avg PM2.5'], 2),
                round(row['Min Temp'], 2),
                round(row['Max Temp'], 2),
                round(row['Avg RH'], 2)
            ])

if combine_mode == "y" and combined_data:
    headers = ["Device Name"] + col
    ws = spreadsheet.sheet1
    ws.update([headers] + combined_data)
    ws.update_title(f"Combined_{start_date}_to_{end_date}")

if summary_data:
    summary_headers = ['Device Name', 'Avg PM2.5 (µg/m³)', 'Max Temp (°C)', 'Min Temp (°C)', 'Avg RH (%)']
    ws_summary = spreadsheet.add_worksheet(title="Summary", rows=str(len(summary_data)+1), cols="5")
    ws_summary.update([summary_headers] + summary_data)

weekly_headers = ['Device Name', 'Week Start', 'Avg PM2.5 (µg/m³)', 'Min Temp (°C)', 'Max Temp (°C)', 'Avg RH (%)']
weekly_rows = []
for device, rows in weekly_summary.items():
    for row in rows:
        weekly_rows.append([device] + row)

if weekly_rows:
    weekly_ws = spreadsheet.add_worksheet(title="Weekly Summary", rows=str(len(weekly_rows)+1), cols="6")
    weekly_ws.update([weekly_headers] + weekly_rows)

# Charts
time.sleep(5)
sheets_api = build('sheets', 'v4', credentials=creds)
sheet_id = spreadsheet.id
meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
weekly_id = next((s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == 'Weekly Summary'), None)

if weekly_id:
    row_idx = 1
    for device, rows in weekly_summary.items():
        chart_req = {
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
                                    "domains": [{
                                        "domain": {
                                            "sourceRange": {
                                                "sources": [{
                                                    "sheetId": weekly_id,
                                                    "startRowIndex": row_idx,
                                                    "endRowIndex": row_idx + len(rows),
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 2
                                                }]
                                            }
                                        }
                                    }],
                                    "series": [{
                                        "series": {
                                            "sourceRange": {
                                                "sources": [{
                                                    "sheetId": weekly_id,
                                                    "startRowIndex": row_idx,
                                                    "endRowIndex": row_idx + len(rows),
                                                    "startColumnIndex": 2,
                                                    "endColumnIndex": 3
                                                }]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS"
                                    }]
                                }
                            },
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": weekly_id,
                                        "rowIndex": row_idx,
                                        "columnIndex": 5
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
        sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=chart_req).execute()
        row_idx += len(rows)


if make_charts == "y":

    # === Add Chart Sheets ===
    import time
    sheets_api = build('sheets', 'v4', credentials=creds)
    sheet_id = spreadsheet.id
    sheets_meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
    weekly_id = None

    for sheet in sheets_meta['sheets']:
        if sheet['properties']['title'] == 'Weekly Summary':
            weekly_id = sheet['properties']['sheetId']
            break

    if weekly_id:
        row_idx = 1
        for device, rows in weekly_summary.items():
            chart_requests = []
            chart_types = []
            if include_pm25:
                chart_types.append(("Avg PM2.5", 2))
            if include_temp_min:
                chart_types.append(("Min Temp", 3))
            if include_temp_max:
                chart_types.append(("Max Temp", 4))
            if include_rh:
                chart_types.append(("Avg RH", 5))

            for measurement, col_offset in chart_types:
                chart_requests.append({
                    "addChart": {
                        "chart": {
                            "spec": {
                                "title": f"{measurement} Trend - {device}",
                                "basicChart": {
                                    "chartType": "LINE",
                                    "legendPosition": "BOTTOM_LEGEND",
                                    "axis": [
                                        {"position": "BOTTOM_AXIS", "title": "Week"},
                                        {"position": "LEFT_AXIS", "title": measurement}
                                    ],
                                    "domains": [{
                                        "domain": {
                                            "sourceRange": {
                                                "sources": [{
                                                    "sheetId": weekly_id,
                                                    "startRowIndex": row_idx,
                                                    "endRowIndex": row_idx + len(rows),
                                                    "startColumnIndex": 1,
                                                    "endColumnIndex": 2
                                                }]
                                            }
                                        }
                                    }],
                                    "series": [{
                                        "series": {
                                            "sourceRange": {
                                                "sources": [{
                                                    "sheetId": weekly_id,
                                                    "startRowIndex": row_idx,
                                                    "endRowIndex": row_idx + len(rows),
                                                    "startColumnIndex": col_offset,
                                                    "endColumnIndex": col_offset + 1
                                                }]
                                            }
                                        },
                                        "targetAxis": "LEFT_AXIS"
                                    }]
                                }
                            },
                            "position": {
                                "newSheet": True
                            }
                        }
                    }
                })
            if chart_requests:
                sheets_api.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": chart_requests}).execute()
        row_idx += len(rows)

