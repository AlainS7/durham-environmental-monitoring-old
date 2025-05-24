#!/usr/bin/env python3
"""
Weather Underground API Key Tester
This script tests your WU API key to help diagnose authentication issues.
"""

import json
import httpx
import os

def test_wu_api_key():
    """Test the Weather Underground API key"""
    
    # Load API key
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wu_api_key_path = os.path.join(script_dir, '..', 'creds', 'wu_api_key.json')
    wu_api_key_abs = os.path.abspath(wu_api_key_path)
    
    if not os.path.exists(wu_api_key_abs):
        print(f"❌ ERROR: WU API key file not found at {wu_api_key_abs}")
        return False
    
    try:
        with open(wu_api_key_abs) as f:
            wu_key = json.load(f)['test_api_key']
        print(f"✅ Loaded API key: {wu_key[:8]}...{wu_key[-4:]}")
    except Exception as e:
        print(f"❌ Error loading API key: {e}")
        return False
    
    # Test with a simple API call
    test_station = "KNCDURHA548"  # One of your stations
    test_date = "20250101"  # A recent date
    
    url = "https://api.weather.com/v2/pws/history/hourly"
    params = {
        "stationId": test_station,
        "date": test_date,
        "format": "json",
        "apiKey": wu_key,
        "units": "m",
        "numericPrecision": "decimal",
    }
    
    print(f"\n🧪 Testing API call...")
    print(f"URL: {url}")
    print(f"Station: {test_station}")
    print(f"Date: {test_date}")
    print(f"API Key: {wu_key[:8]}...{wu_key[-4:]}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            
            print(f"\n📡 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! Your API key is working correctly.")
                data = response.json()
                obs_count = len(data.get('observations', []))
                print(f"📊 Received {obs_count} observations")
                return True
                
            elif response.status_code == 401:
                print("❌ AUTHENTICATION FAILED (401)")
                print("\n🔍 Possible reasons:")
                print("1. Your API key is invalid or expired")
                print("2. Your API key doesn't have the correct permissions")
                print("3. The API key format is incorrect")
                
                try:
                    error_data = response.json()
                    print(f"\n📋 Error details: {error_data}")
                except:
                    print(f"\n📋 Raw error response: {response.text}")
                
                print("\n💡 What to do:")
                print("1. Check your Weather Underground account dashboard")
                print("2. Verify your API key is active and not expired")
                print("3. Ensure you have the right API plan/permissions")
                print("4. Try generating a new API key if needed")
                return False
                
            elif response.status_code == 204:
                print("⚠️ No data available for this station/date (204)")
                print("This might be normal - try a different date or station")
                return True
                
            else:
                print(f"❌ Unexpected response code: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📋 Error details: {error_data}")
                except:
                    print(f"📋 Raw error response: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("❌ Request timed out - network issue or API is slow")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_api_key_format():
    """Check if the API key format looks correct"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wu_api_key_path = os.path.join(script_dir, '..', 'creds', 'wu_api_key.json')
    wu_api_key_abs = os.path.abspath(wu_api_key_path)
    
    try:
        with open(wu_api_key_abs) as f:
            data = json.load(f)
            wu_key = data['test_api_key']
            
        print(f"🔍 API Key Analysis:")
        print(f"   Length: {len(wu_key)} characters")
        print(f"   Format: {wu_key[:8]}...{wu_key[-4:]}")
        
        # WU API keys are typically 32 characters, alphanumeric
        if len(wu_key) == 32:
            print("✅ Length looks correct (32 chars)")
        else:
            print(f"⚠️ Unusual length - WU API keys are typically 32 characters")
            
        if wu_key.isalnum():
            print("✅ Format looks correct (alphanumeric)")
        else:
            print("⚠️ Contains non-alphanumeric characters - this might be unusual")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking API key format: {e}")
        return False

if __name__ == "__main__":
    print("🌦️ Weather Underground API Key Tester")
    print("=" * 50)
    
    print("\n1️⃣ Checking API key format...")
    format_ok = check_api_key_format()
    
    print("\n2️⃣ Testing API authentication...")
    auth_ok = test_wu_api_key()
    
    print("\n" + "=" * 50)
    if format_ok and auth_ok:
        print("🎉 Your Weather Underground API key is working correctly!")
        print("The issue might be with rate limits or specific dates/stations.")
    else:
        print("❌ There are issues with your Weather Underground API key.")
        print("Please resolve these before running the main script.")
