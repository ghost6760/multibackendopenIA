# Tests for Multi-Agent System

This directory contains unit and integration tests for the multi-agent conversational AI platform.

## Test Structure

```
tests/
├── __init__.py
├── unit/                           # Unit tests for individual components
│   ├── test_audit_manager.py      # AuditManager tests
│   ├── test_email_service.py      # EmailService tests
│   └── test_compensation_orchestrator.py  # CompensationOrchestrator tests
└── integration/                    # Integration tests
    └── test_tools_integration.py   # End-to-end tools integration tests
```

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_audit_manager.py -v

# Specific test class
pytest tests/unit/test_audit_manager.py::TestAuditManager -v

# Specific test method
pytest tests/unit/test_audit_manager.py::TestAuditManager::test_log_action_basic -v
```

### Run Tests with Markers

```bash
# Run only unit tests (if marked)
pytest -m unit

# Run only integration tests (if marked)
pytest -m integration

# Run tests that don't require Redis
pytest -m "not requires_redis"
```

## Test Coverage

Current test coverage:

- **AuditManager**: ~95% (24 tests)
- **EmailService**: ~90% (18 tests)
- **CompensationOrchestrator**: ~90% (20 tests)
- **Tools Integration**: ~85% (12 tests)

Total: **74 tests**

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import MagicMock, patch

class TestYourComponent:
    """Test suite for YourComponent"""

    @pytest.fixture
    def your_fixture(self):
        """Setup test fixture"""
        # Setup code here
        return test_object

    def test_basic_functionality(self, your_fixture):
        """Test basic functionality"""
        # Arrange
        input_data = {...}

        # Act
        result = your_fixture.method(input_data)

        # Assert
        assert result is not None
        assert result["success"] is True
```

### Integration Test Template

```python
class TestYourIntegration:
    """Integration test for multiple components"""

    @pytest.fixture
    def full_system(self):
        """Setup full system"""
        # Setup all components
        return {
            "component1": ...,
            "component2": ...
        }

    def test_end_to_end_flow(self, full_system):
        """Test complete flow"""
        # Test integration between components
        ...
```

## Mocking Guidelines

### Mock Redis

```python
@pytest.fixture
def redis_mock(self):
    redis = MagicMock()
    redis.setex = MagicMock(return_value=True)
    redis.get = MagicMock(return_value=None)
    redis.sadd = MagicMock(return_value=True)
    return redis
```

### Mock Services

```python
@pytest.fixture
def email_service_mock(self):
    service = MagicMock()
    service.send_email.return_value = {"success": True}
    return service
```

## Continuous Integration

Tests run automatically on:
- Every push to feature branches
- Pull requests to main/develop
- Scheduled nightly builds

## Troubleshooting

### Issue: Tests fail with "ModuleNotFoundError"

**Solution**: Install dependencies and set PYTHONPATH

```bash
pip install -r requirements.txt
export PYTHONPATH="${PYTHONPATH}:/path/to/multibackendopenIA"
pytest
```

### Issue: Redis connection errors

**Solution**: Use mocks or run Redis locally

```bash
# Option 1: Run Redis with Docker
docker run -d -p 6379:6379 redis:alpine

# Option 2: Skip Redis tests
pytest -m "not requires_redis"
```

### Issue: Import errors in tests

**Solution**: Ensure proper package structure

```bash
# Add __init__.py to all directories
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
```

## Best Practices

1. **One assertion per test** (when possible)
2. **Use descriptive test names** (`test_send_email_with_invalid_address`)
3. **Mock external dependencies** (Redis, SMTP, APIs)
4. **Test both success and failure paths**
5. **Use fixtures for common setup**
6. **Clean up resources in teardown**

## Test Metrics

Target metrics:
- **Code Coverage**: > 80%
- **Test Execution Time**: < 30 seconds
- **Test Success Rate**: 100%

Current metrics can be viewed with:

```bash
pytest --cov=app --cov-report=term-missing
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain > 80% coverage
4. Document complex test scenarios

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Mock](https://pytest-mock.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
