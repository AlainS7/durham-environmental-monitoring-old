# Hot Durham Data Management System

## Overview

This automated data management system provides organized storage, automated pulls, and Google Drive synchronization for Weather Underground (WU) and TSI sensor data.

## Features

✅ **Organized Data Storage**
- Dedicated folders for raw data pulls (weekly, bi-weekly, monthly)
- Automatic file naming with timestamps and date ranges
- Separate folders for WU and TSI data by year
- Processed data summaries (weekly, monthly, annual)

✅ **Automated Data Pulls**
- Scheduled weekly, bi-weekly, or monthly data collection
- Configurable data sources (WU only, TSI only, or both)
- Automatic Google Sheets creation with charts
- Error handling and retry logic

✅ **Google Drive Integration**
- Automatic synchronization of local data to Google Drive
- Maintains folder structure in the cloud
- Backup and archive capabilities
- Metadata tracking for all pulls

✅ **Smart Scheduling**
- Cron job setup for automated runs
- Configurable schedules via JSON config
- Logging and monitoring of automated pulls
- Manual override capabilities

## Quick Start

### 1. Initial Setup

Run the setup script to configure automation:

```bash
cd "/Users/alainsoto/IdeaProjects/Hot Durham"
./setup_automation.sh
```

This will:
- Set up cron jobs for weekly and monthly pulls
- Create log directories
- Generate test scripts
- Configure automation schedules

### 2. Manual Data Pull

To run a manual data pull:

```bash
# Weekly pull (recommended for regular monitoring)
python scripts/faster_wu_tsi_to_sheets_async.py

# Or use the automated script with specific options
python scripts/automated_data_pull.py --weekly
python scripts/automated_data_pull.py --monthly --wu-only
python scripts/automated_data_pull.py --bi-weekly --tsi-only
```

### 3. Test the System

Run a test pull to verify everything works:

```bash
./run_weekly_pull.sh
```

## Folder Structure

```
data/
├── raw_pulls/           # Raw data from APIs
│   ├── wu/             # Weather Underground data
│   │   ├── 2024/       # Organized by year
│   │   └── 2025/
│   └── tsi/            # TSI sensor data
│       ├── 2024/
│       └── 2025/
├── processed/          # Analyzed and summarized data
│   ├── weekly_summaries/
│   ├── monthly_summaries/
│   └── annual_summaries/
├── backup/             # Backup and sync data
│   ├── google_drive_sync/
│   └── local_archive/
└── temp/               # Temporary processing files
```

## Configuration

### Automation Config (`config/automation_config.json`)

```json
{
  "share_email": "hotdurham@gmail.com",
  "automation_enabled": true,
  "default_pull_type": "weekly",
  "google_drive_sync": true,
  "schedules": {
    "weekly_pull": {
      "enabled": true,
      "day_of_week": "monday",
      "time": "06:00",
      "sources": ["wu", "tsi"]
    }
  }
}
```

### Cron Schedule

Default automated schedules:
- **Weekly pulls**: Every Monday at 6:00 AM
- **Monthly summaries**: 1st of each month at 7:00 AM

View current cron jobs:
```bash
crontab -l
```

Edit cron jobs:
```bash
crontab -e
```

## Data Manager API

The `DataManager` class provides programmatic access to the data management system:

```python
from data_manager import DataManager

# Initialize
dm = DataManager("/Users/alainsoto/IdeaProjects/Hot Durham")

# Save raw data with automatic organization
file_path = dm.save_raw_data(
    data=dataframe,
    source='wu',  # or 'tsi'
    start_date='2025-05-01',
    end_date='2025-05-07',
    pull_type='weekly',
    file_format='csv'
)

# Sync to Google Drive
dm.sync_to_drive()

# Get data inventory
inventory = dm.get_data_inventory()
```

## File Naming Convention

Raw data files follow this pattern:
```
{source}_{pull_type}_{start_date}_to_{end_date}_{timestamp}.{format}

Examples:
- wu_weekly_2025-05-19_to_2025-05-25_20250525_140530.csv
- tsi_monthly_2025-05-01_to_2025-05-31_20250601_070015.csv
```

## Google Sheets Integration

Each data pull automatically creates a Google Sheet with:
- Raw data tabs for WU and/or TSI
- Summary statistics
- Weekly/monthly trend charts
- Time-series visualizations

Sheets are automatically shared with the configured email address.

## Monitoring and Logs

### Log Files

- `logs/weekly_pull.log` - Weekly automation logs
- `logs/monthly_pull.log` - Monthly automation logs
- `logs/google_drive_sync.log` - Drive sync operations
- `logs/data_manager.log` - General data management operations

### Check Last Run

```bash
# View recent log entries
tail -20 logs/weekly_pull.log

# Check for errors
grep "ERROR\|❌" logs/*.log
```

### Manual Monitoring

View data inventory:
```python
from scripts.data_manager import DataManager
dm = DataManager("/Users/alainsoto/IdeaProjects/Hot Durham")
print(dm.get_data_inventory())
```

## Troubleshooting

### Common Issues

1. **Cron jobs not running**
   - Check cron service: `sudo launchctl list | grep cron`
   - Verify crontab: `crontab -l`
   - Check logs: `tail logs/weekly_pull.log`

2. **Google Drive sync failing**
   - Verify credentials: `ls -la creds/google_creds.json`
   - Check permissions in Google Cloud Console
   - Run manual sync: `python scripts/google_drive_sync.py`

3. **API failures**
   - WU API: Check `creds/wu_api_key.json` and rate limits
   - TSI API: Verify `creds/tsi_creds.json` and device access

4. **Permission errors**
   - Ensure scripts are executable: `chmod +x scripts/*.py`
   - Check data folder permissions: `ls -la data/`

### Manual Recovery

If automation fails, run manual recovery:

```bash
# Pull specific date range
python scripts/faster_wu_tsi_to_sheets_async.py

# Force Google Drive sync
python scripts/google_drive_sync.py --force-sync

# Check data integrity
python scripts/data_manager.py --verify-data
```

## Maintenance

### Weekly Tasks
- Check log files for errors
- Verify Google Drive sync status
- Monitor data quality in generated sheets

### Monthly Tasks
- Review data inventory and storage usage
- Update automation config if needed
- Clean up temporary files: `rm -rf data/temp/*`

### Quarterly Tasks
- Review and optimize folder structure
- Update API credentials if needed
- Archive old data if storage is limited

## Advanced Usage

### Custom Pull Schedules

Add custom schedules to crontab:

```bash
# Bi-weekly WU data only (every other Friday at 5 PM)
0 17 * * 5 [ $(expr $(date +\%W) \% 2) -eq 0 ] && cd "/Users/alainsoto/IdeaProjects/Hot Durham" && python3 scripts/automated_data_pull.py --bi-weekly --wu-only >> logs/custom_pull.log 2>&1
```

### Data Processing Pipelines

Extend the system with custom processing:

```python
# Custom data processor
from scripts.data_manager import DataManager

dm = DataManager("/Users/alainsoto/IdeaProjects/Hot Durham")

# Load recent data
wu_data = dm.load_recent_data('wu', days=7)
tsi_data = dm.load_recent_data('tsi', days=7)

# Custom analysis
# ... your processing code ...

# Save processed results
dm.save_processed_data(results, 'custom_analysis', 'weekly')
```

### Integration with External Systems

The data manager can be integrated with:
- Jupyter notebooks for analysis
- Streamlit dashboards
- External APIs and webhooks
- Custom reporting systems

## Support

For issues or questions:
1. Check this README and troubleshooting section
2. Review log files for specific error messages
3. Test components individually using the manual scripts
4. Verify all credentials and API access

## Version History

- **v1.0** (May 2025): Initial automated data management system
  - Organized folder structure
  - Automated pulls and scheduling
  - Google Drive integration
  - Comprehensive logging and monitoring
