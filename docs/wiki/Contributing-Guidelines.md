# Contributing Guidelines

Thank you for your interest in contributing to the Hot Durham Environmental Monitoring System! This document outlines how to contribute effectively to the project.

## 🤝 Ways to Contribute

### Code Contributions
* Bug fixes and improvements
* New features and enhancements
* Performance optimizations
* Documentation updates
* Test coverage improvements

### Non-Code Contributions
* Bug reports and feature requests
* Documentation improvements
* User experience feedback
* Community support
* Translation assistance

## 🚀 Getting Started

### 1. Set Up Development Environment

First, fork the repository and clone it locally:

```bash
git clone https://github.com/your-username/hot-durham.git
cd hot-durham
```

Set up your development environment:

```bash
# Preferred (uv)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip sync requirements.txt
uv pip sync requirements-dev.txt

# Or classic virtualenv + pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Create a Branch

Create a feature branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b bugfix/issue-description
```

## 📝 Development Guidelines

### Code Style

We follow Python PEP 8 standards with some project-specific conventions:

* **Line Length**: 88 characters (Black formatter standard)
* **Indentation**: 4 spaces
* **Naming Conventions**:
  * Classes: `PascalCase`
  * Functions/methods: `snake_case`
  * Constants: `UPPER_SNAKE_CASE`
  * Files: `snake_case.py`

### Code Formatting

We use automated code formatting tools:

```bash
# Install formatting tools
pip install black isort flake8

# Format code
black .
isort .

# Check code quality
flake8 .
```

### Testing Requirements

All contributions must include appropriate tests:

* **Unit Tests**: For individual functions/classes
* **Integration Tests**: For system components
* **End-to-End Tests**: For complete workflows

Run tests before submitting:

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test file
python -m pytest tests/test_specific_module.py
```

### Documentation

* Update docstrings for all new functions/classes
* Follow Google-style docstring format
* Update relevant wiki pages
* Include inline comments for complex logic

Example docstring:

```python
def process_sensor_data(data: dict, sensor_type: str) -> dict:
    """Process raw sensor data into standardized format.
    
    Args:
        data: Raw sensor data dictionary
        sensor_type: Type of sensor ('temperature', 'humidity', etc.)
        
    Returns:
        Processed data dictionary with standardized fields
        
    Raises:
        ValueError: If sensor_type is not supported
        KeyError: If required data fields are missing
    """
```

## 🔧 Development Workflow

### 1. Planning Your Contribution

Before starting work:
* Check existing issues and pull requests
* Create or comment on relevant issues
* Discuss major changes with maintainers
* Break large features into smaller, manageable pieces

### 2. Implementation

* Write clean, readable code
* Follow existing patterns and conventions
* Add comprehensive tests
* Update documentation as needed
* Commit frequently with clear messages

### 3. Commit Guidelines

Use clear, descriptive commit messages:

```bash
# Good commit messages
git commit -m "Add temperature anomaly detection algorithm"
git commit -m "Fix API rate limiting issue in weather data fetcher"
git commit -m "Update dashboard UI for mobile responsiveness"

git commit -m "feat: add real-time alert system"
git commit -m "fix: resolve database connection timeout"
git commit -m "docs: update API documentation"
```

## 📋 Pull Request Process

### 1. Before Submitting

Ensure your contribution:
* [ ] Follows code style guidelines
* [ ] Includes appropriate tests
* [ ] Passes all existing tests
* [ ] Updates relevant documentation
* [ ] Resolves any merge conflicts

### 2. Pull Request Template

When creating a pull request, include:

```markdown
## Description
Brief description of changes made

## Related Issue
Closes #123 (if applicable)

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Other (specify)

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No merge conflicts
```

### 3. Review Process

* Maintainers will review your pull request
* Address any feedback or requested changes
* Keep discussions constructive and professional
* Be patient - reviews take time

## 🐛 Bug Reports

When reporting bugs, please include:

### Required Information
* **Environment**: OS, Python version, system specs
* **Version**: Hot Durham version or commit hash
* **Description**: Clear description of the issue
* **Steps to Reproduce**: Detailed reproduction steps
* **Expected Behavior**: What should happen
* **Actual Behavior**: What actually happens
* **Logs**: Relevant error messages or logs

### Bug Report Template

```markdown
**Environment Information**
- OS: [e.g., Ubuntu 20.04, Windows 10, macOS 12]
- Python Version: [e.g., 3.11.2]
- Hot Durham Version: [e.g., 2.0.0]

**Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Logs/Error Messages**
```
Include relevant logs or error messages
```

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

For new feature requests:

* Check if the feature already exists or is planned
* Describe the use case and benefits
* Provide detailed specifications if possible
* Consider implementation complexity
* Be open to alternative solutions

## 🔒 Security Issues

For security-related issues:
* **DO NOT** create public issues
* Email security concerns to: [security@hotdurham.org]
* Include detailed information about the vulnerability
* Allow reasonable time for fixes before disclosure

## 🏆 Recognition

Contributors will be recognized:
* Listed in project contributors
* Credited in release notes
* Badge/recognition for significant contributions
* Potential maintainer opportunities

## 📞 Getting Help

Need help with contributions?

* Check existing documentation and wiki
* Ask questions in GitHub discussions
* Join our community channels
* Contact maintainers directly

## 📜 Code of Conduct

We are committed to providing a welcoming and inclusive environment:

* Be respectful and constructive
* Welcome newcomers and different perspectives
* Focus on what's best for the community
* Show empathy towards others
* Accept responsibility for mistakes

## 🔄 Maintenance and Support

### Project Maintenance
* Regular dependency updates
* Security patch management
* Performance monitoring
* Documentation maintenance

### Long-term Support
* Bug fixes for stable releases
* Security updates
* Migration guides for major changes
* Backward compatibility considerations

---

Thank you for contributing to Hot Durham! Your efforts help make environmental monitoring more accessible and effective for everyone.

*Last updated: June 15, 2025*
