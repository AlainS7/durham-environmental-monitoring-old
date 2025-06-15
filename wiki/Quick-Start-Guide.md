# Quick Start Guide

Get the Hot Durham Environmental Monitoring System up and running in under 10 minutes!

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.11 or higher installed
- ✅ Git installed
- ✅ Internet connection for API access
- ✅ 4GB+ RAM available

Quick check:
```bash
python3 --version  # Should show 3.11+
git --version      # Any recent version
```

## 🚀 5-Minute Setup

### Step 1: Clone and Enter Directory (30 seconds)

```bash
git clone https://github.com/your-org/hot-durham.git
cd hot-durham
```

### Step 2: Setup Python Environment (2 minutes)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Quick Configuration (1 minute)

```bash
# Copy example configuration
cp .env.example .env

# Edit with your preferred editor
nano .env  # or vim, code, etc.
```

**Minimal .env configuration:**
```env
# Basic settings for quick start
DEBUG=True
LOG_LEVEL=INFO
PORT=8080

# Optional: Add your API keys later
# WEATHER_UNDERGROUND_API_KEY=your_key_here
```

### Step 4: Initialize System (1 minute)

```bash
# Initialize database
python scripts/init_database.py

# Run system check
python -m src.utils.system_check
```

### Step 5: Start the System (30 seconds)

```bash
# Start the development server
python quick_start.py
```

**Success!** 🎉 Your system should now be running at `http://localhost:8080`

## 🎯 First Actions

### 1. Access the Dashboard

Open your browser and go to: `http://localhost:8080`

You should see:
- System status indicators
- Sample data visualizations
- Navigation menu

### 2. Test the API

```bash
# Check API health
curl http://localhost:8080/api/v1/health

# Expected response:
# {"status": "healthy", "version": "2.0.0", ...}
```

### 3. Explore Sample Data

The system includes sample data for immediate exploration:

```bash
# View sample sensor data
python scripts/show_sample_data.py

# Generate test visualizations
python scripts/create_sample_charts.py
```

## 📊 Adding Real Data Sources

### Weather Underground API (Optional)

1. **Get API Key**:
   - Sign up at [Weather Underground](https://www.wunderground.com/weather/api)
   - Copy your API key

2. **Configure**:
   ```bash
   # Add to .env file
   echo "WEATHER_UNDERGROUND_API_KEY=your_api_key_here" >> .env
   ```

3. **Test Connection**:
   ```bash
   python scripts/test_wu_connection.py
   ```

### Google Sheets Integration (Optional)

1. **Quick Setup**:
   ```bash
   # Run the setup wizard
   python scripts/setup_google_sheets.py
   ```

2. **Follow the prompts** to:
   - Download credentials
   - Set up service account
   - Configure sheet access

## 🔧 Common Quick Fixes

### Port Already in Use
```bash
# Use a different port
export PORT=8081
python quick_start.py
```

### Missing Dependencies
```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Permission Issues
```bash
# Fix common permission issues (macOS/Linux)
chmod +x scripts/*.py
chmod +x setup_git.sh
```

### Database Issues
```bash
# Reset database
rm -f data/hot_durham.db
python scripts/init_database.py
```

## 📱 Quick Demo

### 1. Dashboard Tour

Navigate through the main sections:

- **📊 Overview**: System status and key metrics
- **🌡️ Sensors**: Live sensor readings and status
- **📈 Charts**: Interactive data visualizations
- **⚙️ Settings**: System configuration
- **📋 Reports**: Data export and reporting

### 2. API Exploration

Test key API endpoints:

```bash
# System health
curl http://localhost:8080/api/v1/health

# List sensors (will show sample sensors)
curl http://localhost:8080/api/v1/sensors

# Get latest readings
curl http://localhost:8080/api/v1/data/latest
```

### 3. Data Export

Try exporting sample data:

1. Go to the **Reports** section in the dashboard
2. Select date range and sensors
3. Choose export format (CSV, JSON, PDF)
4. Download the generated file

## 🎓 Next Steps

### For Developers

1. **Read the Code**:
   ```bash
   # Explore key modules
   ls src/              # Core application code
   ls scripts/          # Utility scripts
   ls tests/            # Test suite
   ```

2. **Run Tests**:
   ```bash
   # Run the test suite
   python -m pytest tests/
   
   # Run with coverage
   python -m pytest tests/ --cov=src
   ```

3. **Development Setup**:
   ```bash
   # Install development dependencies
   pip install -r requirements-dev.txt
   
   # Set up pre-commit hooks
   pre-commit install
   ```

### For Users

1. **Configure Real Data Sources**:
   - Follow [Installation Guide](Installation-Guide.md) for full setup
   - Add your API keys and credentials
   - Configure sensors and data collection

2. **Customize Dashboard**:
   - Modify dashboard layout in `src/gui/dashboard.py`
   - Add custom visualizations
   - Configure alerts and notifications

3. **Set Up Automation**:
   - Configure scheduled data collection
   - Set up automated reports
   - Enable system monitoring

### For System Administrators

1. **Production Deployment**:
   - Read [Production Deployment](Production-Deployment.md)
   - Configure reverse proxy (nginx)
   - Set up SSL certificates
   - Configure backups

2. **Monitoring Setup**:
   - Enable system health checks
   - Configure log rotation
   - Set up alert notifications
   - Monitor performance metrics

## 🆘 Quick Help

### Getting Stuck?

1. **Check Logs**:
   ```bash
   # View recent logs
   tail -f logs/application.log
   ```

2. **Run Diagnostics**:
   ```bash
   # Comprehensive system check
   python scripts/diagnose.py
   ```

3. **Reset to Defaults**:
   ```bash
   # Start fresh (keeps your data)
   python scripts/reset_config.py
   ```

### Common Issues

| Problem | Quick Fix |
|---------|-----------|
| Port 8080 in use | `export PORT=8081` |
| Import errors | `pip install -r requirements.txt` |
| Permission denied | `chmod +x scripts/*.py` |
| Database locked | `rm data/hot_durham.db && python scripts/init_database.py` |
| API not responding | Check if server is running: `ps aux \| grep python` |

### Resources

- 📖 **Full Documentation**: [Installation Guide](Installation-Guide.md)
- 🏗️ **Architecture**: [Architecture Overview](Architecture-Overview.md)
- 🔌 **API Reference**: [API Documentation](API-Documentation.md)
- ❓ **FAQ**: [Frequently Asked Questions](FAQ.md)
- 🐛 **Issues**: [Common Issues](Common-Issues.md)

## 🎉 Success Checklist

After completing this quick start, you should have:

- ✅ Hot Durham system running locally
- ✅ Dashboard accessible in browser
- ✅ API responding to requests
- ✅ Sample data visible
- ✅ Basic understanding of system components

**Congratulations!** You're now ready to explore the full capabilities of the Hot Durham Environmental Monitoring System.

---

**Need more help?** Check the [FAQ](FAQ.md) or open an issue on GitHub.
