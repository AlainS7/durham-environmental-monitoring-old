# Hot Durham Data Storage Structure

This folder contains raw data pulls from Weather Underground (WU) and TSI sensors.

## Folder Structure

```
data/
├── raw_pulls/           # Raw data pulls organized by date
│   ├── wu/             # Weather Underground data
│   │   ├── 2025/       # Year folders
│   │   │   ├── week_01/    # Weekly folders (ISO week format)
│   │   │   ├── week_02/
│   │   │   └── ...
│   │   └── 2024/
│   └── tsi/            # TSI sensor data
│       ├── 2025/
│       │   ├── week_01/
│       │   ├── week_02/
│       │   └── ...
│       └── 2024/
├── processed/          # Processed and combined data
│   ├── weekly_summaries/
│   ├── monthly_summaries/
│   └── annual_summaries/
├── backup/             # Local backup copies
│   ├── google_drive_sync/  # Files synced to Google Drive
│   └── local_archive/      # Local-only archive
└── temp/               # Temporary files (cleared regularly)
```

## Data Pull Schedule

- **Primary pulls**: Weekly (every Sunday at 00:00)
- **Backup pulls**: Bi-weekly (every other Wednesday)
- **Emergency pulls**: On-demand for specific date ranges

## Retention Policy

- **Raw data**: Keep for 2 years locally, indefinitely on Google Drive
- **Processed data**: Keep indefinitely
- **Google Sheets**: Updated automatically, archived monthly
- **Backup frequency**: Daily sync to Google Drive for critical data

## File Naming Convention

### Raw Data Files
- WU: `wu_data_YYYY-MM-DD_to_YYYY-MM-DD.csv`
- TSI: `tsi_data_YYYY-MM-DD_to_YYYY-MM-DD.csv`

### Weekly Files
- WU: `wu_week_YYYY-WW.csv` (e.g., `wu_week_2025-21.csv`)
- TSI: `tsi_week_YYYY-WW.csv`

### Combined Files
- `combined_wu_tsi_YYYY-MM-DD_to_YYYY-MM-DD.csv`
- `annual_summary_YYYY.csv`

## Google Drive Integration

This system automatically syncs with Google Drive to ensure data persistence and accessibility:

1. **Raw data**: Uploaded immediately after each pull
2. **Processed data**: Synced daily
3. **Google Sheets**: Auto-shared and backed up to Drive
4. **Metadata**: Pull logs and processing history
