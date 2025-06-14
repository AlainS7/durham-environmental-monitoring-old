#!/usr/bin/env python3
"""
Configuration Update Utility for Hot Durham Project Organization

This script updates existing configuration files to use the new organized path structure.
It ensures backward compatibility while adopting the new organization.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src" / "config"))

try:
    from paths import (
        PROJECT_ROOT, DATA_ROOT, RAW_DATA_PATH, PROCESSED_DATA_PATH,
        MASTER_DATA_PATH, LOG_ROOT, CONFIG_ROOT, BACKUP_ROOT,
        get_data_path, get_log_path, get_config_path
    )
except ImportError:
    print("Warning: Could not import path configuration. Using fallback paths.")
    PROJECT_ROOT = Path(__file__).parent.parent
    CONFIG_ROOT = PROJECT_ROOT / "config"


class ConfigurationUpdater:
    """Updates configuration files for the new project organization."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.config_root = self.project_root / "config"
        self.backup_dir = self.project_root / "backup" / "configurations" / f"pre_organization_{self._get_timestamp()}"
        self.changes_log = []
        
    def _get_timestamp(self) -> str:
        """Get current timestamp for backup naming."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _log_change(self, config_file: str, change: str):
        """Log a configuration change."""
        self.changes_log.append(f"{config_file}: {change}")
        print(f"✅ {config_file}: {change}")
    
    def backup_configurations(self) -> bool:
        """Backup all configuration files before updating."""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            config_files = list(self.config_root.glob("*.json"))
            config_files.extend(list(self.config_root.glob("*.py")))
            
            for config_file in config_files:
                if config_file.is_file():
                    backup_file = self.backup_dir / config_file.name
                    shutil.copy2(config_file, backup_file)
            
            print(f"✅ Backed up {len(config_files)} configuration files to: {self.backup_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Error backing up configurations: {e}")
            return False
    
    def update_master_data_config(self) -> bool:
        """Update master data configuration with new paths."""
        config_file = self.config_root / "master_data_config.json"
        
        if not config_file.exists():
            print(f"⚠️  Master data config not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update path configurations
            if 'paths' not in config:
                config['paths'] = {}
            
            # Update with new organized paths
            path_updates = {
                'raw_data_root': 'data/raw',
                'processed_data_root': 'data/processed',
                'master_data_root': 'data/master/historical',
                'temp_data_root': 'data/temp',
                'backup_root': 'backup/automated/daily',
                'log_root': 'logs/application/data_collection',
                'wu_production_path': 'data/raw/wu/production',
                'wu_test_path': 'data/raw/wu/test',
                'tsi_production_path': 'data/raw/tsi/production',
                'tsi_test_path': 'data/raw/tsi/test'
            }
            
            config['paths'].update(path_updates)
            
            # Update Google Drive folder structure
            if 'google_drive' in config:
                drive_updates = {
                    'master_folder': 'HotDurham/Data/Master',
                    'backup_folder': 'HotDurham/Backup/MasterData',
                    'export_folder': 'HotDurham/Data/Exports'
                }
                config['google_drive'].update(drive_updates)
            
            # Write updated configuration
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self._log_change("master_data_config.json", "Updated paths and Google Drive structure")
            return True
            
        except Exception as e:
            print(f"❌ Error updating master data config: {e}")
            return False
    
    def update_api_config(self) -> bool:
        """Update API configuration with new paths."""
        config_file = self.config_root / "public_api_config.json"
        
        if not config_file.exists():
            print(f"⚠️  API config not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update data source paths
            if 'data_sources' in config:
                for source_name, source_config in config['data_sources'].items():
                    if 'file_path' in source_config:
                        old_path = source_config['file_path']
                        # Convert old paths to new structure
                        if 'raw_pulls' in old_path:
                            new_path = old_path.replace('raw_pulls', 'data/raw')
                        elif 'processed' in old_path and not old_path.startswith('data/'):
                            new_path = old_path.replace('processed', 'data/processed')
                        else:
                            new_path = old_path
                        
                        source_config['file_path'] = new_path
                        
                        if old_path != new_path:
                            self._log_change("public_api_config.json", f"Updated {source_name} path: {old_path} → {new_path}")
            
            # Update logging configuration
            if 'logging' not in config:
                config['logging'] = {}
            
            config['logging'].update({
                'log_file': 'logs/application/api/public_api.log',
                'error_log': 'logs/application/api/api_errors.log',
                'access_log': 'logs/application/api/api_access.log'
            })
            
            # Write updated configuration
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self._log_change("public_api_config.json", "Updated data source paths and logging configuration")
            return True
            
        except Exception as e:
            print(f"❌ Error updating API config: {e}")
            return False
    
    def update_alert_system_config(self) -> bool:
        """Update alert system configuration."""
        config_file = self.config_root / "alert_system_config.json"
        
        if not config_file.exists():
            print(f"⚠️  Alert system config not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update paths
            path_updates = {
                'data_source_path': 'data/raw',
                'model_path': 'data/processed/ml/models',
                'log_path': 'logs/application/ml/anomaly_detection.log',
                'output_path': 'data/processed/analytics/alerts'
            }
            
            for key, new_path in path_updates.items():
                if key in config:
                    old_path = config[key]
                    config[key] = new_path
                    if old_path != new_path:
                        self._log_change("alert_system_config.json", f"Updated {key}: {old_path} → {new_path}")
            
            # Write updated configuration
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating alert system config: {e}")
            return False
    
    def update_production_pdf_config(self) -> bool:
        """Update production PDF configuration."""
        config_file = self.config_root / "production_pdf_config.json"
        
        if not config_file.exists():
            print(f"⚠️  Production PDF config not found: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update paths
            if 'paths' not in config:
                config['paths'] = {}
            
            path_updates = {
                'data_source': 'data/raw',
                'output_directory': 'data/processed/reports/daily',
                'template_directory': 'templates',
                'log_file': 'logs/application/automation/pdf_generation.log',
                'backup_directory': 'backup/automated/daily'
            }
            
            config['paths'].update(path_updates)
            
            # Write updated configuration
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            self._log_change("production_pdf_config.json", "Updated paths configuration")
            return True
            
        except Exception as e:
            print(f"❌ Error updating production PDF config: {e}")
            return False
    
    def update_test_sensor_config(self) -> bool:
        """Update test sensor configuration."""
        config_file = self.config_root / "test_sensors_config.py"
        
        if not config_file.exists():
            print(f"⚠️  Test sensor config not found: {config_file}")
            return False
        
        try:
            # Read the configuration file
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Update path references
            path_replacements = [
                ('test_data/sensors', 'data/raw'),
                ('test_data/logs', 'logs/application/data_collection'),
                ('test_data/backup', 'backup/automated/daily'),
                ('raw_pulls', 'data/raw')
            ]
            
            updated_content = content
            changes_made = []
            
            for old_path, new_path in path_replacements:
                if old_path in updated_content:
                    updated_content = updated_content.replace(old_path, new_path)
                    changes_made.append(f"{old_path} → {new_path}")
            
            if changes_made:
                # Write updated configuration
                with open(config_file, 'w') as f:
                    f.write(updated_content)
                
                self._log_change("test_sensors_config.py", f"Updated paths: {', '.join(changes_made)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating test sensor config: {e}")
            return False
    
    def create_environment_configs(self) -> bool:
        """Create environment-specific configurations."""
        try:
            environments = ['development', 'testing', 'production']
            
            for env in environments:
                env_dir = self.config_root / "environments" / env
                env_dir.mkdir(parents=True, exist_ok=True)
                
                # Create environment-specific configuration
                env_config = {
                    "environment": env,
                    "data_paths": {
                        "raw_data": f"data/raw",
                        "processed_data": f"data/processed",
                        "temp_data": f"data/temp"
                    },
                    "logging": {
                        "level": "DEBUG" if env == "development" else "INFO",
                        "log_file": f"logs/application/{env}.log"
                    },
                    "backup": {
                        "enabled": True,
                        "frequency": "daily" if env == "production" else "weekly"
                    }
                }
                
                env_config_file = env_dir / "config.json"
                with open(env_config_file, 'w') as f:
                    json.dump(env_config, f, indent=2)
                
                self._log_change(f"environments/{env}/config.json", "Created environment-specific configuration")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating environment configs: {e}")
            return False
    
    def create_base_configs(self) -> bool:
        """Create base configuration files."""
        try:
            base_dir = self.config_root / "base"
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Create paths configuration
            paths_config = {
                "project_root": str(self.project_root),
                "data_paths": {
                    "raw_data": "data/raw",
                    "processed_data": "data/processed",
                    "master_data": "data/master",
                    "temp_data": "data/temp"
                },
                "log_paths": {
                    "application_logs": "logs/application",
                    "system_logs": "logs/system",
                    "scheduler_logs": "logs/scheduler",
                    "archived_logs": "logs/archive"
                },
                "backup_paths": {
                    "automated_backups": "backup/automated",
                    "manual_backups": "backup/manual",
                    "config_backups": "backup/configurations"
                }
            }
            
            with open(base_dir / "paths.json", 'w') as f:
                json.dump(paths_config, f, indent=2)
            
            # Create logging configuration
            logging_config = {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "standard": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    },
                    "detailed": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
                    }
                },
                "handlers": {
                    "file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "filename": "logs/application/app.log",
                        "maxBytes": 10485760,
                        "backupCount": 5,
                        "formatter": "standard"
                    },
                    "error_file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "filename": "logs/application/errors.log",
                        "maxBytes": 10485760,
                        "backupCount": 5,
                        "formatter": "detailed",
                        "level": "ERROR"
                    }
                },
                "loggers": {
                    "hot_durham": {
                        "handlers": ["file", "error_file"],
                        "level": "INFO",
                        "propagate": False
                    }
                }
            }
            
            with open(base_dir / "logging.json", 'w') as f:
                json.dump(logging_config, f, indent=2)
            
            self._log_change("base/paths.json", "Created base paths configuration")
            self._log_change("base/logging.json", "Created base logging configuration")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating base configs: {e}")
            return False
    
    def generate_migration_report(self) -> bool:
        """Generate a report of all configuration changes."""
        try:
            report_file = self.project_root / "CONFIG_MIGRATION_REPORT.md"
            
            report_content = f"""# Configuration Migration Report

**Migration Date:** {self._get_timestamp()}
**Backup Location:** `{self.backup_dir}`

## Summary
Updated Hot Durham project configurations to use the new organized path structure.

## Changes Made

"""
            
            for change in self.changes_log:
                report_content += f"- {change}\n"
            
            report_content += f"""

## Configuration Structure Created

```
config/
├── base/
│   ├── paths.json          # Centralized path definitions
│   └── logging.json        # Base logging configuration
├── environments/
│   ├── development/
│   ├── testing/
│   └── production/
├── features/               # Feature-specific configs
└── schemas/               # Configuration validation schemas
```

## Backup Information
- **Original configurations backed up to:** `{self.backup_dir}`
- **Total changes made:** {len(self.changes_log)}

## Next Steps
1. Test all systems with updated configurations
2. Verify data access with new paths
3. Monitor logs for any path-related issues
4. Update any hardcoded paths in custom scripts

## Rollback Instructions
If rollback is needed:
```bash
# Restore original configurations
cp -r "{self.backup_dir}/"* "{self.config_root}/"
```

---
*Report generated automatically by configuration update utility.*
"""
            
            with open(report_file, 'w') as f:
                f.write(report_content)
            
            print(f"✅ Migration report generated: {report_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating migration report: {e}")
            return False
    
    def run_full_update(self) -> bool:
        """Run the complete configuration update process."""
        print("🔧 Hot Durham Configuration Update Utility")
        print("=" * 50)
        print(f"Project Root: {self.project_root}")
        print(f"Config Root: {self.config_root}")
        print("")
        
        # Backup configurations
        if not self.backup_configurations():
            print("❌ Failed to backup configurations. Aborting.")
            return False
        
        print("")
        print("Updating configuration files...")
        
        # Update individual configuration files
        updates = [
            self.update_master_data_config,
            self.update_api_config,
            self.update_alert_system_config,
            self.update_production_pdf_config,
            self.update_test_sensor_config,
            self.create_base_configs,
            self.create_environment_configs
        ]
        
        success_count = 0
        for update_func in updates:
            try:
                if update_func():
                    success_count += 1
            except Exception as e:
                print(f"❌ Error in {update_func.__name__}: {e}")
        
        print("")
        print(f"Configuration update completed: {success_count}/{len(updates)} successful")
        
        # Generate report
        self.generate_migration_report()
        
        print("")
        print("🎉 Configuration update completed!")
        print(f"📋 See migration report for details")
        print(f"💾 Backup available at: {self.backup_dir}")
        
        return success_count == len(updates)


def main():
    """Main function for command-line usage."""
    updater = ConfigurationUpdater()
    
    # Check if running in interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Run automatically without prompts
        updater.run_full_update()
    else:
        # Interactive mode
        print("Hot Durham Configuration Update Utility")
        print("This will update all configuration files to use the new organized structure.")
        print("")
        
        response = input("Continue with configuration update? (y/N): ")
        if response.lower() in ['y', 'yes']:
            updater.run_full_update()
        else:
            print("Configuration update cancelled.")


if __name__ == "__main__":
    main()
