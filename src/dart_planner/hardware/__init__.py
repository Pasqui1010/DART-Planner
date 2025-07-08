"""
Hardware Interface Module

This module provides interfaces to various hardware platforms and simulators
for the DART-Planner system.
"""

try:
    from .airsim_interface import AirSimDroneInterface, AirSimState, AirSimClient
    from .state import AirSimConfig, AirSimStateManager
    from .connection import AirSimConnection
    from .safety import AirSimSafetyManager
    from .metrics import AirSimMetricsManager
    from .simulated_vehicle_io import SimulatedVehicleIO
except ImportError:
    print("AirSim dependencies not found. AirSim interfaces will not be available.")

__all__ = [
    # Main interface
    "AirSimDroneInterface",
    
    # Configuration
    "AirSimConfig",
    
    # Sub-modules
    "AirSimConnection",
    "AirSimStateManager", 
    "AirSimSafetyManager",
    "AirSimMetricsManager",
    
    # Simulated vehicle I/O
    "SimulatedVehicleIO",
    
    # Type aliases
    "AirSimState",
    "AirSimClient",
] 
