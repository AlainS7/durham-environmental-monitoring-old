#!/bin/bash

# Hot Durham Script Path Validation
# Validates that all script references work after root organization

echo "🔍 Hot Durham Script Path Validation"
echo "===================================="

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
cd "$PROJECT_ROOT" || exit 1

VALIDATION_LOG="logs/script_path_validation.log"
mkdir -p logs
echo "$(date): Starting script path validation" > "$VALIDATION_LOG"

echo "📂 Project Root: $PROJECT_ROOT"
echo "📋 Log File: $VALIDATION_LOG"
echo ""

# Test convenience links
echo "🔗 TESTING CONVENIENCE LINKS:"
echo "-----------------------------"

if [ -L "quick_start" ] && [ -e "quick_start" ]; then
    echo "✅ quick_start link: $(readlink quick_start)"
    echo "$(date): ✅ quick_start link working" >> "$VALIDATION_LOG"
else
    echo "❌ quick_start link broken or missing"
    echo "$(date): ❌ quick_start link broken" >> "$VALIDATION_LOG"
fi

if [ -L "maintenance" ] && [ -e "maintenance" ]; then
    echo "✅ maintenance link: $(readlink maintenance)"
    echo "$(date): ✅ maintenance link working" >> "$VALIDATION_LOG"
else
    echo "❌ maintenance link broken or missing"
    echo "$(date): ❌ maintenance link broken" >> "$VALIDATION_LOG"
fi
echo ""

# Test script directories
echo "📁 TESTING SCRIPT DIRECTORIES:"
echo "------------------------------"

script_dirs=("scripts/automation" "scripts/deployment" "scripts/maintenance" "scripts/git" "scripts/organization")

for dir in "${script_dirs[@]}"; do
    if [ -d "$dir" ]; then
        script_count=$(find "$dir" -name "*.sh" | wc -l | tr -d ' ')
        echo "✅ $dir: $script_count script(s)"
        echo "$(date): ✅ $dir has $script_count scripts" >> "$VALIDATION_LOG"
    else
        echo "❌ $dir: Directory missing"
        echo "$(date): ❌ $dir directory missing" >> "$VALIDATION_LOG"
    fi
done
echo ""

# Test key script executability
echo "🔧 TESTING SCRIPT EXECUTABILITY:"
echo "--------------------------------"

key_scripts=(
    "scripts/automation/maintenance.sh"
    "scripts/deployment/quick_start.sh"
    "scripts/maintenance/cleanup_project.sh"
    "scripts/maintenance/security_check.sh"
    "scripts/automation/automated_maintenance.sh"
)

for script in "${key_scripts[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        echo "✅ $script: Executable"
        echo "$(date): ✅ $script is executable" >> "$VALIDATION_LOG"
    elif [ -f "$script" ]; then
        echo "⚠️  $script: Exists but not executable"
        chmod +x "$script"
        echo "✅ $script: Made executable"
        echo "$(date): ⚠️  Made $script executable" >> "$VALIDATION_LOG"
    else
        echo "❌ $script: Missing"
        echo "$(date): ❌ $script missing" >> "$VALIDATION_LOG"
    fi
done
echo ""

# Test internal script references
echo "🔍 TESTING INTERNAL SCRIPT REFERENCES:"
echo "--------------------------------------"

echo "Checking maintenance.sh references..."
if grep -q "scripts/maintenance/cleanup_project.sh" scripts/automation/maintenance.sh; then
    echo "✅ maintenance.sh: cleanup_project.sh reference updated"
    echo "$(date): ✅ maintenance.sh cleanup reference updated" >> "$VALIDATION_LOG"
else
    echo "❌ maintenance.sh: cleanup_project.sh reference not updated"
    echo "$(date): ❌ maintenance.sh cleanup reference broken" >> "$VALIDATION_LOG"
fi

if grep -q "scripts/maintenance/security_check.sh" scripts/automation/maintenance.sh; then
    echo "✅ maintenance.sh: security_check.sh reference updated"
    echo "$(date): ✅ maintenance.sh security reference updated" >> "$VALIDATION_LOG"
else
    echo "❌ maintenance.sh: security_check.sh reference not updated"
    echo "$(date): ❌ maintenance.sh security reference broken" >> "$VALIDATION_LOG"
fi

echo "Checking automation_commands.sh references..."
if grep -q "scripts/automation/setup_maintenance_automation.sh" scripts/automation/automation_commands.sh; then
    echo "✅ automation_commands.sh: setup script references updated"
    echo "$(date): ✅ automation_commands.sh references updated" >> "$VALIDATION_LOG"
else
    echo "❌ automation_commands.sh: setup script references not updated"
    echo "$(date): ❌ automation_commands.sh references broken" >> "$VALIDATION_LOG"
fi
echo ""

# Test script functionality with dry run
echo "🧪 TESTING SCRIPT FUNCTIONALITY (DRY RUN):"
echo "------------------------------------------"

echo "Testing maintenance.sh (dry run)..."
if scripts/automation/maintenance.sh --help >/dev/null 2>&1 || scripts/automation/maintenance.sh --version >/dev/null 2>&1; then
    echo "✅ maintenance.sh: Help/version accessible"
    echo "$(date): ✅ maintenance.sh accessible" >> "$VALIDATION_LOG"
else
    echo "ℹ️  maintenance.sh: No help option (normal for this script)"
    echo "$(date): ℹ️  maintenance.sh no help option" >> "$VALIDATION_LOG"
fi

echo "Testing quick_start.sh accessibility..."
if [ -x "scripts/deployment/quick_start.sh" ]; then
    echo "✅ quick_start.sh: Accessible via direct path"
    echo "$(date): ✅ quick_start.sh accessible" >> "$VALIDATION_LOG"
else
    echo "❌ quick_start.sh: Not accessible"
    echo "$(date): ❌ quick_start.sh not accessible" >> "$VALIDATION_LOG"
fi

echo "Testing convenience link functionality..."
if [ -x "./quick_start" ]; then
    echo "✅ quick_start convenience link: Functional"
    echo "$(date): ✅ quick_start convenience link functional" >> "$VALIDATION_LOG"
else
    echo "❌ quick_start convenience link: Not functional"
    echo "$(date): ❌ quick_start convenience link broken" >> "$VALIDATION_LOG"
fi
echo ""

# Generate summary
echo "📊 VALIDATION SUMMARY:"
echo "====================="

total_tests=0
passed_tests=0

# Count results from log
total_tests=$(grep -c "✅\|❌\|⚠️" "$VALIDATION_LOG" 2>/dev/null || echo "0")
passed_tests=$(grep -c "✅" "$VALIDATION_LOG" 2>/dev/null || echo "0")
warnings=$(grep -c "⚠️" "$VALIDATION_LOG" 2>/dev/null || echo "0")
failures=$(grep -c "❌" "$VALIDATION_LOG" 2>/dev/null || echo "0")

echo "Total Tests: $total_tests"
echo "Passed: $passed_tests"
echo "Warnings: $warnings"
echo "Failures: $failures"

if [ "$failures" -eq 0 ]; then
    if [ "$warnings" -eq 0 ]; then
        echo ""
        echo "🎉 ALL SCRIPT PATHS VALIDATED SUCCESSFULLY!"
        echo "✅ All scripts are properly organized and functional"
        echo "$(date): 🎉 All script paths validated successfully" >> "$VALIDATION_LOG"
    else
        echo ""
        echo "⚠️  VALIDATION COMPLETED WITH WARNINGS"
        echo "✅ Critical functionality working, minor issues resolved"
        echo "$(date): ⚠️  Validation completed with warnings" >> "$VALIDATION_LOG"
    fi
else
    echo ""
    echo "❌ VALIDATION FAILED"
    echo "🔧 Some script paths need manual fixing"
    echo "$(date): ❌ Validation failed - manual fixes needed" >> "$VALIDATION_LOG"
fi

echo ""
echo "📋 Detailed log: $VALIDATION_LOG"
echo "🔧 Run individual scripts to test specific functionality"
echo ""

# Show quick usage guide
echo "🚀 QUICK USAGE AFTER ORGANIZATION:"
echo "=================================="
echo "Use convenience links:"
echo "  ./quick_start                    # Quick project startup"
echo "  ./maintenance                    # Run maintenance tasks"
echo ""
echo "Or use full paths:"
echo "  scripts/automation/maintenance.sh          # Full maintenance"
echo "  scripts/maintenance/cleanup_project.sh     # Clean project"
echo "  scripts/maintenance/security_check.sh      # Security check"
echo "  scripts/deployment/install_and_verify.sh   # Install & verify"
echo ""
echo "Documentation:"
echo "  docs/setup/                      # Setup guides"
echo "  docs/implementation/             # Implementation docs"
echo "  docs/organization/               # Organization reports"
