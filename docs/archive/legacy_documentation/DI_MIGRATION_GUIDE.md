# Dependency Injection (DI) Migration Guide

## Overview

This guide documents the migration to the new DI container v2 in DART-Planner, including rationale, usage patterns, and best practices.

### Why DI v2?
- Stronger type safety and modularity
- Explicit service registration and resolution
- Improved testability and maintainability

## Usage Patterns

### Registering Services
```python
from dart_planner.common.di_container_v2 import get_container
container = get_container()
container.register_singleton(MyService, MyServiceImpl)
```

### Resolving Services
```python
service = container.resolve(MyService)
```

### Example: Registering and Using a Planner
```python
from dart_planner.common.di_container_v2 import get_container
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner

container = get_container()
planner = container.resolve(SE3MPCPlanner)
```

## Migration Steps
1. Replace imports of the old DI container with `get_container()` from `di_container_v2`.
2. Register all core services at startup.
3. Replace legacy `container.get_service('name')` with `container.resolve(ServiceClass)`.
4. Remove direct instantiation of shared services in favor of DI.

## Best Practices
- Register all singletons and factories at startup.
- Use type annotations for all service interfaces.
- Prefer constructor injection for dependencies.
- Use DI for test mocks and overrides.

## Notes
- The old DI container is deprecated and removed.
- All modules should use the new DI API for service resolution.
