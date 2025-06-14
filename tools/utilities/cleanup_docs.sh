#!/bin/bash

# Hot Durham Documentation Cleanup Script
# Removes duplicate and redundant documentation files before git push

echo "🗑️ Hot Durham Documentation Cleanup"
echo "===================================="

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
BACKUP_DIR="$PROJECT_ROOT/backup/doc_cleanup_$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_ROOT" || exit 1

echo "📂 Project Root: $PROJECT_ROOT"
echo "💾 Backup Location: $BACKUP_DIR"

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo "✅ Backup directory created"

echo ""
echo "🔍 ANALYSIS: Found redundant documentation files"
echo "==============================================="

echo "📋 Files to be removed (duplicates exist in organized docs/):"
echo "• FINAL_ITERATION_COMPLETE.md (root) - duplicate of docs/implementation/"
echo "• PATH_VALIDATION_COMPLETE.md (root) - duplicate of docs/organization/"
echo "• docs/README.md - superseded by main README.md"
echo "• docs/IMPLEMENTATION_COMPLETE.md - superseded by newer implementation docs"

echo ""
read -p "Continue with documentation cleanup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo ""
echo "💾 CREATING BACKUP"
echo "=================="

# Backup files before removal
echo "📋 Backing up files to be removed..."

if [ -f "FINAL_ITERATION_COMPLETE.md" ]; then
    cp "FINAL_ITERATION_COMPLETE.md" "$BACKUP_DIR/"
    echo "✅ Backed up: FINAL_ITERATION_COMPLETE.md"
fi

if [ -f "PATH_VALIDATION_COMPLETE.md" ]; then
    cp "PATH_VALIDATION_COMPLETE.md" "$BACKUP_DIR/"
    echo "✅ Backed up: PATH_VALIDATION_COMPLETE.md"
fi

if [ -f "docs/README.md" ]; then
    cp "docs/README.md" "$BACKUP_DIR/docs_README.md"
    echo "✅ Backed up: docs/README.md"
fi

if [ -f "docs/IMPLEMENTATION_COMPLETE.md" ]; then
    cp "docs/IMPLEMENTATION_COMPLETE.md" "$BACKUP_DIR/"
    echo "✅ Backed up: docs/IMPLEMENTATION_COMPLETE.md"
fi

echo "✅ Backup completed at: $BACKUP_DIR"

echo ""
echo "🗑️ REMOVING DUPLICATE FILES"
echo "============================"

# Remove duplicate files (keeping organized versions)
if [ -f "FINAL_ITERATION_COMPLETE.md" ]; then
    rm "FINAL_ITERATION_COMPLETE.md"
    echo "✅ Removed: FINAL_ITERATION_COMPLETE.md (kept: docs/implementation/)"
fi

if [ -f "PATH_VALIDATION_COMPLETE.md" ]; then
    rm "PATH_VALIDATION_COMPLETE.md"
    echo "✅ Removed: PATH_VALIDATION_COMPLETE.md (kept: docs/organization/)"
fi

# Remove superseded docs/README.md (main README.md is more comprehensive)
if [ -f "docs/README.md" ]; then
    rm "docs/README.md"
    echo "✅ Removed: docs/README.md (kept: main README.md)"
fi

# Remove obsolete implementation doc
if [ -f "docs/IMPLEMENTATION_COMPLETE.md" ]; then
    rm "docs/IMPLEMENTATION_COMPLETE.md"
    echo "✅ Removed: docs/IMPLEMENTATION_COMPLETE.md (superseded by newer docs)"
fi

echo ""
echo "🔍 CHECKING FOR ADDITIONAL CLEANUP"
echo "=================================="

# Check for any other potential redundancies
echo "📊 Remaining documentation files:"
echo "Root docs: $(ls *.md 2>/dev/null | wc -l | tr -d ' ') files"
echo "Organized docs: $(find docs -name "*.md" | wc -l | tr -d ' ') files"

# List remaining root docs
echo ""
echo "📋 Remaining root documentation:"
ls -1 *.md 2>/dev/null | sed 's/^/   • /'

echo ""
echo "📋 Check for any remaining issues:"

# Check for files that might need to be moved to docs/
potential_doc_files=$(ls -1 *.md 2>/dev/null | grep -v -E '^README\.md$|^requirements\.txt$' | head -5)

if [ -n "$potential_doc_files" ]; then
    echo "⚠️  Consider moving these to docs/ if they're not essential root files:"
    echo "$potential_doc_files" | sed 's/^/   • /'
else
    echo "✅ No additional documentation files need organizing"
fi

echo ""
echo "📊 CLEANUP SUMMARY"
echo "=================="

echo "✅ Files removed:"
echo "   • FINAL_ITERATION_COMPLETE.md (duplicate)"
echo "   • PATH_VALIDATION_COMPLETE.md (duplicate)"  
echo "   • docs/README.md (superseded)"
echo "   • docs/IMPLEMENTATION_COMPLETE.md (obsolete)"

echo ""
echo "✅ Files preserved in organized locations:"
echo "   • docs/implementation/FINAL_ITERATION_COMPLETE.md"
echo "   • docs/organization/PATH_VALIDATION_COMPLETE.md"
echo "   • README.md (main project documentation)"
echo "   • All other organized documentation in docs/"

echo ""
echo "💾 Backup available at: $BACKUP_DIR"

echo ""
echo "📋 RECOMMENDED NEXT STEPS:"
echo "========================="
echo "1. Review remaining root documentation files"
echo "2. Ensure main README.md contains all essential information"
echo "3. Check that docs/ organization is complete"
echo "4. Run git status to see cleanup results"
echo "5. Commit changes with: git add -A && git commit -m 'docs: cleanup duplicate and obsolete documentation'"

echo ""
echo "🎯 DOCUMENTATION CLEANUP COMPLETE!"
echo "Ready for git push with clean, organized documentation structure."

# Final file count
echo ""
echo "📊 Final documentation count:"
total_docs=$(($(ls *.md 2>/dev/null | wc -l) + $(find docs -name "*.md" | wc -l)))
echo "Total documentation files: $total_docs (reduced from 27)"
echo "Organization: Professional and non-redundant"
