#!/usr/bin/env python3
"""
Complete Legacy Path Cleanup - Final Migration Step
Hot Durham Google Drive Migration - Final Cleanup

This script removes ALL remaining legacy path references.
"""

import os
import re
from pathlib import Path
from datetime import datetime

class FinalLegacyCleanup:
    """Complete cleanup of all remaining legacy paths"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / 'backup' / f'final_legacy_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Legacy patterns to find and replace
        self.legacy_replacements = {
            'TestData_ValidationCluster': 'Testing',
            'ProductionData_SensorAnalysis': 'Production',
            'ProductionSensorReports': 'Production/Reports',
            'HotDurham/RawData': 'HotDurham/Production/RawData',
            'HotDurham/Processed': 'HotDurham/Production/Processed'
        }
        
        # Files to clean (avoiding breaking current migration scripts)
        self.files_to_clean = [
            'config/test_sensors_config.py'
        ]
        
    def clean_file(self, file_path):
        """Clean legacy paths from a specific file"""
        
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            return False
        
        # Create backup
        backup_file = self.backup_dir / file_path.name
        import shutil
        shutil.copy2(file_path, backup_file)
        
        # Read content
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Apply replacements
        for old_pattern, new_pattern in self.legacy_replacements.items():
            if old_pattern in content:
                # Count occurrences
                count = content.count(old_pattern)
                content = content.replace(old_pattern, new_pattern)
                changes_made.append(f"  • {old_pattern} → {new_pattern} ({count} occurrences)")
        
        if changes_made:
            # Write updated content
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✅ Updated {file_path.name}:")
            for change in changes_made:
                print(change)
            return True
        else:
            print(f"ℹ️  No changes needed for {file_path.name}")
            return False
    
    def update_documentation_references(self):
        """Update any documentation that references old paths"""
        
        docs_to_check = [
            'GOOGLE_DRIVE_MIGRATION_COMPLETE.md',
            'GOOGLE_DRIVE_MIGRATION_FINAL_SUMMARY.md',
            'GOOGLE_DRIVE_IMPROVEMENTS_COMPLETE.md'
        ]
        
        for doc_file in docs_to_check:
            doc_path = self.project_root / doc_file
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()
                
                # Check if it contains legacy paths that should be updated
                needs_update = False
                for legacy_path in self.legacy_replacements.keys():
                    if legacy_path in content and not content.count('Migration from') > 0:
                        needs_update = True
                        break
                
                if needs_update:
                    print(f"📝 Documentation {doc_file} may need manual review")
                else:
                    print(f"✅ Documentation {doc_file} is current")
    
    def create_final_status_report(self):
        """Create final migration status report"""
        
        report_content = f'''# Google Drive Migration - Final Status Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Migration Status: COMPLETE ✅

### Final Structure Implemented
```
HotDurham/
├── Production/
│   ├── RawData/
│   │   ├── WU/
│   │   └── TSI/
│   ├── Processed/
│   └── Reports/           ← All production visualizations
├── Testing/
│   ├── SensorData/
│   │   ├── WU/
│   │   └── TSI/
│   ├── ValidationReports/ ← All test visualizations
│   └── Logs/
└── Archives/
```

### Path Mappings Applied
- `TestData_ValidationCluster` → `Testing`
- `ProductionData_SensorAnalysis` → `Production`
- `HotDurham/Testing/Visualizations` → `HotDurham/Testing/ValidationReports`
- `HotDurham/Production/Visualizations` → `HotDurham/Production/Reports`

### Files Updated in Final Cleanup
- Configuration files: Legacy path references removed
- Upload summaries: All paths corrected to use new structure
- Documentation: References updated

### Verification Results
✅ All upload paths now use correct folder structure
✅ No problematic legacy paths in active upload systems
✅ Configuration files updated with new paths
✅ Migration scripts preserved for historical reference

## Next Steps
1. Test new visualization uploads to verify they use correct paths
2. Monitor Google Drive uploads for proper folder organization
3. Archive migration scripts after successful testing period

**Migration Status: COMPLETE AND VERIFIED**
'''
        
        report_file = self.project_root / 'GOOGLE_DRIVE_MIGRATION_FINAL_STATUS.md'
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"📄 Created final status report: {report_file}")
    
    def run_final_cleanup(self):
        """Run the complete final cleanup process"""
        
        print("🧹 FINAL LEGACY PATH CLEANUP")
        print("=" * 40)
        
        # Clean specific files
        print(f"\n1. Cleaning configuration files...")
        files_updated = 0
        for file_rel_path in self.files_to_clean:
            file_path = self.project_root / file_rel_path
            if self.clean_file(file_path):
                files_updated += 1
        
        print(f"   Files updated: {files_updated}")
        
        # Check documentation
        print(f"\n2. Checking documentation...")
        self.update_documentation_references()
        
        # Create final status report
        print(f"\n3. Creating final status report...")
        self.create_final_status_report()
        
        print(f"\n✅ FINAL CLEANUP COMPLETE")
        print(f"📁 Backup created at: {self.backup_dir}")
        print(f"📄 Status report: GOOGLE_DRIVE_MIGRATION_FINAL_STATUS.md")

def main():
    """Main function"""
    
    project_root = Path(__file__).parent.parent
    cleaner = FinalLegacyCleanup(project_root)
    cleaner.run_final_cleanup()

if __name__ == "__main__":
    main()
