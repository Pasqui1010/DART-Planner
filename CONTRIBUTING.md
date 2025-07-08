# Contributing to DART-Planner

## Development Setup

### Prerequisites
- Python 3.10 or 3.11
- Git
- Virtual environment (recommended)

### Installation
```bash
git clone <repository-url>
cd DART-Planner
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
pip install -e .
```

## Code Quality Standards

### Code Formatting
We use automated formatting tools to maintain consistent code style:

- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **mypy**: Type checking

All formatting checks are **hard failures** in CI - code must be properly formatted to pass.

### Running Quality Checks
```bash
# Format code
black src/ tests/ experiments/ scripts/
isort src/ tests/ experiments/ scripts/

# Lint and type check
flake8 src/ tests/
mypy src/

# Run all quality checks
python -m pytest tests/ -m "not slow"
```

## Architecture Guidelines

### Dependency Injection
Use the new `di_container_v2` system for all dependency management:

```python
from dart_planner.common.di_container_v2 import get_container

# Get dependencies from container
planner = get_container().create_planner_container().get_se3_planner()
controller = get_container().create_control_container().get_geometric_controller()
```

### Configuration
Use the frozen configuration system for all configuration needs:

```python
from dart_planner.config.frozen_config import get_frozen_config

config = get_frozen_config()
control_freq = config.hardware.control_frequency
```

### Units System
Use the units system for all physical quantities:

```python
from dart_planner.common.units import Q_, to_float

# Create quantities with units
velocity = Q_(10.0, 'm/s')
position = Q_([1, 2, 3], 'm')

# Convert to float for calculations
vel_mag = to_float(velocity)
```

## Testing

### Test Structure
- Unit tests: `tests/`
- Integration tests: `tests/integration/`
- E2E tests: `tests/e2e/`
- Slow tests: Marked with `@pytest.mark.slow`

### Running Tests
```bash
# Fast tests only
pytest -m "not slow"

# All tests
pytest

# Specific test file
pytest tests/test_units_safety_comprehensive.py
```

### Test Coverage
Maintain >75% test coverage. Coverage reports are generated in CI.

## Security

### Security Checks
We use multiple security tools:
- **Bandit**: Static security analysis
- **Safety**: Dependency vulnerability scanning
- **pip-audit**: Package vulnerability scanning

All security checks are **hard failures** in CI.

### Secret Management
- Never commit secrets to the repository
- Use environment variables for configuration
- Follow the `.env.example` template for local development

## Pull Request Process

### Before Submitting
1. Ensure all quality checks pass locally
2. Run the full test suite
3. Update documentation if needed
4. Follow the PR template

### CI Requirements
All PRs must pass:
- ✅ Code formatting (Black, isort)
- ✅ Linting (Flake8)
- ✅ Type checking (mypy)
- ✅ Security scans (Bandit, Safety, pip-audit)
- ✅ Test suite (fast tests)
- ✅ Coverage requirements (>75%)

### Review Process
1. Automated checks must pass
2. At least one maintainer review required
3. Address all review comments
4. Merge only after approval

## Migration Status

### ✅ Completed Migrations
- **DI System**: Migrated to `di_container_v2`
- **Configuration**: Migrated to `frozen_config`
- **Units System**: Integrated and tested

### Current Architecture
- Modern dependency injection with lifecycle management
- Immutable, type-safe configuration
- Comprehensive units system for physical quantities
- Real-time capable control and planning systems

## Getting Help

- Check existing issues and documentation
- Create detailed bug reports with reproduction steps
- For feature requests, provide clear use cases
- Join discussions in issues and pull requests

---

**Last updated:** 2024-12-19
