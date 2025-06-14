#!/bin/bash
# security_check.sh - Security audit script for Hot Durham project

echo "🔒 Hot Durham Security Check"
echo "============================"

PROJECT_ROOT="/Users/alainsoto/IdeaProjects/Hot Durham"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES_FOUND=0

echo "🔍 Checking for sensitive files in Git tracking..."
SENSITIVE_IN_GIT=$(git ls-files | grep -E "(api_key|password|secret|token|\.key$|\.pem$|creds\.json|auth\.json)" | grep -v "creds/README.md" | grep -v "creds/\.gitignore")

if [ -n "$SENSITIVE_IN_GIT" ]; then
    echo -e "${RED}❌ CRITICAL: Sensitive files found in Git tracking:${NC}"
    echo "$SENSITIVE_IN_GIT"
    echo -e "${YELLOW}🔧 To remove: git rm --cached <filename> && git commit -m 'Remove sensitive file'${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✅ No sensitive files found in Git tracking${NC}"
fi

echo ""
echo "🔍 Checking for untracked sensitive files..."
UNTRACKED_SENSITIVE=$(find . -type f \( -name "*api_key*" -o -name "*password*" -o -name "*secret*" -o -name "*.key" -o -name "*.pem" -o -name "*creds*.json" \) -not -path "./.venv/*" -not -path "./.git/*" | grep -v "creds/README.md")

if [ -n "$UNTRACKED_SENSITIVE" ]; then
    echo -e "${YELLOW}⚠️  Untracked sensitive files found:${NC}"
    echo "$UNTRACKED_SENSITIVE"
    echo -e "${YELLOW}🔧 Make sure these are properly ignored in .gitignore${NC}"
else
    echo -e "${GREEN}✅ No untracked sensitive files found${NC}"
fi

echo ""
echo "🔍 Checking for hardcoded secrets in code..."
SECRET_PATTERNS=("password\s*=\s*['\"][^'\"]+['\"]" "api_key\s*=\s*['\"][^'\"]+['\"]" "secret\s*=\s*['\"][^'\"]+['\"]" "token\s*=\s*['\"][^'\"]+['\"]")
for pattern in "${SECRET_PATTERNS[@]}"; do
    HARDCODED=$(grep -r -i -E "$pattern" src/ tests/ --include="*.py" --exclude-dir="__pycache__" 2>/dev/null | grep -v "# Example" | grep -v "# TODO" | grep -v "\.get(" | head -5)
    if [ -n "$HARDCODED" ]; then
        echo -e "${RED}❌ Potential hardcoded secrets found:${NC}"
        echo "$HARDCODED"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ No hardcoded secrets detected${NC}"
fi

echo ""
echo "🔍 Checking Git hooks..."
if [ -f ".git/hooks/pre-commit" ] && [ -x ".git/hooks/pre-commit" ]; then
    echo -e "${GREEN}✅ Pre-commit hook is installed and executable${NC}"
else
    echo -e "${YELLOW}⚠️  Pre-commit hook is not properly installed${NC}"
    echo -e "${YELLOW}🔧 Run: chmod +x .git/hooks/pre-commit${NC}"
fi

echo ""
echo "🔍 Checking .gitignore effectiveness..."
# Test if .gitignore would catch common sensitive files
TEST_FILES=("test_api_key.json" "test_secret.env" "test_creds.json")
for test_file in "${TEST_FILES[@]}"; do
    touch "$test_file"
    if git check-ignore "$test_file" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ .gitignore correctly ignores $test_file${NC}"
    else
        echo -e "${RED}❌ .gitignore does NOT ignore $test_file${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
    rm -f "$test_file"
done

echo ""
echo "🔍 Checking for large files..."
LARGE_FILES=$(find . -type f -size +50M -not -path "./.venv/*" -not -path "./.git/*" 2>/dev/null)
if [ -n "$LARGE_FILES" ]; then
    echo -e "${YELLOW}⚠️  Large files found (>50MB):${NC}"
    echo "$LARGE_FILES"
    echo -e "${YELLOW}🔧 Consider using Git LFS or adding to .gitignore${NC}"
else
    echo -e "${GREEN}✅ No large files found${NC}"
fi

echo ""
echo "🔍 Final Security Summary"
echo "========================"
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}🎉 All security checks passed!${NC}"
    echo -e "${GREEN}Your repository is secure for Git operations.${NC}"
else
    echo -e "${RED}⚠️  $ISSUES_FOUND security issues found.${NC}"
    echo -e "${YELLOW}Please review and fix the issues above before committing sensitive changes.${NC}"
fi

echo ""
echo "🔒 Security Best Practices:"
echo "• Always use 'git safe-commit' instead of 'git commit'"
echo "• Run 'scripts/maintenance/security_check.sh' before pushing to remote"
echo "• Keep credentials in the creds/ directory (already gitignored)"
echo "• Use environment variables for secrets in production"
echo "• Regularly audit your .gitignore file"

exit $ISSUES_FOUND
