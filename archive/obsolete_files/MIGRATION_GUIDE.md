# DART-Planner Migration Guide

## Overview

This guide documents the recent architectural changes in DART-Planner, including the migration from legacy DI container and configuration systems to improved versions with better type safety, performance, and maintainability.

## Changes Made

### 1. DI Container Migration

**Old System:** `dart_planner.common.di_container`  
**New System:** `dart_planner.common.di_container_v2`

**Key Improvements:**
- Better type safety with generic support
- Improved error handling and validation
- Enhanced performance with optimized dependency resolution
- Better support for real-time constraints

### 2. Configuration System Migration

**Old System:** `dart_planner.config.settings`  
**New System:** `dart_planner.config.frozen_config`

**Key Improvements:**
- Immutable configuration objects (frozen)
- Pydantic validation with strict type checking
- Environment variable integration
- Startup validation to prevent runtime issues
- Better security configuration management

## Compatibility Shims

To ensure a smooth transition, temporary compatibility shims have been added:

### DI Container Shim
- **File:** `src/dart_planner/common/di_container.py`
- **Purpose:** Re-exports everything from `di_container_v2`
- **Deprecation:** Issues warnings when legacy imports are used

### Config Shim
- **File:** `src/dart_planner/config/settings.py` (compatibility section)
- **Purpose:** Provides `get_config()` and `DARTPlannerConfig` aliases
- **Deprecation:** Issues warnings when legacy imports are used

## Migration Process

### Automated Migration

Use the provided migration script to automatically update imports:

```bash
# Dry run to see what would be changed
python scripts/migrate_imports.py

# Apply changes with backup
python scripts/migrate_imports.py --execute --backup

# Apply changes without backup
python scripts/migrate_imports.py --execute
```

### Manual Migration

If you prefer to migrate manually, update your imports:

**DI Container:**
```python
# Old
from dart_planner.common.di_container import get_container

# New
from dart_planner.common.di_container_v2 import get_container
```

**Configuration:**
```python
# Old
from dart_planner.config.settings import get_config, DARTPlannerConfig

# New
from dart_planner.config.frozen_config import get_frozen_config as get_config, DARTPlannerFrozenConfig as DARTPlannerConfig
```

## CI Workflow Consolidation

The CI workflows have been consolidated to reduce redundancy:

### Main CI Workflow
- **File:** `.github/workflows/quality-pipeline.yml`
- **Purpose:** Runs on all pushes and PRs
- **Includes:** Linting, type-checking, security audits, fast tests

### Nightly/Comprehensive Suite
- **File:** `.github/workflows/slow-suite.yml`
- **Purpose:** Runs on schedule or manual trigger
- **Includes:** Slow tests, integration tests, comprehensive coverage

### Removed Workflows
- `ci-optimized.yml` (consolidated into quality-pipeline)

## Build System Updates

### Cython Extension Support
Added build system configuration to `pyproject.toml`:

```toml
[build-system]
requires = [
    "setuptools>=61.0",
    "wheel",
    "cython>=3.0.0",
]
build-backend = "setuptools.build_meta"
```

This ensures Cython extensions (like `rt_control_extension.pyx`) are compiled during `pip install .`.

## Testing

### Shim Tests
Run the compatibility shim tests to verify everything works:

```bash
pytest tests/test_di_container_shim.py -v
```

### Full Test Suite
After migration, run the full test suite:

```bash
# Fast tests
pytest -m "not slow"

# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html
```

## Timeline

### Phase 1: Compatibility Shims (✅ Complete)
- Added temporary shims with deprecation warnings
- Updated build system for Cython support
- Consolidated CI workflows

### Phase 2: Migration (🔄 In Progress)
- Use migration script to update all imports
- Update documentation and examples
- Remove legacy code references

### Phase 3: Cleanup (📋 Planned)
- Remove compatibility shims
- Update all documentation
- Finalize new API

## Breaking Changes

### Removed Features
- Direct access to mutable configuration objects
- Legacy DI container registration methods
- Some deprecated configuration methods

### New Requirements
- Python 3.9+ (already required)
- Pydantic 2.x for configuration validation
- Cython 3.0+ for real-time extensions

## Troubleshooting

### Import Errors
If you see import errors after migration:

1. Check that you're using the new import paths
2. Verify the compatibility shims are still in place
3. Run the migration script again if needed

### Configuration Issues
If configuration doesn't work as expected:

1. Check that you're using the new frozen config API
2. Verify environment variables are set correctly
3. Check the configuration validation logs

### CI Failures
If CI is failing:

1. Ensure you're using the main quality pipeline
2. Check that all tests pass locally
3. Verify the build system is properly configured

## Support

For issues during migration:

1. Check this guide first
2. Review the migration script output
3. Open an issue with detailed error information
4. Include the migration report if available

## Future Plans

- Remove compatibility shims in v1.0.0
- Add more comprehensive configuration validation
- Enhance DI container with advanced features
- Improve real-time performance monitoring 