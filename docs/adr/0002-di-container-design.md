# ADR-0002: Dependency Injection Container Design

## Status

**Accepted** - 2024-12-19

## Context

DART-Planner needed a robust dependency injection system that could:
- Handle complex dependency graphs with multiple subsystems (planning, control, hardware, communication)
- Support real-time constraints and performance requirements
- Prevent circular dependencies and provide clear error messages
- Enable testing and mocking without global state
- Support staged initialization (bootstrap → runtime → dynamic)

Previous approaches had issues:
- **Global Singletons**: Made testing difficult and created tight coupling
- **Manual Dependency Management**: Error-prone and hard to maintain
- **No Validation**: Circular dependencies and missing dependencies weren't caught early
- **Complex APIs**: Hard for new contributors to understand and use

## Decision

**Implement a staged dependency injection container with static graph validation and lifecycle management.**

### Design Principles

1. **Staged Registration**: Dependencies are registered in stages (bootstrap → runtime → dynamic)
2. **Static Validation**: Dependency graph is validated at build time, not runtime
3. **No Global State**: All containers are instance-based, no global singletons
4. **Type Safety**: Full type annotations and generic support
5. **Lifecycle Management**: Proper initialization and cleanup of dependencies

### Architecture

```
ContainerBuilder
├── BootstrapStageBuilder (config, logging, core services)
├── RuntimeStageBuilder (application services)
└── DIContainerV2 (built container with validation)
```

### Key Features

- **Cycle Detection**: Automatically detects circular dependencies
- **Dependency Resolution**: Topological sorting for correct initialization order
- **Lifecycle Phases**: Tracks dependency state (initializing → ready → running → stopped)
- **Validation**: Comprehensive validation with detailed error messages
- **Performance**: Optimized for real-time constraints

## Consequences

### Positive

- **Testability**: Easy to mock dependencies and test components in isolation
- **Maintainability**: Clear dependency relationships and error messages
- **Performance**: No runtime dependency resolution overhead
- **Type Safety**: Compile-time validation of dependency contracts
- **Flexibility**: Support for different registration patterns (singleton, factory, instance)

### Negative

- **Learning Curve**: More complex than simple global state
- **Boilerplate**: More code required for dependency registration
- **Validation Strictness**: Stricter validation may reveal existing architectural issues

### Risks

- **Over-Engineering**: Container might be too complex for simple use cases
- **Performance**: Validation overhead during container building
- **Debugging**: More complex stack traces when dependency resolution fails

## Implementation

### Container Creation

```python
from dart_planner.common.di_container_v2 import create_container, ContainerConfig

# Create container with validation enabled
config = ContainerConfig(enable_validation=True, strict_mode=True)
builder = create_container(config)

# Bootstrap stage (config, logging, core services)
bootstrap = builder.bootstrap_stage()
bootstrap.register_config(DARTPlannerFrozenConfig)
bootstrap.done()

# Runtime stage (application services)
runtime = builder.runtime_stage()
runtime.register_service(ControllerInterface, GeometricController)
runtime.register_service(PlannerInterface, SE3MPCPlanner)
runtime.done()

# Build and validate
container = builder.build()
```

### Service Resolution

```python
# Resolve services by type
controller = container.resolve(ControllerInterface)
planner = container.resolve(PlannerInterface)

# Optional resolution (returns None if not registered)
optional_service = container.resolve_optional(OptionalService)
```

### Validation

```python
# Validate dependency graph
if not container.validate_graph():
    # Handle validation errors
    graph_info = container.get_graph_info()
    print(f"Cycles: {graph_info.get('cycles')}")
    print(f"Missing dependencies: {graph_info.get('missing_dependencies')}")
```

## CI Integration

The DI container validation is integrated into CI:

```yaml
- name: DI Container validation
  run: python scripts/validate_di_containers.py
```

This ensures:
- All containers can be built successfully
- No circular dependencies exist
- All required dependencies are registered
- Validation catches issues early in the development cycle

## Related ADRs

- [ADR-0001: Configuration System Consolidation](0001-configuration-consolidation.md)

## References

- [DI Container Implementation](../src/dart_planner/common/di_container_v2.py)
- [DI Validation Script](../../scripts/validate_di_containers.py)
- [DI Usage Examples](../../CONTRIBUTING.md#dependency-injection-di-container-quick-start--best-practices) 