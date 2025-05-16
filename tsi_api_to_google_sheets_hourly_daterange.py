from datetime import datetime
import os
import requests
import json
import pandas as pd
from zoneinfo import ZoneInfo
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dateutil import parser  # Add this import at the top

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
spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')  # replace with your email
print("🔗 Google Sheet URL:", spreadsheet.url)

# Columns for data
col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)',
       'NC (4)', 'NC (10)', 'PM 2.5 AQI', 'PM Cal', 'T cal', 'RH cal']

# Ask for date range
start_date_str = input('Enter start date (YYYY-MM-DD): ')
end_date_str = input('Enter end date (YYYY-MM-DD): ')
start_dt = datetime.fromisoformat(start_date_str).strftime('%Y-%m-%dT00:00:00Z')
end_dt = datetime.fromisoformat(end_date_str).strftime('%Y-%m-%dT23:59:59Z')

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
            tz_utc = parser.isoparse(tz_utc)  # Use dateutil's parser instead
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
            data.append(values)

        df = pd.DataFrame(data, columns=col)
        worksheet = spreadsheet.add_worksheet(title=friendly_name[:50], rows=str(len(df)+1), cols=str(len(col)))
        worksheet.update([col] + data)


    else:
        print(f"❌ Failed to retrieve data for device {friendly_name}. Status code: {response.status_code}")