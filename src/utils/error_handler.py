"""
Enhanced error handling and recovery system
"""
import traceback
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.error_log = self.log_dir / "errors.jsonl"
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, 
                  severity: str = "ERROR") -> str:
        """Log error with context and return error ID"""
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        error_record = {
            "error_id": error_id,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        # Append to error log
        with open(self.error_log, "a") as f:
            f.write(json.dumps(error_record) + "\n")
        
        return error_id
    
    def handle_api_error(self, error: Exception, api_name: str, 
                        retry_count: int = 0) -> Dict[str, Any]:
        """Handle API-specific errors with retry strategies"""
        context = {
            "api_name": api_name,
            "retry_count": retry_count,
            "can_retry": retry_count < 3
        }
        
        error_id = self.log_error(error, context)
        
        # Determine recovery strategy
        if "rate limit" in str(error).lower():
            recovery = "wait_and_retry"
            wait_time = min(60 * (retry_count + 1), 300)  # Max 5 minutes
        elif "timeout" in str(error).lower():
            recovery = "retry_with_longer_timeout"
            wait_time = 30
        elif "401" in str(error) or "403" in str(error):
            recovery = "check_credentials"
            wait_time = 0
        else:
            recovery = "skip_and_continue"
            wait_time = 0
        
        return {
            "error_id": error_id,
            "recovery_strategy": recovery,
            "wait_time": wait_time,
            "can_retry": context["can_retry"]
        }
    
    def handle_data_error(self, error: Exception, data_source: str, 
                         record_count: int = 0) -> Dict[str, Any]:
        """Handle data processing errors"""
        context = {
            "data_source": data_source,
            "record_count": record_count,
            "error_stage": "data_processing"
        }
        
        error_id = self.log_error(error, context)
        
        # Determine if we can continue with partial data
        if record_count > 0:
            recovery = "continue_with_partial_data"
        else:
            recovery = "skip_data_source"
        
        return {
            "error_id": error_id,
            "recovery_strategy": recovery,
            "can_continue": record_count > 0
        }
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours"""
        if not self.error_log.exists():
            return {"total_errors": 0, "by_type": {}, "by_severity": {}}
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        errors = []
        
        with open(self.error_log, "r") as f:
            for line in f:
                try:
                    error_record = json.loads(line.strip())
                    error_time = datetime.fromisoformat(error_record["timestamp"]).timestamp()
                    if error_time >= cutoff_time:
                        errors.append(error_record)
                except Exception:
                    continue
        
        # Summarize errors
        by_type = {}
        by_severity = {}
        
        for error in errors:
            error_type = error.get("error_type", "Unknown")
            severity = error.get("severity", "ERROR")
            
            by_type[error_type] = by_type.get(error_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_errors": len(errors),
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_errors": errors[-5:] if errors else []
        }
