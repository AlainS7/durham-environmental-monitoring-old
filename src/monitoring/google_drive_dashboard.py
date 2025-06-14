#!/usr/bin/env python3
"""
Google Drive Sync Status Dashboard
Real-time monitoring of Google Drive sync health and performance.
"""

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass, asdict
import threading

@dataclass
class SyncStatus:
    """Represents the status of a sync operation."""
    timestamp: datetime
    operation_type: str  # 'upload', 'download', 'sync'
    file_path: str
    drive_folder: str
    status: str  # 'success', 'failed', 'pending', 'retry'
    file_size_mb: float
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class GoogleDriveSyncDashboard:
    """Real-time dashboard for monitoring Google Drive sync status."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Sync status tracking
        self.sync_operations: List[SyncStatus] = []
        self.max_operations_history = 1000
        
        # Performance metrics
        self.performance_metrics = {
            'total_uploads': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'total_data_uploaded_mb': 0.0,
            'average_upload_speed_mbps': 0.0,
            'api_calls_today': 0,
            'rate_limit_hits': 0,
            'last_successful_sync': None,
            'current_queue_size': 0
        }
        
        # Storage quota monitoring
        self.storage_info = {
            'total_quota_gb': 0,
            'used_quota_gb': 0,
            'available_quota_gb': 0,
            'quota_usage_percent': 0.0,
            'last_quota_check': None
        }
        
        # Sync health alerts
        self.health_alerts = []
        self.alert_thresholds = {
            'failed_upload_rate': 0.1,  # 10% failure rate triggers alert
            'queue_size_warning': 50,
            'quota_usage_warning': 85,  # 85% quota usage
            'api_rate_limit_warning': 80  # 80% of daily limit
        }
        
        # Dashboard update thread
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Load existing data
        self._load_sync_history()
        
        # Start monitoring
        self.start_monitoring()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the dashboard."""
        logger = logging.getLogger('GoogleDriveDashboard')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_dir = self.project_root / "logs" / "system" / "monitoring"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / f"google_drive_dashboard_{datetime.now().strftime('%Y%m%d')}.log"
            )
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def record_sync_operation(self, operation_type: str, file_path: str, drive_folder: str, 
                            status: str, file_size_mb: float, duration_seconds: Optional[float] = None,
                            error_message: Optional[str] = None, retry_count: int = 0):
        """Record a sync operation for monitoring."""
        sync_status = SyncStatus(
            timestamp=datetime.now(),
            operation_type=operation_type,
            file_path=file_path,
            drive_folder=drive_folder,
            status=status,
            file_size_mb=file_size_mb,
            duration_seconds=duration_seconds,
            error_message=error_message,
            retry_count=retry_count
        )
        
        self.sync_operations.append(sync_status)
        
        # Maintain history limit
        if len(self.sync_operations) > self.max_operations_history:
            self.sync_operations = self.sync_operations[-self.max_operations_history:]
        
        # Update performance metrics
        self._update_performance_metrics(sync_status)
        
        # Check for alerts
        self._check_health_alerts()
        
        # Save to disk
        self._save_sync_history()
        
        self.logger.info(f"Recorded sync operation: {operation_type} {status} for {Path(file_path).name}")
    
    def _update_performance_metrics(self, sync_status: SyncStatus):
        """Update performance metrics based on sync operation."""
        if sync_status.operation_type == 'upload':
            self.performance_metrics['total_uploads'] += 1
            self.performance_metrics['total_data_uploaded_mb'] += sync_status.file_size_mb
            
            if sync_status.status == 'success':
                self.performance_metrics['successful_uploads'] += 1
                self.performance_metrics['last_successful_sync'] = sync_status.timestamp
                
                # Calculate upload speed
                if sync_status.duration_seconds and sync_status.duration_seconds > 0:
                    speed_mbps = sync_status.file_size_mb / sync_status.duration_seconds
                    # Update average (simple moving average)
                    current_avg = self.performance_metrics['average_upload_speed_mbps']
                    total_uploads = self.performance_metrics['successful_uploads']
                    self.performance_metrics['average_upload_speed_mbps'] = (
                        (current_avg * (total_uploads - 1) + speed_mbps) / total_uploads
                    )
            
            elif sync_status.status == 'failed':
                self.performance_metrics['failed_uploads'] += 1
    
    def _check_health_alerts(self):
        """Check for health issues and generate alerts."""
        current_time = datetime.now()
        
        # Calculate failure rate (last 100 operations)
        recent_ops = [op for op in self.sync_operations[-100:] if op.operation_type == 'upload']
        if len(recent_ops) >= 10:
            failed_ops = [op for op in recent_ops if op.status == 'failed']
            failure_rate = len(failed_ops) / len(recent_ops)
            
            if failure_rate >= self.alert_thresholds['failed_upload_rate']:
                self._add_alert('high_failure_rate', f"Upload failure rate: {failure_rate:.1%}")
        
        # Check queue size (would need integration with actual queue)
        queue_size = self.performance_metrics.get('current_queue_size', 0)
        if queue_size >= self.alert_thresholds['queue_size_warning']:
            self._add_alert('large_queue', f"Upload queue size: {queue_size}")
        
        # Check quota usage
        if self.storage_info['quota_usage_percent'] >= self.alert_thresholds['quota_usage_warning']:
            self._add_alert('quota_warning', 
                          f"Storage quota: {self.storage_info['quota_usage_percent']:.1f}% used")
    
    def _add_alert(self, alert_type: str, message: str):
        """Add a health alert."""
        alert = {
            'timestamp': datetime.now(),
            'type': alert_type,
            'message': message,
            'resolved': False
        }
        
        # Avoid duplicate alerts (same type within 5 minutes)
        recent_alerts = [a for a in self.health_alerts 
                        if a['type'] == alert_type and 
                        (datetime.now() - a['timestamp']).seconds < 300]
        
        if not recent_alerts:
            self.health_alerts.append(alert)
            self.logger.warning(f"Health alert: {alert_type} - {message}")
    
    def update_storage_quota(self, total_gb: float, used_gb: float):
        """Update storage quota information."""
        self.storage_info.update({
            'total_quota_gb': total_gb,
            'used_quota_gb': used_gb,
            'available_quota_gb': total_gb - used_gb,
            'quota_usage_percent': (used_gb / total_gb) * 100 if total_gb > 0 else 0,
            'last_quota_check': datetime.now()
        })
    
    def update_queue_size(self, queue_size: int):
        """Update current upload queue size."""
        self.performance_metrics['current_queue_size'] = queue_size
    
    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard data."""
        recent_operations = self.sync_operations[-50:]  # Last 50 operations
        
        # Calculate recent performance
        last_hour_ops = [op for op in self.sync_operations 
                        if (datetime.now() - op.timestamp).seconds <= 3600]
        
        recent_performance = {
            'operations_last_hour': len(last_hour_ops),
            'successful_last_hour': len([op for op in last_hour_ops if op.status == 'success']),
            'failed_last_hour': len([op for op in last_hour_ops if op.status == 'failed']),
            'data_uploaded_last_hour_mb': sum(op.file_size_mb for op in last_hour_ops 
                                            if op.operation_type == 'upload' and op.status == 'success')
        }
        
        # Active alerts
        active_alerts = [alert for alert in self.health_alerts if not alert.get('resolved', False)]
        
        return {
            'timestamp': datetime.now(),
            'performance_metrics': self.performance_metrics,
            'storage_info': self.storage_info,
            'recent_performance': recent_performance,
            'recent_operations': [asdict(op) for op in recent_operations],
            'active_alerts': active_alerts,
            'health_status': self._calculate_health_status()
        }
    
    def _calculate_health_status(self) -> str:
        """Calculate overall health status."""
        active_alerts = [alert for alert in self.health_alerts if not alert.get('resolved', False)]
        
        if any(alert['type'] in ['high_failure_rate', 'quota_warning'] for alert in active_alerts):
            return 'critical'
        elif any(alert['type'] in ['large_queue'] for alert in active_alerts):
            return 'warning'
        elif self.performance_metrics['last_successful_sync']:
            last_sync = self.performance_metrics['last_successful_sync']
            if isinstance(last_sync, str):
                last_sync = datetime.fromisoformat(last_sync)
            if (datetime.now() - last_sync).seconds < 3600:  # Within last hour
                return 'healthy'
            else:
                return 'stale'
        else:
            return 'unknown'
    
    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard."""
        data = self.get_dashboard_data()
        health_status = data['health_status']
        
        # Status color mapping
        status_colors = {
            'healthy': '#28a745',
            'warning': '#ffc107', 
            'critical': '#dc3545',
            'stale': '#6c757d',
            'unknown': '#17a2b8'
        }
        
        status_color = status_colors.get(health_status, '#6c757d')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Google Drive Sync Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .dashboard {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .status-badge {{ 
            display: inline-block; 
            padding: 8px 16px; 
            background-color: {status_color}; 
            color: white; 
            border-radius: 20px; 
            font-weight: bold;
        }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
        .metric-card {{ 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .metric-label {{ color: #6c757d; margin-top: 5px; }}
        .alert {{ 
            background: #f8d7da; 
            border: 1px solid #f5c6cb; 
            color: #721c24; 
            padding: 10px; 
            border-radius: 4px; 
            margin: 10px 0;
        }}
        .recent-ops {{ margin-top: 30px; }}
        .op-entry {{ 
            background: white; 
            padding: 10px; 
            border-left: 4px solid #007bff; 
            margin-bottom: 5px;
        }}
        .op-failed {{ border-left-color: #dc3545; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🚗 Hot Durham - Google Drive Sync Dashboard</h1>
            <div class="status-badge">Status: {health_status.title()}</div>
            <p class="timestamp">Last Updated: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{data['performance_metrics']['total_uploads']}</div>
                <div class="metric-label">Total Uploads</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['performance_metrics']['successful_uploads']}</div>
                <div class="metric-label">Successful Uploads</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['performance_metrics']['failed_uploads']}</div>
                <div class="metric-label">Failed Uploads</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['performance_metrics']['total_data_uploaded_mb']:.1f} MB</div>
                <div class="metric-label">Data Uploaded</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['performance_metrics']['average_upload_speed_mbps']:.2f}</div>
                <div class="metric-label">Avg Speed (MB/s)</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['performance_metrics']['current_queue_size']}</div>
                <div class="metric-label">Queue Size</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['storage_info']['quota_usage_percent']:.1f}%</div>
                <div class="metric-label">Storage Used</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{data['recent_performance']['operations_last_hour']}</div>
                <div class="metric-label">Operations (Last Hour)</div>
            </div>
        </div>
"""
        
        # Add alerts section
        if data['active_alerts']:
            html += "<h2>🚨 Active Alerts</h2>"
            for alert in data['active_alerts']:
                timestamp = alert['timestamp']
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                html += f"""
                <div class="alert">
                    <strong>{alert['type'].replace('_', ' ').title()}:</strong> {alert['message']}
                    <br><small>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</small>
                </div>
                """
        
        # Add recent operations
        html += """
        <div class="recent-ops">
            <h2>📋 Recent Operations</h2>
        """
        
        for op in data['recent_operations'][-10:]:  # Last 10 operations
            timestamp = op['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            op_class = "op-failed" if op['status'] == 'failed' else ""
            status_icon = "❌" if op['status'] == 'failed' else "✅"
            
            html += f"""
            <div class="op-entry {op_class}">
                {status_icon} <strong>{Path(op['file_path']).name}</strong> 
                → {op['drive_folder']} 
                ({op['file_size_mb']:.1f} MB)
                <br><small class="timestamp">{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</small>
            </div>
            """
        
        html += """
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def save_dashboard_html(self) -> Path:
        """Save dashboard HTML to file."""
        html = self.generate_dashboard_html()
        
        dashboard_dir = self.project_root / "logs" / "system" / "monitoring"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        dashboard_file = dashboard_dir / "google_drive_dashboard.html"
        with open(dashboard_file, 'w') as f:
            f.write(html)
        
        return dashboard_file
    
    def _save_sync_history(self):
        """Save sync history to JSON file."""
        try:
            history_dir = self.project_root / "logs" / "system" / "monitoring"
            history_dir.mkdir(parents=True, exist_ok=True)
            
            history_file = history_dir / "sync_history.json"
            
            # Convert to serializable format
            serializable_ops = []
            for op in self.sync_operations[-500:]:  # Save last 500 operations
                op_dict = asdict(op)
                op_dict['timestamp'] = op.timestamp.isoformat()
                serializable_ops.append(op_dict)
            
            data = {
                'sync_operations': serializable_ops,
                'performance_metrics': self.performance_metrics.copy(),
                'storage_info': self.storage_info.copy(),
                'last_updated': datetime.now().isoformat()
            }
            
            # Convert datetime objects to strings
            if data['performance_metrics']['last_successful_sync']:
                if isinstance(data['performance_metrics']['last_successful_sync'], datetime):
                    data['performance_metrics']['last_successful_sync'] = data['performance_metrics']['last_successful_sync'].isoformat()
            
            if data['storage_info']['last_quota_check']:
                if isinstance(data['storage_info']['last_quota_check'], datetime):
                    data['storage_info']['last_quota_check'] = data['storage_info']['last_quota_check'].isoformat()
            
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save sync history: {e}")
    
    def _load_sync_history(self):
        """Load sync history from JSON file."""
        try:
            history_file = self.project_root / "logs" / "system" / "monitoring" / "sync_history.json"
            
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                
                # Load sync operations
                for op_dict in data.get('sync_operations', []):
                    op_dict['timestamp'] = datetime.fromisoformat(op_dict['timestamp'])
                    self.sync_operations.append(SyncStatus(**op_dict))
                
                # Load performance metrics
                metrics = data.get('performance_metrics', {})
                if metrics.get('last_successful_sync'):
                    metrics['last_successful_sync'] = datetime.fromisoformat(metrics['last_successful_sync'])
                self.performance_metrics.update(metrics)
                
                # Load storage info
                storage = data.get('storage_info', {})
                if storage.get('last_quota_check'):
                    storage['last_quota_check'] = datetime.fromisoformat(storage['last_quota_check'])
                self.storage_info.update(storage)
                
                self.logger.info(f"Loaded {len(self.sync_operations)} sync operations from history")
                
        except Exception as e:
            self.logger.error(f"Failed to load sync history: {e}")
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            self.logger.info("Started Google Drive monitoring")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Stopped Google Drive monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.is_monitoring:
            try:
                # Update dashboard HTML every 30 seconds
                self.save_dashboard_html()
                time.sleep(30)
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)

# Global dashboard instance
_dashboard_instance = None

def get_sync_dashboard(project_root: str = None) -> GoogleDriveSyncDashboard:
    """Get or create the sync dashboard singleton."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = GoogleDriveSyncDashboard(project_root)
    return _dashboard_instance

if __name__ == "__main__":
    # Demo the dashboard
    dashboard = GoogleDriveSyncDashboard()
    
    print("🚗 Google Drive Sync Dashboard Demo")
    print("=" * 40)
    
    # Simulate some sync operations
    dashboard.record_sync_operation(
        'upload', '/data/test_file.csv', 'HotDurham/Production/RawData/WU',
        'success', 2.5, 1.2
    )
    
    dashboard.record_sync_operation(
        'upload', '/data/large_file.csv', 'HotDurham/Testing/SensorData/TSI',
        'failed', 15.0, error_message='Network timeout'
    )
    
    # Update storage info
    dashboard.update_storage_quota(100.0, 45.0)
    dashboard.update_queue_size(5)
    
    # Generate and save dashboard
    dashboard_file = dashboard.save_dashboard_html()
    print(f"Dashboard saved to: {dashboard_file}")
    
    # Show current data
    data = dashboard.get_dashboard_data()
    print(f"\nHealth Status: {data['health_status']}")
    print(f"Total Operations: {len(data['recent_operations'])}")
    print(f"Active Alerts: {len(data['active_alerts'])}")
    
    dashboard.stop_monitoring()
