# 🔥 Hot Durham Sensor Dashboard

This project collects environmental sensor data from TSI devices and uploads it to Google Sheets. It supports both command-line and GUI interfaces, allows for live data preview, and selective chart generation.

---

## 🚀 Features

- Pulls telemetry from TSI cloud API
- Logs hourly and weekly summary data
- Option to combine all sensors into a single sheet
- Generate charts for PM2.5, Min/Max Temperature, Relative Humidity
- Streamlit GUI with live chart previews
- Auto-shares Google Sheet with your email
- Data exported to Google Sheets using `gspread`

---

## 📁 Project Structure

- `creds/` — Credential files (`google_creds.json`, `tsi_creds.json`, `wu_api_key.json`)
- `scripts/` — Main and utility Python scripts
- `hot_durham_wu_map/backend/` — Backend server code (Node.js)
- `hot_durham_wu_map/frontend/` — Frontend code (HTML/JS)
- `oldPulls/` — Legacy scripts
- `README.md`, `README_updated.md` — Documentation
- `requirements.txt`, `package.json` — Dependency management

---

## 🧪 Usage

### ▶️ Command-Line

```bash
python scripts/combined_wu_tsi_to_sheets.py
```
You'll be prompted for:
- Sheet format (combined or separate)
- Start and end date
- Google account email
- Chart inclusion and selection

---

### 🖼️ GUI (Streamlit)

```bash
streamlit run scripts/tsi_streamlit_gui_with_preview.py
```
1. Upload your credentials
2. Choose the date range and sheet format
3. Preview PM2.5, Temp, RH charts
4. Upload to Google Sheets

---

## ⚙️ Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Hot Durham
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
   - Save your TSI API credentials as `creds/tsi_creds.json`
   - Save your Google service account credentials as `creds/google_creds.json`
   - Save your Weather Underground API key as `creds/wu_api_key.json`

   > ⚠️ These files are in `.gitignore` and should never be committed to GitHub.

---

## 📝 Notes

- For backend/frontend development, see `hot_durham_wu_map/`.
- For legacy scripts, see `oldPulls/`.
- For any issues, check the `toDo` file or open an issue on GitHub.
