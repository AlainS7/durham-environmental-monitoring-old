#!/usr/bin/env python3
"""
Production Deployment and Health Check System for Hot Durham

This script manages production deployment, monitoring, and maintenance
of the Hot Durham environmental monitoring system.
"""

import os
import sys
import json
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ProductionManager:
    """Production deployment and monitoring manager"""
    
    def __init__(self):
        self.project_root = project_root
        self.log_dir = self.project_root / "logs" / "production"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        log_file = self.log_dir / f"production_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def deploy_production(self) -> bool:
        """Deploy system to production"""
        self.logger.info("🚀 Starting Production Deployment")
        
        # Pre-deployment checks
        if not self._pre_deployment_checks():
            self.logger.error("❌ Pre-deployment checks failed")
            return False
        
        # Deploy components
        deployment_steps = [
            ("Database Setup", self._setup_production_database),
            ("Configuration Validation", self._validate_production_config),
            ("Service Startup", self._start_production_services),
            ("Health Verification", self._verify_system_health),
            ("Performance Optimization", self._optimize_performance)
        ]
        
        for step_name, step_function in deployment_steps:
            self.logger.info(f"📋 Executing: {step_name}")
            try:
                if not step_function():
                    self.logger.error(f"❌ {step_name} failed")
                    return False
                self.logger.info(f"✅ {step_name} completed")
            except Exception as e:
                self.logger.error(f"❌ {step_name} failed with error: {e}")
                return False
        
        self.logger.info("🎉 Production deployment completed successfully")
        return True
    
    def _pre_deployment_checks(self) -> bool:
        """Run pre-deployment validation checks"""
        checks = [
            ("Credentials", self._check_credentials),
            ("Dependencies", self._check_dependencies),
            ("Disk Space", self._check_disk_space),
            ("Network Connectivity", self._check_network),
            ("Permissions", self._check_permissions)
        ]
        
        all_passed = True
        for check_name, check_function in checks:
            try:
                if check_function():
                    self.logger.info(f"✅ {check_name}: OK")
                else:
                    self.logger.error(f"❌ {check_name}: FAILED")
                    all_passed = False
            except Exception as e:
                self.logger.error(f"❌ {check_name}: ERROR - {e}")
                all_passed = False
        
        return all_passed
    
    def _check_credentials(self) -> bool:
        """Check if all required credentials are available"""
        required_creds = [
            "creds/google_creds.json",
            "creds/wu_api_key.json",
            "creds/tsi_creds.json"
        ]
        
        for cred_file in required_creds:
            cred_path = self.project_root / cred_file
            if not cred_path.exists():
                self.logger.error(f"Missing credential file: {cred_file}")
                return False
        
        return True
    
    def _check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        try:
            import pandas, requests, gspread, httpx, streamlit, tenacity, plotly
            return True
        except ImportError as e:
            self.logger.error(f"Missing dependency: {e}")
            return False
    
    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.project_root)
            free_gb = free // (1024**3)
            
            if free_gb < 2:
                self.logger.error(f"Insufficient disk space: {free_gb}GB free")
                return False
            
            self.logger.info(f"Disk space OK: {free_gb}GB free")
            return True
        except Exception as e:
            self.logger.error(f"Error checking disk space: {e}")
            return False
    
    def _check_network(self) -> bool:
        """Check network connectivity to required services"""
        test_urls = [
            "https://api.weather.com",
            "https://accounts.google.com",
            "https://www.googleapis.com"
        ]
        
        import requests
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    self.logger.warning(f"Network check warning for {url}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Network connectivity failed for {url}: {e}")
                return False
        
        return True
    
    def _check_permissions(self) -> bool:
        """Check file and directory permissions"""
        critical_paths = [
            ("data", True),  # (path, is_directory)
            ("logs", True),
            ("config", True),
            ("src/data_collection/faster_wu_tsi_to_sheets_async.py", False)
        ]
        
        for path_str, is_dir in critical_paths:
            path = self.project_root / path_str
            if not path.exists():
                self.logger.error(f"Critical path missing: {path}")
                return False
            
            if is_dir and not os.access(path, os.W_OK):
                self.logger.error(f"No write permission for directory: {path}")
                return False
            elif not is_dir and not os.access(path, os.R_OK):
                self.logger.error(f"No read permission for file: {path}")
                return False
        
        return True
    
    def _setup_production_database(self) -> bool:
        """Setup production database"""
        try:
            from src.database.db_manager import HotDurhamDB
            db = HotDurhamDB()
            
            # Initialize database tables
            db.store_collection_metadata("production_init", {
                "timestamp": datetime.now().isoformat(),
                "status": "initialized"
            })
            
            self.logger.info("Production database initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            return False
    
    def _validate_production_config(self) -> bool:
        """Validate production configuration"""
        try:
            # Set production environment
            os.environ["HOT_DURHAM_ENV"] = "production"
            
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Load production config
            try:
                prod_config = config_manager.load_config("environments/production", "py")
                self.logger.info("Production configuration loaded successfully")
                return True
            except FileNotFoundError:
                # Create minimal production config if it doesn't exist
                self._create_production_config()
                return True
                
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def _create_production_config(self):
        """Create production configuration file"""
        prod_config_content = '''# Production environment
DEBUG = False
LOG_LEVEL = "INFO"
API_RATE_LIMIT = 1.0  # requests per second

# Data sources
TSI_API_ENABLED = True
WU_API_ENABLED = True
GOOGLE_SHEETS_ENABLED = True

# Storage
USE_DATABASE = True

BACKUP_ENABLED = True

# Performance
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 30

# Test sensors
INCLUDE_TEST_SENSORS_IN_LOGS = False
'''
        
        prod_config_file = self.project_root / "config" / "environments" / "production.py"
        prod_config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(prod_config_file, 'w') as f:
            f.write(prod_config_content)
        
        self.logger.info("Created production configuration file")
    
    def _start_production_services(self) -> bool:
        """Start production services"""
        # For now, just verify the main data collection script can be imported
        try:
            sys.path.insert(0, str(self.project_root / "src" / "data_collection"))
            # Test import without running
            import faster_wu_tsi_to_sheets_async
            self.logger.info("Main data collection script validated")
            return True
        except Exception as e:
            self.logger.error(f"Service startup validation failed: {e}")
            return False
    
    def _verify_system_health(self) -> bool:
        """Verify system health after deployment"""
        try:
            # Run a subset of health checks
            from tests.comprehensive_test_suite import HotDurhamTestRunner
            runner = HotDurhamTestRunner()
            
            # Run infrastructure tests only for quick health check
            infra_results = runner.test_infrastructure()
            
            passed = sum(1 for r in infra_results.values() if r.get('status') == 'PASS')
            total = len(infra_results)
            
            if passed / total >= 0.8:  # 80% pass threshold
                self.logger.info(f"System health check passed: {passed}/{total}")
                return True
            else:
                self.logger.error(f"System health check failed: {passed}/{total}")
                return False
                
        except Exception as e:
            self.logger.error(f"Health verification failed: {e}")
            return False
    
    def _optimize_performance(self) -> bool:
        """Apply performance optimizations"""
        try:
            # Create performance monitoring configuration
            perf_config = {
                "monitoring_enabled": True,
                "metrics_collection": True,
                "performance_logging": True,
                "memory_monitoring": True,
                "auto_optimization": True
            }
            
            perf_config_file = self.project_root / "config" / "production_performance.json"
            with open(perf_config_file, 'w') as f:
                json.dump(perf_config, f, indent=2)
            
            self.logger.info("Performance optimization configuration created")
            return True
        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")
            return False
    
    def monitor_production(self) -> Dict[str, Any]:
        """Monitor production system health"""
        self.logger.info("🔍 Starting production monitoring")
        
        monitoring_results = {
            "timestamp": datetime.now().isoformat(),
            "system_health": {},
            "performance_metrics": {},
            "alerts": []
        }
        
        # System health checks
        health_checks = [
            ("Database Connection", self._check_database_health),
            ("File System", self._check_filesystem_health),
            ("Memory Usage", self._check_memory_usage),
            ("Data Freshness", self._check_data_freshness)
        ]
        
        for check_name, check_function in health_checks:
            try:
                result = check_function()
                monitoring_results["system_health"][check_name] = result
                
                if not result.get("healthy", True):
                    monitoring_results["alerts"].append({
                        "severity": "WARNING",
                        "component": check_name,
                        "message": result.get("message", "Health check failed")
                    })
                    
            except Exception as e:
                monitoring_results["system_health"][check_name] = {
                    "healthy": False,
                    "error": str(e)
                }
                monitoring_results["alerts"].append({
                    "severity": "ERROR",
                    "component": check_name,
                    "message": f"Health check error: {e}"
                })
        
        return monitoring_results
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            from src.database.db_manager import HotDurhamDB
            db = HotDurhamDB()
            
            # Test database connection
            db.store_collection_metadata("health_check", {"timestamp": datetime.now().isoformat()})
            
            return {"healthy": True, "message": "Database connection successful"}
        except Exception as e:
            return {"healthy": False, "message": f"Database error: {e}"}
    
    def _check_filesystem_health(self) -> Dict[str, Any]:
        """Check filesystem health"""
        critical_dirs = ["data", "logs", "config"]
        
        for dir_name in critical_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                return {"healthy": False, "message": f"Critical directory missing: {dir_name}"}
            if not os.access(dir_path, os.W_OK):
                return {"healthy": False, "message": f"No write access to: {dir_name}"}
        
        return {"healthy": True, "message": "Filesystem access OK"}
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                return {"healthy": False, "message": f"High memory usage: {memory.percent}%"}
            elif memory.percent > 80:
                return {"healthy": True, "message": f"Memory usage warning: {memory.percent}%"}
            else:
                return {"healthy": True, "message": f"Memory usage OK: {memory.percent}%"}
        except ImportError:
            return {"healthy": True, "message": "Memory monitoring not available (psutil not installed)"}
        except Exception as e:
            return {"healthy": False, "message": f"Memory check error: {e}"}
    
    def _check_data_freshness(self) -> Dict[str, Any]:
        """Check data freshness"""
        data_dir = self.project_root / "data"
        
        if not data_dir.exists():
            return {"healthy": False, "message": "Data directory not found"}
        
        # Check for recent data files
        recent_files = []
        cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
        
        for file_path in data_dir.rglob("*.csv"):
            if file_path.stat().st_mtime > cutoff_time:
                recent_files.append(file_path)
        
        if len(recent_files) > 0:
            return {"healthy": True, "message": f"Found {len(recent_files)} recent data files"}
        else:
            return {"healthy": False, "message": "No recent data files found (last 24 hours)"}

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hot Durham Production Manager")
    parser.add_argument("action", choices=["deploy", "monitor", "status"], 
                       help="Action to perform")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = ProductionManager()
    
    if args.action == "deploy":
        success = manager.deploy_production()
        return 0 if success else 1
    
    elif args.action == "monitor":
        results = manager.monitor_production()
        
        # Print summary
        print(f"🔍 Production Monitoring Report")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Health Checks: {len(results['system_health'])}")
        print(f"Alerts: {len(results['alerts'])}")
        
        if results['alerts']:
            print("\n⚠️ Active Alerts:")
            for alert in results['alerts']:
                print(f"  - {alert['severity']}: {alert['component']} - {alert['message']}")
        else:
            print("\n✅ No active alerts")
        
        # Save monitoring results
        results_file = manager.log_dir / f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Full results saved to: {results_file}")
        return 0
    
    elif args.action == "status":
        print("🎯 Hot Durham Production Status")
        print("=" * 40)
        
        # Quick status check
        status_ok = True
        
        # Check if enhanced features are available
        try:
            from src.utils.enhanced_logging import HotDurhamLogger
            print("✅ Enhanced logging: Available")
        except ImportError:
            print("❌ Enhanced logging: Not available")
            status_ok = False
        
        # Check database
        try:
            from src.database.db_manager import HotDurhamDB
            db = HotDurhamDB()
            print("✅ Database: Connected")
        except Exception as e:
            print(f"❌ Database: Error - {e}")
            status_ok = False
        
        # Check data directory
        data_dir = manager.project_root / "data"
        if data_dir.exists():
            print("✅ Data directory: Exists")
        else:
            print("❌ Data directory: Missing")
            status_ok = False
        
        print(f"\n🎯 Overall Status: {'✅ HEALTHY' if status_ok else '❌ ISSUES DETECTED'}")
        return 0 if status_ok else 1

if __name__ == "__main__":
    sys.exit(main())
