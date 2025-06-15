"""
Performance monitoring and metrics collection
"""
import time
import psutil
import threading
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_io_sent: int
    network_io_recv: int
    active_threads: int
    
class PerformanceMonitor:
    """System performance monitoring"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.metrics_file = self.log_dir / "performance_metrics.jsonl"
        self.is_monitoring = False
        self.monitor_thread = None
        self.interval = 60  # seconds
    
    def start_monitoring(self, interval: int = 60):
        """Start continuous performance monitoring"""
        if self.is_monitoring:
            return
        
        self.interval = interval
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"📊 Performance monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("📊 Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self.is_monitoring:
            try:
                metrics = self.collect_metrics()
                self._log_metrics(metrics)
                time.sleep(self.interval)
            except Exception as e:
                print(f"⚠️ Performance monitoring error: {e}")
                time.sleep(self.interval)
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current system metrics"""
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            net_sent = net_io.bytes_sent
            net_recv = net_io.bytes_recv
        except:
            net_sent = net_recv = 0
        
        # Thread count
        active_threads = threading.active_count()
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            disk_usage_percent=disk.percent,
            network_io_sent=net_sent,
            network_io_recv=net_recv,
            active_threads=active_threads
        )
    
    def _log_metrics(self, metrics: PerformanceMetrics):
        """Log metrics to file"""
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics summary"""
        if not self.metrics_file.exists():
            return {}
        
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        metrics_list = []
        
        with open(self.metrics_file, "r") as f:
            for line in f:
                try:
                    metric = json.loads(line.strip())
                    metric_time = datetime.fromisoformat(metric["timestamp"]).timestamp()
                    if metric_time >= cutoff_time:
                        metrics_list.append(metric)
                except:
                    continue
        
        if not metrics_list:
            return {}
        
        # Calculate averages and peaks
        cpu_values = [m["cpu_percent"] for m in metrics_list]
        memory_values = [m["memory_percent"] for m in metrics_list]
        
        return {
            "sample_count": len(metrics_list),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "latest": metrics_list[-1] if metrics_list else None
        }

class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, logger=None):
        self.operation_name = operation_name
        self.logger = logger
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        if self.logger:
            self.logger.info(f"⏱️ Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if self.logger:
            if exc_type is None:
                self.logger.info(f"✅ Completed {self.operation_name} in {duration:.2f}s")
            else:
                self.logger.error(f"❌ Failed {self.operation_name} after {duration:.2f}s")
        
        return False  # Don't suppress exceptions
    
    @property
    def duration(self) -> float:
        """Get operation duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
