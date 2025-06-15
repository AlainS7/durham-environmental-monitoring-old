"""
Enhanced logging and error handling system for Hot Durham project
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

class HotDurhamLogger:
    """Centralized logging system with structured output"""
    
    def __init__(self, name="hot_durham", log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = self._setup_logger(name)
    
    def _setup_logger(self, name):
        """Setup logger with both file and console handlers"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
    
    def log_data_collection(self, source, success_count, error_count, duration):
        """Structured logging for data collection events"""
        self.logger.info(f"Data Collection - Source: {source}, Success: {success_count}, "
                        f"Errors: {error_count}, Duration: {duration:.2f}s")
    
    def log_test_sensor_separation(self, test_count, prod_count, sensors):
        """Log test sensor separation results"""
        self.logger.info(f"Test Separation - Test: {test_count}, Prod: {prod_count}, "
                        f"Sensors: {len(sensors)}")

# Usage example
# logger = HotDurhamLogger("data_collection")
# logger.log_data_collection("TSI", 942, 0, 125.5)
