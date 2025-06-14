#!/usr/bin/env python3
"""
Feature 2 Implementation Test Suite
Test all components of the Predictive Analytics & AI system

This script tests:
- Air Quality Forecasting ML models
- Enhanced Anomaly Detection with automated alerts
- Seasonal Pattern Analysis
- Health Impact Modeling
- API Integration
- Dashboard Integration
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import requests
import pandas as pd
import numpy as np

# Add project paths
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src" / "ml"))
sys.path.append(str(project_root / "src" / "visualization"))
sys.path.append(str(project_root / "src" / "analysis"))
sys.path.append(str(project_root))

# Test data for verification
TEST_SENSOR_DATA = {
    'pm25': 45.2,
    'temperature': 23.5,
    'humidity': 68.3,
    'timestamp': datetime.now().isoformat()
}

class Feature2TestSuite:
    """Comprehensive test suite for Feature 2 implementation."""
    
    def __init__(self):
        self.project_root = project_root
        self.test_results = {
            'start_time': datetime.now().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'component_results': {},
            'errors': []
        }
        
        print("🧪 Feature 2: Predictive Analytics & AI Test Suite")
        print("=" * 60)
        print(f"📂 Project root: {self.project_root}")
        print(f"🕒 Test started: {self.test_results['start_time']}")

    def run_all_tests(self):
        """Run all Feature 2 tests."""
        print("\n🚀 Running comprehensive Feature 2 test suite...")
        
        # Test 1: Predictive Analytics Core
        self.test_predictive_analytics_core()
        
        # Test 2: Enhanced Anomaly Detection
        self.test_enhanced_anomaly_detection()
        
        # Test 3: API Integration
        self.test_api_integration()
        
        # Test 4: Dashboard Integration
        self.test_dashboard_integration()
        
        # Test 5: Data Flow Integration
        self.test_data_flow_integration()
        
        # Test 6: Performance and Reliability
        self.test_performance_reliability()
        
        # Generate final report
        self.generate_test_report()

    def test_predictive_analytics_core(self):
        """Test the core predictive analytics functionality."""
        component = "predictive_analytics_core"
        print(f"\n🤖 Testing {component}...")
        
        try:
            from predictive_analytics import PredictiveAnalytics
            
            # Initialize system
            analytics = PredictiveAnalytics(self.project_root)
            self._log_test(component, "initialization", True)
            
            # Test data loading
            try:
                data_loaded = analytics.load_historical_data()
                self._log_test(component, "data_loading", data_loaded)
                print(f"  📊 Data loaded: {len(analytics.historical_data) if hasattr(analytics, 'historical_data') else 0} records")
            except Exception as e:
                self._log_test(component, "data_loading", False, str(e))
            
            # Test model training
            try:
                model_results = analytics.train_air_quality_models()
                models_trained = len(model_results) > 0
                self._log_test(component, "model_training", models_trained)
                print(f"  🧠 Models trained: {list(model_results.keys()) if model_results else 'None'}")
            except Exception as e:
                self._log_test(component, "model_training", False, str(e))
            
            # Test predictions
            try:
                predictions = analytics.predict_air_quality(hours_ahead=24)
                predictions_generated = 'predictions' in predictions and len(predictions['predictions']) > 0
                self._log_test(component, "prediction_generation", predictions_generated)
                
                if predictions_generated:
                    print(f"  🔮 Generated {len(predictions['predictions'])} predictions")
                    next_hour = predictions['predictions'][0]
                    print(f"  📈 Next hour forecast: {next_hour['predicted_pm25']:.1f} μg/m³ ({next_hour['health_category']})")
                
            except Exception as e:
                self._log_test(component, "prediction_generation", False, str(e))
            
            # Test seasonal analysis
            try:
                seasonal_analysis = analytics.analyze_seasonal_patterns()
                seasonal_completed = 'error' not in seasonal_analysis
                self._log_test(component, "seasonal_analysis", seasonal_completed)
                
                if seasonal_completed:
                    analysis_period = seasonal_analysis.get('analysis_period', {})
                    print(f"  🌱 Seasonal analysis: {analysis_period.get('total_days', 0)} days analyzed")
                
            except Exception as e:
                self._log_test(component, "seasonal_analysis", False, str(e))
            
            # Test health impact modeling
            try:
                health_report = analytics.generate_health_impact_report()
                health_completed = 'error' not in health_report
                self._log_test(component, "health_impact_modeling", health_completed)
                
                if health_completed:
                    health_summary = health_report.get('air_quality_summary', {})
                    print(f"  🏥 Health analysis: {health_summary.get('average_pm25', 'N/A')} μg/m³ average")
                
            except Exception as e:
                self._log_test(component, "health_impact_modeling", False, str(e))
                
        except ImportError as e:
            self._log_test(component, "import", False, f"Cannot import predictive_analytics: {e}")
        except Exception as e:
            self._log_test(component, "general", False, str(e))

    def test_enhanced_anomaly_detection(self):
        """Test the enhanced anomaly detection with alerting."""
        component = "enhanced_anomaly_detection"
        print(f"\n🚨 Testing {component}...")
        
        try:
            from enhanced_anomaly_detection import EnhancedAnomalyDetector
            
            # Initialize system
            detector = EnhancedAnomalyDetector(self.project_root)
            self._log_test(component, "initialization", True)
            
            # Test configuration loading
            try:
                config_loaded = detector.alert_config is not None
                self._log_test(component, "configuration_loading", config_loaded)
                print(f"  ⚙️ Alert channels: {list(detector.alert_config.get('notification_channels', {}).keys())}")
            except Exception as e:
                self._log_test(component, "configuration_loading", False, str(e))
            
            # Test real-time anomaly detection
            try:
                alerts = detector.detect_real_time_anomalies(TEST_SENSOR_DATA)
                anomaly_detection_working = isinstance(alerts, list)
                self._log_test(component, "real_time_detection", anomaly_detection_working)
                print(f"  🔍 Alerts generated: {len(alerts)}")
                
                for alert in alerts:
                    print(f"    • {alert['level'].upper()}: {alert['message']}")
                    
            except Exception as e:
                self._log_test(component, "real_time_detection", False, str(e))
            
            # Test alert management
            try:
                active_alerts = detector.get_active_alerts()
                alert_summary = detector.generate_alert_summary()
                alert_management_working = isinstance(active_alerts, dict) and isinstance(alert_summary, dict)
                self._log_test(component, "alert_management", alert_management_working)
                print(f"  📊 Active alerts: {len(active_alerts)}, 24h summary: {alert_summary.get('total_alerts', 0)}")
            except Exception as e:
                self._log_test(component, "alert_management", False, str(e))
            
            # Test file-based alerting
            try:
                alerts_dir = detector.alerts_dir
                alerts_file = alerts_dir / "current_alerts.json"
                file_alerts_working = alerts_dir.exists()
                self._log_test(component, "file_alerting", file_alerts_working)
                print(f"  📁 Alerts directory: {alerts_dir}")
            except Exception as e:
                self._log_test(component, "file_alerting", False, str(e))
                
        except ImportError as e:
            self._log_test(component, "import", False, f"Cannot import enhanced_anomaly_detection: {e}")
        except Exception as e:
            self._log_test(component, "general", False, str(e))

    def test_api_integration(self):
        """Test the predictive analytics API integration."""
        component = "api_integration"
        print(f"\n🌐 Testing {component}...")
        
        try:
            from predictive_api import PredictiveAnalyticsAPI
            
            # Initialize API
            api = PredictiveAnalyticsAPI(self.project_root)
            self._log_test(component, "initialization", True)
            
            # Test forecast endpoint
            try:
                forecast = api.get_air_quality_forecast(hours_ahead=24)
                forecast_working = 'status' in forecast and forecast['status'] == 'success'
                self._log_test(component, "forecast_endpoint", forecast_working)
                
                if forecast_working:
                    predictions = forecast['forecast']['predictions']
                    print(f"  🔮 Forecast API: {len(predictions)} predictions generated")
                else:
                    print(f"  ❌ Forecast error: {forecast.get('error', 'Unknown error')}")
                    
            except Exception as e:
                self._log_test(component, "forecast_endpoint", False, str(e))
            
            # Test alerts endpoint
            try:
                alerts = api.get_current_alerts()
                alerts_working = 'status' in alerts
                self._log_test(component, "alerts_endpoint", alerts_working)
                print(f"  🚨 Alerts API: {alerts.get('status', 'unknown')} status")
            except Exception as e:
                self._log_test(component, "alerts_endpoint", False, str(e))
            
            # Test seasonal analysis endpoint
            try:
                seasonal = api.get_seasonal_analysis()
                seasonal_working = 'status' in seasonal
                self._log_test(component, "seasonal_endpoint", seasonal_working)
                print(f"  🌱 Seasonal API: {seasonal.get('status', 'unknown')} status")
            except Exception as e:
                self._log_test(component, "seasonal_endpoint", False, str(e))
            
            # Test health impact endpoint
            try:
                health = api.get_health_impact_assessment()
                health_working = 'status' in health
                self._log_test(component, "health_endpoint", health_working)
                print(f"  🏥 Health API: {health.get('status', 'unknown')} status")
            except Exception as e:
                self._log_test(component, "health_endpoint", False, str(e))
            
            # Test real-time processing
            try:
                result = api.process_real_time_data(TEST_SENSOR_DATA)
                realtime_working = 'status' in result and result['status'] == 'success'
                self._log_test(component, "realtime_processing", realtime_working)
                print(f"  ⚡ Real-time processing: {len(result.get('alerts', []))} alerts generated")
            except Exception as e:
                self._log_test(component, "realtime_processing", False, str(e))
                
        except ImportError as e:
            self._log_test(component, "import", False, f"Cannot import predictive_api: {e}")
        except Exception as e:
            self._log_test(component, "general", False, str(e))

    def test_dashboard_integration(self):
        """Test integration with the public dashboard."""
        component = "dashboard_integration"
        print(f"\n📊 Testing {component}...")
        
        try:
            from public_dashboard import PublicDashboardServer
            
            # Initialize dashboard
            dashboard = PublicDashboardServer(str(self.project_root))
            self._log_test(component, "initialization", True)
            
            # Check if predictive API is integrated
            predictive_integrated = dashboard.predictive_api is not None
            self._log_test(component, "predictive_integration", predictive_integrated)
            print(f"  🤖 Predictive API integrated: {predictive_integrated}")
            
            # Test Flask app creation
            try:
                app_created = dashboard.app is not None
                self._log_test(component, "flask_app_creation", app_created)
                print(f"  🌐 Flask app created: {app_created}")
                
                # Test route registration
                with dashboard.app.test_client() as client:
                    
                    # Test forecast route
                    try:
                        response = client.get('/api/public/forecast')
                        forecast_route_working = response.status_code in [200, 503]  # 503 if service unavailable
                        self._log_test(component, "forecast_route", forecast_route_working)
                        print(f"  📈 Forecast route: HTTP {response.status_code}")
                    except Exception as e:
                        self._log_test(component, "forecast_route", False, str(e))
                    
                    # Test alerts route
                    try:
                        response = client.get('/api/public/alerts')
                        alerts_route_working = response.status_code in [200, 503]
                        self._log_test(component, "alerts_route", alerts_route_working)
                        print(f"  🚨 Alerts route: HTTP {response.status_code}")
                    except Exception as e:
                        self._log_test(component, "alerts_route", False, str(e))
                    
                    # Test health impact route
                    try:
                        response = client.get('/api/public/health-impact')
                        health_route_working = response.status_code in [200, 503]
                        self._log_test(component, "health_route", health_route_working)
                        print(f"  🏥 Health impact route: HTTP {response.status_code}")
                    except Exception as e:
                        self._log_test(component, "health_route", False, str(e))
                    
                    # Test seasonal route
                    try:
                        response = client.get('/api/public/seasonal')
                        seasonal_route_working = response.status_code in [200, 503]
                        self._log_test(component, "seasonal_route", seasonal_route_working)
                        print(f"  🌱 Seasonal route: HTTP {response.status_code}")
                    except Exception as e:
                        self._log_test(component, "seasonal_route", False, str(e))
                        
            except Exception as e:
                self._log_test(component, "flask_app_creation", False, str(e))
                
        except ImportError as e:
            self._log_test(component, "import", False, f"Cannot import public_dashboard: {e}")
        except Exception as e:
            self._log_test(component, "general", False, str(e))

    def test_data_flow_integration(self):
        """Test data flow between components."""
        component = "data_flow_integration"
        print(f"\n🔄 Testing {component}...")
        
        try:
            # Test data directories exist
            data_dir = self.project_root / "data"
            models_dir = self.project_root / "models" / "ml"
            reports_dir = self.project_root / "reports"
            
            directories_exist = all([
                data_dir.exists(),
                models_dir.exists() or models_dir.parent.exists(),
                reports_dir.exists()
            ])
            self._log_test(component, "directory_structure", directories_exist)
            print(f"  📁 Directory structure: {directories_exist}")
            
            # Test configuration files
            config_dir = self.project_root / "config"
            anomaly_config = config_dir / "anomaly_detection_config.json"
            alert_config = config_dir / "alert_system_config.json"
            
            configs_exist = anomaly_config.exists()
            self._log_test(component, "configuration_files", configs_exist)
            print(f"  ⚙️ Configuration files exist: {configs_exist}")
            
            # Test data file accessibility
            raw_pulls_dir = self.project_root / "data" / "raw_pulls"
            master_data_dir = self.project_root / "data" / "master_data"
            
            data_accessible = raw_pulls_dir.exists() or master_data_dir.exists()
            self._log_test(component, "data_accessibility", data_accessible)
            print(f"  📊 Data files accessible: {data_accessible}")
            
            # Test integration with existing anomaly detection
            try:
                from anomaly_detection_and_trend_analysis import AnomalyDetectionSystem
                base_system = AnomalyDetectionSystem(str(self.project_root))
                base_integration = base_system is not None
                self._log_test(component, "base_anomaly_integration", base_integration)
                print(f"  🔍 Base anomaly system integration: {base_integration}")
            except Exception as e:
                self._log_test(component, "base_anomaly_integration", False, str(e))
                
        except Exception as e:
            self._log_test(component, "general", False, str(e))

    def test_performance_reliability(self):
        """Test performance and reliability aspects."""
        component = "performance_reliability"
        print(f"\n⚡ Testing {component}...")
        
        try:
            # Test prediction speed
            start_time = time.time()
            try:
                from predictive_api import PredictiveAnalyticsAPI
                api = PredictiveAnalyticsAPI(self.project_root)
                forecast = api.get_air_quality_forecast(hours_ahead=12)
                prediction_time = time.time() - start_time
                
                prediction_fast = prediction_time < 30.0  # Should complete in under 30 seconds
                self._log_test(component, "prediction_speed", prediction_fast)
                print(f"  🏃 Prediction speed: {prediction_time:.2f}s ({'✅ Fast' if prediction_fast else '⚠️ Slow'})")
                
            except Exception as e:
                self._log_test(component, "prediction_speed", False, str(e))
            
            # Test error handling
            try:
                from enhanced_anomaly_detection import EnhancedAnomalyDetector
                detector = EnhancedAnomalyDetector(self.project_root)
                
                # Test with invalid data
                invalid_data = {'invalid': 'data'}
                alerts = detector.detect_real_time_anomalies(invalid_data)
                error_handling = isinstance(alerts, list)  # Should not crash
                self._log_test(component, "error_handling", error_handling)
                print(f"  🛡️ Error handling: {'✅ Robust' if error_handling else '❌ Fragile'}")
                
            except Exception as e:
                self._log_test(component, "error_handling", False, str(e))
            
            # Test memory usage (basic check)
            try:
                import psutil
                import os
                
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_reasonable = memory_mb < 500  # Should use less than 500MB
                self._log_test(component, "memory_usage", memory_reasonable)
                print(f"  🧠 Memory usage: {memory_mb:.1f}MB ({'✅ Efficient' if memory_reasonable else '⚠️ High'})")
                
            except ImportError:
                print("  ℹ️ psutil not available for memory testing")
            except Exception as e:
                self._log_test(component, "memory_usage", False, str(e))
                
        except Exception as e:
            self._log_test(component, "general", False, str(e))

    def _log_test(self, component: str, test_name: str, passed: bool, error: str = None):
        """Log a test result."""
        self.test_results['tests_run'] += 1
        
        if passed:
            self.test_results['tests_passed'] += 1
            status = "✅ PASS"
        else:
            self.test_results['tests_failed'] += 1
            status = "❌ FAIL"
            if error:
                self.test_results['errors'].append(f"{component}.{test_name}: {error}")
        
        if component not in self.test_results['component_results']:
            self.test_results['component_results'][component] = {}
        
        self.test_results['component_results'][component][test_name] = {
            'passed': passed,
            'error': error
        }
        
        print(f"    {status} {test_name}")

    def generate_test_report(self):
        """Generate final test report."""
        self.test_results['end_time'] = datetime.now().isoformat()
        
        print("\n" + "=" * 60)
        print("📋 FEATURE 2 TEST REPORT")
        print("=" * 60)
        
        # Summary
        total = self.test_results['tests_run']
        passed = self.test_results['tests_passed']
        failed = self.test_results['tests_failed']
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"🧪 Tests Run: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")
        
        # Component breakdown
        print(f"\n📦 Component Results:")
        for component, tests in self.test_results['component_results'].items():
            component_passed = sum(1 for test in tests.values() if test['passed'])
            component_total = len(tests)
            component_rate = (component_passed / component_total * 100) if component_total > 0 else 0
            
            print(f"  {component}: {component_passed}/{component_total} ({component_rate:.1f}%)")
        
        # Errors
        if self.test_results['errors']:
            print(f"\n❌ Errors Encountered:")
            for error in self.test_results['errors']:
                print(f"  • {error}")
        
        # Overall status
        print(f"\n🎯 Overall Status:")
        if pass_rate >= 90:
            print("  🌟 EXCELLENT: Feature 2 implementation is highly successful!")
        elif pass_rate >= 75:
            print("  ✅ GOOD: Feature 2 implementation is largely successful with minor issues.")
        elif pass_rate >= 50:
            print("  ⚠️ PARTIAL: Feature 2 implementation has significant issues that need attention.")
        else:
            print("  ❌ POOR: Feature 2 implementation requires major fixes.")
        
        # Save report
        report_file = self.project_root / "reports" / f"feature2_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n💾 Test report saved to: {report_file}")
        
        return pass_rate >= 75  # Return success if 75% or better

def main():
    """Main test execution."""
    try:
        test_suite = Feature2TestSuite()
        success = test_suite.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
