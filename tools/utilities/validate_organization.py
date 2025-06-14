#!/usr/bin/env python3
"""
Project Organization Validation Script

This script validates the Hot Durham project organization implementation,
ensuring all paths work correctly and systems can find their data.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import importlib.util

# Add project paths
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src" / "config"))
sys.path.append(str(project_root / "src" / "core"))

class OrganizationValidator:
    """Validates the project organization implementation."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent
        self.validation_results = {}
        self.errors = []
        self.warnings = []
        
    def log_error(self, message: str):
        """Log an error."""
        self.errors.append(message)
        print(f"❌ ERROR: {message}")
    
    def log_warning(self, message: str):
        """Log a warning."""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
    
    def log_success(self, message: str):
        """Log a success."""
        print(f"✅ {message}")
    
    def validate_directory_structure(self) -> bool:
        """Validate that the new directory structure exists."""
        print("\n📁 Validating Directory Structure")
        print("-" * 40)
        
        required_directories = [
            # Data directories
            "data/raw/wu/production/2024",
            "data/raw/wu/production/2025",
            "data/raw/wu/test/2024",
            "data/raw/wu/test/2025",
            "data/raw/tsi/production/2024",
            "data/raw/tsi/production/2025",
            "data/raw/tsi/test/2024",
            "data/raw/tsi/test/2025",
            "data/processed/ml/models",
            "data/processed/ml/predictions",
            "data/processed/ml/metrics",
            "data/processed/reports/daily",
            "data/processed/reports/weekly",
            "data/processed/reports/monthly",
            "data/processed/reports/annual",
            "data/processed/analytics",
            "data/master/historical",
            "data/master/combined",
            "data/master/metadata",
            "data/temp/downloads",
            "data/temp/processing",
            "data/temp/uploads",
            
            # Log directories
            "logs/application/data_collection",
            "logs/application/api",
            "logs/application/ml",
            "logs/application/automation",
            "logs/system/backup",
            "logs/system/monitoring",
            "logs/system/security",
            "logs/scheduler/daily",
            "logs/scheduler/weekly",
            "logs/scheduler/monthly",
            "logs/archive/2024",
            "logs/archive/2025",
            
            # Backup directories
            "backup/automated/daily",
            "backup/automated/weekly",
            "backup/automated/monthly",
            "backup/manual",
            "backup/configurations",
            "backup/credentials",
            
            # Archive directories
            "archive/deprecated/scripts",
            "archive/deprecated/configs",
            "archive/deprecated/docs",
            "archive/historical/versions",
            "archive/historical/migrations",
            "archive/removed",
            
            # Configuration directories
            "config/base",
            "config/environments/development",
            "config/environments/testing",
            "config/environments/production",
            "config/features/ml",
            "config/features/api",
            "config/features/automation",
            "config/schemas"
        ]
        
        missing_directories = []
        existing_directories = []
        
        for directory in required_directories:
            dir_path = self.project_root / directory
            if dir_path.exists():
                existing_directories.append(directory)
            else:
                missing_directories.append(directory)
        
        # Report results
        self.log_success(f"Found {len(existing_directories)} of {len(required_directories)} required directories")
        
        if missing_directories:
            self.log_warning(f"Missing {len(missing_directories)} directories:")
            for missing_dir in missing_directories[:10]:  # Show first 10
                self.log_warning(f"  - {missing_dir}")
            if len(missing_directories) > 10:
                self.log_warning(f"  ... and {len(missing_directories) - 10} more")
        
        self.validation_results['directory_structure'] = {
            'total_required': len(required_directories),
            'existing': len(existing_directories),
            'missing': len(missing_directories),
            'success': len(missing_directories) == 0
        }
        
        return len(missing_directories) == 0
    
    def validate_path_configuration(self) -> bool:
        """Validate the centralized path configuration."""
        print("\n🔧 Validating Path Configuration")
        print("-" * 40)
        
        try:
            # Try to import the path configuration
            spec = importlib.util.spec_from_file_location(
                "paths", 
                self.project_root / "src" / "config" / "paths.py"
            )
            if spec is None:
                self.log_error("Could not load path configuration module")
                return False
            
            paths_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(paths_module)
            
            # Test key path functions
            test_cases = [
                ("Raw WU Production Path", lambda: paths_module.get_data_path("raw", "wu", "production", "2025")),
                ("Raw TSI Test Path", lambda: paths_module.get_data_path("raw", "tsi", "test", "2024")),
                ("Processed Data Path", lambda: paths_module.get_data_path("processed")),
                ("Application Log Path", lambda: paths_module.get_log_path("application")),
                ("ML Log Path", lambda: paths_module.get_log_path("application", "ml")),
                ("Production Config Path", lambda: paths_module.get_config_path("environments", "production")),
                ("Daily Backup Path", lambda: paths_module.get_backup_path("automated", "daily")),
            ]
            
            successful_tests = 0
            for test_name, test_func in test_cases:
                try:
                    result_path = test_func()
                    if isinstance(result_path, Path):
                        self.log_success(f"{test_name}: {result_path}")
                        successful_tests += 1
                    else:
                        self.log_error(f"{test_name}: Returned invalid type {type(result_path)}")
                except Exception as e:
                    self.log_error(f"{test_name}: {str(e)}")
            
            # Test validation function
            try:
                validation_results = paths_module.validate_paths()
                valid_paths = sum(1 for v in validation_results.values() if v)
                total_paths = len(validation_results)
                self.log_success(f"Path validation: {valid_paths}/{total_paths} paths valid")
            except Exception as e:
                self.log_error(f"Path validation function failed: {e}")
            
            self.validation_results['path_configuration'] = {
                'total_tests': len(test_cases),
                'successful_tests': successful_tests,
                'success': successful_tests == len(test_cases)
            }
            
            return successful_tests == len(test_cases)
            
        except Exception as e:
            self.log_error(f"Failed to validate path configuration: {e}")
            return False
    
    def validate_configuration_files(self) -> bool:
        """Validate that configuration files were updated correctly."""
        print("\n⚙️  Validating Configuration Files")
        print("-" * 40)
        
        config_files_to_check = [
            "master_data_config.json",
            "public_api_config.json",
            "alert_system_config.json",
            "production_pdf_config.json",
            "base/paths.json",
            "base/logging.json"
        ]
        
        valid_configs = 0
        
        for config_file in config_files_to_check:
            config_path = self.project_root / "config" / config_file
            
            if not config_path.exists():
                self.log_warning(f"Configuration file not found: {config_file}")
                continue
            
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Check if it contains new path structure
                config_str = json.dumps(config_data)
                has_new_paths = any(new_path in config_str for new_path in [
                    "data/raw", "data/processed", "data/master", "logs/application"
                ])
                
                if has_new_paths:
                    self.log_success(f"Configuration updated: {config_file}")
                    valid_configs += 1
                else:
                    self.log_warning(f"Configuration may not be updated: {config_file}")
                
            except json.JSONDecodeError as e:
                self.log_error(f"Invalid JSON in {config_file}: {e}")
            except Exception as e:
                self.log_error(f"Error reading {config_file}: {e}")
        
        self.validation_results['configuration_files'] = {
            'total_files': len(config_files_to_check),
            'valid_files': valid_configs,
            'success': valid_configs >= len(config_files_to_check) * 0.8  # 80% success rate
        }
        
        return valid_configs >= len(config_files_to_check) * 0.8
    
    def validate_data_migration(self) -> bool:
        """Validate that data files were migrated correctly."""
        print("\n📊 Validating Data Migration")
        print("-" * 40)
        
        # Check for migrated data files
        data_locations = {
            "Raw WU Production": self.project_root / "data" / "raw" / "wu" / "production",
            "Raw TSI Production": self.project_root / "data" / "raw" / "tsi" / "production",
            "Raw WU Test": self.project_root / "data" / "raw" / "wu" / "test",
            "Raw TSI Test": self.project_root / "data" / "raw" / "tsi" / "test",
            "Processed Data": self.project_root / "data" / "processed",
            "Master Data": self.project_root / "data" / "master"
        }
        
        data_found = {}
        total_files = 0
        
        for location_name, location_path in data_locations.items():
            if location_path.exists():
                file_count = len(list(location_path.rglob("*.csv")))
                file_count += len(list(location_path.rglob("*.json")))
                file_count += len(list(location_path.rglob("*.xlsx")))
                
                data_found[location_name] = file_count
                total_files += file_count
                
                if file_count > 0:
                    self.log_success(f"{location_name}: {file_count} files")
                else:
                    self.log_warning(f"{location_name}: No data files found")
            else:
                data_found[location_name] = 0
                self.log_warning(f"{location_name}: Directory not found")
        
        # Check for legacy directories (should still exist as symlinks)
        legacy_paths = {
            "raw_pulls": self.project_root / "raw_pulls",
            "processed": self.project_root / "processed"
        }
        
        legacy_status = {}
        for legacy_name, legacy_path in legacy_paths.items():
            if legacy_path.exists():
                if legacy_path.is_symlink():
                    self.log_success(f"Legacy compatibility: {legacy_name} → {legacy_path.readlink()}")
                    legacy_status[legacy_name] = "symlink"
                else:
                    self.log_warning(f"Legacy directory exists but is not a symlink: {legacy_name}")
                    legacy_status[legacy_name] = "directory"
            else:
                self.log_warning(f"Legacy compatibility missing: {legacy_name}")
                legacy_status[legacy_name] = "missing"
        
        self.validation_results['data_migration'] = {
            'total_files': total_files,
            'locations_with_data': sum(1 for count in data_found.values() if count > 0),
            'total_locations': len(data_locations),
            'legacy_compatibility': legacy_status,
            'success': total_files > 0 and sum(1 for count in data_found.values() if count > 0) > 0
        }
        
        return total_files > 0
    
    def validate_system_imports(self) -> bool:
        """Validate that key system modules can still import correctly."""
        print("\n🐍 Validating System Imports")
        print("-" * 40)
        
        modules_to_test = [
            ("Data Manager", "src.core.data_manager", "DataManager"),
            ("Backup System", "src.core.backup_system", "BackupSystem"),
            ("Master Data System", "src.automation.master_data_file_system", "MasterDataFileSystem"),
            ("API System", "src.api.public_api", None),
            ("ML System", "src.ml.predictive_analytics", None)
        ]
        
        successful_imports = 0
        
        for module_name, module_path, class_name in modules_to_test:
            try:
                # Add src directory to path
                src_path = str(self.project_root / "src")
                if src_path not in sys.path:
                    sys.path.insert(0, src_path)
                
                # Try to import the module
                module = importlib.import_module(module_path)
                
                if class_name:
                    # Try to get the specific class
                    cls = getattr(module, class_name)
                    self.log_success(f"Import successful: {module_name} ({class_name})")
                else:
                    self.log_success(f"Import successful: {module_name}")
                
                successful_imports += 1
                
            except ImportError as e:
                self.log_error(f"Import failed: {module_name} - {e}")
            except AttributeError as e:
                self.log_error(f"Class not found: {module_name}.{class_name} - {e}")
            except Exception as e:
                self.log_error(f"Unexpected error importing {module_name}: {e}")
        
        self.validation_results['system_imports'] = {
            'total_modules': len(modules_to_test),
            'successful_imports': successful_imports,
            'success': successful_imports >= len(modules_to_test) * 0.8
        }
        
        return successful_imports >= len(modules_to_test) * 0.8
    
    def validate_api_functionality(self) -> bool:
        """Validate that the API system can find its data sources."""
        print("\n🌐 Validating API Functionality")
        print("-" * 40)
        
        try:
            # Check if API configuration exists and is valid
            api_config_path = self.project_root / "config" / "public_api_config.json"
            
            if not api_config_path.exists():
                self.log_warning("API configuration file not found")
                return False
            
            with open(api_config_path, 'r') as f:
                api_config = json.load(f)
            
            # Check data sources in configuration
            data_sources_valid = 0
            total_data_sources = 0
            
            if 'data_sources' in api_config:
                for source_name, source_config in api_config['data_sources'].items():
                    total_data_sources += 1
                    
                    if 'file_path' in source_config:
                        file_path = self.project_root / source_config['file_path']
                        if file_path.exists() or file_path.parent.exists():
                            self.log_success(f"API data source accessible: {source_name}")
                            data_sources_valid += 1
                        else:
                            self.log_warning(f"API data source path not found: {source_name} ({source_config['file_path']})")
                    else:
                        self.log_warning(f"API data source missing file_path: {source_name}")
            
            # Check if API can be started (basic test)
            api_test_successful = False
            try:
                # Test if we can import the API module
                sys.path.insert(0, str(self.project_root / "src"))
                import src.api.public_api
                self.log_success("API module imports successfully")
                api_test_successful = True
            except Exception as e:
                self.log_error(f"API module import failed: {e}")
            
            self.validation_results['api_functionality'] = {
                'data_sources_total': total_data_sources,
                'data_sources_valid': data_sources_valid,
                'api_import_successful': api_test_successful,
                'success': data_sources_valid > 0 and api_test_successful
            }
            
            return data_sources_valid > 0 and api_test_successful
            
        except Exception as e:
            self.log_error(f"API validation failed: {e}")
            return False
    
    def validate_logging_system(self) -> bool:
        """Validate that the logging system works with new paths."""
        print("\n📝 Validating Logging System")
        print("-" * 40)
        
        try:
            import logging
            import logging.config
            
            # Check if base logging config exists
            logging_config_path = self.project_root / "config" / "base" / "logging.json"
            
            if logging_config_path.exists():
                with open(logging_config_path, 'r') as f:
                    logging_config = json.load(f)
                
                # Test if logging configuration is valid
                try:
                    logging.config.dictConfig(logging_config)
                    self.log_success("Logging configuration is valid")
                    logging_config_valid = True
                except Exception as e:
                    self.log_error(f"Logging configuration invalid: {e}")
                    logging_config_valid = False
            else:
                self.log_warning("Base logging configuration not found")
                logging_config_valid = False
            
            # Check if log directories exist
            log_dirs = [
                "logs/application",
                "logs/system",
                "logs/scheduler"
            ]
            
            log_dirs_exist = 0
            for log_dir in log_dirs:
                log_path = self.project_root / log_dir
                if log_path.exists():
                    self.log_success(f"Log directory exists: {log_dir}")
                    log_dirs_exist += 1
                else:
                    self.log_warning(f"Log directory missing: {log_dir}")
            
            # Test basic logging
            test_log_successful = False
            try:
                test_log_path = self.project_root / "logs" / "application" / "validation_test.log"
                test_log_path.parent.mkdir(parents=True, exist_ok=True)
                
                test_logger = logging.getLogger("validation_test")
                handler = logging.FileHandler(test_log_path)
                test_logger.addHandler(handler)
                test_logger.setLevel(logging.INFO)
                
                test_logger.info("Organization validation test log entry")
                
                if test_log_path.exists() and test_log_path.stat().st_size > 0:
                    self.log_success("Test logging successful")
                    test_log_successful = True
                    # Clean up test log
                    test_log_path.unlink()
                else:
                    self.log_warning("Test logging failed - no output")
                    
            except Exception as e:
                self.log_error(f"Test logging failed: {e}")
            
            self.validation_results['logging_system'] = {
                'config_valid': logging_config_valid,
                'log_dirs_exist': log_dirs_exist,
                'total_log_dirs': len(log_dirs),
                'test_logging_successful': test_log_successful,
                'success': logging_config_valid and log_dirs_exist > 0 and test_log_successful
            }
            
            return logging_config_valid and log_dirs_exist > 0
            
        except Exception as e:
            self.log_error(f"Logging system validation failed: {e}")
            return False
    
    def generate_validation_report(self) -> str:
        """Generate a comprehensive validation report."""
        print("\n📋 Generating Validation Report")
        print("-" * 40)
        
        report_path = self.project_root / "ORGANIZATION_VALIDATION_REPORT.md"
        
        # Calculate overall success rate
        total_tests = len(self.validation_results)
        successful_tests = sum(1 for result in self.validation_results.values() if result.get('success', False))
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Determine overall status
        if success_rate >= 90:
            overall_status = "✅ EXCELLENT"
        elif success_rate >= 75:
            overall_status = "🟡 GOOD"
        elif success_rate >= 50:
            overall_status = "🟠 NEEDS ATTENTION"
        else:
            overall_status = "❌ CRITICAL ISSUES"
        
        report_content = f"""# Hot Durham Project Organization Validation Report

**Validation Date:** {self._get_timestamp()}
**Overall Status:** {overall_status}
**Success Rate:** {success_rate:.1f}% ({successful_tests}/{total_tests} tests passed)

## Executive Summary

The Hot Durham project organization has been validated with the following results:

"""
        
        # Add test results
        for test_name, result in self.validation_results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            report_content += f"- **{test_name.replace('_', ' ').title()}:** {status}\n"
        
        report_content += f"""

## Detailed Results

"""
        
        # Add detailed results for each test
        for test_name, result in self.validation_results.items():
            report_content += f"""### {test_name.replace('_', ' ').title()}

**Status:** {'✅ PASS' if result.get('success', False) else '❌ FAIL'}

"""
            # Add specific metrics for each test type
            if test_name == 'directory_structure':
                report_content += f"""- Required directories: {result['total_required']}
- Existing directories: {result['existing']}
- Missing directories: {result['missing']}

"""
            elif test_name == 'path_configuration':
                report_content += f"""- Total path tests: {result['total_tests']}
- Successful tests: {result['successful_tests']}

"""
            elif test_name == 'configuration_files':
                report_content += f"""- Total configuration files: {result['total_files']}
- Valid configuration files: {result['valid_files']}

"""
            elif test_name == 'data_migration':
                report_content += f"""- Total migrated files: {result['total_files']}
- Locations with data: {result['locations_with_data']}/{result['total_locations']}

"""
            elif test_name == 'system_imports':
                report_content += f"""- Total modules tested: {result['total_modules']}
- Successful imports: {result['successful_imports']}

"""
            elif test_name == 'api_functionality':
                report_content += f"""- Total data sources: {result['data_sources_total']}
- Valid data sources: {result['data_sources_valid']}
- API import successful: {result['api_import_successful']}

"""
            elif test_name == 'logging_system':
                report_content += f"""- Configuration valid: {result['config_valid']}
- Log directories exist: {result['log_dirs_exist']}/{result['total_log_dirs']}
- Test logging successful: {result['test_logging_successful']}

"""
        
        # Add errors and warnings
        if self.errors:
            report_content += f"""## Errors Found ({len(self.errors)})

"""
            for error in self.errors:
                report_content += f"- {error}\n"
            report_content += "\n"
        
        if self.warnings:
            report_content += f"""## Warnings ({len(self.warnings)})

"""
            for warning in self.warnings:
                report_content += f"- {warning}\n"
            report_content += "\n"
        
        # Add recommendations
        report_content += """## Recommendations

"""
        
        if success_rate >= 90:
            report_content += """✅ **Organization implementation is successful!**

The project organization has been implemented successfully. All critical systems are working with the new structure.

**Next Steps:**
1. Monitor system performance over the next few days
2. Update any remaining hardcoded paths in custom scripts
3. Consider removing legacy compatibility links after thorough testing

"""
        elif success_rate >= 75:
            report_content += """🟡 **Organization implementation is mostly successful with minor issues.**

Most systems are working correctly with the new organization. Address the warnings above to achieve full success.

**Next Steps:**
1. Fix the issues mentioned in the warnings section
2. Re-run validation after fixes
3. Monitor system performance

"""
        else:
            report_content += """⚠️  **Organization implementation has significant issues.**

Several critical systems are not working correctly with the new organization. Immediate attention required.

**Next Steps:**
1. Address all errors listed above
2. Consider partial rollback if critical systems are affected
3. Re-run validation after each fix
4. Consider getting additional technical support

"""
        
        report_content += f"""## Technical Details

### Project Structure
- **Project Root:** `{self.project_root}`
- **Data Root:** `{self.project_root}/data`
- **Configuration Root:** `{self.project_root}/config`
- **Log Root:** `{self.project_root}/logs`

### Validation Command
To re-run this validation:
```bash
python3 validate_organization.py
```

### Support
If you encounter issues:
1. Check the error messages above
2. Verify file permissions
3. Ensure all required dependencies are installed
4. Review the organization implementation log

---
*Report generated automatically by organization validation system.*
"""
        
        # Write report
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        self.log_success(f"Validation report generated: {report_path}")
        return str(report_path)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite."""
        print("🔍 Hot Durham Project Organization Validation")
        print("=" * 50)
        print(f"Project Root: {self.project_root}")
        print("")
        
        # Run all validation tests
        validation_tests = [
            ("Directory Structure", self.validate_directory_structure),
            ("Path Configuration", self.validate_path_configuration),
            ("Configuration Files", self.validate_configuration_files),
            ("Data Migration", self.validate_data_migration),
            ("System Imports", self.validate_system_imports),
            ("API Functionality", self.validate_api_functionality),
            ("Logging System", self.validate_logging_system)
        ]
        
        overall_success = True
        
        for test_name, test_func in validation_tests:
            try:
                result = test_func()
                if not result:
                    overall_success = False
            except Exception as e:
                self.log_error(f"Validation test '{test_name}' failed with exception: {e}")
                overall_success = False
        
        # Generate comprehensive report
        report_path = self.generate_validation_report()
        
        # Print summary
        print("\n" + "=" * 50)
        if overall_success:
            print("🎉 VALIDATION SUCCESSFUL!")
            print("The Hot Durham project organization is working correctly.")
        else:
            print("⚠️  VALIDATION COMPLETED WITH ISSUES")
            print("Some issues were found. Check the report for details.")
        
        print(f"\n📋 Detailed report: {report_path}")
        print(f"📊 Total errors: {len(self.errors)}")
        print(f"⚠️  Total warnings: {len(self.warnings)}")
        
        return overall_success


def main():
    """Main function for command-line usage."""
    validator = OrganizationValidator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quiet":
        # Redirect stdout for quiet mode
        import io
        import contextlib
        
        with contextlib.redirect_stdout(io.StringIO()):
            success = validator.run_full_validation()
    else:
        success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
