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
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Place credentials**

- Save your TSI API credentials as `tsi_creds.json`
- Save your Google service account credentials as `google_creds.json`

> ⚠️ Both files are in `.gitignore` and should never be committed to GitHub.

5. **Run the script**

```bash
python tsi_api_to_google_sheets.py
```

## 🧠 IntelliJ: Setting Up Python Interpreter and Virtual Environment

If you're using IntelliJ IDEA with Python:

1. **Create a virtual environment manually** (if not done yet):

```bash
python3 -m venv .venv
```

2. **In IntelliJ**: Go to `File > Project Structure > SDKs`  
   - Click the **`+`** icon > select `Python SDK`
   - Choose **"Add Local Interpreter"** > "Virtualenv Environment"
   - Browse to `.venv/bin/python` and add it

3. Then go to `Project Structure > Project` and set the **Project SDK** to that `.venv` interpreter.

4. Also check `Project Structure > Modules > Dependencies tab`  
   - Make sure **Module SDK** is set to the same `.venv`

5. Finally, open the IntelliJ terminal and activate your environment (if needed):
```bash
source .venv/bin/activate
```

Now IntelliJ will correctly use your virtual environment to run and debug the script.

## 📊 Output

- A Google Sheet is created, named with the current timestamp.
- Each tab contains telemetry from a different TSI device.
- Columns include timestamp, PM data, NC counts, temperature, humidity, and calibration offsets.

## 📝 License

© AQUHI. All rights reserved. For internal use or by permission only.
