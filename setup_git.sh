#!/bin/bash

# Git setup script for Hot Durham project
echo "🚀 Setting up Git configuration for Hot Durham"
echo "=============================================="

# Set up commit message template
echo "📝 Setting up commit message template..."
git config commit.template .gitmessage

# Set up git hooks
echo "🪝 Setting up git hooks..."
git config core.hooksPath .githooks

# Set up git configuration
echo "⚙️ Configuring git settings..."
git config pull.rebase false
git config core.autocrlf false
git config init.defaultBranch main

# Set up user configuration (only if not already set)
if [ -z "$(git config user.name)" ]; then
    echo "👤 Setting up user configuration..."
    read -p "Enter your name: " user_name
    git config user.name "$user_name"
fi

if [ -z "$(git config user.email)" ]; then
    read -p "Enter your email: " user_email
    git config user.email "$user_email"
fi

# Set up useful aliases
echo "🔧 Setting up useful git aliases..."
git config alias.st status
git config alias.co checkout
git config alias.br branch
git config alias.ci commit
git config alias.unstage "reset HEAD --"
git config alias.last "log -1 HEAD"
git config alias.visual "!gitk"
git config alias.graph "log --oneline --graph --decorate --all"
git config alias.contributors "shortlog -sn"

# Create useful ignore patterns
echo "📋 Verifying .gitignore configuration..."
if [ ! -f .gitignore ]; then
    echo "⚠️ No .gitignore found - this should not happen!"
else
    echo "✅ .gitignore is properly configured"
fi

# Show current configuration
echo ""
echo "📊 Current Git Configuration:"
echo "============================="
echo "User: $(git config user.name) <$(git config user.email)>"
echo "Default branch: $(git config init.defaultBranch)"
echo "Hooks path: $(git config core.hooksPath)"
echo "Commit template: $(git config commit.template)"
echo ""

# Verify sensitive files are ignored
echo "🔒 Verifying sensitive files are properly ignored..."
sensitive_patterns=("creds/*.json" "*.env" "*.db" ".venv/")

for pattern in "${sensitive_patterns[@]}"; do
    if git check-ignore "$pattern" > /dev/null 2>&1; then
        echo "✅ $pattern is ignored"
    else
        echo "⚠️ Warning: $pattern may not be properly ignored"
    fi
done

echo ""
echo "🎉 Git setup completed successfully!"
echo ""
echo "📚 Quick reference:"
echo "  git st           - Show status"
echo "  git graph        - Show commit graph"
echo "  git contributors - Show contributors"
echo "  git unstage      - Unstage files"
echo ""
echo "📖 See GIT_WORKFLOW_GUIDE.md for detailed workflow instructions"
