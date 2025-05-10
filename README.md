# TSI Data Uploader to Google Sheets

This Python script connects to the TSI Link API, retrieves air quality telemetry data from registered devices, and uploads the structured data to a Google Sheet — with one worksheet per device.

## 🚀 Features

- Secure OAuth2 authentication with TSI Link API
- Retrieves device-level telemetry data
- Converts timestamps from UTC to Eastern Time (EST)
- Formats sensor data into structured tables
- Creates a single Google Sheet with a tab for each device

## 📦 Requirements

- Python 3.8+
- Google Cloud service account credentials (`google_creds.json`)
- TSI API credentials (`tsi_creds.json`)
- Required Python packages (see below)

## 🔧 Setup Instructions

1. **Clone the repository**

```bash
git clone git@github.com:AQUHI/tsi-data-uploader.git
cd tsi-data-uploader
```

2. **Create a virtual environment (recommended)**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Place credentials**

- Save your TSI API credentials as `tsi_creds.json`
- Save your Google service account credentials as `google_creds.json`

> ⚠️ Both files are in `.gitignore` and should never be committed to GitHub (for security).

5. **Run the script**

```bash
python tsi_api_to_google_sheets.py
```

## 📊 Output

- A Google Sheet is created, named with the current timestamp.
- Each tab contains telemetry from a different TSI device.
- Columns include timestamp, PM data, NC counts, temperature, humidity, and calibration offsets.

## 📝 License

© AQUHI. All rights reserved. For internal use or by permission only.
