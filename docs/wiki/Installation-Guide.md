# Installation Guide

This guide will help you set up the Hot Durham Environmental Monitoring System on your local machine or server.

## Prerequisites

Before installing the Hot Durham system, ensure you have the following:

### System Requirements
- **Operating System**: macOS 10.15+, Ubuntu 18.04+, or Windows 10+
- **Python**: 3.11 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB free space minimum
- **Network**: Stable internet connection for API access

### Required Accounts
- **Google Cloud Platform** account for Sheets API
- **Weather Underground** API key
- **GitHub** account for code access

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/hot-durham.git
cd hot-durham
```

### 2. Python Environment Setup

#### Option A: Using Python 3.11 (Recommended)
```bash
# Install Python 3.11 if not already installed
# macOS with Homebrew
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

#### Option B: Using pyenv (Alternative)
```bash
# Install pyenv if not already installed
curl https://pyenv.run | bash

# Install Python 3.11
pyenv install 3.11.9
pyenv local 3.11.9

# Create virtual environment
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# For development (optional)
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# API Keys
WEATHER_UNDERGROUND_API_KEY=your_wu_api_key_here
GOOGLE_SHEETS_CREDENTIALS_PATH=path/to/credentials.json

# Database Configuration
DATABASE_URL=sqlite:///data/hot_durham.db

# Application Settings
DEBUG=True
LOG_LEVEL=INFO
PORT=8080

# Data Collection Settings
DATA_COLLECTION_INTERVAL=300  # seconds
MAX_RETRIES=3
TIMEOUT=30
```

### 5. Set Up Google Sheets Integration

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Sheets API

2. **Create Service Account**:
   - Go to "IAM & Admin" > "Service Accounts"
   - Create a new service account
   - Download the JSON credentials file
   - Save it as `creds/service_account.json`

3. **Share Google Sheets**:
   - Share your target Google Sheets with the service account email
   - Grant "Editor" permissions

### 6. Initialize Database

```bash
# Run database migrations
python scripts/init_database.py

# Create initial configuration
python scripts/setup_config.py
```

### 7. Verify Installation

```bash
# Run system checks
python -m src.utils.system_check

# Test API connections
python scripts/test_connections.py

# Start the development server
python quick_start.py
```

If successful, you should see:
```
✅ System check passed
✅ API connections verified
🚀 Hot Durham system starting on http://localhost:8080
```

## Post-Installation Setup

### Configure Data Sources

1. **Weather Underground Setup**:
   ```bash
   python scripts/configure_wu_stations.py
   ```

2. **TSI Sensors Setup**:
   ```bash
   python scripts/configure_tsi_sensors.py
   ```

### Set Up Automated Data Collection

```bash
# Install system service (Linux/macOS)
sudo ./scripts/install_service.sh

# Or run manually for testing
python -m src.automation.scheduler
```

### Configure Monitoring

```bash
# Set up health checks
python scripts/setup_monitoring.py

# Configure alerts
python scripts/configure_alerts.py
```

## Troubleshooting

### Common Installation Issues

#### Python Version Issues
```bash
# Check Python version
python --version

# If using wrong version, ensure virtual environment is activated
source .venv/bin/activate
```

#### Dependency Installation Failures
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Google Sheets Authentication
```bash
# Verify credentials file exists
ls -la creds/service_account.json

# Test authentication
python scripts/test_google_auth.py
```

#### API Connection Issues
```bash
# Check network connectivity
python scripts/test_network.py

# Verify API keys
python scripts/validate_api_keys.py
```

### Getting Help

If you encounter issues:

1. Check the [Common Issues](Common-Issues.md) page
2. Review log files in the `logs/` directory
3. Run the diagnostic script: `python scripts/diagnose.py`
4. Open an issue on GitHub with the diagnostic output

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](Quick-Start-Guide.md)
2. Explore the [Dashboard User Guide](Dashboard-User-Guide.md)
3. Check out the [Configuration Reference](Configuration-Reference.md)
4. Set up [Production Deployment](Production-Deployment.md) if needed

---

*For additional help, see the [FAQ](FAQ.md) or contact the development team.*
