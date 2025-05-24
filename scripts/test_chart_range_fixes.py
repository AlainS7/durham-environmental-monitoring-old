#!/usr/bin/env python3
"""
Test script to verify all chart range fixes are working correctly.
This will create test sheets with different data patterns to validate chart creation.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials as GCreds
from googleapiclient.discovery import build

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

def test_tsi_weekly_chart_fixes():
    """Test TSI weekly chart creation with fixed ranges"""
    
    print("🧪 Testing TSI Weekly Chart Fixes")
    print("=" * 50)
    
    # Create test data that matches the actual TSI weekly structure
    weekly_summary = {
        'Duke-MS-01': [
            ['2024-01-01', 25.5, 15.2, 18.7, 45.2],
            ['2024-01-08', 30.2, 12.1, 22.3, 52.1], 
            ['2024-01-15', 28.7, 14.8, 20.1, 48.7],
            ['2024-01-22', 32.1, 11.5, 24.2, 49.8]
        ],
        'Duke-MS-02': [
            ['2024-01-01', 22.3, 16.5, 19.2, 41.8],
            ['2024-01-08', 27.8, 13.7, 21.9, 49.3],
            ['2024-01-15', 26.1, 15.1, 19.8, 46.5],
            ['2024-01-22', 29.4, 12.8, 23.1, 44.2]
        ],
        'Duke-MS-03': [
            ['2024-01-01', 28.9, 14.2, 17.5, 47.6],
            ['2024-01-08', 33.1, 11.8, 20.7, 53.4],
            ['2024-01-15', 31.5, 13.9, 18.9, 50.1],
            ['2024-01-22', 35.7, 10.3, 22.8, 48.9]
        ]
    }
    
    # Create spreadsheet
    creds = create_gspread_client_v2()
    if not creds:
        return None
        
    gc = gspread.authorize(creds)
    
    # Create new spreadsheet
    test_sheet = gc.create("Chart Range Fix Test - " + datetime.now().strftime("%Y%m%d_%H%M%S"))
    test_sheet.share('hotdurham@gmail.com', perm_type='user', role='writer')
    
    print(f"✅ Created test sheet: {test_sheet.url}")
    
    # Create a charts sheet like the main script does
    charts_title = 'Test Charts'
    charts_ws = test_sheet.add_worksheet(title=charts_title, rows=1000, cols=20)
    
    sheets_api = build('sheets', 'v4', credentials=creds)
    sheet_id = test_sheet.id
    
    # Get charts sheet ID
    meta_charts = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
    charts_id = next(s['properties']['sheetId'] for s in meta_charts['sheets'] if s['properties']['title'] == charts_title)
    chart_row_offset = 0
    
    # Test each data column
    data_columns = [
        ('Avg PM2.5', 'PM2.5 (µg/m³)', 1),
        ('Min Temp', 'Min Temp (°C)', 2),
        ('Max Temp', 'Max Temp (°C)', 3),
        ('Avg RH', 'Avg RH (%)', 4)
    ]
    
    for col_name, y_label, col_idx in data_columns:
        print(f"\n📊 Testing {col_name} chart...")
        
        # Recreate the pivot logic from the fixed script
        weeks = sorted({row[0] for rows in weekly_summary.values() for row in rows})
        devices = list(weekly_summary.keys())
        pivot_header = ['Week Start'] + devices
        
        print(f"   Weeks: {len(weeks)} entries")
        print(f"   Devices: {devices}")
        
        pivot_rows = []
        for week in weeks:
            row = [week]
            for device in devices:
                val = ''
                for r in weekly_summary.get(device, []):
                    if r[0] == week:
                        val = r[col_idx]
                        break
                row.append(val)
            pivot_rows.append(row)
        
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
        
        if not has_data:
            print(f"   ⚠️ No meaningful data found for {col_name}")
            continue
        
        print(f"   ✅ Found meaningful data")
        
        # Create worksheet for this metric
        pivot_title = f"{col_name} Weekly Data"
        pivot_ws = test_sheet.add_worksheet(title=pivot_title, rows=len(pivot_rows)+1, cols=len(devices)+1)
        pivot_ws.update([pivot_header] + pivot_rows)
        
        print(f"   📝 Created worksheet: {pivot_title}")
        print(f"   📊 Data dimensions: {len(pivot_rows)+1} rows x {len(devices)+1} cols")
        
        # Get sheet metadata
        meta_p = sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()
        pivot_id = next(s['properties']['sheetId'] for s in meta_p['sheets'] if s['properties']['title'] == pivot_title)
        
        # Create series with FIXED ranges (startRowIndex: 1 to exclude headers)
        series = []
        for i, device in enumerate(devices, start=1):
            series.append({
                "series": {"sourceRange": {"sources": [{
                    "sheetId": pivot_id,
                    "startRowIndex": 1,  # FIXED: Skip header row
                    "endRowIndex": len(weeks)+1,
                    "startColumnIndex": i,
                    "endColumnIndex": i+1
                }]}},
                "targetAxis": "LEFT_AXIS"
            })
            print(f"   📈 {device} series: rows 2-{len(weeks)+1}, col {i+1}")
        
        # Domain (X-axis) - weeks
        domain = {"domain": {"sourceRange": {"sources": [{
            "sheetId": pivot_id,
            "startRowIndex": 1,  # Skip header row
            "endRowIndex": len(weeks)+1,
            "startColumnIndex": 0,
            "endColumnIndex": 1
        }]}}}
        
        print(f"   📅 Domain: rows 2-{len(weeks)+1}, col 1 (weeks)")
        
        # Create chart with fixed ranges
        chart = {
            "requests": [{
                "addChart": {
                    "chart": {
                        "spec": {
                            "title": f"Fixed Range Test - Weekly {col_name} Trend",
                            "basicChart": {
                                "chartType": "LINE",
                                "legendPosition": "BOTTOM_LEGEND",
                                "axis": [
                                    {"position": "BOTTOM_AXIS", "title": "Week"},
                                    {"position": "LEFT_AXIS", "title": y_label}
                                ],
                                "domains": [domain],
                                "series": series,
                                "headerCount": 1
                            }
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": charts_id,
                                    "rowIndex": chart_row_offset,
                                    "columnIndex": 0
                                }
                            }
                        }
                    }
                }
            }]
        }
        
        try:
            result = sheets_api.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id, 
                body=chart
            ).execute()
            print(f"   ✅ Chart created successfully!")
            
        except Exception as e:
            print(f"   ❌ Failed to create chart: {e}")
            print(f"   🐛 Chart request:")
            print(json.dumps(chart, indent=4))
    
    print(f"\n🎯 Test completed!")
    print(f"📊 View all test charts: {test_sheet.url}")
    print(f"\n💡 Key fixes applied:")
    print(f"   • Series startRowIndex changed from 0 to 1 (exclude headers)")
    print(f"   • Domain startRowIndex kept at 1 (exclude headers)")
    print(f"   • Both series and domain now have consistent row ranges")
    
    return test_sheet

if __name__ == "__main__":
    test_sheet = test_tsi_weekly_chart_fixes()
    
    if test_sheet:
        print(f"\n✨ Success! Check the charts in: {test_sheet.url}")
        print(f"📝 If charts show proper data lines instead of 'add a series' message,")
        print(f"   then the fixes are working correctly!")
    else:
        print(f"\n❌ Test failed")
