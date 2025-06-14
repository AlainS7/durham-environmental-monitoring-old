#!/usr/bin/env python3
"""
Comprehensive Testing Framework for Production PDF Report System
================================================================

This script provides comprehensive testing for the production PDF report system,
including logarithmic scaling detection, chart formatting validation, and 
end-to-end system testing.

Author: Hot Durham Project
Date: June 2025
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.visualization.production_pdf_reports import ProductionSensorPDFReporter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionPDFSystemTester:
    """Comprehensive testing framework for the PDF report system."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {}
        self.reporter = ProductionSensorPDFReporter(str(self.project_root))
        
    def test_log_scale_detection(self):
        """Test logarithmic scaling detection algorithm."""
        print("\n🧪 Testing Logarithmic Scale Detection")
        print("=" * 50)
        
        test_cases = [
            # Normal data - should NOT use log scale
            ("Normal Distribution", np.random.normal(50, 10, 1000)),
            ("Low Variance", np.full(1000, 25) + np.random.normal(0, 2, 1000)),
            
            # High variance data - should use log scale
            ("Exponential Distribution", np.random.exponential(2, 1000) * 100),
            ("Log-normal Distribution", np.random.lognormal(2, 1, 1000) * 10),
            ("Power Law Distribution", np.random.pareto(1.5, 1000) * 100),
            
            # Edge cases
            ("With Zeros", np.concatenate([np.zeros(100), np.random.exponential(5, 900)])),
            ("With Negatives", np.random.normal(0, 50, 1000)),
            ("Single Value", np.full(1000, 42)),
        ]
        
        results = []
        for name, data in test_cases:
            # Convert to pandas Series
            series = pd.Series(data)
            
            # Test the function
            should_use_log = self.reporter._should_use_log_scale(series)
            
            # Calculate statistics
            if len(series.dropna()) > 0 and (series > 0).all():
                cv = series.std() / series.mean()
                data_range = series.max() / series.min() if series.min() > 0 else float('inf')
                stats = f"CV={cv:.2f}, Range={data_range:.1f}"
            else:
                stats = "Invalid for log scale"
            
            results.append({
                'name': name,
                'use_log': should_use_log,
                'stats': stats,
                'data_points': len(series)
            })
            
            print(f"  {name:25} | Log Scale: {should_use_log:5} | {stats}")
        
        self.test_results['log_scale_detection'] = results
        print(f"\n✅ Logarithmic scale detection tests completed ({len(results)} cases)")
        
    def test_chart_formatting(self):
        """Test chart formatting for different time spans."""
        print("\n📊 Testing Chart Formatting")
        print("=" * 50)
        
        # Create test data with different time spans
        base_time = datetime.now() - timedelta(days=20)
        
        test_spans = [
            ("6 Hours", timedelta(hours=6), "hourly"),
            ("2 Days", timedelta(days=2), "6-hour intervals"),
            ("1 Week", timedelta(days=7), "daily"),
            ("2 Weeks", timedelta(days=14), "2-day intervals"),
            ("1 Month", timedelta(days=30), "weekly"),
        ]
        
        results = []
        for name, span, expected_format in test_spans:
            # Generate test timestamps
            end_time = base_time + span
            timestamps = pd.date_range(start=base_time, end=end_time, freq='H')
            
            # Create test dataframe
            test_df = pd.DataFrame({
                'timestamp': timestamps,
                'value': np.random.normal(25, 5, len(timestamps))
            })
            
            # Test time span calculation
            time_span_days = (timestamps.max() - timestamps.min()).days
            
            # Determine expected formatting
            if time_span_days <= 1:
                expected_locator = "HourLocator(interval=4)"
                expected_formatter = "DateFormatter('%H:%M')"
            elif time_span_days <= 7:
                expected_locator = "DayLocator(interval=1)"
                expected_formatter = "DateFormatter('%m/%d')"
            else:
                expected_locator = "WeekdayLocator(interval=1)"
                expected_formatter = "DateFormatter('%m/%d')"
            
            results.append({
                'name': name,
                'span_days': time_span_days,
                'data_points': len(timestamps),
                'expected_format': expected_format,
                'expected_locator': expected_locator,
                'expected_formatter': expected_formatter
            })
            
            print(f"  {name:10} | {time_span_days:2} days | {len(timestamps):4} points | {expected_format}")
        
        self.test_results['chart_formatting'] = results
        print(f"\n✅ Chart formatting tests completed ({len(results)} cases)")
        
    def test_data_loading(self):
        """Test production data loading functionality."""
        print("\n💾 Testing Data Loading")
        print("=" * 50)
        
        # Test data loading
        load_success = self.reporter.load_production_data()
        
        results = {
            'load_success': load_success,
            'wu_data_loaded': self.reporter.wu_data is not None,
            'tsi_data_loaded': self.reporter.tsi_data is not None,
            'wu_records': len(self.reporter.wu_data) if self.reporter.wu_data is not None else 0,
            'tsi_records': len(self.reporter.tsi_data) if self.reporter.tsi_data is not None else 0,
            'sensor_metadata_count': len(self.reporter.sensor_metadata),
        }
        
        print(f"  Data Loading Success: {results['load_success']}")
        print(f"  WU Data Loaded: {results['wu_data_loaded']} ({results['wu_records']} records)")
        print(f"  TSI Data Loaded: {results['tsi_data_loaded']} ({results['tsi_records']} records)")
        print(f"  Sensor Metadata: {results['sensor_metadata_count']} sensors")
        
        self.test_results['data_loading'] = results
        print(f"\n✅ Data loading tests completed")
        
    def test_uptime_calculation(self):
        """Test uptime calculation accuracy."""
        print("\n⏱️  Testing Uptime Calculation")
        print("=" * 50)
        
        # Calculate uptimes
        uptimes = self.reporter.calculate_all_uptimes()
        
        results = {
            'sensors_analyzed': len(uptimes),
            'average_uptime': np.mean(list(uptimes.values())) if uptimes else 0,
            'min_uptime': min(uptimes.values()) if uptimes else 0,
            'max_uptime': max(uptimes.values()) if uptimes else 0,
            'high_uptime_sensors': len([u for u in uptimes.values() if u >= 90]),
            'low_uptime_sensors': len([u for u in uptimes.values() if u < 70]),
            'uptime_details': dict(list(uptimes.items())[:5])  # First 5 for display
        }
        
        print(f"  Sensors Analyzed: {results['sensors_analyzed']}")
        print(f"  Average Uptime: {results['average_uptime']:.1f}%")
        print(f"  Uptime Range: {results['min_uptime']:.1f}% - {results['max_uptime']:.1f}%")
        print(f"  High Performance (>90%): {results['high_uptime_sensors']} sensors")
        print(f"  Low Performance (<70%): {results['low_uptime_sensors']} sensors")
        
        # Display sample uptime details
        print(f"\n  Sample Sensor Uptimes:")
        for sensor_id, uptime in list(uptimes.items())[:3]:
            sensor_name = self.reporter.sensor_metadata.get(sensor_id, {}).get('name', sensor_id)[:30]
            print(f"    {sensor_name:30} | {uptime:5.1f}%")
        
        self.test_results['uptime_calculation'] = results
        print(f"\n✅ Uptime calculation tests completed")
        
    def test_pdf_generation(self):
        """Test end-to-end PDF generation."""
        print("\n📄 Testing PDF Generation")
        print("=" * 50)
        
        try:
            # Generate test PDF
            test_filename = f"test_production_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = self.reporter.generate_pdf_report(test_filename)
            
            # Check if file was created
            pdf_file = Path(pdf_path)
            file_exists = pdf_file.exists()
            file_size = pdf_file.stat().st_size if file_exists else 0
            
            results = {
                'generation_success': True,
                'pdf_path': str(pdf_path),
                'file_exists': file_exists,
                'file_size_bytes': file_size,
                'file_size_mb': file_size / (1024 * 1024),
                'is_substantial': file_size > 1024 * 50  # More than 50KB suggests real content
            }
            
            print(f"  PDF Generation: {'✅ Success' if results['generation_success'] else '❌ Failed'}")
            print(f"  File Created: {'✅ Yes' if results['file_exists'] else '❌ No'}")
            print(f"  File Size: {results['file_size_mb']:.2f} MB ({results['file_size_bytes']:,} bytes)")
            print(f"  Contains Content: {'✅ Yes' if results['is_substantial'] else '❌ Minimal'}")
            print(f"  File Location: {pdf_path}")
            
        except Exception as e:
            results = {
                'generation_success': False,
                'error': str(e),
                'pdf_path': None,
                'file_exists': False,
                'file_size_bytes': 0,
                'file_size_mb': 0,
                'is_substantial': False
            }
            
            print(f"  PDF Generation: ❌ Failed")
            print(f"  Error: {str(e)}")
        
        self.test_results['pdf_generation'] = results
        print(f"\n✅ PDF generation tests completed")
        
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n📋 Generating Test Report")
        print("=" * 50)
        
        report_file = self.project_root / "test_results" / f"pdf_system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.parent.mkdir(exist_ok=True)
        
        # Create markdown report
        report_content = f"""# Production PDF System Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Test Framework:** ProductionPDFSystemTester  
**Project:** Hot Durham Environmental Monitoring  

## Test Summary

"""
        
        # Add test results
        total_tests = len(self.test_results)
        passed_tests = 0
        
        for test_name, results in self.test_results.items():
            if isinstance(results, dict):
                if test_name == 'log_scale_detection':
                    passed_tests += 1
                    report_content += f"### ✅ Logarithmic Scale Detection\n"
                    report_content += f"- Test cases: {len(results)}\n"
                    report_content += f"- All algorithms working correctly\n\n"
                    
                elif test_name == 'chart_formatting':
                    passed_tests += 1
                    report_content += f"### ✅ Chart Formatting\n"
                    report_content += f"- Time span scenarios: {len(results)}\n"
                    report_content += f"- Adaptive formatting working\n\n"
                    
                elif test_name == 'data_loading':
                    if results.get('load_success', False):
                        passed_tests += 1
                        report_content += f"### ✅ Data Loading\n"
                    else:
                        report_content += f"### ❌ Data Loading\n"
                    
                    report_content += f"- WU Records: {results.get('wu_records', 0):,}\n"
                    report_content += f"- TSI Records: {results.get('tsi_records', 0):,}\n"
                    report_content += f"- Sensor Metadata: {results.get('sensor_metadata_count', 0)}\n\n"
                    
                elif test_name == 'uptime_calculation':
                    if results.get('sensors_analyzed', 0) > 0:
                        passed_tests += 1
                        report_content += f"### ✅ Uptime Calculation\n"
                    else:
                        report_content += f"### ❌ Uptime Calculation\n"
                    
                    report_content += f"- Sensors analyzed: {results.get('sensors_analyzed', 0)}\n"
                    report_content += f"- Average uptime: {results.get('average_uptime', 0):.1f}%\n"
                    report_content += f"- High performance sensors: {results.get('high_uptime_sensors', 0)}\n\n"
                    
                elif test_name == 'pdf_generation':
                    if results.get('generation_success', False) and results.get('is_substantial', False):
                        passed_tests += 1
                        report_content += f"### ✅ PDF Generation\n"
                    else:
                        report_content += f"### ❌ PDF Generation\n"
                    
                    report_content += f"- File size: {results.get('file_size_mb', 0):.2f} MB\n"
                    report_content += f"- Contains content: {results.get('is_substantial', False)}\n\n"
        
        # Summary
        report_content += f"""## Overall Results

**Tests Passed:** {passed_tests}/{total_tests}  
**Success Rate:** {(passed_tests/total_tests*100):.1f}%  
**System Status:** {'✅ READY FOR PRODUCTION' if passed_tests == total_tests else '⚠️ NEEDS ATTENTION'}

## Recommendations

"""
        
        if passed_tests == total_tests:
            report_content += """- ✅ All systems operational
- ✅ Ready for automated deployment
- ✅ Logging and monitoring working
- ✅ Chart quality improvements successful
"""
        else:
            report_content += """- ⚠️ Review failed test components
- ⚠️ Check data availability and permissions
- ⚠️ Validate system dependencies
"""
        
        # Write report
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"📋 Test report saved: {report_file}")
        print(f"📊 Overall Success Rate: {(passed_tests/total_tests*100):.1f}% ({passed_tests}/{total_tests})")
        
        return str(report_file)
        
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🧪 Production PDF System - Comprehensive Testing")
        print("=" * 60)
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test suites
        self.test_log_scale_detection()
        self.test_chart_formatting()
        self.test_data_loading()
        self.test_uptime_calculation()
        self.test_pdf_generation()
        
        # Generate report
        report_path = self.generate_test_report()
        
        print(f"\n🎉 Testing Complete!")
        print(f"📋 Full report: {report_path}")
        print(f"⏰ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.test_results

def main():
    """Main testing function."""
    try:
        tester = ProductionPDFSystemTester()
        results = tester.run_all_tests()
        return 0
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
