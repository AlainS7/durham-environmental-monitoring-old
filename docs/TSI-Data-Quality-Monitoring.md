# TSI Data Quality Monitoring Setup

## Overview

Added comprehensive TSI-specific data quality monitoring to detect NULL metrics early and prevent recurrence of the historical data issue discovered on Oct 6, 2025.

## What Was Added

### 1. Enhanced Data Quality Script

**File**: `scripts/check_data_quality.py`

**New Function**: `check_raw_tsi_metrics()`
- Checks raw `tsi_raw_materialized` table for NULL values in critical metrics
- Monitors: pm2_5, temperature, humidity, co2_ppm
- **Alert threshold**: >2% NULL for any critical metric
- **Why this matters**: NULL metrics indicate TSI parser failure or data collection bypass

**Updated Functions**:
- `check_raw_table_schema()` → Now checks `tsi_raw_materialized` for record counts
- `check_coverage()` → Fixed to work with current schema (uses metric names instead of source column)
- `check_aggregate_consistency()` → Fixed to use proper table schemas

### 2. GitHub Actions Workflow

**File**: `.github/workflows/tsi-data-quality.yml`

**Schedule**: Daily at 08:30 UTC (after transformations complete at 07:25 UTC)

**Features**:
- Runs data quality checks for yesterday's TSI data
- Creates GitHub issues automatically on quality failures
- Manual trigger with custom date or days parameter
- Detailed failure reporting with investigation steps

**Checks Performed**:
1. ✅ Raw table has data for date range
2. ✅ **Critical TSI metrics <2% NULL** (pm2_5, temperature, humidity)
3. ✅ Coverage above 90% threshold
4. ✅ Aggregate consistency

### 3. Dependencies

**Added**: `db-dtypes>=1.3.0` to `requirements.txt`
- Required for BigQuery DATE types in pandas DataFrames

## Usage

### Manual Quality Check

Check specific date:
```bash
python scripts/check_data_quality.py \
  --start 2025-10-06 \
  --end 2025-10-06 \
  --source TSI \
  --verbose
```

Check last 7 days:
```bash
python scripts/check_data_quality.py \
  --days 7 \
  --source TSI \
  --fail-on-issues
```

Check both TSI and WU:
```bash
python scripts/check_data_quality.py \
  --days 3 \
  --source both
```

### Automated Monitoring

**Daily Check**: GitHub Actions runs automatically at 08:30 UTC
- No action needed - runs in background
- Creates issue if quality problems detected

**Manual Trigger**: 
```bash
# Via GitHub CLI
gh workflow run tsi-data-quality.yml

# Or via web UI:
# Actions → TSI Data Quality Check → Run workflow
```

## Alert Thresholds

| Metric | Threshold | Severity |
|--------|-----------|----------|
| pm2_5 NULL % | >2% | 🔴 CRITICAL |
| temperature NULL | >100 records/day | ⚠️ WARNING |
| humidity NULL | >100 records/day | ⚠️ WARNING |
| Coverage | <90% | 🔴 ERROR |
| Record count | <100/day | ⚠️ WARNING |

## Root Cause This Prevents

**Historical Issue** (Discovered Oct 6, 2025):
- 71 days of TSI data (July 27 - Oct 5) had ALL metrics NULL
- Root cause: Data loaded without TSIClient parser (bypassed measurement extraction)
- Result: UNPIVOT returned 0 rows (drops all-NULL records)
- Looker Studio showed only 3-4 dates instead of 90 days

**Prevention**:
- This monitoring detects NULL metrics IMMEDIATELY (next day)
- Alerts trigger before transformations propagate bad data
- Investigation steps provided in GitHub issue
- Can re-run collection quickly with `make run-collector`

## Troubleshooting

### If NULL Metrics Detected

1. **Check Cloud Scheduler**:
   ```bash
   gcloud scheduler jobs describe daily-data-collection-trigger
   ```
   - Ensure state is "ENABLED"
   - Check last execution status

2. **Check Cloud Run Job**:
   ```bash
   gcloud run jobs executions list --job weather-data-uploader --limit 5
   ```
   - Look for failed executions
   - Check logs for TSIClient errors

3. **Check GCS Parquet Files**:
   ```bash
   gsutil ls -lh gs://YOUR_BUCKET/sensors/tsi/2025-10-06*.parquet
   ```
   - Verify files exist and have reasonable size (>100KB)

4. **Verify Raw Data**:
   ```sql
   SELECT 
     DATE(ts) as date,
     COUNT(*) as total,
     COUNTIF(pm2_5 IS NULL) as null_pm25,
     ROUND(100.0 * COUNTIF(pm2_5 IS NULL) / COUNT(*), 2) as null_pct
   FROM `sensors.tsi_raw_materialized`
   WHERE DATE(ts) = '2025-10-06'
   GROUP BY date
   ```

5. **Re-run Collection** (if needed):
   ```bash
   make run-collector START=2025-10-06 END=2025-10-06 SOURCE=tsi
   ```

### Common Issues

**Issue**: "No TSI raw data found for date range"
- **Cause**: Collection didn't run or failed
- **Fix**: Check Cloud Scheduler enabled, check Cloud Run logs

**Issue**: "pm2_5 >2% NULL"
- **Cause**: TSI API issues or parser problems
- **Fix**: Check API credentials, verify TSI API response format

**Issue**: "Coverage below 90%"
- **Cause**: Transformation didn't run or partial data
- **Fix**: Run transformations manually: `make run-transformations DATE=2025-10-06`

## Testing

### Test on Oct 5 Data (Known Good)

```bash
# Should pass all checks
python scripts/check_data_quality.py \
  --start 2025-10-05 \
  --end 2025-10-05 \
  --source TSI
```

**Expected Result**:
```
✓ Raw TSI table check passed (1 days, 10633 total records)
✓ TSI raw metric NULL check passed (all <2.0%)
✓ Coverage validation passed for TSI
✓ All data quality checks passed!
```

### Simulate NULL Detection

To test alert system:
1. Temporarily update threshold to 0% in script
2. Re-run check (should fail and show NULL percentages)
3. Restore threshold to 2%

## Integration with Existing Workflows

### Cloud Scheduler (5:00 UTC)
↓
### Daily Data Collection
- Cloud Run Job `weather-data-uploader`
- Uses TSIClient with proper parsing ✅
↓
### E2E Nightly (7:05 UTC)
- Materialize: Loads GCS → BigQuery
- Transform: Runs 8 SQL files
↓
### **TSI Data Quality Check (8:30 UTC)** ← NEW
- Validates yesterday's TSI data
- Creates issue if problems detected
↓
### Manual Investigation
- Follow steps in GitHub issue
- Re-collect if needed

## Maintenance

### Adding New Metrics to Monitor

Edit `scripts/check_data_quality.py`:
```python
# In check_raw_tsi_metrics() function
# Add new metric to query:
COUNTIF(new_metric IS NULL) as null_new_metric,
```

### Adjusting Thresholds

```python
# In check_raw_tsi_metrics() function
critical_threshold = 2.0  # Change to 5.0 for more lenient
```

### Disabling Checks Temporarily

Comment out in `.github/workflows/tsi-data-quality.yml`:
```yaml
on:
  schedule:
    # - cron: '30 8 * * *'  # Commented out
```

## Verification

✅ Script tested on Oct 5, 2025 data (100% metrics populated)
✅ NULL check correctly identifies pm2_5, temperature, humidity
✅ GitHub Actions workflow syntax validated
✅ Dependencies added to requirements.txt
✅ db-dtypes installed in environment

## Next Steps

1. **Tomorrow (Oct 7)**: Verify monitoring works on today's data
2. **Weekly**: Review GitHub issues for any quality alerts
3. **Monthly**: Review alert thresholds and adjust if needed
4. **As needed**: Add more metrics or sources to monitoring

## References

- Original issue: Historical backfill (Oct 6, 2025)
- Root cause: TSI data loaded without TSIClient parser
- Solution: Re-collected 71 days with proper parsing
- Prevention: This monitoring system
