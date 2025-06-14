#!/usr/bin/env python3
"""
Git Ready Cleanup Script
Hot Durham Environmental Monitoring Project

This script cleans up the repository to make it git-ready by:
1. Consolidating redundant documentation
2. Organizing migration reports
3. Cleaning up temporary files
4. Archiving old test files
5. Removing unnecessary log files from root
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

class GitReadyCleanup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "backup" / f"git_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.cleaned_files = []
        self.moved_files = []
        self.removed_files = []
    
    def print_header(self, title):
        """Print formatted header."""
        print(f"\n{'='*60}")
        print(f"🧹 {title}")
        print(f"{'='*60}")
    
    def print_action(self, action, item):
        """Print action with icon."""
        icons = {
            'MOVED': '📁',
            'REMOVED': '🗑️',
            'CONSOLIDATED': '📋',
            'ARCHIVED': '📦',
            'CLEANED': '✨'
        }
        print(f"{icons.get(action, '•')} {action}: {item}")
    
    def backup_file(self, file_path):
        """Create backup of file or directory before cleanup."""
        if file_path.exists():
            relative_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path.is_dir():
                shutil.copytree(file_path, backup_path, dirs_exist_ok=True)
            else:
                shutil.copy2(file_path, backup_path)
    
    def cleanup_redundant_migration_docs(self):
        """Clean up redundant migration documentation files."""
        self.print_header("MIGRATION DOCUMENTATION CLEANUP")
        
        # Migration docs to consolidate
        migration_docs = [
            "GOOGLE_DRIVE_IMPROVEMENTS_COMPLETE.md",
            "GOOGLE_DRIVE_MIGRATION_COMPLETE.md", 
            "GOOGLE_DRIVE_MIGRATION_FINAL_STATUS.md",
            "GOOGLE_DRIVE_MIGRATION_FINAL_SUMMARY.md",
            "GOOGLE_DRIVE_MIGRATION_SUCCESS.md",
            "GOOGLE_DRIVE_STRUCTURE_FINAL_STATUS.md"
        ]
        
        # Keep only the most comprehensive final report
        keep_file = "GOOGLE_DRIVE_MIGRATION_COMPLETE_FINAL.md"
        
        migration_archive = self.project_root / "docs" / "migration_archive"
        migration_archive.mkdir(exist_ok=True)
        
        for doc in migration_docs:
            doc_path = self.project_root / doc
            if doc_path.exists() and doc != keep_file:
                self.backup_file(doc_path)
                shutil.move(doc_path, migration_archive / doc)
                self.moved_files.append(f"{doc} -> docs/migration_archive/")
                self.print_action('MOVED', f"{doc} -> docs/migration_archive/")
        
        # Move the final report to docs
        final_report = self.project_root / keep_file
        if final_report.exists():
            docs_final_report = self.project_root / "docs" / keep_file
            if not docs_final_report.exists():
                shutil.move(final_report, docs_final_report)
                self.moved_files.append(f"{keep_file} -> docs/")
                self.print_action('MOVED', f"{keep_file} -> docs/")
    
    def cleanup_verification_files(self):
        """Clean up verification and status files."""
        self.print_header("VERIFICATION FILES CLEANUP")
        
        verification_files = [
            "SCRIPT_PATH_VALIDATION_COMPLETE.md",
            "SYSTEM_VERIFICATION_COMPLETE.md",
            "automation_verification_results.json",
            "final_migration_verification.json"
        ]
        
        verification_archive = self.project_root / "docs" / "verification_archive"
        verification_archive.mkdir(exist_ok=True)
        
        for file in verification_files:
            file_path = self.project_root / file
            if file_path.exists():
                self.backup_file(file_path)
                shutil.move(file_path, verification_archive / file)
                self.moved_files.append(f"{file} -> docs/verification_archive/")
                self.print_action('MOVED', f"{file} -> docs/verification_archive/")
    
    def cleanup_log_files(self):
        """Clean up log files from root directory."""
        self.print_header("LOG FILES CLEANUP")
        
        log_files = [
            "data_management.log",
            "master_data_system.log"
        ]
        
        logs_dir = self.project_root / "logs" / "application"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        for log_file in log_files:
            log_path = self.project_root / log_file
            if log_path.exists():
                self.backup_file(log_path)
                shutil.move(log_path, logs_dir / log_file)
                self.moved_files.append(f"{log_file} -> logs/application/")
                self.print_action('MOVED', f"{log_file} -> logs/application/")
    
    def cleanup_temporary_directories(self):
        """Clean up temporary and old directories."""
        self.print_header("TEMPORARY DIRECTORIES CLEANUP")
        
        temp_dirs = [
            "processed_old",
            "maintenance", 
            "ports",
            "processed",
            "processed_organized",
            "raw_pulls_organized",
            "quick_start"
        ]
        
        temp_archive = self.project_root / "archive" / "temp_cleanup"
        temp_archive.mkdir(parents=True, exist_ok=True)
        
        for temp_dir in temp_dirs:
            temp_path = self.project_root / temp_dir
            if temp_path.exists():
                if temp_path.is_dir():
                    # Check if directory has content
                    if any(temp_path.iterdir()):
                        self.backup_file(temp_path)
                        shutil.move(temp_path, temp_archive / temp_dir)
                        self.moved_files.append(f"{temp_dir}/ -> archive/temp_cleanup/")
                        self.print_action('MOVED', f"{temp_dir}/ -> archive/temp_cleanup/")
                    else:
                        temp_path.rmdir()
                        self.removed_files.append(f"{temp_dir}/ (empty)")
                        self.print_action('REMOVED', f"{temp_dir}/ (empty)")
                else:
                    # It's a file
                    shutil.move(temp_path, temp_archive / temp_dir)
                    self.moved_files.append(f"{temp_dir} -> archive/temp_cleanup/")
                    self.print_action('MOVED', f"{temp_dir} -> archive/temp_cleanup/")
    
    def cleanup_old_scripts(self):
        """Clean up old cleanup scripts."""
        self.print_header("OLD SCRIPTS CLEANUP")
        
        old_scripts = [
            "cleanup_docs.sh",
            "validate_script_paths.sh"
        ]
        
        for script in old_scripts:
            script_path = self.project_root / script
            if script_path.exists():
                self.backup_file(script_path)
                archive_path = self.project_root / "archive" / "deprecated_scripts" / script
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(script_path, archive_path)
                self.moved_files.append(f"{script} -> archive/deprecated_scripts/")
                self.print_action('MOVED', f"{script} -> archive/deprecated_scripts/")
    
    def organize_docs_directory(self):
        """Organize the docs directory for better structure."""
        self.print_header("DOCS DIRECTORY ORGANIZATION")
        
        docs_dir = self.project_root / "docs"
        
        # Create organized structure
        categories = {
            "migration": ["GOOGLE_DRIVE_MIGRATION", "migration"],
            "implementation": ["IMPLEMENTATION", "COMPLETE"],
            "guides": ["GUIDE", "README", "QUICK_START"],
            "planning": ["PLAN", "ROADMAP"],
            "reference": ["REFERENCE", "STATUS"]
        }
        
        for category, keywords in categories.items():
            category_dir = docs_dir / category
            category_dir.mkdir(exist_ok=True)
            
            # Move files that match keywords
            for doc_file in docs_dir.glob("*.md"):
                if doc_file.is_file():
                    filename_upper = doc_file.name.upper()
                    if any(keyword in filename_upper for keyword in keywords):
                        if not (category_dir / doc_file.name).exists():
                            shutil.move(doc_file, category_dir / doc_file.name)
                            self.moved_files.append(f"docs/{doc_file.name} -> docs/{category}/")
                            self.print_action('MOVED', f"docs/{doc_file.name} -> docs/{category}/")
    
    def create_clean_readme(self):
        """Create or update a clean README for the repository."""
        self.print_header("README ORGANIZATION") 
        
        readme_content = """# Hot Durham Environmental Monitoring System

A comprehensive environmental monitoring system for Durham, NC, featuring real-time data collection from Weather Underground and TSI air quality sensors.

## 🌟 Features

- **Real-time Data Collection**: Weather Underground and TSI sensor integration
- **Automated Reporting**: Daily, weekly, and monthly automated reports
- **Google Drive Integration**: Seamless cloud storage and sharing
- **Data Visualization**: Interactive charts and analysis tools
- **Master Data Management**: Historical data aggregation and management
- **Test Sensor Management**: Dedicated testing infrastructure

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Credentials**:
   - Add Google API credentials to `creds/google_creds.json`
   - Add Weather Underground API key to `creds/wu_api_key.json`
   - Add TSI credentials to `creds/tsi_creds.json`

3. **Run Data Collection**:
   ```bash
   python src/data_collection/faster_wu_tsi_to_sheets_async.py
   ```

## 📁 Project Structure

```
├── config/                 # Configuration files
├── src/                   # Source code
│   ├── core/              # Core functionality
│   ├── data_collection/   # Data collection scripts
│   └── automation/        # Automation systems
├── data/                  # Data storage
├── docs/                  # Documentation
├── tests/                 # Test files
└── scripts/               # Utility scripts
```

## 🛠️ System Components

### Data Collection
- **Weather Underground**: Meteorological data collection
- **TSI Sensors**: Air quality monitoring
- **Automated Scheduling**: Configurable data collection intervals

### Data Management
- **Master Data System**: Historical data aggregation
- **Google Drive Sync**: Cloud backup and sharing
- **Test Data Isolation**: Separate handling of test vs production data

### Automation
- **Daily Sheets**: Automated daily reports
- **Master Data Updates**: Weekly data consolidation
- **Alert System**: Anomaly detection and notifications

## 📊 Data Flow

1. **Collection**: Sensors → Raw Data
2. **Processing**: Raw Data → Processed Data
3. **Storage**: Processed Data → Master Files
4. **Reporting**: Master Files → Visualizations & Reports
5. **Distribution**: Reports → Google Drive & Dashboard

## 🔧 Configuration

Main configuration files:
- `config/improved_google_drive_config.py` - Google Drive paths
- `config/test_sensors_config.py` - Test sensor management
- `config/master_data_config.json` - Master data system settings

## 📋 Maintenance

- **Daily**: Automated data collection and basic reporting
- **Weekly**: Master data updates and system health checks
- **Monthly**: Comprehensive system verification and cleanup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions or support, please check the documentation in the `docs/` directory or create an issue in the repository.

---

*Last updated: June 2025*
"""
        
        readme_path = self.project_root / "README.md"
        
        # Backup existing README if it exists
        if readme_path.exists():
            self.backup_file(readme_path)
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        self.print_action('CLEANED', "README.md updated with comprehensive project overview")
    
    def create_cleanup_summary(self):
        """Create a summary of cleanup actions."""
        summary = {
            "cleanup_date": datetime.now().isoformat(),
            "backup_location": str(self.backup_dir.relative_to(self.project_root)),
            "actions_taken": {
                "files_moved": len(self.moved_files),
                "files_removed": len(self.removed_files),
                "files_cleaned": len(self.cleaned_files)
            },
            "moved_files": self.moved_files,
            "removed_files": self.removed_files,
            "cleaned_files": self.cleaned_files
        }
        
        summary_file = self.project_root / "cleanup_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def run_cleanup(self):
        """Run the complete cleanup process."""
        print(f"🧹 Starting Git Ready Cleanup")
        print(f"📦 Backup directory: {self.backup_dir.relative_to(self.project_root)}")
        
        # Run cleanup steps
        self.cleanup_redundant_migration_docs()
        self.cleanup_verification_files()
        self.cleanup_log_files()
        self.cleanup_temporary_directories()
        self.cleanup_old_scripts()
        self.organize_docs_directory()
        self.create_clean_readme()
        
        # Create summary
        summary = self.create_cleanup_summary()
        
        # Final summary
        self.print_header("CLEANUP SUMMARY")
        print(f"✅ Files moved: {summary['actions_taken']['files_moved']}")
        print(f"✅ Files removed: {summary['actions_taken']['files_removed']}")
        print(f"✅ Files cleaned: {summary['actions_taken']['files_cleaned']}")
        print(f"📦 Backup created: {summary['backup_location']}")
        print(f"📋 Summary saved: cleanup_summary.json")
        
        print(f"\n🎉 Repository is now git-ready!")
        print(f"💡 Next steps:")
        print(f"   1. Review changes: git status")
        print(f"   2. Add files: git add .")
        print(f"   3. Commit: git commit -m 'Clean up repository for production'")
        print(f"   4. Push: git push")

def main():
    """Main cleanup function."""
    cleanup = GitReadyCleanup()
    cleanup.run_cleanup()

if __name__ == "__main__":
    main()
