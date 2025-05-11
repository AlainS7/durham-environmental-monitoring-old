# 🔥 Hot Durham Sensor Dashboard

This project collects environmental sensor data from TSI devices and uploads it to Google Sheets. It supports both command-line and GUI interfaces and allows for live data preview and selective chart generation.

---

## 🚀 Features

- 🔗 Pulls telemetry from TSI cloud API
- 🕒 Logs **hourly** and **weekly** summary data
- ✅ Option to **combine** all sensors into a single sheet
- 📊 Generate charts for:
  - PM2.5
  - Min/Max Temperature
  - Relative Humidity
- 🖼️ GUI: Streamlit app with live chart previews
- 📤 Auto-shares Google Sheet with your email
- 💾 Data exported to Google Sheets using `gspread`

---

## 📁 File Overview

| File                                                          | Description                                                 |
|---------------------------------------------------------------|-------------------------------------------------------------|
| `unified_tsi_complete_script_gui_final_charts_conditional.py` | Main CLI script for data pull + summaries + optional charts |
| `tsi_streamlit_gui_selective_charts_with_preview.py`          | Streamlit GUI with chart previews and upload                |
| `tsi_creds.json` / `google_creds.json`                        | Credential files (⚠️ DO NOT COMMIT)                         |
| `.gitignore`                                                  | Ignore virtualenv, credentials, cache, and logs             |


---

## 🧪 Usage

### ▶️ Command-Line

```bash
python unified_tsi_complete_script_gui_final_charts_conditional_clean.py
```

You'll be prompted for:
- Sheet format (combined or separate)
- Start and end date
- Google account email
- Chart inclusion and selection

---

### 🖼️ GUI (Streamlit)

```bash
streamlit run tsi_streamlit_gui_selective_charts_with_preview.py
```

1. Upload your credentials
2. Choose the date range and sheet format
3. Preview PM2.5, Temp, RH charts
4. Upload to Google Sheets

---

## ⚙️ Setup

```bash
pip install -r requirements.txt
```

Recommended packages:
- `streamlit`
- `pandas`
- `gspread`
- `google-auth`
- `requests`
- `python-dateutil`

---

## 🔒 .gitignore Recommendations

```gitignore
# Credentials
tsi_creds.json
google_creds.json

# Python environment
.venv/
__pycache__/
*.py[cod]

# Output files
*.zip
*.log

# Streamlit cache
.streamlit/
```

---

## 📬 Maintainer

Built by Alain Soto — powered by TSI + Google Sheets + Streamlit.

---

## ✅ Notes

- Make sure your Google credentials are authorized for Sheets and Drive access
- The GUI only previews data from the **first available TSI device**
- You can safely remove the JSON credentials after each run for security
