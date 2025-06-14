#!/bin/bash
# cleanup_project.sh - Regular maintenance script for Hot Durham project

echo "🧹 Hot Durham Project Cleanup Script"
echo "===================================="

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
cd "$PROJECT_ROOT"

# Function to safely remove files/directories
safe_remove() {
    if [ -e "$1" ]; then
        echo "Removing: $1"
        rm -rf "$1"
    fi
}

# Clean Python cache files
echo "🐍 Cleaning Python cache files..."
find . -name "__pycache__" -type d -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" -not -path "./.venv/*" -exec rm -f {} + 2>/dev/null || true

# Clean temporary files
echo "🗑️  Cleaning temporary files..."
find . -name "*.tmp" -o -name "*~" -o -name ".DS_Store" -exec rm -f {} + 2>/dev/null || true

# Clean old log files (older than 30 days)
echo "📋 Cleaning old log files..."
find logs/ -name "*.log" -mtime +30 -exec rm -f {} + 2>/dev/null || true
find . -name "*.log" -mtime +30 -not -path "./logs/*" -not -path "./.venv/*" -exec rm -f {} + 2>/dev/null || true

# Clean auto-generated config files with timestamps
echo "⚙️  Cleaning auto-generated config files..."
find config/ -name "*_[0-9]*_[0-9]*.json" -exec rm -f {} + 2>/dev/null || true

# Clean old backup verification logs
echo "🔍 Cleaning old backup verification logs..."
find backup/verification_logs/ -name "*.log" -mtime +7 -exec rm -f {} + 2>/dev/null || true
find src/backup/verification_logs/ -name "*.log" -mtime +7 -exec rm -f {} + 2>/dev/null || true

# Clean old report files (keep last 10)
echo "📊 Cleaning old report files..."
if [ -d "reports" ]; then
    ls -t reports/*.html 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
fi

# Clean Jupyter notebook checkpoints
echo "📓 Cleaning Jupyter checkpoints..."
find . -name ".ipynb_checkpoints" -type d -exec rm -rf {} + 2>/dev/null || true

# Show disk space saved
echo ""
echo "✅ Cleanup completed!"
echo "💾 Current project size:"
du -sh . --exclude='.venv' 2>/dev/null || du -sh . | grep -v '.venv'

# Check Git status
echo ""
echo "📝 Git status after cleanup:"
git status --porcelain

echo ""
echo "🔒 Security reminder: Check that no sensitive files are tracked by Git"
echo "Run 'git ls-files | grep -E \"(key|cred|secret|token|password)\"' to verify"
