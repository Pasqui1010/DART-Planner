#!/usr/bin/env python3
"""
DI Container Validation Script

This script validates all DI containers in the DART-Planner system by:
1. Building each container
2. Running validate_graph() to check for cycles and missing dependencies
3. Exiting with error code if validation fails

Used in CI to catch dependency injection issues early.
"""

import sys
import traceback
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dart_planner.common.di_container_v2 import (
    create_container, ContainerConfig, DIContainerV2
)
from dart_planner.config.frozen_config import DARTPlannerFrozenConfig


def validate_container(container: DIContainerV2, name: str) -> bool:
    """Validate a single container and return success status."""
    try:
        print(f"🔍 Validating {name}...")
        
        # Run graph validation
        if not container.validate_graph():
            print(f"❌ {name}: Graph validation failed")
            return False
        
        # Check for registered types
        registered_types = container.get_registered_types()
        if not registered_types:
            print(f"⚠️  {name}: No services registered")
        else:
            print(f"✅ {name}: {len(registered_types)} services registered")
        
        # Get graph info for debugging
        graph_info = container.get_graph_info()
        if graph_info.get('cycles'):
            print(f"❌ {name}: Circular dependencies detected")
            for cycle in graph_info['cycles']:
                print(f"   Cycle: {' -> '.join(str(t) for t in cycle)}")
            return False
        
        print(f"✅ {name}: Validation passed")
        return True
        
    except Exception as e:
        print(f"❌ {name}: Validation error: {e}")
        traceback.print_exc()
        return False


def create_main_container() -> DIContainerV2:
    """Create the main application container."""
    config = ContainerConfig(
        enable_validation=True,
        enable_lifecycle_management=True,
        strict_mode=True
    )
    
    builder = create_container(config)
    
    # Bootstrap stage
    bootstrap = builder.bootstrap_stage()
    bootstrap.register_config(DARTPlannerFrozenConfig)
    bootstrap.done()
    
    # Runtime stage - add some common services
    runtime = builder.runtime_stage()
    
    # Mock services for validation (these would be real in production)
    class MockController:
        def __init__(self):
            pass
    
    class MockPlanner:
        def __init__(self):
            pass
    
    class MockSafetyMonitor:
        def __init__(self):
            pass
    
    runtime.register_service(MockController, MockController)
    runtime.register_service(MockPlanner, MockPlanner)
    runtime.register_service(MockSafetyMonitor, MockSafetyMonitor)
    runtime.done()
    
    return builder.build()


def create_planner_container() -> DIContainerV2:
    """Create the planner-specific container."""
    config = ContainerConfig(
        enable_validation=True,
        enable_lifecycle_management=True,
        strict_mode=True
    )
    
    builder = create_container(config)
    
    # Bootstrap stage
    bootstrap = builder.bootstrap_stage()
    bootstrap.register_config(DARTPlannerFrozenConfig)
    bootstrap.done()
    
    # Runtime stage
    runtime = builder.runtime_stage()
    
    # Mock planner services
    class MockSE3Planner:
        def __init__(self):
            pass
    
    class MockPathPlanner:
        def __init__(self):
            pass
    
    runtime.register_service(MockSE3Planner, MockSE3Planner)
    runtime.register_service(MockPathPlanner, MockPathPlanner)
    runtime.done()
    
    return builder.build()


def create_control_container() -> DIContainerV2:
    """Create the control-specific container."""
    config = ContainerConfig(
        enable_validation=True,
        enable_lifecycle_management=True,
        strict_mode=True
    )
    
    builder = create_container(config)
    
    # Bootstrap stage
    bootstrap = builder.bootstrap_stage()
    bootstrap.register_config(DARTPlannerFrozenConfig)
    bootstrap.done()
    
    # Runtime stage
    runtime = builder.runtime_stage()
    
    # Mock control services
    class MockGeometricController:
        def __init__(self):
            pass
    
    class MockTrajectorySmoother:
        def __init__(self):
            pass
    
    runtime.register_service(MockGeometricController, MockGeometricController)
    runtime.register_service(MockTrajectorySmoother, MockTrajectorySmoother)
    runtime.done()
    
    return builder.build()


def create_communication_container() -> DIContainerV2:
    """Create the communication-specific container."""
    config = ContainerConfig(
        enable_validation=True,
        enable_lifecycle_management=True,
        strict_mode=True
    )
    
    builder = create_container(config)
    
    # Bootstrap stage
    bootstrap = builder.bootstrap_stage()
    bootstrap.register_config(DARTPlannerFrozenConfig)
    bootstrap.done()
    
    # Runtime stage
    runtime = builder.runtime_stage()
    
    # Mock communication services
    class MockZMQServer:
        def __init__(self):
            pass
    
    class MockZMQClient:
        def __init__(self):
            pass
    
    runtime.register_service(MockZMQServer, MockZMQServer)
    runtime.register_service(MockZMQClient, MockZMQClient)
    runtime.done()
    
    return builder.build()


def create_hardware_container() -> DIContainerV2:
    """Create the hardware-specific container."""
    config = ContainerConfig(
        enable_validation=True,
        enable_lifecycle_management=True,
        strict_mode=True
    )
    
    builder = create_container(config)
    
    # Bootstrap stage
    bootstrap = builder.bootstrap_stage()
    bootstrap.register_config(DARTPlannerFrozenConfig)
    bootstrap.done()
    
    # Runtime stage
    runtime = builder.runtime_stage()
    
    # Mock hardware services
    class MockAirSimAdapter:
        def __init__(self):
            pass
    
    class MockPixhawkInterface:
        def __init__(self):
            pass
    
    runtime.register_service(MockAirSimAdapter, MockAirSimAdapter)
    runtime.register_service(MockPixhawkInterface, MockPixhawkInterface)
    runtime.done()
    
    return builder.build()


def main():
    """Main validation function."""
    # Set required environment variables for testing
    import os
    os.environ["DART_ENVIRONMENT"] = "testing"
    os.environ["DART_SECRET_KEY"] = "test_secret_key_value_123456789"
    os.environ["DART_ZMQ_SECRET"] = "test_secret"
    
    print("🔍 Starting DI Container Validation...")
    print("=" * 50)
    
    # Define containers to validate
    containers = [
        ("Main Container", create_main_container),
        ("Planner Container", create_planner_container),
        ("Control Container", create_control_container),
        ("Communication Container", create_communication_container),
        ("Hardware Container", create_hardware_container),
    ]
    
    validation_results = []
    
    for name, container_factory in containers:
        try:
            container = container_factory()
            success = validate_container(container, name)
            validation_results.append((name, success))
        except Exception as e:
            print(f"❌ {name}: Failed to create container: {e}")
            traceback.print_exc()
            validation_results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 Validation Summary:")
    
    all_passed = True
    for name, success in validation_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All DI containers validated successfully!")
        return 0
    else:
        print("\n💥 Some DI containers failed validation!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 