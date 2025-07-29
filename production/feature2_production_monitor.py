#!/usr/bin/env python3
"""
Hot Durham Production Monitoring - Feature 2
Monitor production deployment health and performance
"""

import json
import psutil
from pathlib import Path
from datetime import datetime, timedelta

class ProductionMonitor:
    """Monitor Feature 2 production deployment."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.log_file = self.base_dir / "logs" / "feature2_production.log"
        self.reports_dir = self.base_dir / "reports" / "production"
    
    def check_system_health(self):
        """Check system health metrics."""
        health = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
        
        # Check if service is running efficiently
        if health['cpu_percent'] > 80:
            print(f"⚠️ High CPU usage: {health['cpu_percent']}%")
        
        if health['memory_percent'] > 85:
            print(f"⚠️ High memory usage: {health['memory_percent']}%")
        
        return health
    
    def check_prediction_freshness(self):
        """Check if predictions are being generated regularly."""
        try:
            if not self.reports_dir.exists():
                return {'status': 'no_reports', 'last_prediction': None}
            
            # Find latest prediction file
            pred_files = list(self.reports_dir.glob("predictions_*.json"))
            if not pred_files:
                return {'status': 'no_predictions', 'last_prediction': None}
            
            latest_file = max(pred_files, key=lambda x: x.stat().st_mtime)
            file_age = datetime.now() - datetime.fromtimestamp(latest_file.stat().st_mtime)
            
            # Check if predictions are fresh (less than 2 hours old)
            if file_age > timedelta(hours=2):
                return {'status': 'stale', 'last_prediction': latest_file.name, 'age_hours': file_age.total_seconds() / 3600}
            else:
                return {'status': 'fresh', 'last_prediction': latest_file.name, 'age_hours': file_age.total_seconds() / 3600}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_model_performance(self):
        """Check latest model performance metrics."""
        try:
            model_files = list(self.reports_dir.glob("model_performance_*.json"))
            if not model_files:
                return {'status': 'no_models'}
            
            latest_file = max(model_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file, 'r') as f:
                model_data = json.load(f)
            
            # Extract performance metrics
            performance = {}
            for model_name, metrics in model_data.items():
                if isinstance(metrics, dict) and 'r2' in metrics:
                    performance[model_name] = {
                        'r2_score': metrics.get('r2', 0),
                        'mae': metrics.get('mae', float('inf'))
                    }
            
            return {'status': 'available', 'performance': performance, 'file': latest_file.name}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def generate_health_report(self):
        """Generate comprehensive health report."""
        print("🏥 Hot Durham Feature 2 - Production Health Check")
        print("=" * 50)
        
        # System health
        print("\n💻 System Health:")
        health = self.check_system_health()
        print(f"  CPU: {health['cpu_percent']}%")
        print(f"  Memory: {health['memory_percent']}%")
        print(f"  Disk: {health['disk_percent']}%")
        
        # Prediction freshness
        print("\n🔮 Prediction Status:")
        pred_status = self.check_prediction_freshness()
        if pred_status['status'] == 'fresh':
            print(f"  ✅ Fresh predictions available ({pred_status['age_hours']:.1f}h old)")
        elif pred_status['status'] == 'stale':
            print(f"  ⚠️ Stale predictions ({pred_status['age_hours']:.1f}h old)")
        else:
            print("  ❌ No predictions available")
        
        # Model performance
        print("\n🤖 Model Performance:")
        model_status = self.check_model_performance()
        if model_status['status'] == 'available':
            for model_name, metrics in model_status['performance'].items():
                print(f"  {model_name}: R²={metrics['r2_score']:.3f}, MAE={metrics['mae']:.2f}")
        else:
            print("  ❌ No model performance data available")
        
        # Service log check
        print("\n📝 Service Logs:")
        if self.log_file.exists():
            file_age = datetime.now() - datetime.fromtimestamp(self.log_file.stat().st_mtime)
            print(f"  Last log entry: {file_age.total_seconds() / 3600:.1f}h ago")
            
            # Check for recent errors
            try:
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    recent_errors = [line for line in lines[-100:] if 'ERROR' in line]
                    if recent_errors:
                        print(f"  ⚠️ {len(recent_errors)} recent errors found")
                    else:
                        print("  ✅ No recent errors")
            except:
                print("  ⚠️ Could not read log file")
        else:
            print("  ❌ No log file found")
        
        print("\n" + "=" * 50)
        return {
            'system_health': health,
            'prediction_status': pred_status,
            'model_status': model_status,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    monitor = ProductionMonitor()
    health_report = monitor.generate_health_report()
