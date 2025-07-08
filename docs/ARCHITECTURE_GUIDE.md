# Developer Guide: Core Architecture & Conventions

## Overview

DART-Planner is built on a modern dependency injection (DI) system and a "frozen" configuration management system. This guide explains the core architecture and the established conventions for developing within this repository.

## 🚀 Core Concepts

### 1. Dependency Injection (`di_container_v2`)

-   **Staged Registration**: Components are registered in distinct lifecycle stages (e.g., `CORE`, `RUNTIME`).
-   **Type Safety**: The container uses full type hinting for resolution and validation.
-   **Dependency Graph**: Dependencies are resolved automatically, and circular dependencies are detected.

### 2. Frozen Configuration (`frozen_config`)

-   **Immutability**: Configuration is immutable and cannot be modified after application startup.
-   **Type Safety**: All configuration values are strongly typed.
-   **Validation**: Configuration is automatically validated against its schema.
-   **Environment Integration**: Seamlessly integrates with environment variables for runtime configuration.

### 3. Enhanced Security

-   **Secure Key Management**: The system supports automatic key rotation and management.
-   **Token Expiration**: Access tokens are short-lived by default (15 minutes).
-   **HMAC Authentication**: APIs are secured using HMAC token authentication.

## 📋 Usage and Conventions

### Accessing the DI Container and Config

To access managed components or configuration, use the following helpers:

```python
from dart_planner.common.di_container_v2 import get_container
from dart_planner.config.frozen_config import get_frozen_config as get_config
```

### Resolving Components

Always resolve components directly from the container using their class type. This is the standard, type-safe way to access dependencies.

```python
# Get the global container instance
container = get_container()

# Resolve components by their class
planner = container.resolve(SE3MPCPlanner)
controller = container.resolve(GeometricController)
```

### Accessing Configuration

The configuration object provides access to all application settings. It is immutable, so any attempts to modify it at runtime will raise an error.

```python
config = get_config()
control_freq = config.control.frequency
planner_timeout = config.planning.timeout

# This will raise an error!
# config.control.frequency = 1000
```

## 🔧 Examples

### Example 1: Basic Component Usage

This example shows the standard pattern for resolving dependencies and using the config in a function.

```python
from dart_planner.common.di_container_v2 import get_container
from dart_planner.config.frozen_config import get_frozen_config
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner
from dart_planner.control.geometric_controller import GeometricController

def run_mission():
    container = get_container()
    config = get_frozen_config()

    # Get components with type safety
    planner = container.resolve(SE3MPCPlanner)
    controller = container.resolve(GeometricController)

    # Use immutable configuration
    control_freq = config.control.frequency

    # Run mission logic
    trajectory = planner.plan(goal)
    controller.execute(trajectory)
```

### Example 2: Hardware Integration

Hardware adapters are managed by the container and should be resolved like any other component.

```python
from dart_planner.hardware.airsim_adapter import AirSimAdapter
from dart_planner.common.di_container_v2 import get_container

def connect_to_simulator():
    container = get_container()
    airsim_adapter = container.resolve(AirSimAdapter)
    await airsim_adapter.connect()
    return airsim_adapter
```

### Example 3: Configuration Management

Since the global configuration is immutable, use dedicated data classes or "tuning profiles" to pass around mutable, scenario-specific parameters.

```python
from dart_planner.config.frozen_config import get_frozen_config
from dart_planner.config.control_config import ControllerTuningProfile

def setup_controller():
    config = get_frozen_config()

    # Configuration is immutable - use tuning profiles instead
    tuning_profile = ControllerTuningProfile(
        frequency=1000,
        gains=ControllerGains(kp=2.0, ki=0.1, kd=0.05)
    )

    return config, tuning_profile
```

## 🛡️ Security Conventions

### Environment Variables

Use the following environment variables for security-related configuration. Refer to `env.example` for a complete list.

```bash
# For development/testing
export DART_SECRET_KEY=test_secret_key_value_123456789
export DART_ZMQ_SECRET=test_secret

# For production (automatic key management)
# Keys are automatically managed in ~/.dart_planner/keys.json
```

### API Authentication

API endpoints are secured via HMAC tokens passed in the `Authorization` header.

```python
import requests
from dart_planner.security.auth import generate_hmac_token

secret_key = "test_secret_key_value_123456789"
token = generate_hmac_token(secret_key)

headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/status", headers=headers)
```

### Unit Tests

In tests, you can mock dependencies or use the real container to test component interactions.

```python
from unittest.mock import MagicMock
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner

def test_planner_with_mock():
    # Test with a mock dependency
    mock_mapper = MagicMock()
    planner = SE3MPCPlanner(mapper=mock_mapper)
    
    result = planner.plan(goal)
    assert result is not None
```

### Integration Tests

Integration tests should resolve components from the container to verify that the dependency graph is correctly configured.

```python
from dart_planner.common.di_container_v2 import get_container
from dart_planner.planning.base_planner import BasePlanner
from dart_planner.control.onboard_controller import OnboardController

def test_full_stack_integration():
    container = get_container()
    
    # Resolve components using their abstract base class or concrete type
    planner = container.resolve(BasePlanner)
    controller = container.resolve(OnboardController)
    
    # Test integration
    trajectory = planner.plan(goal)
    controller.execute(trajectory)
```

## 📈 Performance Considerations

### Real-Time Control Loop

The core control loop is implemented as a Cython extension (`rt_control_extension.pyx`) for maximum performance. When modifying this code, be mindful of the following:
-   Avoid Python objects in performance-critical sections.
-   Use C-level data types (`double`, `int`, etc.).
-   Release the GIL (`with nogil:`) for parallelizable computations.

### Asynchronous Operations

For I/O-bound tasks like network communication or file access, use `async/await` syntax and `asyncio`.

```python
import asyncio

async def handle_request(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    writer.write(data)
    await writer.drain()
    writer.close()
```

## ❌ Error Handling

The system uses custom exception classes defined in `dart_planner.common.errors`.

-   **`ConfigurationError`**: Invalid or missing configuration.
-   **`HardwareError`**: A hardware device failed or disconnected.
-   **`SecurityError`**: Authentication or authorization failure.

Always catch specific exceptions instead of generic `Exception`.

```python
from dart_planner.common.errors import HardwareError

try:
    await device.connect()
except HardwareError as e:
    logger.error(f"Failed to connect to hardware: {e}")
    # Trigger recovery logic
``` 