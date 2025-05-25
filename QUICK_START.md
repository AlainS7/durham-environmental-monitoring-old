# Hot Durham Weather Monitoring - Quick Setup Guide

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
cd "/Users/laptopUser/IdeaProjects/Hot Durham"
pip install pandas numpy matplotlib seaborn
```

### 2. Run Initial Analysis
```bash
python scripts/enhanced_data_analysis.py
```

### 3. Set Up Automation
```bash
./scripts/setup_automation.sh
```
Choose option 1 for daily reports or option 2 for weekly reports.

### 4. View Results
Open the generated HTML reports in your browser:
- Executive Summary: `reports/executive_summary_[timestamp].html`
- System Status: `reports/system_status_[timestamp].json`

## 📁 What Gets Created

### Reports (Updated Automatically)
- **Executive Summary**: Comprehensive HTML dashboard
- **System Status**: JSON health monitoring report
- **Data Quality**: Detailed quality assessment
- **Trend Charts**: Visual analysis of weather patterns

### Processed Data
- **Weekly Summaries**: Aggregated by week for both WU and TSI data
- **Monthly Summaries**: Monthly aggregations with statistics
- **Device Summaries**: Individual sensor health reports

### Automation
- **Cron Jobs**: Scheduled report generation
- **Log Files**: Detailed operation logs
- **Health Monitoring**: System status tracking

## ⚠️ Important Notes

1. **TSI Data Issue**: Air quality sensors currently showing no data - requires investigation
2. **Data Collection**: System works with existing data; new data collection needs setup
3. **Permissions**: Ensure scripts have execute permissions (`chmod +x`)

## 🔧 Troubleshooting

### Common Issues
- **"No module named" errors**: Run `pip install [module_name]`
- **Permission denied**: Run `chmod +x scripts/*.sh`
- **No data files**: Check `raw_data/` directory for CSV files

### Getting Help
- Check logs: `tail -f logs/automated_reports_$(date +%Y%m%d).log`
- Test manually: `python scripts/automated_reporting.py`
- View system status: Check latest `system_status_*.json` file

## 📊 Expected Output

After setup, you should see:
- ✅ 7+ processed summary files
- ✅ HTML reports with charts
- ✅ Automated cron jobs running
- ⚠️ Air quality data showing quality issues (expected)
- ✅ Weather data showing 100% completeness

---
**Setup Time**: ~5 minutes  
**System Status**: Production Ready  
**Last Updated**: 2025-05-25
