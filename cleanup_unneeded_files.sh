#!/bin/bash
"""
Hot Durham Project Cleanup Script
Removes unneeded files while preserving core functionality
"""

echo "🧹 Hot Durham Project Cleanup"
echo "============================="

# Files to be removed - confirmed safe for deletion
FILES_TO_REMOVE=(
    # Duplicate/backup dashboard files
    "src/visualization/public_dashboard_backup.py"
    "src/visualization/public_dashboard_fixed.py"
    
    # Redundant test files (keeping the main test suites)
    "quick_test_feature2.py"
    "interactive_test_feature2.py" 
    "test_feature2_core.py"
    "comprehensive_feature2_test.py"
    
    # Temporary test images
    "temp/dotted_test.png"
    "temp/test_individual_legend.png"
    "temp/test_multisensor_legend.png"
    "temp/test_uptime_legend.png"
    
    # One-time setup/deployment scripts (already executed)
    "deploy_feature2_production.py"
    "deploy_feature2.sh"
    "enhanced_testing_integration.py"
    "final_implementation_summary.py"
    
    # Temporary report files
    "enhanced_testing_report_20250613_180510.json"
    
    # Old cleanup script (replaced by this one)
    "cleanup_outdated_files.py"
    
    # Redundant documentation (info preserved in main docs)
    "CLEANUP_SUMMARY.md"
    "FEATURE2_TESTING_GUIDE.md"
    "IMPLEMENTATION_REPORT.md"
)

echo "Files scheduled for removal:"
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  - $file (already removed)"
    fi
done

echo ""
read -p "Proceed with cleanup? (y/N): " confirm

if [[ $confirm =~ ^[Yy]$ ]]; then
    echo ""
    echo "🗑️ Removing files..."
    
    removed_count=0
    for file in "${FILES_TO_REMOVE[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "  ✅ Removed: $file"
            ((removed_count++))
        fi
    done
    
    # Clean up empty directories
    echo ""
    echo "🧹 Cleaning empty directories..."
    find . -type d -empty -not -path "./.git/*" -not -path "./.venv/*" -delete 2>/dev/null || true
    
    echo ""
    echo "✅ Cleanup complete!"
    echo "📊 Summary:"
    echo "  • Files removed: $removed_count"
    echo "  • Space freed: $(du -sh . 2>/dev/null | cut -f1) total project size"
    
    # Show remaining important files
    echo ""
    echo "🔍 Core files preserved:"
    echo "  ✅ Feature 2: src/ml/predictive_analytics.py"
    echo "  ✅ Feature 3: src/api/public_api.py" 
    echo "  ✅ Main tests: test_feature2_implementation.py, test_feature3_implementation.py"
    echo "  ✅ Production: production/feature2_production_*.py"
    echo "  ✅ Documentation: docs/, README.md"
    echo "  ✅ Configuration: config/*.json"
    
else
    echo "❌ Cleanup cancelled"
    exit 0
fi

echo ""
echo "🎯 Next steps:"
echo "  • Run: python test_feature2_implementation.py"
echo "  • Run: python test_feature3_implementation.py" 
echo "  • Check: API server at http://localhost:5002"
echo "  • Review: FEATURE_IMPLEMENTATION_COMPLETE.md"
