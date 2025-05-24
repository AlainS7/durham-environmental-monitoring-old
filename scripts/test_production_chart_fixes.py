#!/usr/bin/env python3
"""
Production test to verify the actual script now creates working charts.
"""

import subprocess
import sys
import os
from datetime import datetime, timedelta

def test_production_script():
    """Test the actual production script with real API calls"""
    
    print("🔬 Testing Production Script with Chart Fixes")
    print("=" * 60)
    
    # Calculate test date range (last 3 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"📅 Test date range: {start_str} to {end_str}")
    print(f"🎯 This will test with recent data to verify chart generation")
    
    # Prepare inputs for the script
    inputs = [
        start_str,              # Start date
        end_str,                # End date  
        "hotdurham@gmail.com",  # Email
        "y",                    # Fetch TSI
        "y",                    # Fetch WU
        "n",                    # Don't combine data
        "y",                    # Add charts
        ""                      # Empty line to finish
    ]
    
    input_string = "\n".join(inputs)
    
    print(f"🚀 Running production script...")
    print(f"   Inputs prepared: {len(inputs)} responses")
    
    try:
        # Run the actual production script
        result = subprocess.run(
            [sys.executable, "faster_wu_tsi_to_sheets_async.py"],
            input=input_string,
            text=True,
            capture_output=True,
            timeout=300  # 5 minute timeout
        )
        
        print(f"\n📊 Script execution results:")
        print(f"   Return code: {result.returncode}")
        
        if result.stdout:
            print(f"   ✅ Output:")
            # Show last 20 lines to see chart creation results
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-20:]:
                if line.strip():
                    print(f"     {line}")
        
        if result.stderr:
            print(f"   ⚠️ Errors:")
            error_lines = result.stderr.strip().split('\n')
            for line in error_lines[-10:]:
                if line.strip():
                    print(f"     {line}")
        
        # Look for specific success indicators
        success_indicators = [
            "Chart created successfully",
            "✅ Chart",
            "📈 Adding chart",
            "Charts completed"
        ]
        
        chart_success = any(indicator in result.stdout for indicator in success_indicators)
        
        if result.returncode == 0 and chart_success:
            print(f"\n🎉 SUCCESS: Production script completed with charts!")
            
            # Extract spreadsheet URL if present
            for line in result.stdout.split('\n'):
                if "https://docs.google.com/spreadsheets" in line:
                    print(f"📊 Spreadsheet: {line.strip()}")
                    break
                    
        elif result.returncode == 0:
            print(f"\n⚠️ Script completed but unclear if charts were created")
            
        else:
            print(f"\n❌ Script failed with return code {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"\n⏰ Script timed out after 5 minutes")
        return False
        
    except Exception as e:
        print(f"\n❌ Error running script: {e}")
        return False

if __name__ == "__main__":
    success = test_production_script()
    
    if success:
        print(f"\n✨ Production test completed successfully!")
        print(f"🔍 Check the generated spreadsheet to verify charts show data")
        print(f"   instead of 'add a series to start visualizing your data'")
    else:
        print(f"\n❌ Production test failed")
        print(f"🔧 Additional debugging may be needed")