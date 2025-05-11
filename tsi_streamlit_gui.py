
import streamlit as st
from datetime import datetime
import subprocess
import os
import re

st.set_page_config(page_title="TSI Sensor Uploader", layout="centered")

st.title("📊 TSI Sensor → Google Sheets")
st.markdown("Upload TSI and Google credentials, choose a date range, enter your email, and click Start to populate a Google Sheet.")

# Upload credentials
tsi_file = st.file_uploader("🔑 Upload TSI Credentials (tsi_creds.json)", type="json")
google_file = st.file_uploader("📄 Upload Google Credentials (google_creds.json)", type="json")

# Date range
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 Start Date", value=datetime(2025, 3, 1))
with col2:
    end_date = st.date_input("📅 End Date", value=datetime(2025, 4, 30))

# Combine mode
combine = st.checkbox("Combine all device data into one sheet", value=False)

# Email input
email = st.text_input("📧 Enter your Google email (to receive the sheet):", placeholder="you@example.com")

# Button
run = st.button("🚀 Start Upload")

if run:
    if not tsi_file or not google_file:
        st.error("Please upload both credential files.")
    elif start_date > end_date:
        st.error("Start date must be before end date.")
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        st.error("Please enter a valid email address.")
    else:
        with open("tsi_creds.json", "wb") as f:
            f.write(tsi_file.read())
        with open("google_creds.json", "wb") as f:
            f.write(google_file.read())

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        combine_arg = "yes" if combine else "no"

        st.info("Running script. This may take a few seconds...")
        result = subprocess.run(
            ["python3", "unified_tsi_complete_script_gui.py"],
            input=f"{combine_arg}\n{start_str}\n{end_str}\n{email}\n",
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
