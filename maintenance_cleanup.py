#!/usr/bin/env python3
"""
Hot Durham Project - Maintenance Cleanup Script

This script performs regular maintenance tasks:
1. Cleans up old backup files
2. Removes temporary files and caches
3. Optimizes log files
4. Reports on disk space usage
"""

import os
import sys
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', f'maintenance_{datetime.now().strftime("%Y%m%d")}.log'))
    ]
)
logger = logging.getLogger('maintenance')

# Get project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir)

def cleanup_pycache():
    """Remove Python cache directories and compiled Python files"""
    count = 0
    
    # Remove __pycache__ directories
    for pycache_dir in project_root.glob('**/__pycache__'):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            count += 1
    
    # Remove .pyc files
    for pyc_file in project_root.glob('**/*.pyc'):
        pyc_file.unlink()
        count += 1
    
    logger.info(f"Removed {count} Python cache files and directories")

def cleanup_temp_files(days_old=7):
    """Clean up temporary files older than specified days"""
    count = 0
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    temp_dir = project_root / 'temp'
    if temp_dir.exists():
        for file_path in temp_dir.glob('*'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    count += 1
    
    # Also clean Jupyter notebook checkpoints
    for checkpoint_dir in project_root.glob('**/.ipynb_checkpoints'):
        if checkpoint_dir.is_dir():
            shutil.rmtree(checkpoint_dir)
            count += 1
    
    # Remove .DS_Store files
    for ds_store in project_root.glob('**/.DS_Store'):
        ds_store.unlink()
        count += 1
    
    logger.info(f"Removed {count} temporary files and directories")

def cleanup_old_backups(days_to_keep=30):
    """Clean up old backup files using the BackupSystem"""
    try:
        sys.path.append(str(project_root / "src"))
        from core.backup_system import BackupSystem
        
        backup_system = BackupSystem()
        cleaned_count = backup_system.cleanup_old_backups(days_to_keep=days_to_keep)
        logger.info(f"Cleaned up {cleaned_count} old backup files")
    except ImportError:
        logger.error("Could not import BackupSystem - skipping backup cleanup")

def optimize_logs(max_size_mb=10):
    """Optimize log files that exceed the specified size"""
    count = 0
    max_bytes = max_size_mb * 1024 * 1024
    
    main_log = project_root / 'data_management.log'
    if main_log.exists() and main_log.stat().st_size > max_bytes:
        # Archive the log
        archive_name = f"data_management_{datetime.now().strftime('%Y%m%d')}.log"
        archive_path = project_root / 'archive' / archive_name
        
        # Keep only the most recent 1000 lines
        with open(main_log, 'r') as original:
            lines = original.readlines()
        
        with open(main_log, 'w') as truncated:
            truncated.write("# Log file was truncated by maintenance script\n")
            truncated.write(f"# Previous content archived to {archive_name}\n\n")
            truncated.writelines(lines[-1000:])
        
        # Save the archive
        with open(archive_path, 'w') as archive:
            archive.writelines(lines)
        
        count += 1
        logger.info(f"Optimized {main_log} ({len(lines)} lines -> 1000 lines)")
    
    return count

def report_disk_usage():
    """Report on disk space usage"""
    dir_sizes = {}
    total_size = 0
    
    # Calculate directory sizes
    for dir_name in ['src', 'data', 'backup', 'raw_pulls', 'processed', 'logs', 'archive']:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue
            
        size = sum(f.stat().st_size for f in dir_path.glob('**/*') if f.is_file())
        dir_sizes[dir_name] = size / (1024 * 1024)  # Convert to MB
        total_size += size
    
    # Report sizes
    logger.info("Disk usage report:")
    for dir_name, size_mb in sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {dir_name}: {size_mb:.2f} MB")
    
    logger.info(f"Total size: {total_size / (1024 * 1024):.2f} MB")

def main():
    logger.info("Starting Hot Durham maintenance tasks")
    
    # Perform cleanup tasks
    cleanup_pycache()
    cleanup_temp_files(days_old=7)
    cleanup_old_backups(days_to_keep=30)
    optimize_logs(max_size_mb=10)
    
    # Report disk usage
    report_disk_usage()
    
    logger.info("Maintenance tasks completed")

if __name__ == "__main__":
    main()
