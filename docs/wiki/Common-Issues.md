# Common Issues and Troubleshooting

This guide helps you diagnose and resolve common issues with the Hot Durham Environmental Monitoring System.

## 🔧 Quick Diagnostics

### System Health Check

Run the built-in diagnostics to identify common issues:

```bash
# Check system status
python quick_start.py --health-check

# Verify configuration
python scripts/verify_cloud_pipeline.py --date 2025-08-27

# Test API connections
python -c "from src.utils.api_client import APIClient; print('API OK' if APIClient().test_connection() else 'API Failed')"
```

## 🚫 Installation and Setup Issues

### Issue: Python Version Compatibility
**Symptoms:**
* `ModuleNotFoundError` during installation
* Syntax errors on startup
* Import failures

**Solutions:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Create fresh virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies (uv preferred)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip sync requirements.txt
uv pip sync requirements-dev.txt || true

# Or with pip
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Issue: Missing Dependencies
**Symptoms:**
* Import errors for specific modules
* "No module named..." errors

**Solutions:**
```bash
# Install all requirements (prefer uv)
uv pip sync requirements.txt || true

# Or pip fallback
pip install -r requirements.txt

# For specific missing modules
pip install module_name

# Update all packages
pip install --upgrade -r requirements.txt
```

### Issue: Permission Errors
**Symptoms:**
* Cannot create files or directories
* Database access denied
* Log file creation failures

**Solutions:**
```bash
# Fix file permissions (Linux/Mac)
chmod +x scripts/*.py
chmod 755 data/ logs/ temp/

# Create necessary directories
mkdir -p logs temp data processed

# Windows: Run as administrator or check folder permissions
```

## 🌐 API and Data Source Issues

### Issue: Weather Underground API Failures
**Symptoms:**
* "401 Unauthorized" errors
* Empty weather data responses
* Rate limiting messages

**Solutions:**
1. **Check API Key:**
   ```python
   # Verify in config
   grep -r "weather_underground" config/
   ```

2. **Validate Credentials:**
   ```bash
   # Test API directly
   curl -H "Authorization: Bearer YOUR_API_KEY" "https://api.weather.com/v1/current"
   ```

3. **Check Rate Limits:**
   * Review API usage quotas
   * Adjust polling intervals in configuration
   * Implement caching to reduce API calls

### Issue: TSI Sensor Connection Problems
**Symptoms:**
* Sensor timeout errors
* Inconsistent data readings
* Connection refused messages

**Solutions:**
1. **Network Connectivity:**
   ```bash
   # Test sensor connectivity
   ping sensor_ip_address
   telnet sensor_ip_address sensor_port
   ```

2. **Configuration Check:**
   ```python
   # Review sensor settings
   cat config/test_sensors_config.py
   ```

3. **Firewall Issues:**
   * Check firewall rules
   * Verify port accessibility
   * Test from different network locations

### Issue: Google Sheets Integration Errors
**Symptoms:**
* Authentication failures
* Permission denied errors
* Sheet not found errors

**Solutions:**
1. **Credentials Verification:**
   ```bash
   # Check credentials file
   ls -la creds/
   python -c "import json; print(json.load(open('creds/service_account.json'))['client_email'])"
   ```

2. **Sheet Permissions:**
   * Verify service account has access to sheets
   * Check sheet sharing settings
   * Ensure correct sheet IDs in configuration

## 💾 Database Issues

### Issue: Database Connection Failures
**Symptoms:**
* "Database connection refused"
* Timeout errors during queries
* "Table doesn't exist" errors

**Solutions:**
1. **Connection Testing:**
   ```python
   from src.database.db_manager import DatabaseManager
   db = DatabaseManager()
   print("Connection OK" if db.test_connection() else "Connection Failed")
   ```

2. **Database Initialization:**
   ```bash
   # Initialize/reset database
   python src/database/init_db.py
   ```

3. **Permission Issues:**
   ```bash
   # Check database file permissions
   ls -la data/database.db
   chmod 664 data/database.db
   ```

### Issue: Data Import/Export Problems
**Symptoms:**
* CSV export failures
* Data format errors
* Missing historical data

**Solutions:**
1. **File Path Issues:**
   ```bash
   # Check directory permissions
   ls -la data/ processed/
   mkdir -p processed reports
   ```

2. **Data Validation:**
   ```python
   # Test data validator
   from src.validation.data_validator import DataValidator
   validator = DataValidator()
   validator.validate_data_integrity()
   ```

## 🖥️ Dashboard and Web Interface Issues

### Issue: Dashboard Not Loading
**Symptoms:**
* Blank dashboard pages
* 500 Internal Server Error
* CSS/JavaScript not loading

**Solutions:**
1. **Service Status:**
   ```bash
   # Check if dashboard service is running
   ps aux | grep dashboard
   netstat -tlnp | grep :5000
   ```

2. **Static Files:**
   ```bash
   # Verify static files exist
   ls -la static/
   python src/monitoring/dashboard.py --check-static
   ```

3. **Browser Cache:**
   * Clear browser cache and cookies
   * Try incognito/private browsing mode
   * Check browser developer console for errors

### Issue: Real-time Updates Not Working
**Symptoms:**
* Stale data in dashboard
* Charts not updating
* WebSocket connection errors

**Solutions:**
1. **WebSocket Configuration:**
   ```python
   # Check WebSocket settings
   grep -r "websocket\|socketio" src/monitoring/
   ```

2. **Firewall/Proxy Issues:**
   * Check WebSocket ports are open
   * Verify proxy settings don't block WebSocket connections
   * Test from different network locations

## 📊 Data Processing Issues

### Issue: Anomaly Detection False Positives
**Symptoms:**
* Too many alert notifications
* Normal variations flagged as anomalies
* System performance degradation

**Solutions:**
1. **Threshold Adjustment:**
   ```bash
   # Review anomaly detection config
   cat config/anomaly_detection_config.json
   ```

2. **Sensitivity Tuning:**
   ```python
   # Test with different thresholds
   from src.analysis.anomaly_detector import AnomalyDetector
   detector = AnomalyDetector()
   detector.tune_sensitivity(validation_data)
   ```

### Issue: Report Generation Failures
**Symptoms:**
* PDF generation errors
* Incomplete reports
* Missing charts or data

**Solutions:**
1. **Dependencies Check:**
   ```bash
   # Install report generation dependencies
   pip install reportlab matplotlib
   ```

2. **Template Validation:**
   ```bash
   # Check report templates
   ls -la templates/reports/
   python scripts/test_report_generation.py
   ```

## 🔍 Performance Issues

### Issue: Slow Data Processing
**Symptoms:**
* Long response times
* High memory usage
* CPU usage spikes

**Solutions:**
1. **Resource Monitoring:**
   ```bash
   # Monitor system resources
   top
   htop
   python src/monitoring/performance_monitor.py
   ```

2. **Database Optimization:**
   ```sql
   -- Check database performance
   ANALYZE;
   VACUUM;
   ```

3. **Caching Implementation:**
   ```python
   # Enable caching
   from src.utils.cache_manager import CacheManager
   cache = CacheManager()
   cache.enable_caching()
   ```

### Issue: Memory Leaks
**Symptoms:**
* Gradually increasing memory usage
* System becoming unresponsive
* Out of memory errors

**Solutions:**
1. **Memory Profiling:**
   ```python
   # Profile memory usage
   pip install memory-profiler
   python -m memory_profiler scripts/production_manager.py
   ```

2. **Connection Management:**
   ```python
   # Ensure proper connection cleanup
   # Check for unclosed database connections
   # Review API client connection pooling
   ```

## 🔐 Security and Authentication Issues

### Issue: API Key Exposure
**Symptoms:**
* API keys visible in logs
* Credentials in version control
* Unauthorized API access

**Solutions:**
1. **Immediate Actions:**
   ```bash
   # Rotate all API keys immediately
   # Remove from version control history
   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch config/secrets.json'
   ```

2. **Secure Storage:**
   ```bash
   # Use environment variables
   export WEATHER_API_KEY="your_secure_key"
   # Use encrypted credential storage
   ```

### Issue: Unauthorized Access
**Symptoms:**
* Unexpected data modifications
* Unknown user sessions
* Suspicious API activity

**Solutions:**
1. **Access Review:**
   ```bash
   # Review access logs
   grep -r "unauthorized\|failed" logs/
   ```

2. **Security Hardening:**
   ```python
   # Enable additional authentication
   # Implement rate limiting
   # Add request logging
   ```

## 📞 Getting Additional Help

### Log Analysis
```bash
# Check system logs for errors
tail -f logs/data_management.log
grep -i error logs/*.log
grep -i warning logs/*.log
```

### System Information Collection
```bash
# Gather system information for support
python -c "
import sys, platform, pkg_resources
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Packages: {[str(d) for d in pkg_resources.working_set]}')
"
```

### When to Seek Help

* After trying multiple solutions from this guide
* For persistent issues affecting system stability
* When encountering errors not covered here
* For security-related concerns

### Support Resources

* [FAQ](FAQ.md) - Frequently asked questions
* [GitHub Issues](https://github.com/your-org/hot-durham/issues) - Bug reports and feature requests
* [Development Team Contact] - Direct technical support
* [Community Forums] - Community assistance

---

*This troubleshooting guide is regularly updated. If you encounter an issue not covered here, please contribute the solution back to help others.*

*Last updated: June 15, 2025*
