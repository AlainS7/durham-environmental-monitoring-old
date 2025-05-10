import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Check requests
print("✅ requests version:", requests.__version__)

# Check pandas
df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
print("✅ pandas dataframe:")
print(df)

# Check Google Sheets setup
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('google_creds.json', scope)
    client = gspread.authorize(creds)
    print("✅ Google Sheets authentication successful")
except Exception as e:
    print("❌ Google Sheets authentication failed:", e)