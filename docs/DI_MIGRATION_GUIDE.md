# Dependency Injection Migration Guide

## Overview

This guide explains how to migrate from manual path hacks and direct instantiation
to proper dependency injection in DART-Planner.

## What Changed

### Before (Manual Path Hacks)
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from planning.se3_mpc_planner import SE3MPCPlanner
from control.geometric_controller import GeometricController

# Manual instantiation
planner = SE3MPCPlanner(config)
controller = GeometricController(config)
```

### After (Dependency Injection)
```python
from src.common.di_container import get_container

# Get dependencies from container
planner = get_container().create_planner_container().get_se3_planner()
controller = get_container().create_control_container().get_geometric_controller()
```

## Migration Steps

1. **Remove path hacks**: Delete all `sys.path.insert` and `sys.path.append` lines
2. **Add DI imports**: Add `from src.common.di_container import get_container`
3. **Replace instantiations**: Use container methods instead of direct instantiation
4. **Update imports**: Use proper module paths (e.g., `from src.planning.se3_mpc_planner import SE3MPCPlanner`)

## Available Container Methods

### Planner Container
- `get_se3_planner()` - Get SE3 MPC planner
- `get_cloud_planner()` - Get cloud planner
- `get_mission_planner()` - Get mission planner

### Control Container
- `get_geometric_controller()` - Get geometric controller
- `get_onboard_controller()` - Get onboard controller
- `get_trajectory_smoother()` - Get trajectory smoother

### Hardware Container
- `get_airsim_adapter()` - Get AirSim adapter
- `get_pixhawk_interface()` - Get Pixhawk interface
- `get_vehicle_io_factory()` - Get vehicle I/O factory

### Communication Container
- `get_zmq_server()` - Get ZMQ server
- `get_zmq_client()` - Get ZMQ client
- `get_heartbeat_manager()` - Get heartbeat manager

## Benefits

1. **No more path hacks**: Clean, standard Python imports
2. **Dependency management**: Centralized dependency resolution
3. **Testability**: Easy to mock dependencies for testing
4. **Configuration**: Centralized configuration management
5. **Lifecycle management**: Proper initialization and cleanup

## Testing

After migration, run the test suite to ensure everything works:

```bash
python -m pytest tests/
```

## Troubleshooting

### Import Errors
- Ensure you're using proper module paths (e.g., `from src.module import Class`)
- Check that the DI container is properly initialized

### Missing Dependencies
- Register new dependencies in the appropriate container class
- Use `container.register_singleton()` for singleton dependencies

### Configuration Issues
- Use `get_container().resolve(ConfigManager)` to access configuration
- Check that configuration files are in the correct location
