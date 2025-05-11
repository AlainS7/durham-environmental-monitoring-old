
import streamlit as st
from datetime import datetime
import subprocess
import os
import re

st.set_page_config(page_title="TSI Sensor Uploader", layout="centered")

st.title("📊 TSI Sensor → Google Sheets (Selective Charts)")
st.markdown("Upload credentials, select your data range, choose which charts to include, and hit Start.")

# Credential upload
tsi_file = st.file_uploader("🔑 TSI Credentials (tsi_creds.json)", type="json")
google_file = st.file_uploader("📄 Google Credentials (google_creds.json)", type="json")

# Date inputs
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 Start Date", value=datetime(2025, 4, 1))
with col2:
    end_date = st.date_input("📅 End Date", value=datetime(2025, 5, 10))

# Combine mode
combine = st.checkbox("Combine all device data into one sheet", value=False)

# Email
email = st.text_input("📧 Google account to share sheet with:", placeholder="you@example.com")

# Chart toggle
make_charts = st.radio("Include charts in Google Sheet?", ["yes", "no"], index=0)

# Conditional chart options
pm25 = temp_min = temp_max = rh = False
if make_charts == "yes":
    st.markdown("### 📈 Select which charts to include:")
    pm25 = st.checkbox("Include PM2.5 Chart", value=True)
    temp_min = st.checkbox("Include Min Temperature Chart", value=False)
    temp_max = st.checkbox("Include Max Temperature Chart", value=False)
    rh = st.checkbox("Include Relative Humidity Chart", value=False)

# Run button
run = st.button("🚀 Start Upload")

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
            ["python3", "unified_tsi_complete_script_gui_final_charts_conditional.py"],
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
