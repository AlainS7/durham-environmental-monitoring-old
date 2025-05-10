import os
import requests
import json
import pandas as pd
from datetime import datetime
#%%

with open('./tsi_creds.json') as f:
    creds = json.load(f)

tsi_key = creds['key']
tsi_secret = creds['secret']

with open('./wu_api_key.json') as f:
    wu_key = json.load(f)['test_api_key']
#%%
# Authorization flow
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
print(response.status_code)
access_token = response.json()['access_token']
app_name = response.json()['application_name']
#%%
device_url = os.path.join(base_url, 'devices')

header = {
    "Accept": "application/json",
    "Authorization": 'Bearer ' + access_token
}

response = requests.get(device_url, headers=header)
print(response.status_code)
#%%
devices = response.json()

#Change to personal download directory
base_output_dir = "/Users/danieloren/Downloads/Urban_Heat/TSI_Data"

current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join(base_output_dir, current_datetime)

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

for device in devices:
    cloud_device_id = device['device_id']
    friendly_name = device['metadata']['friendlyName']

    params = {
        'age': 21,
        'device_id': cloud_device_id
    }

    device_data_url = os.path.join(base_url, 'telemetry')

    response = requests.get(device_data_url, headers=header, params=params)
    print(f"Status code for device {friendly_name}: {response.status_code}")

    if response.status_code == 200:
        data = []
        for row in response.json():
            timestamp = row['cloud_timestamp']

            pm_2_5 = None
            pm_10 = None
            temp = None
            rh = None

            for sensor in row['sensors']:
                for measurement in sensor['measurements']:
                    if measurement['name'] == 'PM 2.5':
                        pm_2_5 = measurement['data']['value']
                    elif measurement['name'] == 'PM 10':
                        pm_10 = measurement['data']['value']
                    elif measurement['name'] == 'Temperature':
                        temp = measurement['data']['value']
                    elif measurement['name'] == 'Relative Humidity':
                        rh = measurement['data']['value']

            data.append([timestamp, pm_2_5, pm_10, temp, rh])

        if data:
            df = pd.DataFrame(data, columns=['timestamp', 'PM 2.5', 'PM 10', 'temperature', 'relative_humidity'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Save the data to a CSV file
            output_file = os.path.join(output_dir, f"{friendly_name}.csv")
            df.to_csv(output_file, index=False)
            print(f"Data saved to {output_file}")
        else:
            print(f"No data found for device {friendly_name}")
    else:
        print(f"Error fetching data for device {friendly_name}")