# CONTRIBUTING

## Code Style & Linting

This project enforces code style and quality using Black, isort, Flake8 (with docstring and annotation checks), yamllint, markdownlint, and import-linter.

### Local Pre-commit Hooks

We use [pre-commit](https://pre-commit.com/) to provide fast feedback before you push code.

**Setup:**

```bash
pip install pre-commit
pre-commit install
```

This will automatically run formatters and linters on changed files before each commit.

**To run all hooks on all files:**

```bash
pre-commit run --all-files
```

### Manual Linting/Formatting

- **Black:** `black src/ tests/ scripts/`
- **isort:** `isort src/ tests/ scripts/`
- **Flake8:** `flake8 src/ tests/ scripts/`
- **Yamllint:** `yamllint .`
- **Markdownlint:** `markdownlint *.md docs/`
- **Import-linter:** `lint-imports --config importlinter.ini`

### Architectural Boundaries

We use [import-linter](https://import-linter.readthedocs.io/) to enforce architectural boundaries. For example:
- `control` and `planning` modules **cannot import** from `hardware`.
- See `importlinter.ini` for all contracts.

### Docstring & Type Annotation Checks

- **Docstrings:** Enforced via `flake8-docstrings`.
- **Type Annotations:** Enforced via `flake8-annotations`.

## Testing Strategy

DART-Planner uses a comprehensive testing strategy with multiple tiers to ensure code quality and reliability.

### Test Tiers

1. **Unit Tests** (`@pytest.mark.unit`): Fast, isolated tests for individual functions and classes
2. **Integration Tests** (`@pytest.mark.integration`): Tests that verify component interactions
3. **Performance Tests** (`@pytest.mark.performance`): Tests that ensure performance requirements are met
4. **Error Path Tests** (`@pytest.mark.error_path`): Tests for error handling and edge cases
5. **End-to-End Tests** (`@pytest.mark.e2e`): Complete workflow tests
6. **Real-time Tests** (`@pytest.mark.flaky`): Tests that may be non-deterministic (automatically retried)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test tiers
pytest -m "unit"           # Unit tests only
pytest -m "integration"    # Integration tests only
pytest -m "performance"    # Performance tests only
pytest -m "error_path"     # Error path tests only
pytest -m "e2e"           # End-to-end tests only

# Exclude slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov=dart_planner --cov-report=term-missing

# Run performance benchmarks
pytest tests/test_performance_regression.py --benchmark-only
```

### Test Fixtures

Common test fixtures are available in `tests/conftest.py`:
- `sample_drone_state`: Sample drone state for testing
- `mock_controller`: Mock controller for testing
- `mock_planner`: Mock planner for testing
- `mock_airsim_interface`: Mock AirSim interface
- `performance_benchmark`: Performance benchmarking utility

### Performance Testing

Performance tests ensure critical algorithms meet real-time requirements:

```python
from tests.utils.performance_testing import PerformanceBenchmark

def test_controller_performance(mock_controller, sample_drone_state):
    benchmark = PerformanceBenchmark("controller", threshold_seconds=0.001)
    
    def compute_control():
        mock_controller.compute_control(sample_drone_state)
    
    result = benchmark.assert_performance(compute_control, iterations=1000)
    assert result.passed
```

### Error Path Testing

Error path tests verify robust error handling:

```python
def test_invalid_inputs(mock_controller):
    # Test with None input
    with pytest.raises(ValueError):
        mock_controller.compute_control(None)
    
    # Test with invalid data
    with pytest.raises(ValueError):
        mock_controller.compute_control("invalid_data")
```

### Test Best Practices

1. **Use descriptive test names** that explain what is being tested
2. **Test both happy paths and error paths** for comprehensive coverage
3. **Use parametrized tests** for testing multiple scenarios
4. **Mock external dependencies** to ensure test isolation
5. **Add performance tests** for critical algorithms
6. **Mark flaky tests** with `@pytest.mark.flaky` for automatic retry
7. **Use fixtures** to reduce code duplication

### Test Coverage Requirements

- **Minimum coverage**: 75% for all code
- **Critical modules**: 90%+ coverage for safety-critical components
- **Error paths**: Comprehensive testing of error conditions

## CI/CD

All linters, formatters, and tests are run in CI. Please ensure your code passes all checks locally before pushing.

### CI Pipeline

The CI pipeline includes:
- Code formatting and linting
- Type checking with mypy
- Security scanning with bandit and safety
- Unit and integration tests
- Performance regression tests
- Error path tests
- Coverage reporting

## Dependency Injection (DI) Container: Quick Start & Best Practices

DART-Planner uses a modern DI container for modularity and testability. Here’s how to use it:

### Registering Services

```python
from dart_planner.common.di_container_v2 import create_container

# Create a container builder
builder = create_container()

# Register your config and services
builder.bootstrap_stage().register_config(MyConfigClass).done()
builder.runtime_stage().register_service(MyServiceInterface, MyServiceImpl).done()

# Build the container
container = builder.build()
```

### Resolving Services

```python
# Resolve a service by type
service = container.resolve(MyServiceInterface)
service.do_something()
```

### Validating the Dependency Graph

```python
# Validate the container for cycles and missing dependencies
container.validate_graph()
```

### Best Practices
- Register all configs in the bootstrap stage.
- Register services in the runtime stage.
- Use `validate_graph()` in tests and CI to catch issues early.
- Avoid global singletons; always resolve via the container.

See `src/dart_planner/common/di_container_v2.py` for advanced usage.
