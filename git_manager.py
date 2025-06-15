#!/usr/bin/env python3
"""
Git Repository Status and Cleanup Tool for Hot Durham

This script provides comprehensive git repository management including:
- Status checking and reporting
- Staged changes review
- Sensitive data detection
- Cleanup recommendations
- Commit preparation
"""

import os
import subprocess
import sys
import re
from pathlib import Path

class GitManager:
    """Git repository management utilities"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        os.chdir(self.project_root)
        
    def run_git_command(self, command):
        """Run git command and return output"""
        try:
            result = subprocess.run(
                f"git {command}", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return False, "", str(e)
    
    def get_status(self):
        """Get comprehensive git status"""
        print("🔍 Git Repository Status")
        print("=" * 50)
        
        # Basic status
        success, output, error = self.run_git_command("status --porcelain")
        if not success:
            print(f"❌ Error getting git status: {error}")
            return False
        
        if not output:
            print("✅ Working tree clean")
            return True
        
        # Parse status
        modified = []
        added = []
        deleted = []
        untracked = []
        
        for line in output.split('\n'):
            if line:
                status = line[:2]
                filename = line[3:]
                
                if status.startswith('M'):
                    modified.append(filename)
                elif status.startswith('A'):
                    added.append(filename)
                elif status.startswith('D'):
                    deleted.append(filename)
                elif status.startswith('??'):
                    untracked.append(filename)
        
        # Report status
        if modified:
            print(f"📝 Modified files ({len(modified)}):")
            for file in modified[:10]:  # Show first 10
                print(f"   - {file}")
            if len(modified) > 10:
                print(f"   ... and {len(modified) - 10} more")
        
        if added:
            print(f"➕ Added files ({len(added)}):")
            for file in added[:10]:
                print(f"   - {file}")
            if len(added) > 10:
                print(f"   ... and {len(added) - 10} more")
        
        if deleted:
            print(f"🗑️ Deleted files ({len(deleted)}):")
            for file in deleted:
                print(f"   - {file}")
        
        if untracked:
            print(f"❓ Untracked files ({len(untracked)}):")
            for file in untracked[:10]:
                print(f"   - {file}")
            if len(untracked) > 10:
                print(f"   ... and {len(untracked) - 10} more")
        
        return True
    
    def check_sensitive_data(self):
        """Check for sensitive data in staged changes"""
        print("\n🔒 Sensitive Data Check")
        print("-" * 30)
        
        # Check staged files
        success, output, error = self.run_git_command("diff --cached --name-only")
        if not success:
            print(f"❌ Error checking staged files: {error}")
            return False
        
        if not output:
            print("ℹ️ No staged changes to check")
            return True
        
        staged_files = output.split('\n')
        sensitive_patterns = [
            r'password', r'api_key', r'secret', r'token', 
            r'credentials', r'auth', r'private_key'
        ]
        
        issues_found = []
        
        for file in staged_files:
            if file and os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        for pattern in sensitive_patterns:
                            if re.search(pattern, content):
                                issues_found.append((file, pattern))
                except Exception:
                    continue
        
        if issues_found:
            print("⚠️ Potential sensitive data found:")
            for file, pattern in issues_found:
                print(f"   - {file}: contains '{pattern}'")
            return False
        else:
            print("✅ No sensitive data detected in staged changes")
            return True
    
    def suggest_cleanup(self):
        """Suggest cleanup actions"""
        print("\n🧹 Cleanup Suggestions")
        print("-" * 30)
        
        suggestions = []
        
        # Check for backup files
        backup_files = list(self.project_root.glob("*_backup*"))
        if backup_files:
            suggestions.append(f"Remove {len(backup_files)} backup files")
        
        # Check for log files
        log_files = list(self.project_root.glob("logs/*.log"))
        large_logs = [f for f in log_files if f.stat().st_size > 10 * 1024 * 1024]  # >10MB
        if large_logs:
            suggestions.append(f"Archive or clean {len(large_logs)} large log files")
        
        # Check for test result files
        test_results = list(self.project_root.glob("logs/test_results_*.json"))
        if len(test_results) > 10:
            suggestions.append(f"Clean up old test result files (keep latest 10)")
        
        # Check for temporary files
        temp_files = list(self.project_root.glob("temp_*")) + list(self.project_root.glob("*.tmp"))
        if temp_files:
            suggestions.append(f"Remove {len(temp_files)} temporary files")
        
        if suggestions:
            for suggestion in suggestions:
                print(f"   • {suggestion}")
        else:
            print("✅ Repository looks clean")
        
        return suggestions
    
    def prepare_commit(self):
        """Help prepare a commit"""
        print("\n📝 Commit Preparation")
        print("-" * 30)
        
        # Check if there are changes to commit
        success, output, error = self.run_git_command("diff --cached --name-only")
        if not success or not output:
            print("ℹ️ No staged changes. Stage some files first with 'git add'")
            return False
        
        staged_files = output.split('\n')
        print(f"📋 Staged files ({len(staged_files)}):")
        for file in staged_files:
            if file:
                print(f"   - {file}")
        
        # Run pre-commit checks
        print("\n🔍 Running pre-commit checks...")
        
        # Check Python syntax
        python_files = [f for f in staged_files if f.endswith('.py')]
        if python_files:
            print("📋 Checking Python syntax...")
            for py_file in python_files:
                if os.path.exists(py_file):
                    result = subprocess.run([sys.executable, '-m', 'py_compile', py_file], 
                                          capture_output=True)
                    if result.returncode != 0:
                        print(f"❌ Syntax error in {py_file}")
                        return False
            print("✅ Python syntax check passed")
        
        # Final sensitive data check
        if not self.check_sensitive_data():
            print("⚠️ Sensitive data check failed - review before committing")
            return False
        
        print("\n✅ Ready to commit!")
        print("\nSuggested commit command:")
        print("git commit -m 'feat(scope): brief description'")
        print("\nSee GIT_WORKFLOW_GUIDE.md for commit message conventions")
        
        return True
    
    def interactive_add(self):
        """Interactive file staging"""
        print("\n📂 Interactive File Staging")
        print("-" * 30)
        
        # Get untracked and modified files
        success, output, error = self.run_git_command("status --porcelain")
        if not success:
            print(f"❌ Error getting status: {error}")
            return
        
        if not output:
            print("✅ No changes to stage")
            return
        
        files_to_stage = []
        
        for line in output.split('\n'):
            if line and not line.startswith('D'):  # Skip deleted files
                filename = line[3:]
                if not any(pattern in filename for pattern in ['__pycache__', '.pyc', '.log']):
                    files_to_stage.append(filename)
        
        if not files_to_stage:
            print("✅ No suitable files to stage")
            return
        
        print("📋 Files available for staging:")
        for i, file in enumerate(files_to_stage, 1):
            print(f"   {i}. {file}")
        
        print("\nEnter file numbers to stage (space-separated), 'all' for all files, or 'q' to quit:")
        try:
            response = input("Choice: ").strip()
            
            if response.lower() == 'q':
                return
            elif response.lower() == 'all':
                for file in files_to_stage:
                    self.run_git_command(f"add '{file}'")
                print(f"✅ Staged {len(files_to_stage)} files")
            else:
                indices = [int(x) - 1 for x in response.split() if x.isdigit()]
                staged_count = 0
                for i in indices:
                    if 0 <= i < len(files_to_stage):
                        self.run_git_command(f"add '{files_to_stage[i]}'")
                        staged_count += 1
                print(f"✅ Staged {staged_count} files")
        
        except (ValueError, KeyboardInterrupt):
            print("❌ Invalid input or cancelled")

def main():
    """Main interface"""
    manager = GitManager()
    
    print("🚀 Hot Durham Git Management Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        print("\nAvailable actions:")
        print("  status    - Show repository status")
        print("  check     - Run comprehensive checks")
        print("  cleanup   - Show cleanup suggestions") 
        print("  prepare   - Prepare commit")
        print("  stage     - Interactive file staging")
        print("  all       - Run all checks")
        
        action = input("\nChoose action (or press Enter for 'all'): ").strip() or "all"
    
    if action in ['status', 'all']:
        manager.get_status()
    
    if action in ['check', 'all']:
        manager.check_sensitive_data()
    
    if action in ['cleanup', 'all']:
        manager.suggest_cleanup()
    
    if action == 'prepare':
        manager.prepare_commit()
    
    if action == 'stage':
        manager.interactive_add()
    
    if action == 'all':
        print("\n🎯 Summary")
        print("-" * 30)
        print("✅ Repository status checked")
        print("✅ Sensitive data scan completed")
        print("✅ Cleanup suggestions provided")
        print("\nNext steps:")
        print("1. Review and stage files: python git_manager.py stage")
        print("2. Prepare commit: python git_manager.py prepare")
        print("3. Commit: git commit")

if __name__ == "__main__":
    main()
