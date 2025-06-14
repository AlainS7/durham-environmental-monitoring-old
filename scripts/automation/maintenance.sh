#!/bin/bash
# maintenance.sh - Weekly maintenance script for Hot Durham project

echo "🛠️  Hot Durham Weekly Maintenance"
echo "================================="

# Run cleanup
echo "📋 Step 1: Running project cleanup..."
scripts/maintenance/cleanup_project.sh

echo ""
echo "📋 Step 2: Running security check..."
scripts/maintenance/security_check.sh

echo ""
echo "📋 Step 3: Checking Git repository health..."
cd "/Users/alainsoto/IdeaProjects/Hot Durham"

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Uncommitted changes found:"
    git status --short
    echo ""
fi

# Check if we're ahead/behind remote
if git status | grep -q "ahead\|behind"; then
    echo "⚠️  Local branch is out of sync with remote:"
    git status | grep -E "(ahead|behind)"
    echo ""
fi

# Check repository size
REPO_SIZE=$(du -sh .git | cut -f1)
echo "📊 Repository .git size: $REPO_SIZE"

# Check for large objects in git history
echo "📊 Largest objects in Git history:"
git rev-list --objects --all | \
git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
sed -n 's/^blob //p' | \
sort --numeric-sort --key=2 | \
tail -n 5 | \
cut -c 1-12,41- | \
numfmt --field=2 --to=iec-i --suffix=B

echo ""
echo "📋 Step 4: Checking Python environment..."
if [ -f "requirements.txt" ]; then
    echo "📦 Checking for outdated packages..."
    if command -v pip-outdated &> /dev/null; then
        pip-outdated
    else
        echo "ℹ️  Install pip-outdated for package update checking: pip install pip-outdated"
    fi
fi

echo ""
echo "✅ Maintenance completed!"
echo ""
echo "📋 Action Items:"
echo "• Review any security warnings above"
echo "• Commit or stash uncommitted changes"
echo "• Consider cleaning up large files if repository is growing too large"
echo "• Update dependencies if needed"
