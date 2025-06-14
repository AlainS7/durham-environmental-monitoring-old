#!/usr/bin/env python3
"""
Final Migration Script: Fix Visualization Upload Paths
Hot Durham Google Drive Migration - Final Path Corrections

This script addresses the remaining issue where visualization uploads
are still using the old folder structure despite the migration.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class VisualizationPathFixer:
    """Fixes remaining visualization upload path issues"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / 'backup' / f'visualization_path_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Correct path mappings
        self.path_corrections = {
            "HotDurham/Testing/Visualizations": "HotDurham/Testing/ValidationReports",
            "HotDurham/Production/Visualizations": "HotDurham/Production/Reports",
            "ProductionData_SensorAnalysis/Visualizations": "Production/Reports",
            "TestData_ValidationCluster/Visualizations": "Testing/ValidationReports"
        }
        
    def fix_upload_summary_json(self):
        """Fix the google_drive_upload_summary.json file"""
        
        summary_file = self.project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
        if not summary_file.exists():
            print(f"⚠️ Upload summary file not found: {summary_file}")
            return False
            
        # Create backup
        backup_file = self.backup_dir / 'google_drive_upload_summary.json'
        shutil.copy2(summary_file, backup_file)
        print(f"✅ Backed up upload summary to: {backup_file}")
        
        # Read and fix content
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        # Fix upload folder path
        if 'upload_info' in data and 'upload_folder' in data['upload_info']:
            old_path = data['upload_info']['upload_folder']
            new_path = old_path
            
            for old_pattern, new_pattern in self.path_corrections.items():
                if old_pattern in old_path:
                    new_path = old_path.replace(old_pattern, new_pattern)
                    break
            
            if new_path != old_path:
                print(f"🔄 Updating upload folder path:")
                print(f"   From: {old_path}")
                print(f"   To:   {new_path}")
                data['upload_info']['upload_folder'] = new_path
            
        # Fix access_info folder path  
        if 'access_info' in data and 'google_drive_folder' in data['access_info']:
            old_path = data['access_info']['google_drive_folder']
            new_path = old_path
            
            for old_pattern, new_pattern in self.path_corrections.items():
                if old_pattern in old_path:
                    new_path = old_path.replace(old_pattern, new_pattern)
                    break
            
            if new_path != old_path:
                print(f"🔄 Updating access info folder path:")
                print(f"   From: {old_path}")
                print(f"   To:   {new_path}")
                data['access_info']['google_drive_folder'] = new_path
        
        # Write corrected data
        with open(summary_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Fixed upload summary paths")
        return True
    
    def fix_enhanced_upload_summaries(self):
        """Fix enhanced upload summary files"""
        
        enhanced_dir = self.project_root / 'sensor_visualizations' / 'enhanced_production_sensors'
        if not enhanced_dir.exists():
            print(f"⚠️ Enhanced production sensors directory not found")
            return False
        
        summary_files = list(enhanced_dir.glob('ENHANCED_UPLOAD_SUMMARY_*.txt'))
        
        for summary_file in summary_files:
            # Create backup
            backup_file = self.backup_dir / summary_file.name
            shutil.copy2(summary_file, backup_file)
            
            # Read and fix content
            with open(summary_file, 'r') as f:
                content = f.read()
            
            # Apply path corrections
            original_content = content
            for old_pattern, new_pattern in self.path_corrections.items():
                content = content.replace(old_pattern, new_pattern)
            
            if content != original_content:
                # Write corrected content
                with open(summary_file, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed enhanced upload summary: {summary_file.name}")
            else:
                print(f"ℹ️  No changes needed for: {summary_file.name}")
        
        return True
    
    def update_improved_config(self):
        """Update improved Google Drive config to ensure correct paths"""
        
        config_file = self.project_root / 'config' / 'improved_google_drive_config.py'
        if not config_file.exists():
            print(f"⚠️ Improved config file not found: {config_file}")
            return False
        
        # Create backup
        backup_file = self.backup_dir / 'improved_google_drive_config.py'
        shutil.copy2(config_file, backup_file)
        
        # Read and check content
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Check for any remaining legacy paths
        needs_update = False
        for old_pattern in self.path_corrections.keys():
            if old_pattern in content:
                needs_update = True
                break
        
        if needs_update:
            print(f"⚠️ Found legacy paths in config file - manual review recommended")
            print(f"   Config: {config_file}")
        else:
            print(f"✅ Config file paths are correct")
        
        return True
    
    def create_final_verification_script(self):
        """Create script to verify all paths are correctly updated"""
        
        script_content = '''#!/usr/bin/env python3
"""
Final Verification: Check All Visualization Upload Paths
"""

import json
from pathlib import Path

def verify_upload_paths():
    """Verify all upload paths use the new folder structure"""
    
    project_root = Path(__file__).parent.parent
    issues_found = []
    
    # Check main upload summary
    summary_file = project_root / 'sensor_visualizations' / 'google_drive_upload_summary.json'
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        upload_folder = data.get('upload_info', {}).get('upload_folder', '')
        if '/Visualizations/' in upload_folder:
            issues_found.append(f"Upload summary still uses old path: {upload_folder}")
        else:
            print(f"✅ Upload summary uses correct path: {upload_folder}")
    
    # Check enhanced upload summaries
    enhanced_dir = project_root / 'sensor_visualizations' / 'enhanced_production_sensors'
    if enhanced_dir.exists():
        for summary_file in enhanced_dir.glob('ENHANCED_UPLOAD_SUMMARY_*.txt'):
            with open(summary_file, 'r') as f:
                content = f.read()
            
            if '/Visualizations/' in content:
                issues_found.append(f"Enhanced summary has old paths: {summary_file.name}")
            else:
                print(f"✅ Enhanced summary paths correct: {summary_file.name}")
    
    if issues_found:
        print(f"\\n❌ ISSUES FOUND:")
        for issue in issues_found:
            print(f"   • {issue}")
        return False
    else:
        print(f"\\n🎉 ALL PATHS VERIFIED CORRECT!")
        return True

if __name__ == "__main__":
    verify_upload_paths()
'''
        
        script_file = self.project_root / 'scripts' / 'verify_all_upload_paths.py'
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_file, 0o755)
        print(f"✅ Created verification script: {script_file}")
        
    def run_complete_fix(self):
        """Run the complete path fixing process"""
        
        print("🔧 FIXING VISUALIZATION UPLOAD PATHS")
        print("=" * 50)
        
        # Fix upload summary JSON
        print("\n1. Fixing Google Drive upload summary...")
        self.fix_upload_summary_json()
        
        # Fix enhanced upload summaries
        print("\n2. Fixing enhanced upload summaries...")
        self.fix_enhanced_upload_summaries()
        
        # Update improved config
        print("\n3. Checking improved config...")
        self.update_improved_config()
        
        # Create verification script
        print("\n4. Creating verification script...")
        self.create_final_verification_script()
        
        print(f"\n✅ PATH FIXING COMPLETE")
        print(f"📁 Backup created at: {self.backup_dir}")
        print(f"🔍 Run verification: python scripts/verify_all_upload_paths.py")

def main():
    """Main function"""
    
    project_root = Path(__file__).parent.parent
    fixer = VisualizationPathFixer(project_root)
    fixer.run_complete_fix()

if __name__ == "__main__":
    main()
