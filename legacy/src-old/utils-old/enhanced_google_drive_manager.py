#!/usr/bin/env python3
"""
Enhanced Google Drive Manager with Rate Limiting and Performance Improvements
Implements the recommended improvements for the Hot Durham project.
"""

import threading
import time
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from queue import Queue, Empty
import hashlib

from config.base.paths import LOG_PATHS
from config.google_drive_manager_config import (
    RATE_LIMITING, PERFORMANCE, MONITORING, SHARE_EMAIL
)

# Optional imports for Google Drive
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    from google.oauth2.service_account import Credentials
    import io
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

@dataclass
class UploadTask:
    """Represents a file upload task for the queue system."""
    local_path: Path
    drive_folder: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    retry_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class RateLimitedGoogleDriveManager:
    """Enhanced Google Drive manager with rate limiting and performance improvements."""
    
    def __init__(self, project_root: str = None, config_file: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Initialize Google Drive service
        self.drive_service = self._setup_google_drive()
        
        # Rate limiting
        self.rate_limiter = self._setup_rate_limiter()
        
        # Upload queue system
        self.upload_queue = Queue()
        self.upload_worker_thread = None
        self.is_worker_running = False
        
        # Performance monitoring
        self.performance_stats = {
            'uploads_completed': 0,
            'uploads_failed': 0,
            'total_upload_time': 0,
            'api_calls_made': 0,
            'rate_limit_hits': 0
        }
        
        # Folder cache to avoid repeated API calls
        self.folder_cache = {}
        self.cache_expiry = datetime.now() + timedelta(hours=1)
        
        # Start upload worker
        self._start_upload_worker()
    
    def _load_config(self, config_file: str = None) -> Dict:
        """Load configuration with improved defaults."""
        return {
            'rate_limiting': RATE_LIMITING,
            'performance': PERFORMANCE,
            'monitoring': MONITORING,
            'share_email': SHARE_EMAIL,
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up enhanced logging system."""
        logger = logging.getLogger('GoogleDriveManager')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_dir = Path(LOG_PATHS["system"])
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler(
                log_dir / f"google_drive_enhanced_{datetime.now().strftime('%Y%m%d')}.log"
            )
            file_handler.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def _setup_google_drive(self) -> Optional[Any]:
        """Initialize Google Drive service with error handling."""
        if not GOOGLE_DRIVE_AVAILABLE:
            self.logger.warning("Google Drive SDK not available")
            return None
        
        creds_path = self.project_root / "creds" / "google_creds.json"
        if not creds_path.exists():
            self.logger.warning(f"Google credentials not found at {creds_path}")
            return None
        
        try:
            credentials = Credentials.from_service_account_file(
                str(creds_path),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            service = build('drive', 'v3', credentials=credentials)
            self.logger.info("Enhanced Google Drive service initialized successfully")
            return service
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Drive service: {e}")
            return None
    
    def _setup_rate_limiter(self) -> Dict:
        """Set up rate limiting system."""
        return {
            'requests_made': 0,
            'window_start': time.time(),
            'window_duration': 1.0,  # 1 second windows
            'max_requests': self.config['rate_limiting']['requests_per_second'],
            'burst_tokens': self.config['rate_limiting']['burst_allowance']
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make an API request without hitting rate limits."""
        now = time.time()
        limiter = self.rate_limiter
        
        # Reset window if needed
        if now - limiter['window_start'] >= limiter['window_duration']:
            limiter['requests_made'] = 0
            limiter['window_start'] = now
        
        # Check if we can make a request
        if limiter['requests_made'] < limiter['max_requests']:
            limiter['requests_made'] += 1
            self.performance_stats['api_calls_made'] += 1
            return True
        
        # Rate limit hit
        self.performance_stats['rate_limit_hits'] += 1
        self.logger.warning("Rate limit hit, waiting...")
        sleep_time = limiter['window_duration'] - (now - limiter['window_start'])
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        return self._check_rate_limit()  # Recursive check after wait
    
    def _start_upload_worker(self):
        """Start the background upload worker thread."""
        if not self.upload_worker_thread or not self.upload_worker_thread.is_alive():
            self.is_worker_running = True
            self.upload_worker_thread = threading.Thread(
                target=self._upload_worker,
                daemon=True
            )
            self.upload_worker_thread.start()
            self.logger.info("Upload worker thread started")
    
    def _upload_worker(self):
        """Background worker that processes the upload queue."""
        while self.is_worker_running:
            try:
                # Get task from queue with timeout
                task = self.upload_queue.get(timeout=5)
                
                # Process the upload
                success = self._process_upload_task(task)
                
                if success:
                    self.performance_stats['uploads_completed'] += 1
                    self.logger.info(f"✅ Upload completed: {task.local_path.name}")
                else:
                    self.performance_stats['uploads_failed'] += 1
                    self.logger.error(f"❌ Upload failed: {task.local_path.name}")
                
                # Mark task as done
                self.upload_queue.task_done()
                
            except Empty:
                # No tasks in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Upload worker error: {e}")
    
    def _process_upload_task(self, task: UploadTask) -> bool:
        """Process a single upload task with retry logic."""
        max_retries = self.config['rate_limiting']['max_retries']
        
        for attempt in range(max_retries + 1):
            try:
                # Rate limiting check
                self._check_rate_limit()
                
                # Perform the upload
                start_time = time.time()
                success = self._perform_upload(task.local_path, task.drive_folder)
                upload_time = time.time() - start_time
                
                if success:
                    self.performance_stats['total_upload_time'] += upload_time
                    return True
                
                # Failed, increment retry count
                task.retry_count += 1
                
                if attempt < max_retries:
                    backoff_time = self.config['rate_limiting']['backoff_factor'] ** attempt
                    self.logger.warning(
                        f"Upload attempt {attempt + 1} failed for {task.local_path.name}, "
                        f"retrying in {backoff_time}s..."
                    )
                    time.sleep(backoff_time)
                
            except Exception as e:
                self.logger.error(f"Upload error (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    backoff_time = self.config['rate_limiting']['backoff_factor'] ** attempt
                    time.sleep(backoff_time)
        
        return False
    
    def _perform_upload(self, local_path: Path, drive_folder: str) -> bool:
        """Perform the actual file upload with chunking support."""
        if not self.drive_service or not local_path.exists():
            return False
        
        try:
            # Get or create folder
            folder_id = self.get_or_create_drive_folder(drive_folder)
            if not folder_id:
                return False
            
            # Check if file already exists and is identical
            if self._file_already_uploaded(local_path, folder_id):
                self.logger.info(f"File {local_path.name} already exists and is identical, skipping")
                return True
            
            # Prepare upload
            file_size_mb = local_path.stat().st_size / (1024 * 1024)
            chunk_size = self.config['rate_limiting']['chunk_size_mb'] * 1024 * 1024
            
            # Use chunked upload for large files
            if (file_size_mb > self.config['rate_limiting']['chunk_size_mb'] and 
                self.config['performance']['enable_chunked_upload']):
                return self._chunked_upload(local_path, folder_id, chunk_size)
            else:
                return self._simple_upload(local_path, folder_id)
        
        except Exception as e:
            self.logger.error(f"Upload error for {local_path.name}: {e}")
            return False
    
    def _simple_upload(self, local_path: Path, folder_id: str) -> bool:
        """Simple file upload for smaller files."""
        try:
            media = MediaFileUpload(str(local_path))
            file_metadata = {
                'name': local_path.name,
                'parents': [folder_id]
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            if file_id:
                self._share_file(file_id)
            return file_id is not None
        
        except Exception as e:
            self.logger.error(f"Simple upload error: {e}")
            return False
    
    def _chunked_upload(self, local_path: Path, folder_id: str, chunk_size: int) -> bool:
        """Chunked file upload for large files."""
        try:
            media = MediaFileUpload(
                str(local_path),
                chunksize=chunk_size,
                resumable=True
            )
            
            file_metadata = {
                'name': local_path.name,
                'parents': [folder_id]
            }
            
            request = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.logger.info(f"Upload progress: {progress}% for {local_path.name}")
                
                # Rate limiting between chunks
                time.sleep(0.1)
            
            file_id = response.get('id')
            if file_id:
                self._share_file(file_id)
            return file_id is not None
        
        except Exception as e:
            self.logger.error(f"Chunked upload error: {e}")
            return False

    def _share_file(self, file_id: str):
        """Share a file with the configured email address."""
        try:
            share_email = self.config.get('share_email', 'hotdurham@gmail.com')
            permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': share_email
            }
            self.drive_service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id'
            ).execute()
            self.logger.info(f"Shared file {file_id} with {share_email}")
        except Exception as e:
            self.logger.error(f"Failed to share file {file_id}: {e}")
    
    def _file_already_uploaded(self, local_path: Path, folder_id: str) -> bool:
        """Check if file already exists in Drive and is identical."""
        try:
            # Search for file by name in the folder
            query = f"name='{local_path.name}' and '{folder_id}' in parents"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, size, md5Checksum)"
            ).execute()
            
            files = results.get('files', [])
            if not files:
                return False
            
            # Check if file size matches
            local_size = str(local_path.stat().st_size)
            for file in files:
                if file.get('size') == local_size:
                    # Optionally check MD5 if available
                    if 'md5Checksum' in file:
                        local_md5 = self._calculate_md5(local_path)
                        if local_md5 == file['md5Checksum']:
                            return True
                    else:
                        # If no MD5, assume same size means same file
                        return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error checking existing file: {e}")
            return False
    
    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_or_create_drive_folder(self, folder_path: str) -> Optional[str]:
        """Get or create a folder in Google Drive with caching."""
        if not self.drive_service:
            return None
        
        # Check cache first
        if (folder_path in self.folder_cache and 
            datetime.now() < self.cache_expiry):
            return self.folder_cache[folder_path]
        
        try:
            folder_names = folder_path.strip('/').split('/')
            parent_id = 'root'
            
            for folder_name in folder_names:
                # Rate limiting
                self._check_rate_limit()
                
                # Search for existing folder
                query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
                results = self.drive_service.files().list(
                    q=query, 
                    fields="files(id, name)"
                ).execute()
                
                items = results.get('files', [])
                
                if items:
                    parent_id = items[0]['id']
                else:
                    # Create new folder
                    folder_metadata = {
                        'name': folder_name,
                        'parents': [parent_id],
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    
                    # Rate limiting
                    self._check_rate_limit()
                    
                    folder = self.drive_service.files().create(
                        body=folder_metadata, 
                        fields='id'
                    ).execute()
                    parent_id = folder.get('id')
            
            # Cache the result
            self.folder_cache[folder_path] = parent_id
            return parent_id
        
        except Exception as e:
            self.logger.error(f"Failed to create/access folder {folder_path}: {e}")
            return None
    
    def queue_upload(self, local_path: Path, drive_folder: str, priority: int = 2) -> bool:
        """Queue a file for upload with priority."""
        if not local_path.exists():
            self.logger.error(f"File not found: {local_path}")
            return False
        
        task = UploadTask(
            local_path=local_path,
            drive_folder=drive_folder,
            priority=priority
        )
        
        try:
            self.upload_queue.put(task)
            self.logger.info(f"Queued upload: {local_path.name} -> {drive_folder}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue upload: {e}")
            return False
    
    def upload_file_sync(self, local_path: Path, drive_folder: str) -> bool:
        """Synchronous file upload (bypass queue)."""
        task = UploadTask(
            local_path=local_path,
            drive_folder=drive_folder,
            priority=1
        )
        return self._process_upload_task(task)
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics."""
        stats = self.performance_stats.copy()
        
        # Calculate averages
        if stats['uploads_completed'] > 0:
            stats['average_upload_time'] = stats['total_upload_time'] / stats['uploads_completed']
        else:
            stats['average_upload_time'] = 0
        
        stats['queue_size'] = self.upload_queue.qsize()
        stats['worker_thread_alive'] = self.upload_worker_thread.is_alive() if self.upload_worker_thread else False
        
        return stats
    
    def create_health_dashboard(self) -> str:
        """Create a health monitoring dashboard."""
        stats = self.get_performance_stats()
        
        dashboard = f"""
🏥 GOOGLE DRIVE HEALTH DASHBOARD
===============================
📊 Upload Statistics:
   ✅ Completed: {stats['uploads_completed']}
   ❌ Failed: {stats['uploads_failed']}
   ⏱️ Average Time: {stats['average_upload_time']:.2f}s
   📦 Queue Size: {stats['queue_size']}

🚀 Performance Metrics:
   🔥 API Calls Made: {stats['api_calls_made']}
   ⏸️ Rate Limit Hits: {stats['rate_limit_hits']}
   🧵 Worker Thread: {'✅ Active' if stats['worker_thread_alive'] else '❌ Inactive'}

💾 Cache Status:
   📁 Cached Folders: {len(self.folder_cache)}
   🕐 Cache Expires: {self.cache_expiry.strftime('%Y-%m-%d %H:%M:%S')}

⚙️ Configuration:
   🚀 Max RPS: {self.config['rate_limiting']['requests_per_second']}
   🔄 Max Retries: {self.config['rate_limiting']['max_retries']}
   📦 Chunk Size: {self.config['rate_limiting']['chunk_size_mb']}MB
"""
        return dashboard
    
    def shutdown(self):
        """Gracefully shutdown the manager."""
        self.logger.info("Shutting down Google Drive manager...")
        
        # Stop worker thread
        self.is_worker_running = False
        
        # Wait for queue to empty
        if not self.upload_queue.empty():
            self.logger.info("Waiting for upload queue to complete...")
            self.upload_queue.join()
        
        # Wait for worker thread to finish
        if self.upload_worker_thread and self.upload_worker_thread.is_alive():
            self.upload_worker_thread.join(timeout=10)
        
        self.logger.info("Google Drive manager shutdown complete")

# Global instance
enhanced_drive_manager = None

def get_enhanced_drive_manager(project_root: str = None) -> RateLimitedGoogleDriveManager:
    """Get or create the enhanced drive manager singleton."""
    global enhanced_drive_manager
    if enhanced_drive_manager is None:
        enhanced_drive_manager = RateLimitedGoogleDriveManager(project_root)
    return enhanced_drive_manager

if __name__ == "__main__":
    # Demo the enhanced system
    manager = RateLimitedGoogleDriveManager()
    
    print("🚀 Enhanced Google Drive Manager Demo")
    print("=" * 40)
    
    # Show health dashboard
    print(manager.create_health_dashboard())
    
    # Demonstrate rate limiting
    print("\n🔄 Rate Limiting Test:")
    for i in range(5):
        can_proceed = manager._check_rate_limit()
        print(f"   Request {i+1}: {'✅ Allowed' if can_proceed else '❌ Limited'}")
    
    # Show configuration
    print("\n⚙️ Current Configuration:")
    print(f"   Rate Limit: {manager.config['rate_limiting']['requests_per_second']} req/sec")
    print(f"   Chunk Size: {manager.config['rate_limiting']['chunk_size_mb']} MB")
    print(f"   Max Retries: {manager.config['rate_limiting']['max_retries']}")
    
    # Cleanup
    manager.shutdown()
