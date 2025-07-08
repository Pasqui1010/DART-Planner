# DART-Planner Error Handling Policy

## Overview

This document defines the error handling policy for DART-Planner, ensuring consistent, robust, and maintainable error management across the entire system.

## Principles

1. **Explicit Error Handling**: All errors should be explicit, never silently ignored
2. **Domain-Specific Exceptions**: Use custom exception classes for different error domains
3. **Proper Error Propagation**: Catch exceptions at module boundaries, not deep inside logic
4. **Context Preservation**: Include relevant context when raising or wrapping exceptions
5. **Recovery Strategies**: Implement appropriate recovery mechanisms where possible
6. **Logging**: Log errors with sufficient context for debugging

## Exception Hierarchy

### Base Exception
- `DARTPlannerError`: Base exception for all DART-Planner errors

### Domain-Specific Exceptions
- `ConfigurationError`: Configuration-related errors (missing files, invalid settings)
- `DependencyError`: Dependency injection or resolution errors
- `CommunicationError`: Network, IPC, or communication protocol errors
- `ControlError`: Control system errors (controller failures, actuator issues)
- `PlanningError`: Planning algorithm errors (optimization failures, invalid goals)
- `HardwareError`: Hardware interface errors (connection failures, sensor issues)
- `ValidationError`: Input or data validation errors
- `SecurityError`: Authentication, authorization, or cryptographic errors

## Error Handling Patterns

### 1. Raising Exceptions

```python
from src.common.errors import ConfigurationError, HardwareError

# Good: Domain-specific exception with context
if not config_file.exists():
    raise ConfigurationError(f"Configuration file not found: {config_file}")

# Good: Wrapping lower-level exceptions with context
try:
    client.connect()
except ConnectionRefusedError as e:
    raise HardwareError(f"Failed to connect to hardware: {e}") from e
```

### 2. Catching and Propagating

```python
from src.common.errors import DARTPlannerError, CommunicationError

try:
    result = some_operation()
except CommunicationError as e:
    # Log the error and re-raise with additional context
    logger.error(f"Communication failed in {operation_name}: {e}")
    raise CommunicationError(f"{operation_name} failed: {e}") from e
except DARTPlannerError as e:
    # Re-raise DART-specific errors as-is
    raise
except Exception as e:
    # Wrap unexpected errors with domain context
    logger.error(f"Unexpected error in {operation_name}: {e}")
    raise DARTPlannerError(f"Unexpected error in {operation_name}: {e}") from e
```

### 3. Error Recovery

```python
from src.common.error_recovery import retry_with_backoff, RetryConfig

# Retry with exponential backoff
@retry_with_backoff(
    config=RetryConfig(max_attempts=3, base_delay=1.0),
    retryable_exceptions=(CommunicationError, HardwareError)
)
async def send_command(command):
    # Implementation that may fail
    pass

# Fallback strategy
from src.common.error_recovery import get_degradation_manager

manager = get_degradation_manager()
if manager.is_feature_degraded("planning"):
    trajectory = manager.execute_fallback("trajectory_planning", current_state)
```

## Recovery Strategies

### 1. Retry Logic

Use `retry_with_backoff` decorator for transient failures:

```python
from src.common.error_recovery import retry_with_backoff

@retry_with_backoff(
    config=RetryConfig(max_attempts=3, base_delay=1.0),
    retryable_exceptions=(CommunicationError, HardwareError)
)
async def connect_to_hardware():
    # Implementation
    pass
```

### 2. Fallback Mechanisms

Register fallback strategies for critical failures:

```python
from src.common.error_recovery import get_degradation_manager, HoverFallback

manager = get_degradation_manager()
manager.register_fallback("trajectory_planning", HoverFallback())

# When planning fails
try:
    trajectory = planner.plan_trajectory(current_state, goal)
except PlanningError:
    trajectory = manager.execute_fallback("trajectory_planning", current_state)
```

### 3. Circuit Breaker

Use circuit breaker pattern to prevent cascading failures:

```python
from src.common.error_recovery import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exception=CommunicationError
)

try:
    result = circuit_breaker.call(risky_operation)
except DARTPlannerError as e:
    # Handle circuit breaker failure
    pass
```

### 4. Graceful Degradation

Mark features as degraded when they fail repeatedly:

```python
from src.common.error_recovery import get_degradation_manager

manager = get_degradation_manager()

try:
    result = advanced_feature()
except DARTPlannerError as e:
    manager.mark_feature_degraded("advanced_feature", str(e))
    result = basic_feature()  # Fallback to basic functionality
```

## Module-Specific Guidelines

### Configuration Module
- Use `ConfigurationError` for all configuration-related issues
- Validate configuration early and fail fast
- Provide clear error messages with file paths and line numbers

### Hardware Module
- Use `HardwareError` for hardware interface issues
- Implement retry logic for connection failures
- Provide fallback to simulation when hardware is unavailable

### Communication Module
- Use `CommunicationError` for network and IPC issues
- Implement circuit breakers for external services
- Retry transient network failures with exponential backoff

### Planning Module
- Use `PlanningError` for algorithm failures
- Implement hover fallback for planning failures
- Validate inputs before planning to prevent errors

### Security Module
- Use `SecurityError` for authentication and authorization issues
- Never expose sensitive information in error messages
- Log security events for audit purposes

## Logging Guidelines

### Error Logging
```python
import logging

logger = logging.getLogger(__name__)

try:
    result = risky_operation()
except DARTPlannerError as e:
    logger.error(
        f"Operation failed: {e}",
        extra={
            "operation": "risky_operation",
            "parameters": {"param1": value1},
            "error_type": type(e).__name__
        }
    )
    raise
```

### Context Information
Always include relevant context in error logs:
- Operation name and parameters
- Module and function name
- Timestamp and request ID
- Error type and message
- Stack trace for unexpected errors

## Testing Error Handling

### Unit Tests
```python
import pytest
from src.common.errors import ConfigurationError

def test_configuration_error():
    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        load_config("nonexistent.yaml")
```

### Integration Tests
```python
def test_error_recovery():
    # Test that fallback strategies work
    manager = get_degradation_manager()
    manager.mark_feature_degraded("planning", "test")
    
    result = manager.execute_fallback("trajectory_planning", mock_state)
    assert result is not None
```

## Best Practices

1. **Fail Fast**: Detect and report errors as early as possible
2. **Fail Safe**: Ensure system remains in a safe state when errors occur
3. **Provide Context**: Include relevant information in error messages
4. **Log Appropriately**: Use appropriate log levels (ERROR, WARNING, INFO)
5. **Don't Suppress**: Never catch and ignore exceptions without good reason
6. **Use Type Hints**: Include exception types in function signatures
7. **Document Exceptions**: Document which exceptions functions may raise

## Migration Guide

### From Generic Exceptions
```python
# Before
raise ValueError("Invalid configuration")

# After
from src.common.errors import ConfigurationError
raise ConfigurationError("Invalid configuration")
```

### From Silent Failures
```python
# Before
try:
    result = operation()
except Exception:
    pass  # Silent failure

# After
try:
    result = operation()
except DARTPlannerError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Adding Recovery
```python
# Before
result = risky_operation()

# After
from src.common.error_recovery import retry_with_backoff

@retry_with_backoff()
def risky_operation():
    # Implementation
    pass
```

## Monitoring and Alerting

### Error Metrics
- Error rate by exception type
- Error rate by module/component
- Recovery success rate
- Circuit breaker state changes

### Alerting Rules
- High error rate (>5% for critical operations)
- Circuit breaker opening
- Feature degradation events
- Security error spikes

## Conclusion

This error handling policy ensures that DART-Planner operates reliably and safely, with clear error reporting and appropriate recovery mechanisms. All developers should follow these guidelines to maintain system robustness and observability. 