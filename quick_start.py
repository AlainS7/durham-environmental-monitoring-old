#!/usr/bin/env python3
"""
Hot Durham Quick Start Script

This script provides a comprehensive quick start for the Hot Durham project,
including system checks, dependency installation, and initial setup.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_status(message, status="INFO"):
    """Print status message"""
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}
    print(f"{icons.get(status, 'ℹ️')} {message}")

def run_command(command, description):
    """Run command and return success status"""
    print_status(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"✅ {description} completed successfully", "SUCCESS")
            return True
        else:
            print_status(f"❌ {description} failed: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        print_status(f"❌ {description} failed: {e}", "ERROR")
        return False

def main():
    """Main quick start process"""
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print_header("Hot Durham Environmental Monitoring System - Quick Start")
    
    print("""
🌟 Welcome to Hot Durham!
This comprehensive environmental monitoring system will help you:
- Collect real-time data from Weather Underground and TSI sensors
- Store and manage environmental data efficiently
- Generate automated reports and visualizations
- Monitor air quality and weather conditions

Let's get you set up...
    """)
    
    # Step 1: Check Python version
    print_header("Step 1: System Prerequisites")
    python_version = sys.version_info
    if python_version >= (3, 11) and python_version < (3, 12):
        print_status(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} ✓ (Recommended)", "SUCCESS")
    elif python_version >= (3, 8) and python_version < (3, 12):
        print_status(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} ✓ (Compatible)", "SUCCESS")
    elif python_version >= (3, 12):
        print_status(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} - Some packages may have compatibility issues", "WARNING")
        print_status("Python 3.11 is recommended for best compatibility", "INFO")
    else:
        print_status("Python 3.11 recommended. Please upgrade Python.", "ERROR")
        return False
    
    # Step 2: Install dependencies
    print_header("Step 2: Installing Dependencies")
    if run_command("pip install -r requirements.txt", "Installing Python packages"):
        print_status("All dependencies installed successfully", "SUCCESS")
    else:
        print_status("Dependency installation failed. Check your Python environment.", "ERROR")
        return False
    
    # Step 3: Check directory structure
    print_header("Step 3: Verifying Project Structure")
    required_dirs = ["data", "logs", "config", "src", "creds"]
    missing_dirs = []
    
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print_status(f"Directory '{dir_name}' ✓", "SUCCESS")
        else:
            print_status(f"Creating directory '{dir_name}'", "INFO")
            dir_path.mkdir(parents=True, exist_ok=True)
            print_status(f"Directory '{dir_name}' created ✓", "SUCCESS")
    
    # Step 4: Run system tests
    print_header("Step 4: System Health Check")
    if run_command("python tests/comprehensive_test_suite.py", "Running comprehensive tests"):
        print_status("System health check passed", "SUCCESS")
    else:
        print_status("Some tests failed, but system should still be functional", "WARNING")
    
    # Step 5: Configuration check
    print_header("Step 5: Configuration Setup")
    
    creds_dir = project_root / "creds"
    if not creds_dir.exists():
        creds_dir.mkdir(exist_ok=True)
    
    required_creds = [
        ("google_creds.json", "Google API credentials for Sheets integration"),
        ("wu_api_key.json", "Weather Underground API key"),
        ("tsi_creds.json", "TSI sensor credentials")
    ]
    
    missing_creds = []
    for cred_file, description in required_creds:
        cred_path = creds_dir / cred_file
        if cred_path.exists():
            print_status(f"Credential file '{cred_file}' found ✓", "SUCCESS")
        else:
            print_status(f"Missing: {cred_file} - {description}", "WARNING")
            missing_creds.append((cred_file, description))
    
    # Step 6: Quick test run
    print_header("Step 6: Quick Functionality Test")
    
    # Test enhanced features
    try:
        sys.path.insert(0, str(project_root / "src"))
        from src.utils.enhanced_logging import HotDurhamLogger
        from src.validation.data_validator import SensorDataValidator
        from src.database.db_manager import HotDurhamDB
        
        logger = HotDurhamLogger("quickstart")
        validator = SensorDataValidator()
        db = HotDurhamDB()
        
        logger.info("Quick start test message")
        print_status("Enhanced features working ✓", "SUCCESS")
        
    except Exception as e:
        print_status(f"Enhanced features test failed: {e}", "WARNING")
    
    # Final summary
    print_header("Setup Complete!")
    
    if missing_creds:
        print_status("⚠️ ACTION REQUIRED: Add credential files", "WARNING")
        print("\nTo complete setup, please add these credential files:")
        for cred_file, description in missing_creds:
            print(f"  📁 creds/{cred_file} - {description}")
        
        print("\n📚 See README.md for detailed credential setup instructions")
    
    print("""
🎉 Hot Durham is ready to use!

🚀 Quick Commands:
  • Test data collection:
    python src/data_collection/faster_wu_tsi_to_sheets_async.py
  
  • Run system status check:
    python scripts/production_manager.py status
  
  • Start monitoring dashboard:
    python src/monitoring/dashboard.py
  
  • Run comprehensive tests:
    python tests/comprehensive_test_suite.py

📖 Next Steps:
  1. Add your API credentials to the creds/ directory
  2. Configure your sensors in config/test_sensors_config.py
  3. Run your first data collection
  4. Set up automated scheduling (see docs/)

💡 Need help? Check out:
  • README.md - Complete documentation
  • docs/ - Detailed guides and tutorials
  • logs/ - System logs and diagnostics

Happy monitoring! 🌍📊
    """)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
