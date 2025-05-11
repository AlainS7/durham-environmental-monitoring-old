
import streamlit as st
from datetime import datetime
import subprocess
import os
import re
import json
import pandas as pd
import requests
from zoneinfo import ZoneInfo
from dateutil import parser

st.set_page_config(page_title="TSI Sensor Uploader", layout="centered")

st.title("📊 TSI Sensor → Google Sheets (Selective Charts + Preview)")
st.markdown("Upload credentials, select date range and charts, preview them, then upload to Google Sheets.")

tsi_file = st.file_uploader("🔑 TSI Credentials (tsi_creds.json)", type="json")
google_file = st.file_uploader("📄 Google Credentials (google_creds.json)", type="json")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 Start Date", value=datetime(2025, 4, 1))
with col2:
    end_date = st.date_input("📅 End Date", value=datetime(2025, 5, 10))

combine = st.checkbox("Combine all device data into one sheet", value=False)
email = st.text_input("📧 Google account to share sheet with:", placeholder="you@example.com")

make_charts = st.radio("Include charts in Google Sheet?", ["yes", "no"], index=0)

pm25 = temp_min = temp_max = rh = False
if make_charts == "yes":
    st.markdown("### 📈 Select which charts to include:")
    pm25 = st.checkbox("Include PM2.5 Chart", value=True)
    temp_min = st.checkbox("Include Min Temperature Chart", value=False)
    temp_max = st.checkbox("Include Max Temperature Chart", value=False)
    rh = st.checkbox("Include Relative Humidity Chart", value=False)

preview = st.button("👁️ Preview Charts")
run = st.button("🚀 Upload to Google Sheets")

def extract_value(row, target_type):
    for sensor in row.get("sensors", []):
        for m in sensor.get("measurements", []):
            if m.get("type") == target_type:
                return m.get("data", {}).get("value", None)
    return None

if preview and tsi_file:
    try:
        creds = json.load(tsi_file)
        tsi_key = creds['key']
        tsi_secret = creds['secret']
        base_url = 'https://api-prd.tsilink.com/api/v3/external'
        token_url = f"{base_url}/oauth/client_credential/accesstoken"
        data = {'client_id': tsi_key, 'client_secret': tsi_secret, 'grant_type': 'client_credentials'}
        token = requests.post(token_url, data=data).json()['access_token']
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        device_list = requests.get(f"{base_url}/devices", headers=headers).json()

        st.markdown("### 🔍 Chart Preview (1st Device Only)")
        first_device = device_list[0]
        device_id = first_device['device_id']
        params = {
            "device_id": device_id,
            "start_date": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "end_date": end_date.strftime("%Y-%m-%dT23:59:59Z")
        }
        telemetry = requests.get(f"{base_url}/telemetry", headers=headers, params=params).json()
        rows = []
        for row in telemetry:
            ts_utc = parser.isoparse(row['cloud_timestamp'])
            ts_est = ts_utc.astimezone(ZoneInfo('America/New_York'))
            rows.append({
                "Time": ts_est,
                "PM2.5": extract_value(row, "mcpm2x5"),
                "Temp": extract_value(row, "temp_c"),
                "RH": extract_value(row, "rh_percent")
            })
        df = pd.DataFrame(rows).dropna()

        if pm25:
            st.line_chart(df.set_index("Time")[["PM2.5"]])
        if temp_min or temp_max:
            st.line_chart(df.set_index("Time")[["Temp"]])
        if rh:
            st.line_chart(df.set_index("Time")[["RH"]])

    except Exception as e:
        st.error(f"❌ Failed to preview data: {e}")

if run:
    if not tsi_file or not google_file:
        st.error("Please upload both TSI and Google credential files.")
    elif start_date > end_date:
        st.error("Start date must be before end date.")
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.error("Please enter a valid email address.")
    else:
        with open("tsi_creds.json", "wb") as f:
            f.write(tsi_file.read())
        with open("google_creds.json", "wb") as f:
            f.write(google_file.read())

        combine_arg = "yes" if combine else "no"
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        chart_flags = ["no", "no", "no", "no"]
        if make_charts == "yes":
            chart_flags = [
                "yes" if pm25 else "no",
                "yes" if temp_min else "no",
                "yes" if temp_max else "no",
                "yes" if rh else "no"
            ]

        st.info("Running script. This may take a few moments...")
        result = subprocess.run(
            ["python3", "unified_tsi_complete_script_gui_final_charts_conditional_clean.py"],
            input=f"{combine_arg}\n{start_str}\n{end_str}\n{email}\n" + "\n".join(chart_flags) + "\n",
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and "https://docs.google.com" in result.stdout:
            link_line = next((line for line in result.stdout.splitlines() if "https://" in line), None)
            if link_line:
                st.success("✅ Upload complete!")
                st.markdown(f"📄 [Open Google Sheet]({link_line})")
        else:
            st.error("❌ Something went wrong.")
            st.text(result.stderr)
