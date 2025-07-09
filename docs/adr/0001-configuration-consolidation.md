# ADR-0001: Configuration System Consolidation

## Status

**Accepted** - 2024-12-19

## Context

DART-Planner had multiple configuration systems:
- Legacy `dart_planner.config.settings` module with global state
- Legacy `dart_planner.config.real_time_config` module with separate real-time settings
- New `dart_planner.config.frozen_config` module with Pydantic validation

This created:
- **Configuration Duplication**: Two sources of truth for configuration
- **Inconsistent Access Patterns**: Different ways to access config depending on which module was used
- **No Type Safety**: Legacy modules lacked validation and type checking
- **Maintenance Overhead**: Changes needed to be made in multiple places

## Decision

**Consolidate all configuration into a single, immutable system using `dart_planner.config.frozen_config`.**

### What Was Done

1. **Extended `RealTimeConfig`**: Merged all real-time configuration options from `real_time_config.py` into the central `RealTimeConfig` class in `frozen_config.py`.

2. **Enhanced Environment Variable Support**: Added comprehensive environment variable mappings for all real-time settings (e.g., `DART_RT_CONTROL_FREQUENCY_HZ`, `DART_RT_ENABLE_OS`).

3. **Removed Legacy Modules**: 
   - Deleted `src/dart_planner/config/real_time_config.py`
   - Updated all imports to use `frozen_config`

4. **Migration Support**: Created migration scripts and guides to help users transition.

### Technical Details

- **Immutable Configuration**: All config objects are frozen using Pydantic's `frozen = True`
- **Validation**: Comprehensive validation at startup with meaningful error messages
- **Environment Integration**: All settings can be overridden via environment variables
- **Type Safety**: Full type annotations and Pydantic validation

## Consequences

### Positive

- **Single Source of Truth**: All configuration is now centralized
- **Type Safety**: Pydantic validation prevents runtime configuration errors
- **Immutability**: Prevents accidental runtime modification
- **Better Developer Experience**: Clear, consistent API for accessing configuration
- **Environment Flexibility**: Easy to override settings for different environments

### Negative

- **Migration Effort**: Existing code needed updates (mitigated by migration scripts)
- **Learning Curve**: New API requires understanding (mitigated by documentation)

### Risks

- **Breaking Changes**: Some existing code may need updates
- **Validation Strictness**: Stricter validation may reveal existing configuration issues

## Implementation

### Migration Process

1. **Automated Migration**: Scripts identify and update legacy imports
2. **Manual Review**: Migration guide provides step-by-step instructions
3. **Validation**: Tests ensure configuration works correctly

### Code Examples

**Before (Legacy)**:
```python
from dart_planner.config.real_time_config import get_real_time_config
config = get_config()
rt_config = get_real_time_config(config)
frequency = rt_config.task_timing.control_loop_frequency_hz
```

**After (Consolidated)**:
```python
from dart_planner.config.frozen_config import get_frozen_config
config = get_frozen_config()
frequency = config.real_time.control_loop_frequency_hz
```

## Related ADRs

- None yet

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Configuration Migration Guide](../REAL_TIME_CONFIG_MIGRATION_GUIDE.md)
- [Frozen Configuration Implementation](../src/dart_planner/config/frozen_config.py) 