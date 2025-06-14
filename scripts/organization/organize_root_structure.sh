#!/bin/bash

# Hot Durham Project Root Organization Script
# Organizes root directory files into logical categories

echo "🗂️ Hot Durham Project Root Organization"
echo "======================================="

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
BACKUP_DIR="$PROJECT_ROOT/backup/root_organization_$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_ROOT" || exit 1

echo "📂 Project Root: $PROJECT_ROOT"
echo "💾 Backup Location: $BACKUP_DIR"

# Confirm with user
read -p "Continue with root organization? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Organization cancelled"
    exit 1
fi

echo "======================================="
echo "CREATING BACKUP"
echo "======================================="

# Create backup
mkdir -p "$BACKUP_DIR"
echo "📋 Backing up current root files..."

# Copy all root files to backup (excluding directories)
for file in *.*; do
    if [[ -f "$file" ]]; then
        cp "$file" "$BACKUP_DIR/"
        echo "✅ Backed up: $file"
    fi
done

echo "✅ Backup completed at: $BACKUP_DIR"

echo "======================================="
echo "CREATING NEW DIRECTORY STRUCTURE"
echo "======================================="

# Create new directories
mkdir -p scripts/{automation,deployment,maintenance,git,organization}
mkdir -p docs/{implementation,organization,setup,notebooks}
mkdir -p tools/{testing,utilities,config}

echo "✅ Directory structure created"

echo "======================================="
echo "ORGANIZING FILES"
echo "======================================="

# Move shell scripts
echo "📁 Organizing shell scripts..."
mv automated_maintenance.sh scripts/automation/ 2>/dev/null && echo "✅ Moved: automated_maintenance.sh"
mv automation_commands.sh scripts/automation/ 2>/dev/null && echo "✅ Moved: automation_commands.sh"  
mv maintenance.sh scripts/automation/ 2>/dev/null && echo "✅ Moved: maintenance.sh"
mv setup_maintenance_automation.sh scripts/automation/ 2>/dev/null && echo "✅ Moved: setup_maintenance_automation.sh"
mv setup_production_pdf_automation.sh scripts/automation/ 2>/dev/null && echo "✅ Moved: setup_production_pdf_automation.sh"

mv install_and_verify.sh scripts/deployment/ 2>/dev/null && echo "✅ Moved: install_and_verify.sh"
mv quick_start.sh scripts/deployment/ 2>/dev/null && echo "✅ Moved: quick_start.sh"
mv run_weekly_pull.sh scripts/deployment/ 2>/dev/null && echo "✅ Moved: run_weekly_pull.sh"

mv cleanup_project.sh scripts/maintenance/ 2>/dev/null && echo "✅ Moved: cleanup_project.sh"
mv cleanup_unneeded_files.sh scripts/maintenance/ 2>/dev/null && echo "✅ Moved: cleanup_unneeded_files.sh"
mv security_check.sh scripts/maintenance/ 2>/dev/null && echo "✅ Moved: security_check.sh"

mv git_final_commands.sh scripts/git/ 2>/dev/null && echo "✅ Moved: git_final_commands.sh"
mv git_prepare.sh scripts/git/ 2>/dev/null && echo "✅ Moved: git_prepare.sh"

mv organize_project_structure.sh scripts/organization/ 2>/dev/null && echo "✅ Moved: organize_project_structure.sh"

# Move documentation files
echo "📖 Organizing documentation..."
mv FEATURE_IMPLEMENTATION_COMPLETE.md docs/implementation/ 2>/dev/null && echo "✅ Moved: FEATURE_IMPLEMENTATION_COMPLETE.md"
mv FINAL_ITERATION_COMPLETE.md docs/implementation/ 2>/dev/null && echo "✅ Moved: FINAL_ITERATION_COMPLETE.md"
mv ITERATION_4_COMPLETE.md docs/implementation/ 2>/dev/null && echo "✅ Moved: ITERATION_4_COMPLETE.md"
mv TEST_SENSOR_IMPLEMENTATION_GUIDE.md docs/implementation/ 2>/dev/null && echo "✅ Moved: TEST_SENSOR_IMPLEMENTATION_GUIDE.md"

mv ORGANIZATION_COMPLETE.md docs/organization/ 2>/dev/null && echo "✅ Moved: ORGANIZATION_COMPLETE.md"
mv ORGANIZATION_IMPLEMENTATION_REPORT.md docs/organization/ 2>/dev/null && echo "✅ Moved: ORGANIZATION_IMPLEMENTATION_REPORT.md"
mv ORGANIZATION_VALIDATION_REPORT.md docs/organization/ 2>/dev/null && echo "✅ Moved: ORGANIZATION_VALIDATION_REPORT.md"
mv PATH_VALIDATION_COMPLETE.md docs/organization/ 2>/dev/null && echo "✅ Moved: PATH_VALIDATION_COMPLETE.md"
mv PROJECT_ORGANIZATION_PLAN.md docs/organization/ 2>/dev/null && echo "✅ Moved: PROJECT_ORGANIZATION_PLAN.md"

mv AUTOMATION_SETUP_GUIDE.md docs/setup/ 2>/dev/null && echo "✅ Moved: AUTOMATION_SETUP_GUIDE.md"
mv CLEANUP_COMPLETE.md docs/setup/ 2>/dev/null && echo "✅ Moved: CLEANUP_COMPLETE.md"
mv GIT_READY.md docs/setup/ 2>/dev/null && echo "✅ Moved: GIT_READY.md"
mv PRODUCTION_PDF_SYSTEM_README.md docs/setup/ 2>/dev/null && echo "✅ Moved: PRODUCTION_PDF_SYSTEM_README.md"

mv next_steps_guide.ipynb docs/notebooks/ 2>/dev/null && echo "✅ Moved: next_steps_guide.ipynb"

# Move Python tools
echo "🐍 Organizing Python tools..."
mv test_feature2_implementation.py tools/testing/ 2>/dev/null && echo "✅ Moved: test_feature2_implementation.py"
mv test_feature3_implementation.py tools/testing/ 2>/dev/null && echo "✅ Moved: test_feature3_implementation.py"  
mv test_production_pdf_system.py tools/testing/ 2>/dev/null && echo "✅ Moved: test_production_pdf_system.py"

mv update_configurations.py tools/utilities/ 2>/dev/null && echo "✅ Moved: update_configurations.py"
mv validate_organization.py tools/utilities/ 2>/dev/null && echo "✅ Moved: validate_organization.py"
mv generate_production_pdf_report.py tools/utilities/ 2>/dev/null && echo "✅ Moved: generate_production_pdf_report.py"

# Move config files
echo "⚙️ Organizing config files..."
mv com.hotdurham.maintenance.plist tools/config/ 2>/dev/null && echo "✅ Moved: com.hotdurham.maintenance.plist"
mv com.hotdurham.testsensor.automation.plist tools/config/ 2>/dev/null && echo "✅ Moved: com.hotdurham.testsensor.automation.plist"
mv MANIFEST.in tools/config/ 2>/dev/null && echo "✅ Moved: MANIFEST.in"
mv data_management.log tools/config/ 2>/dev/null && echo "✅ Moved: data_management.log"

echo "======================================="
echo "CREATING CONVENIENCE LINKS"
echo "======================================="

# Create convenience links for commonly used scripts
ln -sf scripts/deployment/quick_start.sh quick_start 2>/dev/null && echo "🔗 Created link: quick_start"
ln -sf scripts/automation/maintenance.sh maintenance 2>/dev/null && echo "🔗 Created link: maintenance"

echo "======================================="
echo "ORGANIZATION COMPLETE"
echo "======================================="

echo "✅ Root organization completed successfully!"
echo ""
echo "📊 New structure:"
echo "   📁 scripts/ - Shell scripts organized by purpose"
echo "   📖 docs/ - Documentation organized by category"  
echo "   🔧 tools/ - Development and testing tools"
echo "   🔗 Convenience links created for common scripts"
echo ""
echo "💾 Backup available at: $BACKUP_DIR"
echo "📋 Organization plan: ROOT_ORGANIZATION_PLAN.md"
echo ""
echo "🎯 Next steps:"
echo "   1. Test that all scripts work from new locations"
echo "   2. Update any hardcoded paths if needed"
echo "   3. Remove backup once satisfied with organization"

# Final verification
echo ""
echo "📈 Organization Results:"
echo "Scripts moved: $(find scripts -name "*.sh" | wc -l | tr -d ' ')"
echo "Docs moved: $(find docs -name "*.md" | wc -l | tr -d ' ')"
echo "Tools moved: $(find tools -name "*.py" | wc -l | tr -d ' ')"
echo "Root files remaining: $(ls -1 *.* 2>/dev/null | wc -l | tr -d ' ')"
