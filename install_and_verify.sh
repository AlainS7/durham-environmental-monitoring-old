#!/bin/bash
# Hot Durham Project - Installation and Verification Script
# This script installs the project and verifies that everything is working correctly

echo "🔥 Hot Durham Air Quality Monitoring - Installation & Verification"
echo "================================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: Please run this script from the Hot Durham project root directory"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1)
echo "   $python_version"

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider activating .venv: source .venv/bin/activate"
else
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
fi
echo ""

# Install the package in development mode
echo "📦 Installing Hot Durham package in development mode..."
pip install -e . --quiet
if [ $? -eq 0 ]; then
    echo "✅ Package installation successful"
else
    echo "❌ Package installation failed"
    exit 1
fi
echo ""

# Verify imports
echo "🔍 Verifying module imports..."
python verify_imports.py
if [ $? -eq 0 ]; then
    echo "✅ All imports verified successfully"
else
    echo "❌ Import verification failed"
    exit 1
fi
echo ""

# Run integration tests
echo "🧪 Running integration tests..."
PYTHONPATH="$PWD/src:$PWD" python tests/integration_test.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Integration tests passed (8/8)"
else
    echo "❌ Integration tests failed"
    echo "   Run manually: PYTHONPATH=\"\$PWD/src:\$PWD\" python tests/integration_test.py"
fi
echo ""

# Check command line tools
echo "🛠️  Checking command line tools..."
commands=("hot-durham-collect" "hot-durham-analyze" "hot-durham-backup" "hot-durham-status")
for cmd in "${commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo "   ✅ $cmd available"
    else
        echo "   ⚠️  $cmd not found (may need to restart shell)"
    fi
done
echo ""

# Check critical files
echo "📋 Checking critical files..."
critical_files=("creds/tsi_creds.json" "creds/google_creds.json" "creds/wu_api_key.json")
for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file exists"
    else
        echo "   ⚠️  $file missing (required for data collection)"
    fi
done
echo ""

# Final status
echo "🎉 Hot Durham Installation Complete!"
echo ""
echo "📚 Next Steps:"
echo "   1. Place your credential files in the creds/ directory"
echo "   2. Run: ./setup_automation.sh (to set up scheduled data pulls)"
echo "   3. Test: python src/automation/status_check.py"
echo "   4. Start collecting: python src/data_collection/automated_data_pull.py --weekly"
echo ""
echo "📖 Documentation:"
echo "   • Quick Start: docs/QUICK_START.md"
echo "   • Features: docs/NEW_FEATURES_DOCUMENTATION.md"
echo "   • Reorganization: REORGANIZATION_COMPLETE.md"
echo ""
echo "🚀 Happy monitoring!"
