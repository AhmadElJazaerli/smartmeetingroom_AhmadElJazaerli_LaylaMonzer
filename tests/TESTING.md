# Testing Guide

## Test Structure

The project has two types of tests:

### Integration Tests (`tests/`)
- `test_users.py` - Full API tests for user endpoints
- `test_rooms.py` - Full API tests for room endpoints  
- `test_bookings.py` - Full API tests for booking endpoints
- `test_reviews.py` - Full API tests for review endpoints

### Unit Tests (`tests/unit/`)
- `test_auth.py` - Password hashing, JWT tokens, authentication logic
- `test_cache.py` - TTL cache functionality
- `test_config.py` - Configuration management
- `test_schemas.py` - Pydantic schema validation

## Running Tests

### Run All Tests
```powershell
pytest tests/
```

### Run Only Unit Tests
```powershell
pytest tests/unit/
```

### Run Only Integration Tests
```powershell
pytest tests/test_*.py
```

### Run Specific Test File
```powershell
pytest tests/unit/test_auth.py
pytest tests/test_users.py
```

### Run Specific Test Function
```powershell
pytest tests/unit/test_auth.py::TestPasswordHashing::test_password_hash_and_verify
```

### Verbose Output
```powershell
pytest tests/ -v
```

### Show Print Statements
```powershell
pytest tests/ -s
```

### Stop on First Failure
```powershell
pytest tests/ -x
```

## Coverage Reports

### Basic Coverage Report (Terminal)
```powershell
pytest tests/ --cov=common --cov=services
```

### Coverage with Missing Lines
```powershell
pytest tests/ --cov=common --cov=services --cov-report=term-missing
```

### HTML Coverage Report (Recommended)
```powershell
pytest tests/ --cov=common --cov=services --cov-report=html
```
Then open `htmlcov/index.html` in your browser to see detailed coverage.

### Coverage for Specific Module
```powershell
pytest tests/unit/ --cov=common.auth --cov-report=html
```

### XML Coverage Report (for CI/CD)
```powershell
pytest tests/ --cov=common --cov=services --cov-report=xml
```

### Combined Coverage Report
```powershell
pytest tests/ --cov=common --cov=services --cov-report=term --cov-report=html --cov-report=xml
```

## Coverage Configuration

Coverage settings are in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q"
testpaths = ["tests"]
```

To add coverage defaults, you can add:
```toml
[tool.coverage.run]
source = ["common", "services"]
omit = ["*/tests/*", "*/__pycache__/*", "*/migrations/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

## Quick Commands Reference

| Command | Description |
|---------|-------------|
| `pytest tests/` | Run all tests |
| `pytest tests/unit/` | Run only unit tests |
| `pytest tests/ -v` | Verbose output |
| `pytest tests/ -x` | Stop on first failure |
| `pytest tests/ -s` | Show print statements |
| `pytest tests/ --cov=common --cov=services` | Run with coverage |
| `pytest tests/ --cov=common --cov-report=html` | Generate HTML coverage report |
| `pytest -k "test_password"` | Run tests matching pattern |

## Viewing HTML Coverage Report

After generating HTML coverage:
```powershell
# Windows
start htmlcov/index.html

# Or navigate to the file in File Explorer and open it
```

The HTML report shows:
- Overall coverage percentage
- Line-by-line coverage for each file
- Missing lines highlighted in red
- Branch coverage information

## Coverage Goals

Aim for:
- **Unit tests**: 80%+ coverage on `common/` modules
- **Integration tests**: Cover all API endpoints and main user flows
- **Critical paths**: 100% coverage on authentication, authorization, and data validation

## Tips

1. **Run unit tests frequently** - they're fast and catch bugs early
2. **Use coverage to find untested code** - focus on critical paths first
3. **Integration tests are slower** - use them to verify full workflows
4. **Mock external dependencies** in unit tests (database, HTTP calls)
5. **Use `-x` flag** during development to stop on first failure
