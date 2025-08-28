# Development Setup

This guide will help you set up a local development environment for the Hot Durham Environmental Monitoring System.

## 🛠️ Prerequisites

### Required Software

* **Python 3.11+** - Primary programming language
* **Git** - Version control
* **Code Editor** - VS Code, PyCharm, or your preferred IDE
* **Terminal/Command Line** - For running commands

### Optional but Recommended

* **Docker** - For containerized development
* **PostgreSQL** - Production database (SQLite used for development)
* **Redis** - Caching and task queue
* **Node.js** - For frontend tooling (if applicable)

## 📥 Initial Setup

### 1. Clone the Repository

```bash
# Clone the main repository
git clone https://github.com/your-org/hot-durham.git
cd hot-durham

# Or clone your fork
git clone https://github.com/your-username/hot-durham.git
cd hot-durham
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify Python version
python --version  # Should show 3.11.x
```

### 3. Install Dependencies

```bash
# With uv (preferred)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip sync requirements.txt
uv pip sync requirements-dev.txt

# Or with pip
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables
nano .env  # or use your preferred editor
```

Example `.env` file:

```bash
# Environment
ENVIRONMENT=development
DEBUG=True

# Database (SQLite for development)
DATABASE_URL=sqlite:///data/development.db

# API Keys (get from respective services)
WEATHER_API_KEY=your_weather_underground_api_key
TSI_API_ENDPOINT=https://your-tsi-endpoint.com/api
TSI_API_KEY=your_tsi_api_key

# Google Sheets (optional for development)
GOOGLE_SHEETS_ENABLED=False
GOOGLE_CREDENTIALS_PATH=creds/service_account.json

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/development.log

# Security
SECRET_KEY=your-development-secret-key

# Cache (Redis optional for development)
CACHE_ENABLED=False
REDIS_URL=redis://localhost:6379/0
```

### 5. Initialize Database

```bash
# Create necessary directories
mkdir -p data logs temp processed reports

# Initialize database
python src/database/init_db.py

# Run any database migrations
python scripts/migrate_database.py
```

### 6. Verify Installation

```bash
# Run quick start script
python quick_start.py --development

# Run system health check
python quick_start.py --health-check

# Test API connections (optional)
python -c "from src.utils.api_client import APIClient; print('API OK' if APIClient().test_connection() else 'Check API keys')"
```

## 🔧 Development Tools

### Code Formatting and Linting

```bash
# Install pre-commit hooks
pre-commit install

# Format code with Black
black .

# Sort imports with isort
isort .

# Lint code with flake8
flake8 .

# Type checking with mypy
mypy src/
```

### Code Editor Configuration

**VS Code Settings (`.vscode/settings.json`):**

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

**PyCharm Configuration:**

* Set Python interpreter to `./venv/bin/python`
* Enable Black formatter
* Configure pytest as test runner
* Set up flake8 as external tool

### Git Configuration

```bash
# Set up git hooks
cp .githooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit

# Configure git (if not already done)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Set up commit message template
git config commit.template .gitmessage
```

## 🧪 Testing Setup

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api_client.py

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

### Test Configuration

Create `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    api: API tests
```

### Mock Data for Testing

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock
from src.database.db_manager import DatabaseManager

@pytest.fixture
def mock_api_client():
    """Mock API client for testing."""
    mock_client = Mock()
    mock_client.get_weather_data.return_value = {
        'temperature': 25.0,
        'humidity': 60.0,
        'timestamp': '2025-06-15T12:00:00Z'
    }
    return mock_client

@pytest.fixture
def test_database():
    """Test database fixture."""
    db = DatabaseManager(database_url='sqlite:///:memory:')
    db.create_tables()
    yield db
    db.close()
```

## 🗂️ Project Structure Understanding

### Core Directories

```text
hot-durham/
├── src/                    # Main application code
│   ├── config/            # Configuration management
│   ├── database/          # Database models and operations
│   ├── monitoring/        # Dashboard and monitoring
│   ├── utils/            # Utility functions
│   └── validation/       # Data validation
├── scripts/              # Standalone scripts
├── tests/               # Test files
├── config/              # Configuration files
├── data/               # Data storage
├── logs/               # Log files
├── docs/               # Documentation
└── wiki/               # Project wiki
```

### Key Files

```python
# src/config/config_manager.py - Configuration management
# src/database/db_manager.py - Database operations
# src/monitoring/dashboard.py - Web dashboard
# src/utils/api_client.py - External API integration
# quick_start.py - Main entry point
# scripts/production_manager.py - Production utilities
```

## 🚀 Running the Development Environment

### Start the Application

```bash
# Start in development mode
python quick_start.py --development

# Start with debug logging
python quick_start.py --debug

# Start dashboard only
python src/monitoring/dashboard.py

# Start background workers
python scripts/production_manager.py --worker
```

### Access the Application

* **Dashboard**: <http://localhost:5000>
* **API**: <http://localhost:5000/api>
* **Health Check**: <http://localhost:5000/health>

### Development Workflow

1. **Create Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**

   * Edit code
   * Add tests
   * Update documentation

3. **Test Changes**

   ```bash
   # Run tests
   pytest
   
   # Check code quality
   flake8 .
   black --check .
   mypy src/
   ```

4. **Commit Changes**

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**

   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

## 🔍 Debugging and Troubleshooting

### Common Development Issues

#### 1. **Import Errors**

```bash
# Make sure you're in the project root and virtual environment is activated
pwd  # Should show hot-durham directory
which python  # Should show venv path
```

#### **2. Database Issues**

```bash
# Reset development database
rm data/development.db
python src/database/init_db.py
```

#### **3. API Connection Issues**

```bash
# Test API connectivity
python -c "
from src.utils.api_client import APIClient
client = APIClient()
print(client.test_connection())
"
```

#### **4. Port Already in Use**

```bash
# Find and kill process using port 5000
lsof -ti:5000 | xargs kill -9
```

### Debugging Tools

#### **1. Python Debugger**

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use modern debugger
import ipdb; ipdb.set_trace()
```

#### **2. Logging**

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message here")
```

#### **3. Profile Performance**

```bash
# Profile application performance
python -m cProfile -o profile.stats quick_start.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
```

## 📚 Learning Resources

### Project Documentation

* [Architecture Overview](Architecture-Overview.md)
* [API Documentation](API-Documentation.md)
* [Configuration Reference](Configuration-Reference.md)

### Python Resources

* [Python 3.11 Documentation](https://docs.python.org/3.11/)
* [Flask Documentation](https://flask.palletsprojects.com/)
* [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

### Development Best Practices

* [PEP 8 Style Guide](https://pep8.org/)
* [Python Type Hints](https://docs.python.org/3/library/typing.html)
* [pytest Documentation](https://docs.pytest.org/)

## 🤝 Contributing

### Before Contributing

1. Read [Contributing Guidelines](Contributing-Guidelines.md)
2. Set up development environment (this guide)
3. Run tests to ensure everything works
4. Check existing issues and pull requests

### Development Standards

* Follow PEP 8 style guidelines
* Write comprehensive tests
* Document new features
* Use type hints
* Keep commits atomic and well-described

---

*This development setup guide is regularly updated. If you encounter issues not covered here, please contribute improvements back to help other developers.*

Last updated: June 15, 2025
