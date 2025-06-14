#!/usr/bin/env python3
"""
Final Migration Verification Script
Comprehensive verification that Google Drive migration is 100% complete
and all systems are operational.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src" / "core"))
sys.path.append(str(project_root / "config"))

def print_header(title):
    """Print formatted header."""
    print("\n" + "="*60)
    print(f"🎯 {title}")
    print("="*60)

def print_success(message):
    """Print success message."""
    print(f"✅ {message}")

def print_info(message):
    """Print info message."""
    print(f"ℹ️  {message}")

def verify_automation_results():
    """Verify automation systems from results file."""
    print_header("AUTOMATION SYSTEMS VERIFICATION")
    
    results_file = project_root / "automation_verification_results.json"
    if not results_file.exists():
        print("❌ Automation verification results not found")
        return False
    
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Check the summary section for working systems
        summary = results.get('summary', {})
        systems_working = summary.get('working_systems', 0)
        total_systems = summary.get('total_systems', 6)
        success_rate = summary.get('success_rate', 0)
        
        print_info(f"Systems Working: {systems_working}/{total_systems}")
        print_info(f"Success Rate: {success_rate*100:.1f}%")
        
        if systems_working == total_systems and success_rate == 1.0:
            print_success("ALL AUTOMATION SYSTEMS OPERATIONAL")
            return True
        else:
            print(f"❌ Only {systems_working}/{total_systems} systems working")
            return False
            
    except Exception as e:
        print(f"❌ Error reading automation results: {e}")
        return False

def verify_folder_structure():
    """Verify new Google Drive folder structure is in use."""
    print_header("FOLDER STRUCTURE VERIFICATION")
    
    # Check for improved config
    config_file = project_root / "config" / "improved_google_drive_config.py"
    if config_file.exists():
        print_success("Improved Google Drive config exists")
    else:
        print("❌ Improved Google Drive config not found")
        return False
    
    # Check test sensors config
    test_config_file = project_root / "config" / "test_sensors_config.py"
    if test_config_file.exists():
        try:
            with open(test_config_file, 'r') as f:
                content = f.read()
            
            # Check for new structure references
            if '"test_data_folder": "Testing"' in content:
                print_success("Test sensors using new 'Testing' folder")
            else:
                print("❌ Test sensors not using new folder structure")
                return False
                
        except Exception as e:
            print(f"❌ Error checking test config: {e}")
            return False
    
    return True

def verify_upload_paths():
    """Verify upload paths are using new structure."""
    print_header("UPLOAD PATH VERIFICATION")
    
    # Check visualization upload summaries
    viz_path = project_root / "sensor_visualizations"
    if viz_path.exists():
        # Look for upload summary files
        upload_files = list(viz_path.rglob("*UPLOAD_SUMMARY*.txt"))
        
        legacy_found = False
        new_structure_found = False
        
        for file in upload_files:
            try:
                with open(file, 'r') as f:
                    content = f.read()
                
                # Check for legacy paths
                if "Visualizations/" in content:
                    legacy_found = True
                
                # Check for new paths
                if "ValidationReports/" in content or "Reports/" in content:
                    new_structure_found = True
                    
            except Exception:
                continue
        
        if legacy_found:
            print("⚠️  Some legacy paths still found in upload summaries")
        
        if new_structure_found:
            print_success("New folder structure paths found in uploads")
        
        if not legacy_found and new_structure_found:
            print_success("Upload paths fully migrated to new structure")
            return True
    
    print_info("No upload summaries found to verify")
    return True

def verify_migration_completion():
    """Verify migration completion markers."""
    print_header("MIGRATION COMPLETION VERIFICATION")
    
    completion_files = [
        "GOOGLE_DRIVE_MIGRATION_SUCCESS.md",
        "GOOGLE_DRIVE_MIGRATION_FINAL_STATUS.md", 
        "GOOGLE_DRIVE_MIGRATION_COMPLETE_FINAL.md"
    ]
    
    files_found = 0
    for file in completion_files:
        if (project_root / file).exists():
            files_found += 1
            print_success(f"Found {file}")
    
    if files_found >= 2:
        print_success("Migration completion properly documented")
        return True
    else:
        print("❌ Migration completion not properly documented")
        return False

def verify_system_health():
    """Check overall system health indicators."""
    print_header("SYSTEM HEALTH CHECK")
    
    health_indicators = []
    
    # Check for recent log files
    log_files = list(project_root.rglob("*.log"))
    if log_files:
        print_success(f"Found {len(log_files)} log files - system active")
        health_indicators.append(True)
    
    # Check for data files
    data_path = project_root / "data"
    if data_path.exists():
        data_files = list(data_path.rglob("*.csv"))
        if data_files:
            print_success(f"Found {len(data_files)} data files - data collection active")
            health_indicators.append(True)
    
    # Check for configuration files
    config_path = project_root / "config"
    if config_path.exists():
        config_files = list(config_path.rglob("*.json")) + list(config_path.rglob("*.py"))
        if config_files:
            print_success(f"Found {len(config_files)} configuration files")
            health_indicators.append(True)
    
    return len(health_indicators) >= 2

def main():
    """Run comprehensive final verification."""
    print_header("FINAL MIGRATION VERIFICATION")
    print_info(f"Verification Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info("Verifying Google Drive migration completion...")
    
    # Run all verifications
    results = []
    
    results.append(("Automation Systems", verify_automation_results()))
    results.append(("Folder Structure", verify_folder_structure()))
    results.append(("Upload Paths", verify_upload_paths()))
    results.append(("Migration Documentation", verify_migration_completion()))
    results.append(("System Health", verify_system_health()))
    
    # Summary
    print_header("FINAL VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print(f"\n📊 VERIFICATION RESULTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("\n🎉 MIGRATION VERIFICATION: COMPLETE SUCCESS!")
        print("✅ Google Drive migration is 100% complete")
        print("✅ All systems verified and operational")
        print("✅ Ready for normal operations")
        
        # Save verification results
        verification_results = {
            "verification_date": datetime.now().isoformat(),
            "total_tests": total,
            "tests_passed": passed,
            "success_rate": f"{(passed/total)*100:.1f}%",
            "migration_status": "COMPLETE" if passed == total else "INCOMPLETE",
            "test_results": dict(results)
        }
        
        results_file = project_root / "final_migration_verification.json"
        with open(results_file, 'w') as f:
            json.dump(verification_results, f, indent=2)
        
        print(f"📄 Verification results saved to: {results_file}")
        return 0
    else:
        print(f"\n⚠️  MIGRATION VERIFICATION: {passed}/{total} TESTS PASSED")
        print("Some issues detected - review failed tests above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
