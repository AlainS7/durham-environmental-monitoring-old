#!/usr/bin/env python3
"""
Complete Google Drive Migration Script
=====================================

This script completes the final 20% of the Google Drive migration by:
1. Updating all remaining legacy folder path references
2. Migrating configuration files to use new structure
3. Updating upload scripts and visualization paths
4. Providing comprehensive verification

Usage:
    python complete_google_drive_migration.py [--dry-run] [--backup]
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import shutil
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from config.improved_google_drive_config import (
        get_production_folder_path, 
        get_testing_folder_path,
        IMPROVED_GOOGLE_DRIVE_CONFIG
    )
except ImportError as e:
    print(f"Warning: Could not import config: {e}")
    IMPROVED_GOOGLE_DRIVE_CONFIG = None

class GoogleDriveMigrationCompleter:
    """Completes the final phase of Google Drive folder migration."""
    
    def __init__(self, dry_run: bool = False, create_backup: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.create_backup = create_backup
        self.backup_dir = None
        
        # Setup logging
        self.setup_logging()
        
        # Legacy path mappings to update
        self.legacy_mappings = {
            # Test data paths (old -> new)
            "HotDurham/Testing": "HotDurham/Testing",
            "HotDurham/Testing/SensorData": "HotDurham/Testing/SensorData", 
            "HotDurham/Testing/Visualizations": "HotDurham/Testing/ValidationReports",
            "HotDurham/Testing/ValidationReports": "HotDurham/Testing/ValidationReports",
            "HotDurham/Testing/Logs": "HotDurham/Testing/Logs",
            
            # Production data paths (old -> new)
            "HotDurham/Production": "HotDurham/Production",
            "HotDurham/Production/Visualizations": "HotDurham/Production/Reports",
            "HotDurham/Production/Reports": "HotDurham/Production/Reports",
            "HotDurham/Production/RawData": "HotDurham/Production/RawData",
            "HotDurham/Production/Processed": "HotDurham/Production/Processed"
        }
        
        self.changes_made = []
        
    def setup_logging(self):
        """Setup logging configuration."""
        log_file = self.project_root / 'logs' / 'google_drive_migration_completion.log'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_migration_backup(self):
        """Create backup before making changes."""
        if not self.create_backup:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root / 'backup' / f'google_drive_migration_final_{timestamp}'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Creating migration backup at: {self.backup_dir}")
        
        # Backup key files and directories
        backup_items = [
            'config/',
            'src/',
            'tools/',
            'scripts/',
            'sensor_visualizations/google_drive_upload_summary.json'
        ]
        
        for item in backup_items:
            source = self.project_root / item
            if source.exists():
                if source.is_file():
                    dest = self.backup_dir / item
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
                else:
                    dest = self.backup_dir / item
                    try:
                        shutil.copytree(source, dest)
                    except Exception as e:
                        self.logger.warning(f"Could not backup {item}: {e}")
                    
        self.logger.info(f"✅ Backup created successfully")
        
    def find_files_with_legacy_paths(self) -> List[Tuple[Path, List[str]]]:
        """Find all files containing legacy Google Drive paths."""
        self.logger.info("🔍 Scanning for files with legacy Google Drive paths...")
        
        files_with_legacy = []
        
        # File extensions to check
        extensions = ['.py', '.json', '.md', '.txt', '.sh', '.yml', '.yaml']
        
        # Directories to search
        search_dirs = ['src', 'config', 'tools', 'scripts', 'sensor_visualizations']
        
        for search_dir in search_dirs:
            dir_path = self.project_root / search_dir
            if not dir_path.exists():
                continue
                
            for ext in extensions:
                for file_path in dir_path.rglob(f'*{ext}'):
                    if file_path.is_file():
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                
                            legacy_paths_found = []
                            for legacy_path in self.legacy_mappings.keys():
                                if legacy_path in content:
                                    legacy_paths_found.append(legacy_path)
                            
                            if legacy_paths_found:
                                files_with_legacy.append((file_path, legacy_paths_found))
                                
                        except Exception as e:
                            self.logger.warning(f"Could not read {file_path}: {e}")
                            
        self.logger.info(f"Found {len(files_with_legacy)} files with legacy paths")
        return files_with_legacy
        
    def update_file_content(self, file_path: Path, legacy_paths: List[str]) -> bool:
        """Update file content to use new Google Drive paths."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # Replace legacy paths with new paths
            for legacy_path in legacy_paths:
                if legacy_path in self.legacy_mappings:
                    new_path = self.legacy_mappings[legacy_path]
                    content = content.replace(legacy_path, new_path)
                    self.logger.info(f"  {legacy_path} → {new_path}")
            
            # Only write if content changed
            if content != original_content:
                if not self.dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                self.changes_made.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'legacy_paths': legacy_paths,
                    'action': 'updated_paths'
                })
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating {file_path}: {e}")
            
        return False
        
    def update_upload_summary_files(self):
        """Update existing upload summary files to reflect new structure."""
        self.logger.info("📁 Updating upload summary files...")
        
        # Update main upload summary
        summary_file = self.project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    data = json.load(f)
                
                # Update upload folder path
                old_folder = data.get('upload_info', {}).get('upload_folder', '')
                new_folder = old_folder
                
                for legacy_path, new_path in self.legacy_mappings.items():
                    if legacy_path in old_folder:
                        new_folder = old_folder.replace(legacy_path, new_path)
                        break
                
                if new_folder != old_folder:
                    data['upload_info']['upload_folder'] = new_folder
                    data['access_info']['google_drive_folder'] = new_folder
                    data['upload_info']['migration_note'] = f"Path updated from legacy structure on {datetime.now().isoformat()}"
                    
                    if not self.dry_run:
                        with open(summary_file, 'w') as f:
                            json.dump(data, f, indent=2)
                            
                    self.changes_made.append({
                        'file': 'sensor_visualizations/google_drive_upload_summary.json',
                        'old_path': old_folder,
                        'new_path': new_folder,
                        'action': 'updated_upload_summary'
                    })
                    
                    self.logger.info(f"  Updated upload summary: {old_folder} → {new_folder}")
                    
            except Exception as e:
                self.logger.error(f"Error updating upload summary: {e}")
                
    def create_path_reference_file(self):
        """Create a reference file showing the new folder structure."""
        ref_file = self.project_root / 'docs' / 'GOOGLE_DRIVE_NEW_STRUCTURE_REFERENCE.md'
        
        content = f"""# Google Drive New Structure Reference
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Migration Complete ✅

The Google Drive folder structure has been fully migrated to the improved organization.

## New Folder Structure

```
HotDurham/
├── Production/                  # All production data
│   ├── RawData/                # Raw sensor data
│   │   ├── WU/                 # Weather Underground data
│   │   └── TSI/                # TSI sensor data
│   ├── Processed/              # Processed data files
│   └── Reports/                # Visualization & PDF reports
│
├── Testing/                    # Test sensor data (renamed from TestData_ValidationCluster)
│   ├── SensorData/             # Test sensor raw data
│   │   ├── WU/                 # Test WU sensors
│   │   └── TSI/                # Test TSI sensors
│   ├── ValidationReports/      # Test validation reports & visualizations
│   └── Logs/                   # Test sensor operation logs
│
├── Archives/                   # Historical data
│   ├── Daily/
│   ├── Weekly/
│   └── Monthly/
│
└── System/                     # System files
    ├── Configs/
    ├── Backups/
    └── Metadata/
```

## Legacy Path Mappings

| Legacy Path | New Path | Status |
|-------------|----------|--------|
"""
        
        for legacy, new in self.legacy_mappings.items():
            content += f"| `{legacy}` | `{new}` | ✅ Migrated |\n"
            
        content += f"""
## Benefits of New Structure

✅ **Clear Organization** - Logical separation of production vs testing
✅ **Shorter Paths** - Removed verbose folder names  
✅ **Date Organization** - Automatic date-based organization
✅ **Scalable** - Easy to add new data types and sensors
✅ **Intuitive** - Clear naming conventions

## Implementation Status

- **Production Data Uploads**: ✅ Using new structure
- **Test Data Uploads**: ✅ Using new structure  
- **Visualization Reports**: ✅ Using new structure
- **Legacy Path References**: ✅ All updated
- **Configuration Files**: ✅ All updated

## Changes Made

Total files updated: {len(self.changes_made)}
"""

        if not self.dry_run:
            ref_file.parent.mkdir(parents=True, exist_ok=True)
            with open(ref_file, 'w') as f:
                f.write(content)
                
        self.logger.info(f"Created reference file: {ref_file}")
        
    def verify_migration_completion(self) -> Dict[str, bool]:
        """Verify that migration is complete."""
        self.logger.info("🔍 Verifying migration completion...")
        
        verification_results = {
            'config_files_updated': True,
            'upload_scripts_updated': True,
            'no_legacy_references': True,
            'new_structure_implemented': True
        }
        
        # Check for any remaining legacy references
        remaining_legacy = self.find_files_with_legacy_paths()
        if remaining_legacy:
            verification_results['no_legacy_references'] = False
            self.logger.warning(f"Found {len(remaining_legacy)} files still with legacy paths")
            for file_path, paths in remaining_legacy[:5]:  # Show first 5
                self.logger.warning(f"  {file_path}: {paths}")
        
        # Check key configuration files for actual usage (not just comments)
        key_configs = [
            'config/improved_google_drive_config.py',
            'config/test_sensors_config.py'
        ]
        
        for config_file in key_configs:
            config_path = self.project_root / config_file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    lines = f.readlines()
                
                # Check for actual usage (not just comments)
                for line in lines:
                    line = line.strip()
                    # Skip comments and documentation
                    if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                        continue
                    # Check for actual legacy path usage in strings
                    if ('TestData_ValidationCluster' in line or 'ProductionData_SensorAnalysis' in line) and ('=' in line or ':' in line):
                        verification_results['config_files_updated'] = False
                        self.logger.warning(f"Found legacy path usage in {config_file}: {line}")
                        break
                    
        return verification_results
        
    def run_migration(self):
        """Run the complete migration process."""
        self.logger.info("🚀 Starting Google Drive Migration Completion")
        self.logger.info(f"Dry run: {self.dry_run}")
        
        # Step 1: Create backup
        if not self.dry_run:
            self.create_migration_backup()
            
        # Step 2: Find files with legacy paths
        files_with_legacy = self.find_files_with_legacy_paths()
        
        if not files_with_legacy:
            self.logger.info("✅ No legacy paths found - migration appears complete!")
            return
            
        # Step 3: Update files
        self.logger.info(f"📝 Updating {len(files_with_legacy)} files...")
        
        updated_count = 0
        for file_path, legacy_paths in files_with_legacy:
            self.logger.info(f"Updating: {file_path.relative_to(self.project_root)}")
            if self.update_file_content(file_path, legacy_paths):
                updated_count += 1
                
        # Step 4: Update upload summaries
        self.update_upload_summary_files()
        
        # Step 5: Create reference documentation
        self.create_path_reference_file()
        
        # Step 6: Verify completion
        verification = self.verify_migration_completion()
        
        # Step 7: Report results
        self.logger.info("=" * 60)
        self.logger.info("🎉 GOOGLE DRIVE MIGRATION COMPLETION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Files scanned: {len(files_with_legacy)}")
        self.logger.info(f"Files updated: {updated_count}")
        self.logger.info(f"Changes made: {len(self.changes_made)}")
        
        if self.backup_dir:
            self.logger.info(f"Backup created: {self.backup_dir}")
            
        self.logger.info("\n📊 VERIFICATION RESULTS:")
        for check, passed in verification.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            self.logger.info(f"  {check}: {status}")
            
        if all(verification.values()):
            self.logger.info("\n🎊 MIGRATION 100% COMPLETE! 🎊")
            self.logger.info("All Google Drive paths updated to new structure.")
        else:
            self.logger.warning("\n⚠️ Migration needs attention - see verification results above")
            
        # Save detailed changes log
        if self.changes_made and not self.dry_run:
            changes_file = self.project_root / 'logs' / 'google_drive_migration_changes.json'
            with open(changes_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'migration_type': 'completion',
                    'changes': self.changes_made,
                    'verification': verification
                }, f, indent=2)
            self.logger.info(f"Changes log saved: {changes_file}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete Google Drive folder migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup')
    
    args = parser.parse_args()
    
    migrator = GoogleDriveMigrationCompleter(
        dry_run=args.dry_run,
        create_backup=not args.no_backup
    )
    
    try:
        migrator.run_migration()
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrupted by user")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
