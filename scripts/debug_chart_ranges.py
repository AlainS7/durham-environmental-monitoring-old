#!/usr/bin/env python3
"""
Debug script to examine chart range issues in production runs.
This script will create a minimal test case to verify chart series ranges.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials as GCreds
from googleapiclient.discovery import build

# Add the current directory to the path so we can import from faster_wu_tsi_to_sheets_async
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def create_gspread_client_v2():
    """Create Google Sheets API client using service account credentials"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    google_creds_path = os.path.join(script_dir, '../creds/google_creds.json')
    
    try:
        creds = GCreds.from_service_account_file(
            google_creds_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets',
                   'https://www.googleapis.com/auth/drive']
        )
        return creds
    except Exception as e:
        print(f"❌ Failed to create Google credentials: {e}")
        return None

def create_test_sheet_with_chart():
    """Create a minimal test sheet to debug chart series issues"""
    
    # Create test data
    test_data = {
        'weeks': ['2024-01-01', '2024-01-08', '2024-01-15', '2024-01-22'],
        'Device1': [25.5, 30.2, 28.7, 32.1],
        'Device2': [22.3, 27.8, 26.1, 29.5],
        'Device3': [31.2, 35.6, 33.4, 37.8]
    }
    
    print("🔧 Creating test spreadsheet...")
    
    # Create spreadsheet
    creds = create_gspread_client_v2()
    if not creds:
        return None
        
    gc = gspread.authorize(creds)
    
    # Create new spreadsheet
    test_sheet = gc.create("Chart Debug Test - " + datetime.now().strftime("%Y%m%d_%H%M%S"))
    test_sheet.share('hotdurham@gmail.com', perm_type='user', role='writer')
    
    # Add test data
    headers = ['Week Start', 'Device1', 'Device2', 'Device3']
    rows = []
    for i, week in enumerate(test_data['weeks']):
        rows.append([week, test_data['Device1'][i], test_data['Device2'][i], test_data['Device3'][i]])
    
    ws = test_sheet.sheet1
    ws.update([headers] + rows)
    ws.update_title("Test Data")
    
    print(f"✅ Created test sheet: {test_sheet.url}")
    print(f"📊 Data written:")
    print(f"   Headers: {headers}")
    for i, row in enumerate(rows):
        print(f"   Row {i+2}: {row}")
    
    # Now create chart using Sheets API
    sheets_api = build('sheets', 'v4', credentials=creds)
    sheet_id = test_sheet.id
    
    # Get sheet metadata to find the sheet ID
    meta = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
    data_sheet_id = meta['sheets'][0]['properties']['sheetId']
    
    print(f"\n🎯 Creating chart with ranges:")
    print(f"   Sheet ID: {data_sheet_id}")
    print(f"   Domain range: Row 2-5, Col 0-1 (weeks)")
    print(f"   Series ranges:")
    
    # Create series for each device
    series = []
    for i, device in enumerate(['Device1', 'Device2', 'Device3'], start=1):
        series_range = {
            "series": {
                "sourceRange": {
                    "sources": [{
                        "sheetId": data_sheet_id,
                        "startRowIndex": 1,  # Row 2 (0-based)
                        "endRowIndex": 5,    # Row 5 (0-based, exclusive)
                        "startColumnIndex": i,  # Device column
                        "endColumnIndex": i + 1
                    }]
                }
            },
            "targetAxis": "LEFT_AXIS"
        }
        series.append(series_range)
        print(f"   {device}: Row 2-5, Col {i}-{i+1}")
    
    # Domain (X-axis) - weeks
    domain = {
        "domain": {
            "sourceRange": {
                "sources": [{
                    "sheetId": data_sheet_id,
                    "startRowIndex": 1,  # Row 2 (0-based)
                    "endRowIndex": 5,    # Row 5 (0-based, exclusive)
                    "startColumnIndex": 0,  # Week column
                    "endColumnIndex": 1
                }]
            }
        }
    }
    
    # Create chart
    chart_request = {
        "requests": [{
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Test Chart - PM2.5 Weekly Trend",
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "BOTTOM_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Week"},
                                {"position": "LEFT_AXIS", "title": "PM2.5 (µg/m³)"}
                            ],
                            "domains": [domain],
                            "series": series,
                            "headerCount": 1
                        }
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": data_sheet_id,
                                "rowIndex": 0,
                                "columnIndex": 5
                            }
                        }
                    }
                }
            }
        }]
    }
    
    print(f"\n📈 Adding chart...")
    try:
        result = sheets_api.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id, 
            body=chart_request
        ).execute()
        print(f"✅ Chart created successfully!")
        print(f"🔗 View spreadsheet: {test_sheet.url}")
        
        # Debug: Print the actual chart request for comparison
        print(f"\n🐛 Chart request JSON:")
        print(json.dumps(chart_request, indent=2))
        
    except Exception as e:
        print(f"❌ Failed to create chart: {e}")
        print(f"🐛 Chart request that failed:")
        print(json.dumps(chart_request, indent=2))
    
    return test_sheet

def analyze_real_data_ranges():
    """Analyze what ranges would be generated by the actual data processing logic"""
    
    # Simulate the weekly_summary structure from the real script
    weekly_summary = {
        'Device1': [
            ['2024-01-01', 25.5, 15.2, 18.7, 45.2],
            ['2024-01-08', 30.2, 12.1, 22.3, 52.1], 
            ['2024-01-15', 28.7, 14.8, 20.1, 48.7]
        ],
        'Device2': [
            ['2024-01-01', 22.3, 16.5, 19.2, 41.8],
            ['2024-01-08', 27.8, 13.7, 21.9, 49.3],
            ['2024-01-15', 26.1, 15.1, 19.8, 46.5]
        ]
    }
    
    print(f"\n🔍 Analyzing real data structure:")
    print(f"Weekly summary devices: {list(weekly_summary.keys())}")
    
    # Recreate the pivot logic from the real script
    data_columns = [
        ('Avg PM2.5', 'PM2.5 (µg/m³)'),
        ('Min Temp', 'Min Temp (°C)'),
        ('Max Temp', 'Max Temp (°C)'),
        ('Avg RH', 'Avg RH (%)')
    ]
    
    for col_name, y_label in data_columns:
        print(f"\n📊 Processing {col_name}:")
        
        weeks = sorted({row[0] for rows in weekly_summary.values() for row in rows})
        devices = list(weekly_summary.keys())
        pivot_header = ['Week Start'] + devices
        idx_map = {'Avg PM2.5':1, 'Min Temp':2, 'Max Temp':3, 'Avg RH':4}
        
        print(f"   Weeks: {weeks}")
        print(f"   Devices: {devices}")
        print(f"   Header: {pivot_header}")
        print(f"   Column index for {col_name}: {idx_map[col_name]}")
        
        pivot_rows = []
        for week in weeks:
            row = [week]
            for device in devices:
                val = ''
                for r in weekly_summary.get(device, []):
                    if r[0] == week:
                        val = r[idx_map[col_name]]
                        break
                row.append(val)
            pivot_rows.append(row)
        
        print(f"   Pivot data:")
        print(f"     Header: {pivot_header}")
        for i, row in enumerate(pivot_rows):
            print(f"     Row {i+1}: {row}")
        
        # Check for meaningful data
        has_data = False
        for row in pivot_rows:
            for val in row[1:]:  # Skip week column
                if val and val != '' and val != '0' and val != '0.0':
                    try:
                        if float(val) > 0:
                            has_data = True
                            break
                    except (ValueError, TypeError):
                        pass
            if has_data:
                break
        
        print(f"   Has meaningful data: {has_data}")
        
        if has_data:
            print(f"   Chart ranges would be:")
            print(f"     Domain: startRow=1, endRow={len(weeks)+1}, startCol=0, endCol=1")
            for i, device in enumerate(devices, start=1):
                print(f"     {device}: startRow=0, endRow={len(weeks)+1}, startCol={i}, endCol={i+1}")

if __name__ == "__main__":
    print("🚀 Chart Range Debug Tool")
    print("=" * 50)
    
    # First analyze what the real data structure would look like
    analyze_real_data_ranges()
    
    # Then create a test sheet to verify chart creation works
    print("\n" + "=" * 50)
    test_sheet = create_test_sheet_with_chart()
    
    if test_sheet:
        print(f"\n✨ Test completed!")
        print(f"📝 Please check the test sheet to see if the chart displays data correctly:")
        print(f"   {test_sheet.url}")
        print(f"\n💡 If the test chart shows data but production charts don't,")
        print(f"   the issue is likely in the data processing or range calculation logic.")
    else:
        print(f"\n❌ Test failed - could not create test sheet")
