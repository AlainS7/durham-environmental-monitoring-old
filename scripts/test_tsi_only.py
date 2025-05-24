#!/usr/bin/env python3
"""
Run the script with TSI data only (skip WU) to test the chart fixes
while resolving the Weather Underground API authentication issue.
"""

import subprocess
import sys
import os

def run_tsi_only():
    """Run the script with TSI data only"""
    print("🔧 Running script with TSI data only (skipping WU due to API issues)")
    print("This will test the chart generation fixes while you resolve the WU API key issue.")
    
    # Change to the scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run the script and automatically select TSI only (option 2)
    # Provide default responses for all prompts
    inputs = [
        "2",  # Select TSI only
        "",   # Default start date (2025-03-01)
        "",   # Default end date (2025-04-30)
        "",   # Default email (hotdurham@gmail.com)
        "n",  # No local download
        "n",  # No OneDrive upload
        "y"   # Yes to charts
    ]
    
    input_string = "\n".join(inputs) + "\n"
    
    try:
        # Run the main script with our inputs
        result = subprocess.run(
            [sys.executable, "faster_wu_tsi_to_sheets_async.py"],
            input=input_string,
            text=True,
            capture_output=True,
            timeout=300  # 5 minute timeout
        )
        
        print("📋 Script Output:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Errors/Warnings:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("✅ Script completed successfully!")
        else:
            print(f"❌ Script failed with exit code: {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⏰ Script timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Error running script: {e}")

if __name__ == "__main__":
    print("🧪 Testing TSI functionality only")
    print("This bypasses the Weather Underground API authentication issue")
    print("=" * 60)
    
    run_tsi_only()
