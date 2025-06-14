#!/usr/bin/env python3
"""
Google Drive Structure Verification and Update Tool
Helps verify current structure and update configurations to use new paths.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from config.improved_google_drive_config import ImprovedGoogleDriveConfig
    from config.test_sensors_config import TestSensorConfig, get_drive_folder_path_with_date
    from src.utils.enhanced_google_drive_manager import get_enhanced_drive_manager
    ENHANCED_AVAILABLE = True
except ImportError as e:
    logger.error(f"Required modules not available: {e}")
    ENHANCED_AVAILABLE = False

class GoogleDriveStructureVerifier:
    """Verifies and updates Google Drive folder structure usage."""
    
    def __init__(self):
        self.project_root = project_root
        self.improved_config = ImprovedGoogleDriveConfig()
        self.test_config = TestSensorConfig()
        
        if ENHANCED_AVAILABLE:
            self.drive_manager = get_enhanced_drive_manager(str(self.project_root))
        else:
            self.drive_manager = None
    
    def check_current_structure_usage(self) -> Dict[str, any]:
        """Check what folder structure is currently being used."""
        logger.info("🔍 Checking current Google Drive structure usage...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_sensor_paths": {},
            "production_paths": {},
            "recent_uploads": {},
            "structure_status": "mixed"
        }
        
        # Check test sensor paths
        today = datetime.now().strftime("%Y%m%d")
        test_sensors = self.test_config.get_test_sensors()[:3]  # Check first 3
        
        for sensor_id in test_sensors:
            current_path = get_drive_folder_path_with_date(sensor_id, today, "sensors")
            improved_path = self.improved_config.get_testing_folder_path("sensors", "WU", today)
            
            results["test_sensor_paths"][sensor_id] = {
                "current_path": current_path,
                "improved_path": improved_path,
                "using_improved": current_path == improved_path
            }
        
        # Check production paths
        wu_production = self.improved_config.get_production_folder_path("raw", "WU")
        tsi_production = self.improved_config.get_production_folder_path("raw", "TSI")
        
        results["production_paths"] = {
            "wu_improved": wu_production,
            "tsi_improved": tsi_production,
            "legacy_wu": "HotDurham/Production/RawData/WU",
            "legacy_tsi": "HotDurham/Production/RawData/TSI"
        }
        
        # Check recent upload evidence
        upload_summary_file = self.project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
        if upload_summary_file.exists():
            with open(upload_summary_file) as f:
                upload_data = json.load(f)
                results["recent_uploads"] = {
                    "last_upload_folder": upload_data.get("upload_info", {}).get("upload_folder", ""),
                    "uses_old_structure": "TestData_ValidationCluster" in upload_data.get("upload_info", {}).get("upload_folder", "")
                }
        
        # Determine overall status
        all_using_improved = all(
            path_info["using_improved"] 
            for path_info in results["test_sensor_paths"].values()
        )
        
        if all_using_improved and not results["recent_uploads"].get("uses_old_structure", True):
            results["structure_status"] = "fully_improved"
        elif any(path_info["using_improved"] for path_info in results["test_sensor_paths"].values()):
            results["structure_status"] = "partially_improved" 
        else:
            results["structure_status"] = "legacy"
        
        return results
    
    def verify_upload_functionality(self) -> Dict[str, any]:
        """Test upload functionality with new structure."""
        logger.info("🧪 Testing upload functionality with new structure...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "drive_service_available": False,
            "enhanced_manager_available": ENHANCED_AVAILABLE,
            "folder_creation_test": False,
            "upload_test": False
        }
        
        if self.drive_manager and self.drive_manager.drive_service:
            results["drive_service_available"] = True
            
            # Test folder creation (safe test)
            try:
                test_folder = "HotDurham/System/Test"
                folder_id = self.drive_manager.get_or_create_folder(test_folder)
                if folder_id:
                    results["folder_creation_test"] = True
                    # Clean up test folder
                    self.drive_manager.drive_service.files().delete(fileId=folder_id).execute()
                    logger.info("✅ Folder creation test passed")
            except Exception as e:
                logger.error(f"❌ Folder creation test failed: {e}")
            
            # Test file upload (create small test file)
            try:
                test_file = self.project_root / 'temp' / 'structure_test.txt'
                test_file.parent.mkdir(exist_ok=True)
                test_file.write_text(f"Structure test - {datetime.now().isoformat()}")
                
                # Upload to new structure
                upload_success = self.drive_manager.upload_file_sync(
                    test_file, 
                    "HotDurham/System/Test"
                )
                
                if upload_success:
                    results["upload_test"] = True
                    logger.info("✅ Upload functionality test passed")
                
                # Clean up
                test_file.unlink(missing_ok=True)
                
            except Exception as e:
                logger.error(f"❌ Upload test failed: {e}")
        
        return results
    
    def generate_status_report(self) -> str:
        """Generate comprehensive status report."""
        logger.info("📊 Generating comprehensive status report...")
        
        structure_check = self.check_current_structure_usage()
        upload_test = self.verify_upload_functionality()
        
        # Determine recommendations
        status = structure_check["structure_status"]
        
        if status == "fully_improved":
            status_emoji = "✅"
            status_text = "FULLY MIGRATED - Using improved structure"
            recommendations = [
                "System is using the new improved folder structure",
                "Monitor for any legacy uploads",
                "Update team documentation if needed"
            ]
        elif status == "partially_improved":
            status_emoji = "⚠️"
            status_text = "PARTIAL MIGRATION - Mixed structure usage"
            recommendations = [
                "Complete migration of remaining components",
                "Update configurations to use new structure consistently",
                "Test all upload paths thoroughly"
            ]
        else:
            status_emoji = "❌"
            status_text = "LEGACY STRUCTURE - Migration needed"
            recommendations = [
                "Execute migration plan immediately",
                "Update all configurations to new structure",
                "Test thoroughly before production use"
            ]
        
        report = f"""
# Google Drive Structure Status Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## {status_emoji} Overall Status: {status_text}

## Current Structure Usage Analysis

### Test Sensor Paths
"""
        
        for sensor_id, path_info in structure_check["test_sensor_paths"].items():
            using_status = "✅ New" if path_info["using_improved"] else "❌ Old"
            report += f"- **{sensor_id}:** {using_status}\n"
            report += f"  - Current: `{path_info['current_path']}`\n"
            report += f"  - Expected: `{path_info['improved_path']}`\n\n"
        
        report += f"""
### Production Paths
- **WU Production:** `{structure_check['production_paths']['wu_improved']}`
- **TSI Production:** `{structure_check['production_paths']['tsi_improved']}`

### Recent Upload Evidence
"""
        
        if structure_check["recent_uploads"]:
            recent_folder = structure_check["recent_uploads"]["last_upload_folder"]
            uses_old = structure_check["recent_uploads"]["uses_old_structure"]
            status_icon = "❌ Old" if uses_old else "✅ New"
            
            report += f"- **Last Upload:** {status_icon}\n"
            report += f"  - Folder: `{recent_folder}`\n\n"
        
        report += f"""
## System Functionality Tests

### Google Drive Integration
- **Drive Service Available:** {"✅ Yes" if upload_test['drive_service_available'] else "❌ No"}
- **Enhanced Manager:** {"✅ Available" if upload_test['enhanced_manager_available'] else "❌ Not Available"}
- **Folder Creation:** {"✅ Working" if upload_test['folder_creation_test'] else "❌ Failed"}
- **File Upload:** {"✅ Working" if upload_test['upload_test'] else "❌ Failed"}

## Folder Structure Comparison

### Old Structure (Legacy)
```
HotDurham/
├── TestData_ValidationCluster/     # ❌ Confusing name
├── ProductionData_SensorAnalysis/  # ❌ Long, unclear
└── RawData/                        # ❌ No organization
    ├── WU/
    └── TSI/
```

### New Structure (Improved)
```
HotDurham/
├── Testing/                        # ✅ Clear purpose
│   ├── SensorData/
│   │   ├── WU/2025/06-June/       # ✅ Date organized
│   │   └── TSI/2025/06-June/
│   ├── ValidationReports/
│   └── Logs/
├── Production/                     # ✅ Clear separation
│   ├── RawData/
│   │   ├── WU/
│   │   └── TSI/
│   ├── Processed/
│   └── Reports/
├── Archives/                      # ✅ Historical data
│   ├── Daily/2025/
│   ├── Weekly/2025/
│   └── Monthly/2025/
└── System/                        # ✅ System files
    ├── Configs/
    ├── Backups/
    └── Metadata/
```

## Recommendations

"""
        
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
        
        report += f"""

## Next Steps

### Immediate Actions
1. **Review Migration Plan:** Check `docs/GOOGLE_DRIVE_MIGRATION_PLAN.md`
2. **Backup Current Data:** Ensure all important data is backed up
3. **Test New Structure:** Verify upload functionality with new paths

### Implementation Steps
1. **Update Configurations:** Ensure all configs use new structure
2. **Test Uploads:** Verify all upload points use correct paths
3. **Monitor Results:** Check that new uploads go to correct locations
4. **Update Documentation:** Inform team of new structure

### Validation Checklist
- [ ] All test sensor uploads go to `HotDurham/Testing/SensorData/`
- [ ] All production uploads go to `HotDurham/Production/RawData/`
- [ ] Reports and visualizations go to appropriate folders
- [ ] Date organization is working correctly
- [ ] Enhanced upload manager is functioning
- [ ] Team is informed of new structure

---
Generated by Google Drive Structure Verification Tool
Hot Durham Environmental Monitoring Project
"""
        
        return report
    
    def save_status_report(self) -> Path:
        """Save the status report to file."""
        report = self.generate_status_report()
        
        report_file = self.project_root / 'docs' / 'GOOGLE_DRIVE_STRUCTURE_STATUS.md'
        report_file.write_text(report)
        
        # Also save raw data
        structure_check = self.check_current_structure_usage()
        upload_test = self.verify_upload_functionality()
        
        data_file = self.project_root / 'docs' / 'google_drive_structure_status.json'
        status_data = {
            "structure_check": structure_check,
            "upload_test": upload_test,
            "generated": datetime.now().isoformat()
        }
        data_file.write_text(json.dumps(status_data, indent=2))
        
        logger.info(f"Status report saved to: {report_file}")
        return report_file

def main():
    """Main function to run structure verification."""
    print("🚗 Hot Durham - Google Drive Structure Status Check")
    print("=" * 55)
    
    if not ENHANCED_AVAILABLE:
        print("❌ Enhanced Google Drive manager not available")
        print("   Install required dependencies first")
        return
    
    verifier = GoogleDriveStructureVerifier()
    
    # Generate status report
    report_file = verifier.save_status_report()
    
    # Show quick summary
    structure_check = verifier.check_current_structure_usage()
    status = structure_check["structure_status"]
    
    print(f"\n📊 Structure Status: {status.upper()}")
    
    if status == "fully_improved":
        print("✅ Your system is fully using the improved folder structure!")
    elif status == "partially_improved":
        print("⚠️  Your system is partially migrated - some components still use old structure")
    else:
        print("❌ Your system is still using the legacy folder structure")
    
    print(f"\n📄 Full report: {report_file}")
    print(f"🔧 Review the report for detailed recommendations")

if __name__ == "__main__":
    main()
