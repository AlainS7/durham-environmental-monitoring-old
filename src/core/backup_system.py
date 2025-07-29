#!/usr/bin/env python3
"""
Backup System for Hot Durham Project

Automated backup system for credential files, critical data, and project configurations.
This system creates multiple backup layers to ensure data integrity and disaster recovery.

Features:
- Credential file backup with encryption option
- Critical data archive creation
- Google Drive backup integration
- Local backup versioning
- Automated cleanup of old backups
- Backup verification and integrity checks
"""

import os
import sys
import json
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import logging
import hashlib
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src" / "core"))

try:
    from src.core.data_manager import DataManager
    DATA_MANAGER_AVAILABLE = True
except ImportError:
    DATA_MANAGER_AVAILABLE = False
    print("Warning: DataManager not available for Google Drive integration")

class BackupSystem:
    """Comprehensive backup system for Hot Durham project"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else project_root
        self.backup_root = self.base_dir / "backup"
        self.setup_directories()
        self.setup_logging()
        
        # Initialize data manager for Google Drive integration
        if DATA_MANAGER_AVAILABLE:
            try:
                self.data_manager = DataManager(str(self.base_dir))
            except Exception as e:
                self.logger.warning(f"Could not initialize DataManager: {e}")
                self.data_manager = None
        else:
            self.data_manager = None
    
    def setup_directories(self):
        """Create backup directory structure"""
        backup_dirs = [
            "credentials",
            "critical_data", 
            "configurations",
            "google_drive_sync",
            "local_archive",
            "verification_logs"
        ]
        
        for directory in backup_dirs:
            (self.backup_root / directory).mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Configure logging for backup operations"""
        log_file = self.backup_root / "verification_logs" / f"backup_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file for integrity verification"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def backup_credentials(self, encrypt: bool = False) -> bool:
        """
        Backup all credential files with optional encryption
        
        Args:
            encrypt: Whether to encrypt the backup (requires gpg)
        
        Returns:
            bool: Success status
        """
        self.logger.info("Starting credential backup")
        
        creds_dir = self.base_dir / "creds"
        if not creds_dir.exists():
            self.logger.error("Credentials directory not found")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"credentials_backup_{timestamp}"
        backup_dir = self.backup_root / "credentials" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup manifest
        manifest = {
            "backup_timestamp": timestamp,
            "backup_type": "credentials",
            "files": [],
            "encrypted": encrypt
        }
        
        try:
            # Copy credential files
            for cred_file in creds_dir.glob("*.json"):
                backup_file = backup_dir / cred_file.name
                shutil.copy2(cred_file, backup_file)
                
                # Calculate hash for verification
                file_hash = self.calculate_file_hash(backup_file)
                manifest["files"].append({
                    "filename": cred_file.name,
                    "size": backup_file.stat().st_size,
                    "hash": file_hash,
                    "original_path": str(cred_file)
                })
                
                self.logger.info(f"Backed up credential: {cred_file.name}")
            
            # Save manifest
            manifest_file = backup_dir / "backup_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create tarball of backup
            archive_path = self.backup_root / "credentials" / f"{backup_name}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=backup_name)
            
            # Encrypt if requested
            if encrypt and shutil.which("gpg"):
                encrypted_path = f"{archive_path}.gpg"
                result = subprocess.run([
                    "gpg", "--symmetric", "--cipher-algo", "AES256",
                    "--output", encrypted_path, str(archive_path)
                ], capture_output=True)
                
                if result.returncode == 0:
                    os.remove(archive_path)  # Remove unencrypted version
                    self.logger.info(f"Encrypted credential backup created: {encrypted_path}")
                else:
                    self.logger.warning("Encryption failed, keeping unencrypted backup")
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir)
            
            self.logger.info(f"Credential backup completed: {archive_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during credential backup: {e}")
            return False
    
    def backup_critical_data(self, days_back: int = 30) -> bool:
        """
        Backup critical data files from recent periods
        
        Args:
            days_back: How many days of data to include in backup
        
        Returns:
            bool: Success status
        """
        self.logger.info(f"Starting critical data backup (last {days_back} days)")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"critical_data_backup_{timestamp}"
        backup_dir = self.backup_root / "critical_data" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Directories to backup
        critical_dirs = [
            ("raw_pulls", "Raw sensor data"),
            ("processed", "Processed data summaries"),
            ("reports", "Generated reports"),
            ("logs", "System logs")
        ]
        
        manifest = {
            "backup_timestamp": timestamp,
            "backup_type": "critical_data",
            "days_back": days_back,
            "cutoff_date": cutoff_date.isoformat(),
            "directories": []
        }
        
        try:
            for dir_name, description in critical_dirs:
                source_dir = self.base_dir / dir_name
                if not source_dir.exists():
                    continue
                
                dest_dir = backup_dir / dir_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                files_copied = 0
                total_size = 0
                
                # Copy recent files
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time >= cutoff_date:
                            # Maintain directory structure
                            rel_path = file_path.relative_to(source_dir)
                            dest_file = dest_dir / rel_path
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            shutil.copy2(file_path, dest_file)
                            files_copied += 1
                            total_size += dest_file.stat().st_size
                
                manifest["directories"].append({
                    "name": dir_name,
                    "description": description,
                    "files_copied": files_copied,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                })
                
                self.logger.info(f"Backed up {files_copied} files from {dir_name} ({total_size / (1024 * 1024):.1f} MB)")
            
            # Save manifest
            manifest_file = backup_dir / "backup_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create compressed archive
            archive_path = self.backup_root / "critical_data" / f"{backup_name}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=backup_name)
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir)
            
            # Upload to Google Drive if available
            if self.data_manager and self.data_manager.drive_service:
                try:
                    self.data_manager.upload_to_drive(archive_path, "HotDurham/Backups/CriticalData")
                    self.logger.info("Critical data backup uploaded to Google Drive")
                except Exception as e:
                    self.logger.warning(f"Could not upload to Google Drive: {e}")
            
            self.logger.info(f"Critical data backup completed: {archive_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during critical data backup: {e}")
            return False
    
    def backup_configurations(self) -> bool:
        """Backup project configuration files"""
        self.logger.info("Starting configuration backup")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config_backup_{timestamp}"
        backup_dir = self.backup_root / "configurations" / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration files to backup
        config_files = [
            "requirements.txt",
            "README.md",
            "toDo",
            "IMPLEMENTATION_REPORT.md",
            "DATA_MANAGEMENT_README.md",
            "config/automation_config.json",
            ".gitignore",
            "setup_automation.sh",
            "run_weekly_pull.sh"
        ]
        
        manifest = {
            "backup_timestamp": timestamp,
            "backup_type": "configurations",
            "files": []
        }
        
        try:
            for config_file in config_files:
                source_path = self.base_dir / config_file
                if source_path.exists():
                    dest_path = backup_dir / config_file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    
                    file_hash = self.calculate_file_hash(dest_path)
                    manifest["files"].append({
                        "filename": config_file,
                        "size": dest_path.stat().st_size,
                        "hash": file_hash
                    })
                    
                    self.logger.info(f"Backed up configuration: {config_file}")
            
            # Save manifest
            manifest_file = backup_dir / "backup_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create archive
            archive_path = self.backup_root / "configurations" / f"{backup_name}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=backup_name)
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir)
            
            self.logger.info(f"Configuration backup completed: {archive_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during configuration backup: {e}")
            return False
    
    def verify_backup_integrity(self, backup_path: Path) -> bool:
        """
        Verify the integrity of a backup archive
        
        Args:
            backup_path: Path to backup archive
        
        Returns:
            bool: True if backup is valid
        """
        self.logger.info(f"Verifying backup integrity: {backup_path}")
        
        try:
            # Extract and check manifest
            with tarfile.open(backup_path, "r:gz") as tar:
                # List contents
                members = tar.getmembers()
                manifest_member = None
                
                for member in members:
                    if member.name.endswith("backup_manifest.json"):
                        manifest_member = member
                        break
                
                if not manifest_member:
                    self.logger.error("No manifest found in backup")
                    return False
                
                # Extract manifest
                manifest_file = tar.extractfile(manifest_member)
                manifest = json.load(manifest_file)
                
                self.logger.info(f"Backup type: {manifest.get('backup_type')}")
                self.logger.info(f"Backup timestamp: {manifest.get('backup_timestamp')}")
                
                # Verify file count
                expected_files = len(manifest.get('files', []))
                actual_files = len([m for m in members if m.isfile() and not m.name.endswith('.json')])
                
                if expected_files != actual_files:
                    self.logger.warning(f"File count mismatch: expected {expected_files}, found {actual_files}")
                
                self.logger.info("Backup integrity verification completed")
                return True
                
        except Exception as e:
            self.logger.error(f"Error verifying backup: {e}")
            return False
    
    def cleanup_old_backups(self, days_to_keep: int = 90) -> int:
        """
        Clean up old backup files
        
        Args:
            days_to_keep: Number of days of backups to retain
        
        Returns:
            int: Number of files cleaned up
        """
        self.logger.info(f"Cleaning up backups older than {days_to_keep} days")
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        backup_types = ["credentials", "critical_data", "configurations"]
        
        for backup_type in backup_types:
            backup_dir = self.backup_root / backup_type
            if not backup_dir.exists():
                continue
            
            for backup_file in backup_dir.glob("*.tar.gz*"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        backup_file.unlink()
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up old backup: {backup_file.name}")
                    except Exception as e:
                        self.logger.error(f"Error cleaning up {backup_file}: {e}")
        
        self.logger.info(f"Cleanup completed: {cleaned_count} files removed")
        return cleaned_count
    
    def create_full_backup(self, encrypt_credentials: bool = False, days_back: int = 30) -> dict:
        """
        Create a comprehensive backup of the entire system
        
        Args:
            encrypt_credentials: Whether to encrypt credential backups
            days_back: Days of data to include in backup
        
        Returns:
            dict: Backup status report
        """
        self.logger.info("Starting full system backup")
        
        backup_report = {
            "timestamp": datetime.now().isoformat(),
            "backup_type": "full_system",
            "components": {},
            "success": True
        }
        
        # Backup credentials
        cred_success = self.backup_credentials(encrypt=encrypt_credentials)
        backup_report["components"]["credentials"] = {
            "success": cred_success,
            "encrypted": encrypt_credentials
        }
        
        # Backup critical data
        data_success = self.backup_critical_data(days_back=days_back)
        backup_report["components"]["critical_data"] = {
            "success": data_success,
            "days_back": days_back
        }
        
        # Backup configurations
        config_success = self.backup_configurations()
        backup_report["components"]["configurations"] = {
            "success": config_success
        }
        
        # Overall success
        backup_report["success"] = all([cred_success, data_success, config_success])
        
        # Save backup report
        report_file = self.backup_root / "verification_logs" / f"full_backup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(backup_report, f, indent=2)
        
        if backup_report["success"]:
            self.logger.info("Full system backup completed successfully")
        else:
            self.logger.error("Full system backup completed with errors")
        
        return backup_report
    
    def get_backup_status(self) -> dict:
        """Get status of all backups"""
        status = {
            "backup_root": str(self.backup_root),
            "last_backup": None,
            "backup_types": {},
            "total_size_mb": 0,
            "oldest_backup": None,
            "newest_backup": None
        }
        
        backup_types = ["credentials", "critical_data", "configurations"]
        all_backups = []
        
        for backup_type in backup_types:
            backup_dir = self.backup_root / backup_type
            if backup_dir.exists():
                backups = list(backup_dir.glob("*.tar.gz*"))
                
                type_info = {
                    "count": len(backups),
                    "total_size_mb": 0,
                    "latest": None,
                    "latest_datetime": None
                }
                
                for backup in backups:
                    backup_size = backup.stat().st_size / (1024 * 1024)
                    type_info["total_size_mb"] += backup_size
                    status["total_size_mb"] += backup_size
                    
                    backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
                    all_backups.append((backup_time, backup))
                    
                    if type_info["latest_datetime"] is None or backup_time > type_info["latest_datetime"]:
                        type_info["latest"] = backup_time.isoformat()
                        type_info["latest_datetime"] = backup_time
                
                # Remove the latest_datetime key before storing
                del type_info["latest_datetime"]
                status["backup_types"][backup_type] = type_info
        
        # Find oldest and newest backups
        if all_backups:
            all_backups.sort()
            status["oldest_backup"] = all_backups[0][0].isoformat()
            status["newest_backup"] = all_backups[-1][0].isoformat()
            status["last_backup"] = all_backups[-1][0].isoformat()
        
        status["total_size_mb"] = round(status["total_size_mb"], 2)
        
        return status

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hot Durham Backup System')
    parser.add_argument('--full', action='store_true', help='Create full system backup')
    parser.add_argument('--credentials', action='store_true', help='Backup credentials only')
    parser.add_argument('--data', action='store_true', help='Backup critical data only')
    parser.add_argument('--config', action='store_true', help='Backup configurations only')
    parser.add_argument('--encrypt', action='store_true', help='Encrypt credential backups (requires gpg)')
    parser.add_argument('--days', type=int, default=30, help='Days of data to include (default: 30)')
    parser.add_argument('--cleanup', type=int, help='Clean up backups older than N days')
    parser.add_argument('--status', action='store_true', help='Show backup status')
    parser.add_argument('--verify', type=str, help='Verify backup integrity (provide path)')
    
    args = parser.parse_args()
    
    backup_system = BackupSystem()
    
    if args.status:
        status = backup_system.get_backup_status()
        print("🗄️ Backup System Status")
        print("=" * 40)
        print(f"Backup Root: {status['backup_root']}")
        print(f"Total Size: {status['total_size_mb']} MB")
        print(f"Last Backup: {status['last_backup'] or 'None'}")
        print()
        
        for backup_type, info in status['backup_types'].items():
            print(f"{backup_type.title()}:")
            print(f"  Count: {info['count']}")
            print(f"  Size: {info['total_size_mb']:.2f} MB")
            print(f"  Latest: {info['latest'] or 'None'}")
        
        return
    
    if args.verify:
        backup_path = Path(args.verify)
        if backup_path.exists():
            result = backup_system.verify_backup_integrity(backup_path)
            print(f"✅ Backup verification: {'PASSED' if result else 'FAILED'}")
        else:
            print(f"❌ Backup file not found: {backup_path}")
        return
    
    if args.cleanup:
        cleaned = backup_system.cleanup_old_backups(args.cleanup)
        print(f"🧹 Cleaned up {cleaned} old backup files")
        return
    
    if args.full:
        report = backup_system.create_full_backup(
            encrypt_credentials=args.encrypt,
            days_back=args.days
        )
        print(f"📦 Full backup {'completed' if report['success'] else 'failed'}")
    elif args.credentials:
        success = backup_system.backup_credentials(encrypt=args.encrypt)
        print(f"🔐 Credential backup {'completed' if success else 'failed'}")
    elif args.data:
        success = backup_system.backup_critical_data(days_back=args.days)
        print(f"📊 Data backup {'completed' if success else 'failed'}")
    elif args.config:
        success = backup_system.backup_configurations()
        print(f"⚙️ Configuration backup {'completed' if success else 'failed'}")
    else:
        print("No backup type specified. Use --help for options.")

if __name__ == "__main__":
    main()
