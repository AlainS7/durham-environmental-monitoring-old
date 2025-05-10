import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load Weather Underground API key
with open('./wu_api_key.json') as f:
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
    r = requests.get(url, params=params)
    return r

start_date_str = input("Enter the start date (YYYYMMDD): ")
end_date_str = input("Enter the end date (YYYYMMDD): ")

start_date = datetime.strptime(start_date_str, "%Y%m%d")
end_date = datetime.strptime(end_date_str, "%Y%m%d")

# Create a directory to store the station data files
base_output_dir = "./WU_Data"
output_dir = os.path.join(base_output_dir, end_date_str)

# Create the directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

all_data = []
current_date = start_date
while current_date <= end_date:
    date_str = current_date.strftime("%Y%m%d")
    
    for station in stations:
        stationId = station['stationId']
        data = get_station_data(stationId, date_str, wu_key)
        all_data.append(data)
    
    current_date += timedelta(days=1)

print(f"Number of API responses: {len(all_data)}")
collected_data = []
columns = [
    'stationId', 'obsTimeUtc', 'tempAvg', 'humidityAvg', 'solarRadiationHigh',
    'winddirAvg', 'windspeedAvg', 'precipTotal', 'heatindexAvg'
]

for response in all_data:
    try:
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code} for station {response.url}")
            continue
        
        data = response.json()
        for obs in data['observations']:
            obs_time = pd.to_datetime(obs['obsTimeUtc']).round('H')
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
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error occurred for a station: {str(e)}")
        print(f"Response content: {response.text}")

# Create a DataFrame from the collected data
df = pd.DataFrame(collected_data, columns=columns)

# Save the data to a CSV file locally (if you would like to)
# output_file = os.path.join(output_dir, "combined_data.csv")
# df.to_csv(output_file, index=False)
# print(f"Combined data saved to {output_file}")

# --- Google Sheets Upload ---
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = ServiceAccountCredentials.from_json_keyfile_name('google_creds.json', scope)
client = gspread.authorize(creds)

# Create and share the spreadsheet
spreadsheet = client.create(f"WU Data - {end_date_str}")
spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')  # Replace with your email
worksheet = spreadsheet.sheet1

# Upload DataFrame to the Google Sheet
worksheet.update([df.columns.values.tolist()] + df.values.tolist())
print("🔗 Google Sheet URL:", spreadsheet.url)
