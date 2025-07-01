# Hot Durham Git Workflow Guide

## 🚀 Getting Started

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd "Hot Durham"

# Set up Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up git hooks and configuration
git config core.autocrlf false
git config pull.rebase false
```

## 📝 Commit Message Convention

We follow a structured commit message format for better project tracking:

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, semicolons, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **perf**: Performance improvements
- **ci**: Continuous integration changes

### Scopes
- **data**: Data collection and processing
- **api**: API endpoints and services
- **ui**: User interface and dashboards
- **db**: Database operations
- **config**: Configuration changes
- **monitor**: Monitoring and logging
- **test**: Testing infrastructure
- **deploy**: Deployment and production

### Examples
```bash
feat(data): add enhanced TSI sensor validation

- Implement comprehensive data validation for TSI sensors
- Add anomaly detection for temperature readings
- Include retry logic for failed API calls

Closes #123

fix(api): resolve rate limiting issues

- Implement exponential backoff for API requests
- Add proper error handling for 429 responses
- Update documentation for rate limit configuration

perf(db): optimize database query performance

- Add indexes for frequently queried columns
- Implement connection pooling
- Reduce query execution time by 60%
```

## 🌳 Branch Strategy

### Main Branches
- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`staging`**: Pre-production testing

### Feature Branches
- **Format**: `feature/<feature-name>`
- **Example**: `feature/enhanced-logging`, `feature/api-rate-limiting`

### Hotfix Branches
- **Format**: `hotfix/<issue-description>`
- **Example**: `hotfix/sensor-data-corruption`

### Workflow
```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/new-enhancement

# Work on feature
git add .
git commit -m "feat(data): implement new enhancement"

# Push feature branch
git push origin feature/new-enhancement

# Create pull request to develop
# After review and approval, merge to develop

# Release to production
git checkout main
git merge develop
git tag v1.2.0
git push origin main --tags
```

## 🔍 Pre-commit Checklist

Before committing, ensure:

### Code Quality
- [ ] Code follows project style guidelines
- [ ] No sensitive data (API keys, credentials) in commit
- [ ] All new files have appropriate headers/documentation
- [ ] No debugging print statements or console.logs

### Testing
- [ ] Run comprehensive test suite: `python tests/comprehensive_test_suite.py`
- [ ] All tests pass with >80% success rate
- [ ] New features include appropriate tests
- [ ] Manual testing completed for critical paths

### Documentation
- [ ] README.md updated if needed
- [ ] Code comments added for complex logic
- [ ] Configuration changes documented
- [ ] API changes documented

### Environment
- [ ] Requirements.txt updated if new packages added
- [ ] Environment variables documented
- [ ] .gitignore updated for new file types

## 🚢 Release Process

### Version Numbering
We use Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Steps
```bash
# 1. Ensure develop is ready
git checkout develop
python tests/comprehensive_test_suite.py
python scripts/production_manager.py deploy

# 2. Create release branch
git checkout -b release/v1.2.0

# 3. Update version numbers and changelog
# Edit version in setup.py, __init__.py, etc.

# 4. Final testing
python tests/comprehensive_test_suite.py
python scripts/production_manager.py monitor

# 5. Merge to main
git checkout main
git merge release/v1.2.0
git tag v1.2.0
git push origin main --tags

# 6. Merge back to develop
git checkout develop
git merge main
git push origin develop

# 7. Delete release branch
git branch -d release/v1.2.0
```

## 🛡️ Security Guidelines

### Sensitive Data
- **Never commit**: API keys, passwords, tokens, certificates
- **Use**: Environment variables and credential files in `creds/`
- **Verify**: Run `git log --all --grep="password\|key\|secret"` before pushing

### File Security
```bash
# Check for sensitive data before commit
git diff --cached | grep -i "password\|key\|secret\|token"

# Remove sensitive data from history (if accidentally committed)
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch path/to/sensitive/file' \
--prune-empty --tag-name-filter cat -- --all
```

## 📊 Monitoring and Maintenance

### Weekly Tasks
- [ ] Review open pull requests
- [ ] Check system health: `python scripts/production_manager.py monitor`
- [ ] Update dependencies if needed
- [ ] Review and clean up old branches

### Monthly Tasks
- [ ] Security audit: `git log --grep="fix\|security"`
- [ ] Performance review: analyze test suite results
- [ ] Documentation review and updates
- [ ] Backup verification

## 🔧 Troubleshooting

### Common Issues

**Large commits**:
```bash
# Split large commits
git reset HEAD~1
git add -p  # Add changes in chunks
git commit -m "feat(data): part 1 of enhancement"
```

**Merge conflicts**:
```bash
# Resolve conflicts
git status  # See conflicted files
# Edit files to resolve conflicts
git add .
git commit -m "resolve: merge conflict in data processing"
```

**Sensitive data committed**:
```bash
# Remove from last commit
git reset HEAD~1
git add .  # Add only safe files
git commit -m "fix: remove sensitive data"

# Remove from history (use with caution)
git filter-branch --index-filter 'git rm --cached --ignore-unmatch creds/secret.json'
```

## 📚 Resources

- [Git Documentation](https://git-scm.com/doc)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)

---

**Remember**: Good git practices make collaboration easier and project history cleaner! 🌟
