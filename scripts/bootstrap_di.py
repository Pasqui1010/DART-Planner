#!/usr/bin/env python3
"""
Dependency Injection Bootstrap Script

This script initializes the global dependency injection container
and registers all system dependencies.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import using proper module paths
from dart_planner.common.di_container import DIContainer, ContainerConfig, set_container
from dart_planner.config.settings import ConfigManager
from dart_planner.config.airframe_config import AirframeConfigManager

def bootstrap_di_container():
    """Initialize the global dependency injection container."""
    
    # Create container configuration
    config = ContainerConfig(
        environment="development",
        log_level="INFO",
        enable_metrics=True,
        enable_safety=True
    )
    
    # Create and configure container
    container = DIContainer(config)
    
    # Register core dependencies
    container.register_singleton(ConfigManager, ConfigManager)
    container.register_singleton(AirframeConfigManager, AirframeConfigManager)
    
    # Set as global container
    set_container(container)
    
    print("✅ Dependency injection container initialized")
    return container

if __name__ == "__main__":
    bootstrap_di_container()
