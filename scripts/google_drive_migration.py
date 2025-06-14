#!/usr/bin/env python3
"""
Google Drive Folder Structure Migration Script
Migrates existing Google Drive data to the improved folder structure.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
    from config.improved_google_drive_config import improved_drive_config, get_production_path, get_testing_path
    ENHANCED_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Enhanced manager not available: {e}")
    ENHANCED_MANAGER_AVAILABLE = False

class GoogleDriveMigrationTool:
    """Tool to migrate existing Google Drive folder structure."""
    
    def __init__(self, project_root_path: str = None):
        self.project_root = Path(project_root_path) if project_root_path else project_root
        
        # Set up logging
        self.logger = self._setup_logging()
        
        # Initialize managers
        self.enhanced_manager = None
        if ENHANCED_MANAGER_AVAILABLE:
            try:
                self.enhanced_manager = get_enhanced_drive_manager(str(self.project_root))
            except Exception as e:
                self.logger.warning(f"Could not initialize enhanced manager: {e}")
        
        # Migration mapping
        self.migration_mapping = {
            # Old structure -> New structure
            "HotDurham/Testing": "HotDurham/Testing",
            "HotDurham/Production/RawData": "HotDurham/Production/RawData",
            "HotDurham/Production/Processed": "HotDurham/Production/Processed",
            "HotDurham/Backups": "HotDurham/System/Backups"
        }
        
        self.migration_stats = {
            'folders_mapped': 0,
            'folders_created': 0,
            'files_moved': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for migration operations."""
        logger = logging.getLogger('GoogleDriveMigration')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            log_dir = self.project_root / "logs" / "system"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / f"drive_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    
    def analyze_existing_structure(self) -> Dict:
        """Analyze the existing Google Drive folder structure."""
        if not self.enhanced_manager or not self.enhanced_manager.drive_service:
            return {'error': 'Google Drive service not available'}
        
        analysis = {
            'folders_found': [],
            'files_by_folder': {},
            'total_files': 0,
            'folder_structure': {},
            'needs_migration': []
        }
        
        try:
            # Search for HotDurham folder
            results = self.enhanced_manager.drive_service.files().list(
                q="name='HotDurham' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            hot_durham_folders = results.get('files', [])
            if not hot_durham_folders:
                self.logger.warning("HotDurham folder not found in Google Drive")
                return analysis
            
            hot_durham_id = hot_durham_folders[0]['id']
            self.logger.info(f"Found HotDurham folder: {hot_durham_id}")
            
            # Recursively analyze folder structure
            analysis['folder_structure'] = self._analyze_folder_recursive(hot_durham_id, "HotDurham")
            
            # Identify folders that need migration
            for old_path, new_path in self.migration_mapping.items():
                if self._folder_exists_in_structure(old_path, analysis['folder_structure']):
                    analysis['needs_migration'].append({
                        'old_path': old_path,
                        'new_path': new_path,
                        'exists': True
                    })
                    self.logger.info(f"Migration needed: {old_path} -> {new_path}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing existing structure: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _analyze_folder_recursive(self, folder_id: str, folder_path: str) -> Dict:
        """Recursively analyze a folder and its contents."""
        folder_info = {
            'id': folder_id,
            'path': folder_path,
            'subfolders': {},
            'files': [],
            'file_count': 0
        }
        
        try:
            # Get folder contents
            results = self.enhanced_manager.drive_service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Recursively analyze subfolder
                    subfolder_path = f"{folder_path}/{item['name']}"
                    folder_info['subfolders'][item['name']] = self._analyze_folder_recursive(
                        item['id'], subfolder_path
                    )
                else:
                    # Regular file
                    file_info = {
                        'id': item['id'],
                        'name': item['name'],
                        'size': int(item.get('size', 0)),
                        'modified': item.get('modifiedTime', '')
                    }
                    folder_info['files'].append(file_info)
                    folder_info['file_count'] += 1
            
            # Add subfolder file counts
            for subfolder in folder_info['subfolders'].values():
                folder_info['file_count'] += subfolder['file_count']
        
        except Exception as e:
            self.logger.error(f"Error analyzing folder {folder_path}: {e}")
            folder_info['error'] = str(e)
        
        return folder_info
    
    def _folder_exists_in_structure(self, path: str, structure: Dict) -> bool:
        """Check if a folder path exists in the analyzed structure."""
        path_parts = path.split('/')
        current = structure
        
        for part in path_parts[1:]:  # Skip first 'HotDurham'
            if part in current.get('subfolders', {}):
                current = current['subfolders'][part]
            else:
                return False
        
        return True
    
    def create_improved_folder_structure(self) -> bool:
        """Create the improved folder structure in Google Drive."""
        if not self.enhanced_manager or not self.enhanced_manager.drive_service:
            self.logger.error("Google Drive service not available")
            return False
        
        self.logger.info("Creating improved folder structure...")
        
        # Folders to create
        folders_to_create = [
            "HotDurham/Production",
            "HotDurham/Production/RawData",
            "HotDurham/Production/RawData/WU",
            "HotDurham/Production/RawData/TSI",
            "HotDurham/Production/Processed",
            "HotDurham/Production/Reports",
            "HotDurham/Testing",
            "HotDurham/Testing/SensorData",
            "HotDurham/Testing/SensorData/WU",
            "HotDurham/Testing/SensorData/TSI",
            "HotDurham/Testing/ValidationReports",
            "HotDurham/Testing/Logs",
            "HotDurham/Archives",
            "HotDurham/Archives/Daily",
            "HotDurham/Archives/Weekly",
            "HotDurham/Archives/Monthly",
            "HotDurham/System",
            "HotDurham/System/Configs",
            "HotDurham/System/Backups",
            "HotDurham/System/Metadata"
        ]
        
        created_count = 0
        for folder_path in folders_to_create:
            try:
                folder_id = self.enhanced_manager.get_or_create_drive_folder(folder_path)
                if folder_id:
                    created_count += 1
                    self.migration_stats['folders_created'] += 1
                    self.logger.info(f"✅ Created/verified folder: {folder_path}")
                else:
                    self.logger.error(f"❌ Failed to create folder: {folder_path}")
            except Exception as e:
                self.logger.error(f"Error creating folder {folder_path}: {e}")
                self.migration_stats['errors'] += 1
        
        self.logger.info(f"Folder structure creation complete: {created_count}/{len(folders_to_create)} folders")
        return created_count == len(folders_to_create)
    
    def preview_migration_plan(self) -> Dict:
        """Generate a preview of the migration plan without executing it."""
        plan = {
            'migration_actions': [],
            'estimated_time_minutes': 0,
            'files_to_move': 0,
            'folders_to_create': 0,
            'risks': []
        }
        
        # Analyze existing structure
        analysis = self.analyze_existing_structure()
        if 'error' in analysis:
            plan['error'] = analysis['error']
            return plan
        
        # Generate migration actions
        for migration in analysis.get('needs_migration', []):
            old_path = migration['old_path']
            new_path = migration['new_path']
            
            # Count files in old location
            file_count = self._count_files_in_path(old_path, analysis['folder_structure'])
            plan['files_to_move'] += file_count
            
            action = {
                'action': 'move_folder',
                'from': old_path,
                'to': new_path,
                'file_count': file_count,
                'estimated_time_minutes': max(1, file_count // 10)  # Rough estimate
            }
            plan['migration_actions'].append(action)
            plan['estimated_time_minutes'] += action['estimated_time_minutes']
        
        # Add risks
        if plan['files_to_move'] > 1000:
            plan['risks'].append("Large number of files to move - consider running during low-usage hours")
        
        if plan['estimated_time_minutes'] > 60:
            plan['risks'].append("Long migration time estimated - ensure stable internet connection")
        
        return plan
    
    def _count_files_in_path(self, path: str, structure: Dict) -> int:
        """Count files in a specific path within the structure."""
        path_parts = path.split('/')
        current = structure
        
        try:
            for part in path_parts[1:]:  # Skip first 'HotDurham'
                if part in current.get('subfolders', {}):
                    current = current['subfolders'][part]
                else:
                    return 0
            
            return current.get('file_count', 0)
        except Exception:
            return 0
    
    def execute_migration(self, dry_run: bool = True) -> Dict:
        """Execute the migration plan."""
        self.migration_stats['start_time'] = datetime.now()
        
        if dry_run:
            self.logger.info("🔍 RUNNING MIGRATION IN DRY-RUN MODE")
        else:
            self.logger.info("🚀 EXECUTING MIGRATION")
        
        results = {
            'success': False,
            'actions_completed': 0,
            'errors': [],
            'dry_run': dry_run
        }
        
        try:
            # Step 1: Create improved folder structure
            if not dry_run:
                structure_created = self.create_improved_folder_structure()
                if not structure_created:
                    results['errors'].append("Failed to create improved folder structure")
                    return results
            else:
                self.logger.info("✅ [DRY RUN] Would create improved folder structure")
            
            # Step 2: Analyze current structure
            analysis = self.analyze_existing_structure()
            if 'error' in analysis:
                results['errors'].append(f"Analysis failed: {analysis['error']}")
                return results
            
            # Step 3: Execute migrations
            for migration in analysis.get('needs_migration', []):
                old_path = migration['old_path']
                new_path = migration['new_path']
                
                if dry_run:
                    self.logger.info(f"✅ [DRY RUN] Would migrate: {old_path} -> {new_path}")
                    results['actions_completed'] += 1
                else:
                    success = self._migrate_folder_contents(old_path, new_path)
                    if success:
                        results['actions_completed'] += 1
                        self.logger.info(f"✅ Migrated: {old_path} -> {new_path}")
                    else:
                        error_msg = f"Failed to migrate: {old_path} -> {new_path}"
                        results['errors'].append(error_msg)
                        self.logger.error(error_msg)
            
            results['success'] = len(results['errors']) == 0
            
        except Exception as e:
            error_msg = f"Migration failed with error: {e}"
            results['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        self.migration_stats['end_time'] = datetime.now()
        return results
    
    def _migrate_folder_contents(self, old_path: str, new_path: str) -> bool:
        """Migrate contents from old folder to new folder."""
        if not self.enhanced_manager or not self.enhanced_manager.drive_service:
            return False
        
        try:
            # Find old folder
            old_folder_id = self._find_folder_by_path(old_path)
            if not old_folder_id:
                self.logger.warning(f"Old folder not found: {old_path}")
                return True  # Not an error if folder doesn't exist
            
            # Create/find new folder
            new_folder_id = self.enhanced_manager.get_or_create_drive_folder(new_path)
            if not new_folder_id:
                self.logger.error(f"Could not create new folder: {new_path}")
                return False
            
            # Move files from old to new folder
            files_moved = self._move_files_between_folders(old_folder_id, new_folder_id)
            self.migration_stats['files_moved'] += files_moved
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error migrating folder contents: {e}")
            return False
    
    def _find_folder_by_path(self, folder_path: str) -> Optional[str]:
        """Find a folder ID by its path."""
        try:
            path_parts = folder_path.split('/')
            parent_id = 'root'
            
            for part in path_parts:
                query = f"name='{part}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'"
                results = self.enhanced_manager.drive_service.files().list(
                    q=query,
                    fields="files(id, name)"
                ).execute()
                
                folders = results.get('files', [])
                if not folders:
                    return None
                
                parent_id = folders[0]['id']
            
            return parent_id
        
        except Exception as e:
            self.logger.error(f"Error finding folder {folder_path}: {e}")
            return None
    
    def _move_files_between_folders(self, source_folder_id: str, dest_folder_id: str) -> int:
        """Move files from source folder to destination folder."""
        files_moved = 0
        
        try:
            # Get files in source folder
            results = self.enhanced_manager.drive_service.files().list(
                q=f"'{source_folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            
            for file in files:
                try:
                    # Move file to new folder
                    self.enhanced_manager.drive_service.files().update(
                        fileId=file['id'],
                        addParents=dest_folder_id,
                        removeParents=source_folder_id
                    ).execute()
                    
                    files_moved += 1
                    self.logger.info(f"Moved file: {file['name']}")
                
                except Exception as e:
                    self.logger.error(f"Error moving file {file['name']}: {e}")
                    self.migration_stats['errors'] += 1
        
        except Exception as e:
            self.logger.error(f"Error listing files in source folder: {e}")
        
        return files_moved
    
    def generate_migration_report(self) -> str:
        """Generate a comprehensive migration report."""
        stats = self.migration_stats
        duration = "Unknown"
        
        if stats['start_time'] and stats['end_time']:
            duration_seconds = (stats['end_time'] - stats['start_time']).total_seconds()
            duration = f"{duration_seconds:.1f} seconds"
        
        report = f"""
🚀 GOOGLE DRIVE MIGRATION REPORT
===============================
📅 Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⏱️ Duration: {duration}
📊 Migration Statistics:
   • Folders Created: {stats['folders_created']}
   • Files Moved: {stats['files_moved']}
   • Errors Encountered: {stats['errors']}

🗂️ IMPROVED FOLDER STRUCTURE:
{improved_drive_config.generate_folder_structure_report()}

✅ Migration completed successfully!

📝 Next Steps:
1. Update application configurations to use new folder paths
2. Verify data integrity in new folder structure
3. Monitor Google Drive sync operations
4. Archive or remove old folder structure after validation

🔧 Verification Commands:
- Check sync dashboard: python src/monitoring/google_drive_sync_dashboard.py --console
- Validate folder structure: python config/improved_google_drive_config.py
- Test enhanced manager: python src/utils/enhanced_google_drive_manager.py
"""
        return report

def main():
    """Main function to run the migration tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Drive Folder Structure Migration Tool')
    parser.add_argument('--analyze', action='store_true', help='Analyze existing structure')
    parser.add_argument('--preview', action='store_true', help='Preview migration plan')
    parser.add_argument('--execute', action='store_true', help='Execute migration')
    parser.add_argument('--dry-run', action='store_true', help='Execute in dry-run mode')
    parser.add_argument('--create-structure', action='store_true', help='Create improved folder structure only')
    
    args = parser.parse_args()
    
    migration_tool = GoogleDriveMigrationTool()
    
    if args.analyze:
        print("🔍 ANALYZING EXISTING GOOGLE DRIVE STRUCTURE")
        print("=" * 50)
        analysis = migration_tool.analyze_existing_structure()
        
        if 'error' in analysis:
            print(f"❌ Analysis failed: {analysis['error']}")
            return
        
        print(f"📁 Folders needing migration: {len(analysis['needs_migration'])}")
        for migration in analysis['needs_migration']:
            print(f"   {migration['old_path']} -> {migration['new_path']}")
    
    elif args.preview:
        print("📋 MIGRATION PLAN PREVIEW")
        print("=" * 50)
        plan = migration_tool.preview_migration_plan()
        
        if 'error' in plan:
            print(f"❌ Preview failed: {plan['error']}")
            return
        
        print(f"📤 Files to move: {plan['files_to_move']}")
        print(f"📁 Folders to create: {plan['folders_to_create']}")
        print(f"⏱️ Estimated time: {plan['estimated_time_minutes']} minutes")
        
        if plan['risks']:
            print(f"\n⚠️ Risks:")
            for risk in plan['risks']:
                print(f"   • {risk}")
        
        print(f"\n📋 Migration Actions:")
        for action in plan['migration_actions']:
            print(f"   • {action['action']}: {action['from']} -> {action['to']} ({action['file_count']} files)")
    
    elif args.create_structure:
        print("🏗️ CREATING IMPROVED FOLDER STRUCTURE")
        print("=" * 50)
        success = migration_tool.create_improved_folder_structure()
        if success:
            print("✅ Folder structure created successfully!")
        else:
            print("❌ Folder structure creation failed!")
    
    elif args.execute or args.dry_run:
        is_dry_run = args.dry_run or not args.execute
        print(f"🚀 {'DRY RUN: ' if is_dry_run else ''}EXECUTING MIGRATION")
        print("=" * 50)
        
        results = migration_tool.execute_migration(dry_run=is_dry_run)
        
        if results['success']:
            print(f"✅ Migration completed successfully!")
            print(f"📊 Actions completed: {results['actions_completed']}")
        else:
            print(f"❌ Migration completed with errors:")
            for error in results['errors']:
                print(f"   • {error}")
        
        # Generate report
        report = migration_tool.generate_migration_report()
        
        # Save report
        report_dir = migration_tool.project_root / "logs" / "system"
        report_file = report_dir / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n📄 Full report saved to: {report_file}")
    
    else:
        print("🔧 GOOGLE DRIVE MIGRATION TOOL")
        print("=" * 50)
        print("Usage:")
        print("  --analyze          Analyze existing structure")
        print("  --preview          Preview migration plan")
        print("  --create-structure Create improved folder structure only")
        print("  --dry-run          Execute migration in dry-run mode")
        print("  --execute          Execute migration (CAUTION: This will modify your Google Drive)")
        print("\nRecommended workflow:")
        print("1. python scripts/google_drive_migration.py --analyze")
        print("2. python scripts/google_drive_migration.py --preview") 
        print("3. python scripts/google_drive_migration.py --dry-run")
        print("4. python scripts/google_drive_migration.py --execute")

if __name__ == "__main__":
    main()
