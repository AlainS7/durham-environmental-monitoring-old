#!/usr/bin/env python3
"""
Hot Durham Production Service - Feature 2
Predictive Analytics & AI Production Service
"""

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ml.predictive_analytics import PredictiveAnalytics

class ProductionService:
    """Production service for Feature 2 - Predictive Analytics."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.config_file = self.base_dir / "production" / "feature2_production_config.json"
        self.log_file = self.base_dir / "logs" / "feature2_production.log"
        
        # Setup logging
        self.log_file.parent.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize analytics
        self.analytics = PredictiveAnalytics()
        
        self.logger.info("🚀 Production Service initialized")
    
    def load_config(self):
        """Load production configuration."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """Default configuration if file is missing."""
        return {
            "model_settings": {"auto_retrain_hours": 24, "prediction_horizon_hours": 48},
            "alert_settings": {"enabled": True, "check_interval_minutes": 15},
            "data_settings": {"max_historical_days": 90},
            "performance_settings": {"max_memory_mb": 1024}
        }
    
    def run_production_cycle(self):
        """Run one complete production cycle."""
        try:
            self.logger.info("🔄 Starting production cycle...")
            
            # 1. Load latest data
            self.logger.info("📥 Loading historical data...")
            data_loaded = self.analytics.load_historical_data()
            
            if not data_loaded:
                self.logger.error("❌ Failed to load historical data")
                return False
            
            # 2. Train/update models
            self.logger.info("🤖 Training/updating ML models...")
            model_results = self.analytics.train_air_quality_models()
            
            if not model_results:
                self.logger.error("❌ Model training failed")
                return False
            
            # 3. Generate predictions
            horizon_hours = self.config['model_settings']['prediction_horizon_hours']
            self.logger.info(f"🔮 Generating {horizon_hours}h predictions...")
            predictions = self.analytics.predict_air_quality(hours_ahead=horizon_hours)
            
            if 'error' in predictions:
                self.logger.error(f"❌ Prediction failed: {predictions['error']}")
                return False
            
            # 4. Check for alerts
            if self.config['alert_settings']['enabled']:
                self.check_alerts(predictions)
            
            # 5. Generate reports
            self.generate_production_reports(predictions, model_results)
            
            self.logger.info("✅ Production cycle completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Production cycle failed: {e}")
            return False
    
    def check_alerts(self, predictions):
        """Check predictions for alert conditions."""
        try:
            critical_threshold = self.config['alert_settings'].get('critical_threshold_pm25', 150.5)
            high_threshold = self.config['alert_settings'].get('high_threshold_pm25', 55.5)
            
            for pred in predictions.get('predictions', []):
                pm25 = pred['predicted_pm25']
                timestamp = pred['timestamp']
                
                if pm25 > critical_threshold:
                    self.logger.warning(f"🚨 CRITICAL ALERT: PM2.5 {pm25} μg/m³ at {timestamp}")
                elif pm25 > high_threshold:
                    self.logger.warning(f"⚠️ HIGH ALERT: PM2.5 {pm25} μg/m³ at {timestamp}")
                    
        except Exception as e:
            self.logger.error(f"Alert check failed: {e}")
    
    def generate_production_reports(self, predictions, model_results):
        """Generate production reports."""
        try:
            reports_dir = self.base_dir / "reports" / "production"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save predictions
            pred_file = reports_dir / f"predictions_{timestamp}.json"
            with open(pred_file, 'w') as f:
                json.dump(predictions, f, indent=2)
            
            # Save model performance
            model_file = reports_dir / f"model_performance_{timestamp}.json"
            with open(model_file, 'w') as f:
                json.dump(model_results, f, indent=2, default=str)
            
            self.logger.info(f"📊 Reports saved to {reports_dir}")
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
    
    def run_continuous(self):
        """Run service continuously."""
        self.logger.info("🔄 Starting continuous production service...")
        
        check_interval = self.config['alert_settings'].get('check_interval_minutes', 15)
        retrain_interval = self.config['model_settings'].get('auto_retrain_hours', 24)
        
        last_retrain = datetime.now()
        
        while True:
            try:
                current_time = datetime.now()
                
                # Check if it's time to retrain
                if (current_time - last_retrain).total_seconds() > (retrain_interval * 3600):
                    self.logger.info("🔄 Scheduled model retraining...")
                    self.run_production_cycle()
                    last_retrain = current_time
                else:
                    # Quick prediction and alert check
                    predictions = self.analytics.predict_air_quality(hours_ahead=6)
                    if 'error' not in predictions and self.config['alert_settings']['enabled']:
                        self.check_alerts(predictions)
                
                # Wait for next check
                time.sleep(check_interval * 60)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Service stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Service error: {e}")
                time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    service = ProductionService()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        service.run_continuous()
    else:
        # Run single cycle
        success = service.run_production_cycle()
        sys.exit(0 if success else 1)
