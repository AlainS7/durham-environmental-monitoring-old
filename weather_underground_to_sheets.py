import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    try:
        r = requests.get(url, params=params, timeout=30)
        return r
    except requests.exceptions.Timeout:
        print(f"Timeout occurred for station {stationId} on {date}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed for station {stationId} on {date}: {e}")
        return None

def input_with_default(prompt, default):
    user_input = input(f"{prompt} [{default}]: ").strip()
    return user_input if user_input else default

start_date_str = input_with_default("Enter the start date (YYYY-MM-DD):", "2025-03-01")
end_date_str = input_with_default("Enter the end date (YYYY-MM-DD):", "2025-04-30")

# Prompt for email to share the spreadsheet with (moved up)
while True:
    share_email = input("Enter the email address to share the Google Sheet with: ").strip()
    if re.match(r"[^@]+@[^@]+\.[^@]+", share_email):
        break
    print("Invalid email address. Please enter a valid Google email address.")

start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

# --- API Key Diagnostic Check ---
test_station = stations[0]['stationId']
test_date = start_date.strftime('%Y%m%d')
test_url = "https://api.weather.com/v2/pws/history/hourly"
test_params = {
    "stationId": test_station,
    "date": test_date,
    "format": "json",
    "apiKey": wu_key,
    "units": "m",
    "numericPrecision": "decimal",
}
test_response = requests.get(test_url, params=test_params)
if test_response.status_code == 401:
    print("\nERROR: Your Weather Underground API key is unauthorized or does not have access to the PWS API.")
    print(f"Tested with station {test_station} and date {test_date}.")
    print("Please check your API key, permissions, and Weather Underground account.")
    exit(1)
elif test_response.status_code != 200:
    print(f"\nERROR: Weather Underground API test failed with status code {test_response.status_code}.")
    print(f"Response: {test_response.text}")
    exit(1)
else:
    print("Weather Underground API key test passed. Proceeding with data fetch...\n")

# Create a directory to store the station data files
base_output_dir = "./WU_Data"
output_dir = os.path.join(base_output_dir, end_date_str)

# Create the directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

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

# Replace the old data fetching loop with the parallel version
all_data = fetch_all_data_parallel(stations, start_date, end_date, wu_key, max_workers=10)
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
            obs_time = pd.to_datetime(obs['obsTimeUtc']).round('h')  # Changed 'H' to 'h'
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

# Convert obsTimeUtc column to string to avoid JSON serialization issues
df['obsTimeUtc'] = df['obsTimeUtc'].astype(str)

# Replace NaN and infinite values with empty string for Google Sheets compatibility
df = df.replace([pd.NA, pd.NaT, float('inf'), float('-inf')], '')
df = df.fillna('')

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
spreadsheet = client.create(f"WU Data - {start_date_str} to {end_date_str}")
spreadsheet.share(share_email, perm_type='user', role='writer')
# Rename the first worksheet to 'WU'
worksheet = spreadsheet.sheet1
worksheet.update_title('WU')

try:
    # Upload DataFrame to the Google Sheet
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("🔗 Google Sheet URL:", spreadsheet.url)
except KeyboardInterrupt:
    print("\nScript interrupted by user.")
    exit(1)
except Exception as e:
    print(f"An error occurred during Google Sheets upload: {e}")
    exit(1)
