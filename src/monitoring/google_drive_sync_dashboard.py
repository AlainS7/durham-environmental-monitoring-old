#!/usr/bin/env python3
"""
Google Drive Sync Status Dashboard
Real-time monitoring of Google Drive sync operations and health.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
    from config.improved_google_drive_config import improved_drive_config
    ENHANCED_MANAGER_AVAILABLE = True
except ImportError:
    ENHANCED_MANAGER_AVAILABLE = False

class GoogleDriveSyncDashboard:
    """Real-time dashboard for monitoring Google Drive sync operations."""
    
    def __init__(self, project_root_path: str = None):
        self.project_root = Path(project_root_path) if project_root_path else project_root
        self.dashboard_data = {}
        self.last_refresh = None
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Initialize managers
        self.enhanced_manager = None
        if ENHANCED_MANAGER_AVAILABLE:
            try:
                self.enhanced_manager = get_enhanced_drive_manager(str(self.project_root))
            except Exception as e:
                self.logger.warning(f"Could not initialize enhanced manager: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the dashboard."""
        logger = logging.getLogger('GoogleDriveDashboard')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_dir = self.project_root / "logs" / "system"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / f"sync_dashboard_{datetime.now().strftime('%Y%m%d')}.log"
            )
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def collect_sync_status(self) -> Dict:
        """Collect comprehensive sync status information."""
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'enhanced_manager_available': ENHANCED_MANAGER_AVAILABLE,
            'folder_structure_status': self._check_folder_structure(),
            'performance_metrics': self._get_performance_metrics(),
            'recent_uploads': self._get_recent_uploads(),
            'error_summary': self._get_error_summary(),
            'storage_analysis': self._analyze_storage_usage(),
            'api_health': self._check_api_health()
        }
        
        self.dashboard_data = status_data
        self.last_refresh = datetime.now()
        return status_data
    
    def _check_folder_structure(self) -> Dict:
        """Check the status of the improved folder structure."""
        try:
            validation_results = improved_drive_config.validate_folder_structure()
            return {
                'validation_passed': all(validation_results.values()),
                'details': validation_results,
                'structure_report': improved_drive_config.generate_folder_structure_report()
            }
        except Exception as e:
            return {
                'validation_passed': False,
                'error': str(e),
                'details': {}
            }
    
    def _get_performance_metrics(self) -> Dict:
        """Get performance metrics from enhanced manager."""
        if not self.enhanced_manager:
            return {'error': 'Enhanced manager not available'}
        
        try:
            return self.enhanced_manager.get_performance_stats()
        except Exception as e:
            return {'error': f'Could not get performance metrics: {e}'}
    
    def _get_recent_uploads(self) -> List[Dict]:
        """Get information about recent uploads."""
        recent_uploads = []
        
        # Check logs for recent upload activity
        log_dir = self.project_root / "logs" / "system"
        if log_dir.exists():
            for log_file in log_dir.glob("google_drive_enhanced_*.log"):
                try:
                    # Get file modification time
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if datetime.now() - file_time < timedelta(hours=24):
                        recent_uploads.append({
                            'log_file': log_file.name,
                            'last_modified': file_time.isoformat(),
                            'size_kb': log_file.stat().st_size / 1024
                        })
                except Exception as e:
                    self.logger.warning(f"Error reading log file {log_file}: {e}")
        
        return sorted(recent_uploads, key=lambda x: x['last_modified'], reverse=True)
    
    def _get_error_summary(self) -> Dict:
        """Analyze recent errors from logs."""
        error_summary = {
            'total_errors': 0,
            'rate_limit_errors': 0,
            'upload_failures': 0,
            'auth_errors': 0,
            'recent_errors': []
        }
        
        # Parse recent log files for errors
        log_dir = self.project_root / "logs" / "system"
        if log_dir.exists():
            for log_file in log_dir.glob("google_drive_enhanced_*.log"):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if datetime.now() - file_time < timedelta(hours=24):
                        with open(log_file, 'r') as f:
                            for line in f:
                                if 'ERROR' in line:
                                    error_summary['total_errors'] += 1
                                    if 'rate limit' in line.lower():
                                        error_summary['rate_limit_errors'] += 1
                                    elif 'upload' in line.lower() and 'fail' in line.lower():
                                        error_summary['upload_failures'] += 1
                                    elif 'auth' in line.lower():
                                        error_summary['auth_errors'] += 1
                                    
                                    # Keep last 10 errors
                                    if len(error_summary['recent_errors']) < 10:
                                        error_summary['recent_errors'].append({
                                            'timestamp': line.split(' - ')[0] if ' - ' in line else 'unknown',
                                            'message': line.strip()
                                        })
                except Exception as e:
                    self.logger.warning(f"Error parsing log file {log_file}: {e}")
        
        return error_summary
    
    def _analyze_storage_usage(self) -> Dict:
        """Analyze local storage usage and Google Drive usage."""
        storage_analysis = {
            'local_data_size_mb': 0,
            'folders_analyzed': 0,
            'largest_files': [],
            'folder_breakdown': {}
        }
        
        # Analyze local data directories
        data_paths = [
            self.project_root / "data",
            self.project_root / "raw_pulls",
            self.project_root / "processed"
        ]
        
        for data_path in data_paths:
            if data_path.exists():
                folder_size = self._get_folder_size(data_path)
                storage_analysis['local_data_size_mb'] += folder_size
                storage_analysis['folders_analyzed'] += 1
                storage_analysis['folder_breakdown'][data_path.name] = folder_size
        
        # Find largest files
        all_files = []
        for data_path in data_paths:
            if data_path.exists():
                for file_path in data_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            size_mb = file_path.stat().st_size / (1024 * 1024)
                            all_files.append({
                                'path': str(file_path),
                                'size_mb': round(size_mb, 2),
                                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
                        except Exception:
                            continue
        
        # Get top 10 largest files
        storage_analysis['largest_files'] = sorted(
            all_files, key=lambda x: x['size_mb'], reverse=True
        )[:10]
        
        return storage_analysis
    
    def _get_folder_size(self, folder_path: Path) -> float:
        """Get total size of a folder in MB."""
        total_size = 0
        try:
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"Error calculating size for {folder_path}: {e}")
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _check_api_health(self) -> Dict:
        """Check Google Drive API health and connectivity."""
        api_health = {
            'drive_service_available': False,
            'credentials_valid': False,
            'api_responsive': False,
            'last_api_call': None,
            'response_time_ms': None
        }
        
        if self.enhanced_manager and self.enhanced_manager.drive_service:
            api_health['drive_service_available'] = True
            
            try:
                # Test API call
                start_time = time.time()
                results = self.enhanced_manager.drive_service.files().list(pageSize=1).execute()
                response_time = (time.time() - start_time) * 1000
                
                if results:
                    api_health['credentials_valid'] = True
                    api_health['api_responsive'] = True
                    api_health['last_api_call'] = datetime.now().isoformat()
                    api_health['response_time_ms'] = round(response_time, 2)
                
            except Exception as e:
                api_health['error'] = str(e)
                self.logger.error(f"API health check failed: {e}")
        
        return api_health
    
    def generate_dashboard_html(self) -> str:
        """Generate HTML dashboard for web viewing."""
        if not self.dashboard_data:
            self.collect_sync_status()
        
        data = self.dashboard_data
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Google Drive Sync Dashboard - Hot Durham</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .dashboard {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-title {{ font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #2c3e50; }}
        .status-good {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-error {{ color: #e74c3c; }}
        .progress-bar {{ width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #3498db; transition: width 0.3s ease; }}
        .error-list {{ max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border-radius: 4px; }}
        .timestamp {{ color: #7f8c8d; font-size: 12px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🔄 Google Drive Sync Dashboard</h1>
            <p>Real-time monitoring of Hot Durham Google Drive operations</p>
            <p class="timestamp">Last updated: {data['timestamp']}</p>
        </div>
        
        <div class="metrics-grid">
            <!-- API Health -->
            <div class="metric-card">
                <div class="metric-title">🏥 API Health Status</div>
                <div class="{'status-good' if data['api_health']['api_responsive'] else 'status-error'}">
                    Drive Service: {'✅ Available' if data['api_health']['drive_service_available'] else '❌ Unavailable'}
                </div>
                <div class="{'status-good' if data['api_health']['credentials_valid'] else 'status-error'}">
                    Credentials: {'✅ Valid' if data['api_health']['credentials_valid'] else '❌ Invalid'}
                </div>
                <div class="{'status-good' if data['api_health']['api_responsive'] else 'status-error'}">
                    API Response: {'✅ Responsive' if data['api_health']['api_responsive'] else '❌ Not Responding'}
                </div>
                {f"<div>Response Time: {data['api_health']['response_time_ms']}ms</div>" if data['api_health'].get('response_time_ms') else ''}
            </div>
            
            <!-- Performance Metrics -->
            <div class="metric-card">
                <div class="metric-title">📊 Performance Metrics</div>
                {'<div>Enhanced Manager: ✅ Available</div>' if data['enhanced_manager_available'] else '<div>Enhanced Manager: ❌ Not Available</div>'}
                {self._format_performance_metrics(data['performance_metrics'])}
            </div>
            
            <!-- Error Summary -->
            <div class="metric-card">
                <div class="metric-title">⚠️ Error Summary (24h)</div>
                <div>Total Errors: <span class="{'status-error' if data['error_summary']['total_errors'] > 0 else 'status-good'}">{data['error_summary']['total_errors']}</span></div>
                <div>Rate Limit Hits: <span class="{'status-warning' if data['error_summary']['rate_limit_errors'] > 0 else 'status-good'}">{data['error_summary']['rate_limit_errors']}</span></div>
                <div>Upload Failures: <span class="{'status-error' if data['error_summary']['upload_failures'] > 0 else 'status-good'}">{data['error_summary']['upload_failures']}</span></div>
                <div>Auth Errors: <span class="{'status-error' if data['error_summary']['auth_errors'] > 0 else 'status-good'}">{data['error_summary']['auth_errors']}</span></div>
            </div>
            
            <!-- Storage Analysis -->
            <div class="metric-card">
                <div class="metric-title">💾 Storage Analysis</div>
                <div>Local Data: {data['storage_analysis']['local_data_size_mb']:.1f} MB</div>
                <div>Folders Analyzed: {data['storage_analysis']['folders_analyzed']}</div>
                <div style="margin-top: 10px;">
                    <strong>Folder Breakdown:</strong>
                    {self._format_folder_breakdown(data['storage_analysis']['folder_breakdown'])}
                </div>
            </div>
            
            <!-- Folder Structure Status -->
            <div class="metric-card">
                <div class="metric-title">🗂️ Folder Structure</div>
                <div class="{'status-good' if data['folder_structure_status']['validation_passed'] else 'status-error'}">
                    Structure Valid: {'✅ Passed' if data['folder_structure_status']['validation_passed'] else '❌ Failed'}
                </div>
                {self._format_validation_details(data['folder_structure_status']['details'])}
            </div>
            
            <!-- Recent Activity -->
            <div class="metric-card">
                <div class="metric-title">📝 Recent Activity</div>
                <div>Recent Log Files: {len(data['recent_uploads'])}</div>
                {self._format_recent_uploads(data['recent_uploads'])}
            </div>
        </div>
        
        <!-- Recent Errors Detail -->
        {self._format_recent_errors(data['error_summary']['recent_errors'])}
        
        <!-- Largest Files -->
        {self._format_largest_files(data['storage_analysis']['largest_files'])}
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(function() {{
            window.location.reload();
        }}, 300000);
    </script>
</body>
</html>
"""
        return html
    
    def _format_performance_metrics(self, metrics: Dict) -> str:
        """Format performance metrics for HTML display."""
        if 'error' in metrics:
            return f'<div class="status-error">Error: {metrics["error"]}</div>'
        
        return f"""
        <div>Uploads Completed: {metrics.get('uploads_completed', 0)}</div>
        <div>Uploads Failed: {metrics.get('uploads_failed', 0)}</div>
        <div>API Calls: {metrics.get('api_calls_made', 0)}</div>
        <div>Queue Size: {metrics.get('queue_size', 0)}</div>
        <div>Avg Upload Time: {metrics.get('average_upload_time', 0):.2f}s</div>
        """
    
    def _format_folder_breakdown(self, breakdown: Dict) -> str:
        """Format folder size breakdown for HTML display."""
        html = ""
        for folder, size_mb in breakdown.items():
            html += f'<div>{folder}: {size_mb:.1f} MB</div>'
        return html
    
    def _format_validation_details(self, details: Dict) -> str:
        """Format validation details for HTML display."""
        html = ""
        for check, passed in details.items():
            status = "✅" if passed else "❌"
            html += f'<div>{status} {check.replace("_", " ").title()}</div>'
        return html
    
    def _format_recent_uploads(self, uploads: List[Dict]) -> str:
        """Format recent uploads for HTML display."""
        if not uploads:
            return '<div>No recent activity</div>'
        
        html = '<div style="margin-top: 10px;"><strong>Recent Logs:</strong></div>'
        for upload in uploads[:5]:  # Show last 5
            html += f'<div class="timestamp">{upload["log_file"]} ({upload["size_kb"]:.1f} KB)</div>'
        return html
    
    def _format_recent_errors(self, errors: List[Dict]) -> str:
        """Format recent errors for HTML display."""
        if not errors:
            return ''
        
        html = '''
        <div class="metric-card" style="margin-top: 20px;">
            <div class="metric-title">🚨 Recent Errors</div>
            <div class="error-list">
        '''
        
        for error in errors:
            html += f'<div class="timestamp">{error["timestamp"]}: {error["message"]}</div>'
        
        html += '</div></div>'
        return html
    
    def _format_largest_files(self, files: List[Dict]) -> str:
        """Format largest files for HTML display."""
        if not files:
            return ''
        
        html = '''
        <div class="metric-card" style="margin-top: 20px;">
            <div class="metric-title">📁 Largest Files</div>
            <div style="max-height: 300px; overflow-y: auto;">
        '''
        
        for file in files:
            html += f'<div>{file["size_mb"]} MB - {Path(file["path"]).name}</div>'
        
        html += '</div></div>'
        return html
    
    def save_dashboard_html(self, output_path: Path = None) -> Path:
        """Save HTML dashboard to file."""
        if output_path is None:
            output_path = self.project_root / "dashboard" / "google_drive_sync_status.html"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        html_content = self.generate_dashboard_html()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Dashboard saved to: {output_path}")
        return output_path
    
    def print_console_summary(self):
        """Print a console summary of the sync status."""
        if not self.dashboard_data:
            self.collect_sync_status()
        
        data = self.dashboard_data
        
        print("🔄 GOOGLE DRIVE SYNC DASHBOARD")
        print("=" * 50)
        print(f"📅 Last Updated: {data['timestamp']}")
        print(f"🏥 API Health: {'✅ Healthy' if data['api_health']['api_responsive'] else '❌ Issues'}")
        print(f"📊 Enhanced Manager: {'✅ Available' if data['enhanced_manager_available'] else '❌ Not Available'}")
        print(f"🗂️ Folder Structure: {'✅ Valid' if data['folder_structure_status']['validation_passed'] else '❌ Issues'}")
        
        # Performance metrics
        perf = data['performance_metrics']
        if 'error' not in perf:
            print(f"📈 Uploads Completed: {perf.get('uploads_completed', 0)}")
            print(f"❌ Uploads Failed: {perf.get('uploads_failed', 0)}")
            print(f"📞 API Calls: {perf.get('api_calls_made', 0)}")
            print(f"⏱️ Queue Size: {perf.get('queue_size', 0)}")
        
        # Error summary
        errors = data['error_summary']
        print(f"⚠️ Total Errors (24h): {errors['total_errors']}")
        print(f"🚫 Rate Limit Hits: {errors['rate_limit_errors']}")
        print(f"📤 Upload Failures: {errors['upload_failures']}")
        
        # Storage
        storage = data['storage_analysis']
        print(f"💾 Local Data Size: {storage['local_data_size_mb']:.1f} MB")
        
        print("\n" + "=" * 50)

def main():
    """Main function to run the dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Drive Sync Status Dashboard')
    parser.add_argument('--console', action='store_true', help='Show console summary')
    parser.add_argument('--html', action='store_true', help='Generate HTML dashboard')
    parser.add_argument('--output', help='Output path for HTML dashboard')
    
    args = parser.parse_args()
    
    dashboard = GoogleDriveSyncDashboard()
    
    if args.console:
        dashboard.print_console_summary()
    
    if args.html:
        output_path = Path(args.output) if args.output else None
        saved_path = dashboard.save_dashboard_html(output_path)
        print(f"HTML dashboard saved to: {saved_path}")
    
    if not args.console and not args.html:
        # Default: show console summary
        dashboard.print_console_summary()

if __name__ == "__main__":
    main()
