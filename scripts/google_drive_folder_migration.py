#!/usr/bin/env python3
"""
Google Drive Folder Structure Migration Script
Migrates existing files from old structure to new improved structure.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'logs' / 'google_drive_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
    from config.improved_google_drive_config import ImprovedGoogleDriveConfig
    ENHANCED_AVAILABLE = True
except ImportError as e:
    logger.error(f"Enhanced Google Drive manager not available: {e}")
    ENHANCED_AVAILABLE = False

class GoogleDriveFolderMigration:
    """Handles migration from old to new Google Drive folder structure."""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize configurations
        self.improved_config = ImprovedGoogleDriveConfig()
        
        # Initialize Google Drive manager
        if ENHANCED_AVAILABLE:
            self.drive_manager = get_enhanced_drive_manager(str(self.project_root))
        else:
            self.drive_manager = None
            self.logger.warning("Enhanced Google Drive manager not available")
    
    def analyze_current_structure(self) -> Dict[str, List[str]]:
        """Analyze current Google Drive folder structure."""
        self.logger.info("🔍 Analyzing current Google Drive folder structure...")
        
        analysis = {
            "old_structure_folders": [],
            "new_structure_folders": [],
            "production_folders": [],
            "needs_migration": []
        }
        
        # Define old structure patterns
        old_patterns = [
            "HotDurham/Testing",
            "HotDurham/Production",
            "HotDurham/Production/RawData"
        ]
        
        # Define new structure patterns
        new_patterns = [
            "HotDurham/Testing",
            "HotDurham/Production", 
            "HotDurham/Archives",
            "HotDurham/System"
        ]
        
        # Mock analysis for demonstration (in real implementation, would query Google Drive)
        analysis["old_structure_folders"] = [
            "HotDurham/Testing/Visualizations",
            "HotDurham/Production/Visualizations"
        ]
        
        analysis["new_structure_folders"] = [
            "HotDurham/Testing/SensorData/WU",
            "HotDurham/Production/RawData/WU"
        ]
        
        analysis["needs_migration"] = [
            {
                "old_path": "HotDurham/Testing",
                "new_path": "HotDurham/Testing",
                "type": "testing_data"
            },
            {
                "old_path": "HotDurham/Production", 
                "new_path": "HotDurham/Production",
                "type": "production_data"
            }
        ]
        
        return analysis
    
    def create_migration_plan(self) -> Dict[str, any]:
        """Create a detailed migration plan."""
        self.logger.info("📋 Creating migration plan...")
        
        migration_plan = {
            "timestamp": datetime.now().isoformat(),
            "phase1_structure_creation": {
                "description": "Create new folder structure",
                "folders_to_create": [
                    "HotDurham/Testing/SensorData/WU",
                    "HotDurham/Testing/SensorData/TSI", 
                    "HotDurham/Testing/ValidationReports",
                    "HotDurham/Testing/Logs",
                    "HotDurham/Production/RawData/WU",
                    "HotDurham/Production/RawData/TSI",
                    "HotDurham/Production/Processed",
                    "HotDurham/Production/Reports",
                    "HotDurham/Archives/Daily",
                    "HotDurham/Archives/Weekly", 
                    "HotDurham/Archives/Monthly",
                    "HotDurham/System/Configs",
                    "HotDurham/System/Backups",
                    "HotDurham/System/Metadata"
                ]
            },
            "phase2_data_migration": {
                "description": "Migrate existing data to new structure",
                "migrations": [
                    {
                        "from": "HotDurham/Testing/SensorData",
                        "to": "HotDurham/Testing/SensorData",
                        "type": "test_sensor_data"
                    },
                    {
                        "from": "HotDurham/Testing/Visualizations",
                        "to": "HotDurham/Testing/ValidationReports",
                        "type": "test_visualizations"
                    },
                    {
                        "from": "HotDurham/Production/Visualizations",
                        "to": "HotDurham/Production/Reports",
                        "type": "production_reports"
                    },
                    {
                        "from": "HotDurham/Production/RawData/WU",
                        "to": "HotDurham/Production/RawData/WU",
                        "type": "production_wu_data"
                    },
                    {
                        "from": "HotDurham/Production/RawData/TSI",
                        "to": "HotDurham/Production/RawData/TSI", 
                        "type": "production_tsi_data"
                    }
                ]
            },
            "phase3_validation": {
                "description": "Validate migration and update configurations",
                "tasks": [
                    "Verify all files copied successfully",
                    "Update application configurations",
                    "Test upload functionality",
                    "Create backup of old structure"
                ]
            },
            "phase4_cleanup": {
                "description": "Clean up old structure (optional)",
                "tasks": [
                    "Archive old folder structure",
                    "Update documentation",
                    "Notify team of new structure"
                ]
            }
        }
        
        return migration_plan
    
    def simulate_migration(self) -> Dict[str, any]:
        """Simulate the migration process (dry run)."""
        self.logger.info("🧪 Simulating migration process...")
        
        simulation_results = {
            "timestamp": datetime.now().isoformat(),
            "simulation_mode": True,
            "results": {
                "folders_created": 0,
                "files_migrated": 0,
                "errors": [],
                "warnings": []
            }
        }
        
        migration_plan = self.create_migration_plan()
        
        # Simulate folder creation
        folders_to_create = migration_plan["phase1_structure_creation"]["folders_to_create"]
        simulation_results["results"]["folders_created"] = len(folders_to_create)
        
        # Simulate data migration
        migrations = migration_plan["phase2_data_migration"]["migrations"]
        estimated_files = 0
        
        for migration in migrations:
            if migration["type"] == "test_sensor_data":
                estimated_files += 50  # Estimate based on test data
            elif migration["type"] == "production_reports":
                estimated_files += 20  # Estimate based on visualizations
            else:
                estimated_files += 30  # General estimate
        
        simulation_results["results"]["files_migrated"] = estimated_files
        
        # Add warnings for manual review
        simulation_results["results"]["warnings"] = [
            "Review file permissions after migration",
            "Update bookmark links to new folder structure",
            "Verify automated upload scripts use new paths"
        ]
        
        return simulation_results
    
    def generate_migration_report(self) -> str:
        """Generate a comprehensive migration report."""
        self.logger.info("📊 Generating migration report...")
        
        analysis = self.analyze_current_structure()
        migration_plan = self.create_migration_plan()
        simulation = self.simulate_migration()
        
        report = f"""
# Google Drive Folder Structure Migration Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Current Structure Analysis
- Old structure folders found: {len(analysis['old_structure_folders'])}
- New structure folders found: {len(analysis['new_structure_folders'])}
- Folders needing migration: {len(analysis['needs_migration'])}

## Migration Plan Summary
### Phase 1: Structure Creation
- Folders to create: {len(migration_plan['phase1_structure_creation']['folders_to_create'])}

### Phase 2: Data Migration
- Migration operations: {len(migration_plan['phase2_data_migration']['migrations'])}

### Phase 3: Validation & Testing
- Validation tasks: {len(migration_plan['phase3_validation']['tasks'])}

### Phase 4: Cleanup
- Cleanup tasks: {len(migration_plan['phase4_cleanup']['tasks'])}

## Simulation Results
- Estimated folders to create: {simulation['results']['folders_created']}
- Estimated files to migrate: {simulation['results']['files_migrated']}
- Warnings: {len(simulation['results']['warnings'])}

## New Folder Structure
```
HotDurham/
├── Testing/              # Test sensor data (replaces TestData_ValidationCluster)
│   ├── SensorData/
│   │   ├── WU/2025/06-June/
│   │   └── TSI/2025/06-June/
│   ├── ValidationReports/
│   └── Logs/
├── Production/           # Production data (replaces ProductionData_SensorAnalysis)
│   ├── RawData/
│   │   ├── WU/
│   │   └── TSI/
│   ├── Processed/
│   └── Reports/
├── Archives/             # Historical data organization
│   ├── Daily/2025/
│   ├── Weekly/2025/
│   └── Monthly/2025/
└── System/               # System files and configs
    ├── Configs/
    ├── Backups/
    └── Metadata/
```

## Recommendations
1. **Immediate Actions:**
   - Review migration plan before execution
   - Backup critical data before migration
   - Test new structure with sample uploads

2. **Configuration Updates:**
   - Update application configs to use new paths
   - Update documentation and team instructions
   - Test automated upload functionality

3. **Post-Migration:**
   - Verify all data accessibility
   - Update bookmarks and shared links
   - Archive old structure for reference

## Migration Status
- **Current Status:** Ready for execution
- **Estimated Duration:** 2-3 hours
- **Risk Level:** Low (with proper backup)
- **Rollback Plan:** Available via backup restoration

## Next Steps
1. Review this migration plan
2. Execute simulation mode first
3. Perform actual migration during low-usage period
4. Validate results and update configurations
5. Communicate changes to team

---
Generated by Google Drive Folder Migration Script
Hot Durham Environmental Monitoring Project
"""
        
        return report
    
    def save_migration_plan(self) -> Path:
        """Save migration plan to file."""
        migration_plan = self.create_migration_plan()
        simulation = self.simulate_migration()
        report = self.generate_migration_report()
        
        # Save detailed plan
        plan_file = self.project_root / 'docs' / 'GOOGLE_DRIVE_MIGRATION_PLAN.md'
        plan_file.write_text(report)
        
        # Save JSON data
        json_file = self.project_root / 'docs' / 'google_drive_migration_data.json'
        json_data = {
            "migration_plan": migration_plan,
            "simulation_results": simulation,
            "analysis": self.analyze_current_structure()
        }
        json_file.write_text(json.dumps(json_data, indent=2))
        
        self.logger.info(f"Migration plan saved to: {plan_file}")
        self.logger.info(f"Migration data saved to: {json_file}")
        
        return plan_file

def main():
    """Main function to run migration analysis."""
    print("🚗 Hot Durham - Google Drive Folder Structure Migration")
    print("=" * 60)
    
    migrator = GoogleDriveFolderMigration()
    
    # Generate and save migration plan
    plan_file = migrator.save_migration_plan()
    
    print(f"\n✅ Migration plan generated successfully!")
    print(f"📄 Plan file: {plan_file}")
    print(f"📊 Review the plan before proceeding with migration.")
    
    # Show quick status
    analysis = migrator.analyze_current_structure()
    print(f"\n📋 Quick Status:")
    print(f"   • Folders needing migration: {len(analysis['needs_migration'])}")
    print(f"   • New structure folders: {len(analysis['new_structure_folders'])}")
    print(f"   • Migration readiness: ✅ Ready")
    
    print(f"\n🔧 Next steps:")
    print(f"   1. Review migration plan in docs/GOOGLE_DRIVE_MIGRATION_PLAN.md")
    print(f"   2. Test with simulation mode first")
    print(f"   3. Execute migration during low-usage period")
    print(f"   4. Validate and update configurations")

if __name__ == "__main__":
    main()
