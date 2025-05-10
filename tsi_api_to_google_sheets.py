import os
import requests
import json
import pandas as pd
from datetime import datetime
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
spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')  #replace your-email@gmail.com
print("🔗 Google Sheet URL:", spreadsheet.url)

# Columns for data
col = ['timestamp', 'PM 2.5', 'T (C)', 'RH (%)', 'PM 1', 'PM 4', 'PM 10', 'NC (0.5)', 'NC (1)', 'NC (2.5)', 'NC (4)', 'NC (10)', 'PM 2.5 AQI', 'PM Cal', 'T cal', 'RH cal']

# Loop through devices
for device in devices:
    cloud_device_id = device['device_id']
    friendly_name = device['metadata']['friendlyName']

    params = {
        'age': 1,   #how many days back to get data
        'device_id': cloud_device_id
    }

    device_data_url = "https://api-prd.tsilink.com/api/v3/external/telemetry"
    response = requests.get(device_data_url, headers=header, params=params)
    print(f"Status code for device {friendly_name}: {response.status_code}")

    if response.status_code == 200:
        data = []
        for row in response.json():
            tz_utc = row['cloud_timestamp'].replace('T', ' ')
            raw_timestamp = tz_utc.replace('Z', '+00:00')

            # Ensure fractional seconds are padded to 6 digits if needed
            if '.' in raw_timestamp:
                date_part, frac_part = raw_timestamp.split('.')
                frac, offset = frac_part[:], ''
                if '+' in frac:
                    frac, offset = frac.split('+')
                    offset = '+' + offset
                elif '-' in frac:
                    frac, offset = frac.split('-')
                    offset = '-' + offset
                frac = frac.ljust(6, '0')  # Pad to 6 digits
                tz_utc = f"{date_part}.{frac}{offset}"
            else:
                tz_utc = raw_timestamp

            tz_utc = datetime.fromisoformat(tz_utc)
            tz_est = tz_utc.astimezone(ZoneInfo('America/New_York'))
            tz_est = tz_est.strftime('%Y-%m-%d %H:%M:%S.%f')[:-7]

            pm_2_5 = pm_10 = temp = rh = pm_1 = pm_4 = nc_10 = nc_4 = nc_1 = nc_pt5 = nc_2_5 = AQI = None
            pm_offset = T_offset = rh_offset = None

            for sensor in row['sensors']:
                for measurement in sensor['measurements']:
                    name = measurement['name']
                    value = measurement['data']['value']
                    if name == 'PM 2.5': pm_2_5 = value
                    elif name == 'PM 10': pm_10 = value
                    elif name == 'Temperature': temp = value
                    elif name == 'Relative Humidity': rh = value
                    elif name == 'NC 0.5': nc_pt5 = value
                    elif name == 'NC 4.0': nc_4 = value
                    elif name == 'NC 1.0': nc_1 = value
                    elif name == 'NC 10': nc_10 = value
                    elif name == 'PM 4.0': pm_4 = value
                    elif name == 'PM 1.0': pm_1 = value
                    elif name == 'PM 2.5 AQI': AQI = value
                    elif name == 'NC 2.5': nc_2_5 = value
                    elif name == 'PM 2.5': pm_offset = value
                    elif name == 'Temperature': T_offset = value
                    elif name == 'Relative Humidity': rh_offset = measurement.get('user_offset')

            data.append([tz_est, pm_2_5, temp, rh, pm_1, pm_4, pm_10, nc_pt5, nc_1, nc_2_5, nc_4, nc_10, AQI, pm_offset, T_offset, rh_offset])

        if data:
            df = pd.DataFrame(data, columns=col)
            sheet_name = friendly_name[:99]
            try:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=str(len(df)+1), cols=str(len(df.columns)))
            except gspread.exceptions.APIError:
                worksheet = spreadsheet.worksheet(sheet_name)

            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            print(f"Uploaded data for device '{friendly_name}' to worksheet '{sheet_name}'.")
        else:
            print(f"No data found for device {friendly_name}")
    else:
        print(f"Error fetching data for device {friendly_name}")
