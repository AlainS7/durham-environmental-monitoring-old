# 🐍 Python Environment Setup Guide for Hot Durham

## Current Issue
You're experiencing package installation failures due to Python 3.13 compatibility issues and a corrupted pip installation in your virtual environment.

## 🎯 Recommended Solution: Python 3.11

### Why Python 3.11?
- **Maximum Compatibility**: All packages in Hot Durham are tested and work perfectly with Python 3.11
- **Stable Ecosystem**: Python 3.11 has mature package support
- **Performance**: Excellent performance for data processing tasks
- **Long-term Support**: Widely adopted and supported

## 🚀 Setup Instructions

### Option 1: Homebrew Installation (Recommended for macOS)

```bash
# 1. Install Python 3.11
brew install python@3.11

# 2. Navigate to your project
cd "/Users/alainsoto/IdeaProjects/Hot Durham"

# 3. Remove existing broken virtual environment
rm -rf .venv

# 4. Create new virtual environment with Python 3.11
python3.11 -m venv .venv

# 5. Activate the virtual environment
source .venv/bin/activate

# 6. Upgrade pip
pip install --upgrade pip

# 7. Install Hot Durham dependencies
pip install -r requirements_minimal.txt

# 8. Test the setup
python quick_start.py
```

### Option 2: Pyenv (Version Manager)

```bash
# 1. Install pyenv
brew install pyenv

# 2. Install Python 3.11.9
pyenv install 3.11.9

# 3. Set local Python version
pyenv local 3.11.9

# 4. Follow steps 2-8 from Option 1, but use python instead of python3.11
```

### Option 3: Direct Download

1. Download Python 3.11.9 from [python.org](https://www.python.org/downloads/release/python-3119/)
2. Install following the installer instructions
3. Follow steps 2-8 from Option 1

## 🔧 Troubleshooting Current Environment

If you want to try fixing your current Python 3.13 setup first:

```bash
# Run the fix script
chmod +x fix_current_env.sh
./fix_current_env.sh
```

## 📦 Package Installation Order

Once you have Python 3.11 set up, install packages in this order:

```bash
# Core data processing
pip install pandas numpy requests

# Google services
pip install gspread google-auth google-auth-oauthlib google-api-python-client

# Web and async
pip install httpx streamlit

# Utilities
pip install tqdm tenacity plotly psutil pyyaml colorama tabulate
```

## ✅ Verification Steps

After setup, verify everything works:

```bash
# Test imports
python -c "import pandas, numpy, requests, gspread; print('✅ Core packages OK')"

# Run system health check
python tests/comprehensive_test_suite.py

# Test data collection (with credentials)
python src/data_collection/faster_wu_tsi_to_sheets_async.py
```

## 🎉 Post-Setup

Once your environment is working:

1. **Add Credentials**: Place your API credentials in the `creds/` directory
2. **Configure Sensors**: Update `config/test_sensors_config.py` 
3. **Run First Collection**: Test data collection with real sensors
4. **Set Up Automation**: Configure automated data collection schedules

## 💡 Tips

- **Always use virtual environments** to avoid conflicts
- **Stick with Python 3.11** for maximum compatibility
- **Update packages regularly** but test after updates
- **Use the comprehensive test suite** to validate changes

## 📞 Need Help?

If you continue having issues:
1. Check the error logs in `logs/`
2. Run the comprehensive test suite
3. Verify your Python version with `python --version`
4. Ensure virtual environment is activated (you should see `(.venv)` in your terminal prompt)

The Hot Durham system is robust and will work excellently once you have Python 3.11 properly set up! 🌍📊
