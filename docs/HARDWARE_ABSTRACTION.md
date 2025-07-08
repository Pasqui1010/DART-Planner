# DART-Planner Hardware Abstraction Layer (HAL)

## Overview

The DART-Planner Hardware Abstraction Layer (HAL) provides a unified, testable, and extensible interface for all hardware backends (real, simulated, or virtual). This enables the planner and control stack to interact with any supported hardware using a common API, improving modularity, testability, and maintainability.

## Key Concepts

- **HardwareInterface**: The abstract base class (ABC) that defines the contract for all hardware adapters. Located in `src/common/interfaces.py`.
- **Adapters**: Concrete implementations of `HardwareInterface` for specific hardware backends (e.g., Pixhawk, AirSim, Simulated).
- **Dependency Injection**: The DI container selects and injects the appropriate adapter at runtime based on configuration.
- **Testing**: All adapters are unit tested with mocks, and integration/simulation-based tests are provided for supported backends.

## Implementing a New Hardware Adapter

1. **Inherit from HardwareInterface**

   ```python
   from src.common.interfaces import HardwareInterface
   from typing import Any, Dict, Optional

   class MyHardwareAdapter(HardwareInterface):
       def connect(self) -> None:
           ...
       def disconnect(self) -> None:
           ...
       def is_connected(self) -> bool:
           ...
       def send_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> Any:
           ...
       def get_state(self) -> Dict[str, Any]:
           ...
       def reset(self) -> None:
           ...
       def emergency_stop(self) -> None:
           ...
       def get_capabilities(self) -> Dict[str, Any]:
           ...
       def update(self) -> None:
           ...
   ```

2. **Implement All Required Methods**
   - Each method should map to the hardware's API or simulation logic.
   - For unsupported features, raise `NotImplementedError`.

3. **Expose Capabilities**
   - `get_capabilities()` should return a dictionary describing the hardware's limits and features (e.g., max velocity, sensors, simulated=True/False).

4. **Testing**
   - Add unit tests in `tests/hardware/test_<your_adapter>.py` using mocks for hardware dependencies.
   - For simulation/integration, provide tests that run against a real or simulated backend if possible.

## Using the Hardware Interface in the Planner

- The planner, controller, and other modules should depend only on `HardwareInterface`, not on specific adapters.
- Use the DI container to obtain the correct adapter:

  ```python
  from dart_planner.common.di_container_v2 import get_container
  hardware = get_container().get_hardware_adapter()
  hardware.connect()
  state = hardware.get_state()
  hardware.send_command("takeoff", {"altitude": 2.0})
  ```

## Testing and Extending the System

- **Unit Tests**: Use mocks to test adapter logic in isolation.
- **Integration/Simulation Tests**: Use real or simulated hardware to verify end-to-end behavior.
- **Contract Tests**: Ensure all adapters conform to the `HardwareInterface` contract.

## Example: Adding a New Adapter

Suppose you want to add support for a new drone API called `SuperDroneAPI`:

1. Create `src/dart_planner/hardware/superdrone_adapter.py`:
   ```python
   from src.common.interfaces import HardwareInterface
   from superdrone import SuperDroneClient

   class SuperDroneAdapter(HardwareInterface):
       def __init__(self):
           self.client = SuperDroneClient()
           self.connected = False
       def connect(self):
           self.client.connect()
           self.connected = True
       # ... implement other methods ...
   ```
2. Add unit tests in `tests/hardware/test_superdrone_adapter.py`.
3. Register the adapter in the DI container if needed.
4. Update documentation and configuration as appropriate.

## Best Practices

- Always implement the full `HardwareInterface` contract.
- Use clear, descriptive error messages for unsupported features.
- Document hardware-specific quirks or limitations in the adapter docstring.
- Prefer composition over inheritance for complex hardware logic.
- Keep simulation and mock adapters up to date for CI and development.

## Reference

- `src/common/interfaces.py` — HardwareInterface definition
- `src/dart_planner/hardware/pixhawk_adapter.py` — Pixhawk reference adapter
- `src/dart_planner/hardware/airsim_adapter.py` — AirSim reference adapter
- `src/dart_planner/hardware/simulated_adapter.py` — Simulated/mock reference adapter
- `tests/hardware/` — Unit and integration tests for all adapters

For questions or contributions, see the main project README or contact the maintainers. 

# Hardware Abstraction and Adapter Capabilities

## Overview

DART-Planner uses a hardware abstraction layer to support multiple vehicle types and simulators.

## Adapter Capabilities
- Each hardware adapter implements `get_capabilities()` to enumerate supported commands.
- Use `supports(command: str) -> bool` to check if a command is available before calling.

### Example
```python
if adapter.supports("takeoff"):
    adapter.takeoff()
else:
    logger.warning("Takeoff not supported on this hardware.")
```

## Error Handling
- If an unsupported command is called, the adapter logs a warning and raises a clear exception.
- Always check capabilities before invoking advanced features.

## Extending Adapters
- To add a new hardware feature, implement it in the relevant adapter and update `get_capabilities()`.
- Document new capabilities in the adapter docstring. 