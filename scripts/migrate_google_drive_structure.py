#!/usr/bin/env python3
"""
Google Drive Folder Structure Migration Script
Migrates from the old folder structure to the improved organization.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.improved_google_drive_config import (
        get_production_path, get_testing_path, get_system_path, get_archive_path,
        IMPROVED_FOLDER_STRUCTURE
    )
    from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
    from src.monitoring.google_drive_dashboard import get_sync_dashboard
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Configuration not available: {e}")
    CONFIG_AVAILABLE = False

class GoogleDriveFolderMigration:
    """Handles migration from old to new Google Drive folder structure."""
    
    def __init__(self, project_root: str = None, dry_run: bool = True):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.dry_run = dry_run
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Get enhanced drive manager
        if CONFIG_AVAILABLE:
            self.drive_manager = get_enhanced_drive_manager(str(self.project_root))
            self.dashboard = get_sync_dashboard(str(self.project_root))
        else:
            self.drive_manager = None
            self.dashboard = None
        
        # Migration mapping
        self.migration_mapping = self._create_migration_mapping()
        
        # Migration statistics
        self.migration_stats = {
            'folders_migrated': 0,
            'files_moved': 0,
            'folders_created': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for migration."""
        logger = logging.getLogger('GoogleDriveMigration')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_dir = self.project_root / "logs" / "system"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / f"google_drive_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            file_handler.setLevel(logging.INFO)
            
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def _create_migration_mapping(self) -> Dict[str, str]:
        """Create mapping from old paths to new paths."""
        if not CONFIG_AVAILABLE:
            return {}
        
        return {
            # Production data migration
            "HotDurham/Production/RawData/WU": get_production_path('raw', 'WU'),
            "HotDurham/Production/RawData/TSI": get_production_path('raw', 'TSI'),
            "HotDurham/Production/Processed": get_production_path('processed'),
            "HotDurham/Production/Processed/MasterData": get_production_path('processed'),
            "HotDurham/Visualizations": get_production_path('reports'),
            
            # Testing data migration (rename TestData_ValidationCluster to Testing)
            "HotDurham/Testing/SensorData/WU": get_testing_path('raw', 'WU'),
            "HotDurham/Testing/SensorData/TSI": get_testing_path('raw', 'TSI'),
            "HotDurham/Testing/ValidationReports": get_testing_path('reports'),
            "HotDurham/Testing/TestVsProduction": get_testing_path('comparisons'),
            "HotDurham/Testing/Logs": get_testing_path('logs'),
            
            # System files migration
            "HotDurham/Backups": get_system_path('backups'),
            "HotDurham/Backups/MasterData": f"{get_system_path('backups')}/MasterData",
            "HotDurham/Configs": get_system_path('configs'),
            
            # Archive data
            "HotDurham/Archives": get_archive_path('monthly')
        }
    
    def analyze_current_structure(self) -> Dict:
        """Analyze the current Google Drive folder structure."""
        if not self.drive_manager or not self.drive_manager.drive_service:
            self.logger.error("Google Drive service not available for analysis")
            return {}
        
        analysis = {
            'existing_folders': [],
            'files_to_migrate': [],
            'migration_needed': [],
            'already_migrated': []
        }
        
        try:
            self.logger.info("🔍 Analyzing current Google Drive structure...")
            
            # Get all folders in HotDurham
            query = "name='HotDurham' and mimeType='application/vnd.google-apps.folder'"
            results = self.drive_manager.drive_service.files().list(q=query).execute()
            
            if not results.get('files'):
                self.logger.warning("HotDurham folder not found in Google Drive")
                return analysis
            
            hotdurham_id = results['files'][0]['id']
            
            # Recursively analyze folder structure
            self._analyze_folder_recursive(hotdurham_id, "HotDurham", analysis)
            
            # Determine what needs migration
            for old_path, new_path in self.migration_mapping.items():
                if old_path in [folder['path'] for folder in analysis['existing_folders']]:
                    if new_path not in [folder['path'] for folder in analysis['existing_folders']]:
                        analysis['migration_needed'].append({
                            'old_path': old_path,
                            'new_path': new_path
                        })
                    else:
                        analysis['already_migrated'].append(old_path)
            
            self.logger.info(f"Analysis complete:")
            self.logger.info(f"  📁 Existing folders: {len(analysis['existing_folders'])}")
            self.logger.info(f"  📄 Files found: {len(analysis['files_to_migrate'])}")
            self.logger.info(f"  🔄 Need migration: {len(analysis['migration_needed'])}")
            self.logger.info(f"  ✅ Already migrated: {len(analysis['already_migrated'])}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing structure: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _analyze_folder_recursive(self, folder_id: str, folder_path: str, analysis: Dict):
        """Recursively analyze folder structure."""
        try:
            # Get all items in this folder
            query = f"'{folder_id}' in parents"
            results = self.drive_manager.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)"
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                item_path = f"{folder_path}/{item['name']}"
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # It's a folder
                    analysis['existing_folders'].append({
                        'id': item['id'],
                        'name': item['name'],
                        'path': item_path
                    })
                    
                    # Recurse into subfolder
                    self._analyze_folder_recursive(item['id'], item_path, analysis)
                else:
                    # It's a file
                    file_size_mb = float(item.get('size', 0)) / (1024 * 1024) if item.get('size') else 0
                    analysis['files_to_migrate'].append({
                        'id': item['id'],
                        'name': item['name'],
                        'path': item_path,
                        'size_mb': file_size_mb
                    })
        
        except Exception as e:
            self.logger.error(f"Error analyzing folder {folder_path}: {e}")
    
    def create_new_folder_structure(self) -> bool:
        """Create the new improved folder structure."""
        if not self.drive_manager or not self.drive_manager.drive_service:
            self.logger.error("Google Drive service not available")
            return False
        
        self.logger.info("🏗️ Creating new folder structure...")
        
        try:
            # Create all the new folder paths
            new_folders = [
                get_production_path('raw', 'WU'),
                get_production_path('raw', 'TSI'),
                get_production_path('processed'),
                get_production_path('reports'),
                get_testing_path('raw', 'WU'),
                get_testing_path('raw', 'TSI'),
                get_testing_path('reports'),
                get_testing_path('comparisons'),
                get_testing_path('logs'),
                get_system_path('backups'),
                get_system_path('configs'),
                get_system_path('metadata'),
                get_archive_path('daily'),
                get_archive_path('weekly'),
                get_archive_path('monthly')
            ]
            
            for folder_path in new_folders:
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would create folder: {folder_path}")
                else:
                    folder_id = self.drive_manager.get_or_create_drive_folder(folder_path)
                    if folder_id:
                        self.migration_stats['folders_created'] += 1
                        self.logger.info(f"✅ Created folder: {folder_path}")
                    else:
                        self.logger.error(f"❌ Failed to create folder: {folder_path}")
                        self.migration_stats['errors'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating folder structure: {e}")
            return False
    
    def migrate_files(self, analysis: Dict) -> bool:
        """Migrate files from old structure to new structure."""
        if not self.drive_manager or not self.drive_manager.drive_service:
            self.logger.error("Google Drive service not available")
            return False
        
        self.logger.info("📦 Starting file migration...")
        
        try:
            for migration in analysis.get('migration_needed', []):
                old_path = migration['old_path']
                new_path = migration['new_path']
                
                self.logger.info(f"Migrating: {old_path} → {new_path}")
                
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would migrate files from {old_path} to {new_path}")
                    continue
                
                # Find files in old folder
                old_folder_id = self._find_folder_id(old_path)
                if not old_folder_id:
                    self.logger.warning(f"Old folder not found: {old_path}")
                    continue
                
                # Get new folder ID
                new_folder_id = self.drive_manager.get_or_create_drive_folder(new_path)
                if not new_folder_id:
                    self.logger.error(f"Could not create new folder: {new_path}")
                    self.migration_stats['errors'] += 1
                    continue
                
                # Move files
                success = self._move_folder_contents(old_folder_id, new_folder_id, old_path, new_path)
                if success:
                    self.migration_stats['folders_migrated'] += 1
                else:
                    self.migration_stats['errors'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during file migration: {e}")
            return False
    
    def _find_folder_id(self, folder_path: str) -> Optional[str]:
        """Find folder ID by path."""
        try:
            folder_names = folder_path.strip('/').split('/')
            parent_id = 'root'
            
            for folder_name in folder_names:
                query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
                results = self.drive_manager.drive_service.files().list(q=query).execute()
                items = results.get('files', [])
                
                if not items:
                    return None
                
                parent_id = items[0]['id']
            
            return parent_id
            
        except Exception as e:
            self.logger.error(f"Error finding folder {folder_path}: {e}")
            return None
    
    def _move_folder_contents(self, old_folder_id: str, new_folder_id: str, 
                            old_path: str, new_path: str) -> bool:
        """Move all contents from old folder to new folder."""
        try:
            # Get all files in old folder
            query = f"'{old_folder_id}' in parents"
            results = self.drive_manager.drive_service.files().list(q=query).execute()
            items = results.get('files', [])
            
            for item in items:
                # Move file to new folder
                file_id = item['id']
                
                # Update parents
                self.drive_manager.drive_service.files().update(
                    fileId=file_id,
                    addParents=new_folder_id,
                    removeParents=old_folder_id
                ).execute()
                
                self.migration_stats['files_moved'] += 1
                self.logger.info(f"  📄 Moved: {item['name']}")
                
                # Record in dashboard if available
                if self.dashboard:
                    file_size_mb = float(item.get('size', 0)) / (1024 * 1024) if item.get('size') else 0
                    self.dashboard.record_sync_operation(
                        'migration', item['name'], new_path, 'success', file_size_mb
                    )
            
            self.logger.info(f"✅ Migrated {len(items)} files from {old_path} to {new_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error moving folder contents: {e}")
            return False
    
    def cleanup_old_folders(self, analysis: Dict) -> bool:
        """Clean up empty old folders after migration."""
        if not self.drive_manager or not self.drive_manager.drive_service:
            return False
        
        self.logger.info("🧹 Cleaning up old empty folders...")
        
        try:
            for migration in analysis.get('migration_needed', []):
                old_path = migration['old_path']
                
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would check if {old_path} is empty and remove it")
                    continue
                
                old_folder_id = self._find_folder_id(old_path)
                if old_folder_id:
                    # Check if folder is empty
                    query = f"'{old_folder_id}' in parents"
                    results = self.drive_manager.drive_service.files().list(q=query).execute()
                    items = results.get('files', [])
                    
                    if not items:
                        # Folder is empty, safe to delete
                        self.drive_manager.drive_service.files().delete(fileId=old_folder_id).execute()
                        self.logger.info(f"🗑️ Removed empty folder: {old_path}")
                    else:
                        self.logger.warning(f"⚠️ Folder not empty, keeping: {old_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up folders: {e}")
            return False
    
    def run_migration(self) -> bool:
        """Run the complete migration process."""
        self.migration_stats['start_time'] = datetime.now()
        
        self.logger.info("🚀 Starting Google Drive folder structure migration")
        self.logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
        
        try:
            # Step 1: Analyze current structure
            self.logger.info("\n📋 Step 1: Analyzing current structure")
            analysis = self.analyze_current_structure()
            
            if analysis.get('error'):
                self.logger.error("Analysis failed, aborting migration")
                return False
            
            # Step 2: Create new folder structure
            self.logger.info("\n🏗️ Step 2: Creating new folder structure")
            if not self.create_new_folder_structure():
                self.logger.error("Failed to create new folder structure")
                return False
            
            # Step 3: Migrate files
            self.logger.info("\n📦 Step 3: Migrating files")
            if not self.migrate_files(analysis):
                self.logger.error("File migration failed")
                return False
            
            # Step 4: Cleanup (only in live mode)
            if not self.dry_run:
                self.logger.info("\n🧹 Step 4: Cleaning up old folders")
                self.cleanup_old_folders(analysis)
            
            self.migration_stats['end_time'] = datetime.now()
            duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
            
            # Final report
            self.logger.info("\n✅ MIGRATION COMPLETE!")
            self.logger.info("=" * 40)
            self.logger.info(f"📊 Migration Statistics:")
            self.logger.info(f"   📁 Folders migrated: {self.migration_stats['folders_migrated']}")
            self.logger.info(f"   📄 Files moved: {self.migration_stats['files_moved']}")
            self.logger.info(f"   🏗️ Folders created: {self.migration_stats['folders_created']}")
            self.logger.info(f"   ❌ Errors: {self.migration_stats['errors']}")
            self.logger.info(f"   ⏱️ Duration: {duration}")
            
            return self.migration_stats['errors'] == 0
            
        except Exception as e:
            self.logger.error(f"Migration failed with error: {e}")
            return False
    
    def generate_migration_report(self) -> str:
        """Generate a detailed migration report."""
        report = f"""
🚗 HOT DURHAM GOOGLE DRIVE MIGRATION REPORT
==========================================

Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}

IMPROVED FOLDER STRUCTURE:
{IMPROVED_FOLDER_STRUCTURE['root']}/
├── Production/
│   ├── RawData/WU/          # Weather Underground production data
│   ├── RawData/TSI/         # TSI production sensors
│   ├── Processed/           # Processed production data
│   └── Reports/             # Production reports
├── Testing/                 # Renamed from TestData_ValidationCluster
│   ├── SensorData/WU/       # Test WU sensors (date organized)
│   ├── SensorData/TSI/      # Test TSI sensors (date organized)
│   ├── ValidationReports/   # Quality validation reports
│   ├── TestVsProduction/    # Comparison analyses
│   └── Logs/                # Test operation logs
├── Archives/                # Organized archives
│   ├── Daily/
│   ├── Weekly/
│   └── Monthly/
└── System/                  # System files
    ├── Backups/
    ├── Configs/
    └── Metadata/

MIGRATION STATISTICS:
📁 Folders migrated: {self.migration_stats['folders_migrated']}
📄 Files moved: {self.migration_stats['files_moved']}
🏗️ New folders created: {self.migration_stats['folders_created']}
❌ Errors encountered: {self.migration_stats['errors']}

KEY IMPROVEMENTS:
✅ Renamed confusing "TestData_ValidationCluster" to "Testing"
✅ Clear separation between Production and Testing
✅ System files organized in dedicated folder
✅ Archive structure for better data lifecycle management
✅ Rate limiting implemented to prevent API issues
✅ Monitoring dashboard for sync health

MIGRATION MAPPING:
"""
        
        for old_path, new_path in self.migration_mapping.items():
            report += f"  {old_path}\n  → {new_path}\n\n"
        
        if self.migration_stats['start_time'] and self.migration_stats['end_time']:
            duration = self.migration_stats['end_time'] - self.migration_stats['start_time']
            report += f"\nMigration Duration: {duration}\n"
        
        report += "\n✅ Migration completed successfully!" if self.migration_stats['errors'] == 0 else "\n❌ Migration completed with errors."
        
        return report

def main():
    """Main function to run the migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate Google Drive folder structure')
    parser.add_argument('--live', action='store_true', help='Run live migration (default is dry run)')
    parser.add_argument('--project-root', help='Project root directory')
    
    args = parser.parse_args()
    
    dry_run = not args.live
    
    print("🚗 Hot Durham Google Drive Migration")
    print("=" * 40)
    
    if not CONFIG_AVAILABLE:
        print("❌ Required configuration not available")
        print("Please ensure all dependencies are installed")
        return 1
    
    migration = GoogleDriveFolderMigration(
        project_root=args.project_root,
        dry_run=dry_run
    )
    
    # Run migration
    success = migration.run_migration()
    
    # Generate report
    report = migration.generate_migration_report()
    
    # Save report
    report_dir = migration.project_root / "logs" / "system"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Migration report saved to: {report_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
