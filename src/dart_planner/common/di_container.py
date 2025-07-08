"""
Dependency Injection Container for DART-Planner

This module provides a centralized dependency injection container that manages
all system dependencies, eliminating manual path hacks and providing clean
separation between interfaces and implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, Union
from dataclasses import dataclass
from pathlib import Path
import threading
import contextvars
import numpy as np

from .types import DroneState, Trajectory
from .errors import DependencyError

# Type variable for generic dependency registration
T = TypeVar('T')


class DependencyProvider(ABC):
    """Abstract base class for dependency providers."""
    
    @abstractmethod
    def get(self) -> Any:
        """Get the dependency instance."""
        pass
    
    @abstractmethod
    def get_type(self) -> Type:
        """Get the type of the dependency."""
        pass


class SingletonProvider(DependencyProvider):
    """Provider that creates and caches a single instance."""
    
    def __init__(self, dependency_type: Type[T], **kwargs):
        self.dependency_type = dependency_type
        self.kwargs = kwargs
        self._instance: Optional[T] = None
    
    def get(self) -> T:
        if self._instance is None:
            self._instance = self.dependency_type(**self.kwargs)
        return self._instance
    
    def get_type(self) -> Type[T]:
        return self.dependency_type


class FactoryProvider(DependencyProvider):
    """Provider that creates a new instance each time."""
    
    def __init__(self, factory_func, dependency_type: Type[T]):
        self.factory_func = factory_func
        self.dependency_type = dependency_type
    
    def get(self) -> T:
        return self.factory_func()
    
    def get_type(self) -> Type[T]:
        return self.dependency_type


class InstanceProvider(DependencyProvider):
    """Provider that returns a pre-created instance."""
    
    def __init__(self, instance: T, dependency_type: Type[T]):
        self.instance = instance
        self.dependency_type = dependency_type
    
    def get(self) -> T:
        return self.instance
    
    def get_type(self) -> Type[T]:
        return self.dependency_type


@dataclass
class ContainerConfig:
    """Configuration for the dependency injection container."""
    config_path: Optional[Path] = None
    environment: str = "development"
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_safety: bool = True


class DIContainer:
    """
    Centralized dependency injection container for DART-Planner.
    
    This container manages all system dependencies and provides:
    - Singleton management
    - Interface-implementation separation
    - Configuration injection
    - Lifecycle management
    - Dependency resolution
    """
    
    def __init__(self, config: Optional[ContainerConfig] = None):
        self.config = config or ContainerConfig()
        self._providers: Dict[Type, DependencyProvider] = {}  # Do not access directly; use register_* methods with locking
        self._singletons: Dict[Type, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self._finalized = False  # Prevent further registration after finalize()
        # Register core configuration
        self._register_core_dependencies()
    
    def finalize(self) -> None:
        """Prevent further registration of dependencies."""
        with self._lock:
            self._finalized = True
            self.logger.info("DIContainer finalized; no further registrations allowed.")
    
    def _check_finalized(self):
        if self._finalized:
            raise DependencyError("DIContainer has been finalized; no further registrations allowed.")
    
    def register_singleton(self, interface: Type[T], implementation: Type[T], **kwargs) -> None:
        """Register a singleton dependency."""
        with self._lock:
            self._check_finalized()
            provider = SingletonProvider(implementation, **kwargs)
            self._providers[interface] = provider
            self.logger.debug(f"Registered singleton: {interface.__name__} -> {implementation.__name__}")
    
    def register_factory(self, interface: Type[T], factory_func, **kwargs) -> None:
        """Register a factory dependency."""
        with self._lock:
            self._check_finalized()
            provider = FactoryProvider(factory_func, interface)
            self._providers[interface] = provider
            self.logger.debug(f"Registered factory: {interface.__name__}")
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Register a pre-created instance."""
        with self._lock:
            self._check_finalized()
            provider = InstanceProvider(instance, interface)
            self._providers[interface] = provider
            self.logger.debug(f"Registered instance: {interface.__name__}")
    
    def resolve(self, dependency_type: Type[T]) -> T:
        """Resolve a dependency by type."""
        with self._lock:
            if dependency_type not in self._providers:
                from dart_planner.common.errors import DependencyError
                raise DependencyError(f"Dependency not registered: {dependency_type.__name__}")
        
            provider = self._providers[dependency_type]
            return provider.get()
    
    def resolve_optional(self, dependency_type: Type[T]) -> Optional[T]:
        """Resolve a dependency by type, returning None if not registered."""
        try:
            return self.resolve(dependency_type)
        except DependencyError:
            return None
    
    def has_dependency(self, dependency_type: Type[T]) -> bool:
        """Check if a dependency is registered."""
        with self._lock:
            return dependency_type in self._providers
    
    def get_registered_types(self) -> list[Type]:
        """Get all registered dependency types."""
        with self._lock:
            return list(self._providers.keys())
    
    def clear(self) -> None:
        """Clear all registered dependencies."""
        with self._lock:
            self._providers.clear()
            self._singletons.clear()
            self.logger.info("Cleared all dependencies")
    
    def _register_core_dependencies(self) -> None:
        """Register core system dependencies."""
        # Import here to avoid circular dependencies
        from ..config.settings import ConfigManager, get_config
        from ..config.airframe_config import AirframeConfigManager
        
        # Register configuration managers (simplified to avoid kwargs issues)
        self.register_singleton(ConfigManager, ConfigManager)
        self.register_singleton(AirframeConfigManager, AirframeConfigManager)
        
        # Register configuration getters
        self.register_instance(type(get_config), get_config)
    
    def create_planner_container(self) -> 'PlannerContainer':
        """Create a specialized container for planning components."""
        return PlannerContainer(self)
    
    def create_hardware_container(self) -> 'HardwareContainer':
        """Create a specialized container for hardware components."""
        return HardwareContainer(self)
    
    def create_control_container(self) -> 'ControlContainer':
        """Create a specialized container for control components."""
        return ControlContainer(self)
    
    def create_communication_container(self) -> 'CommunicationContainer':
        """Create a specialized container for communication components."""
        return CommunicationContainer(self)


class PlannerContainer:
    """Specialized container for planning components."""
    
    def __init__(self, parent_container: DIContainer):
        self.parent = parent_container
        self._register_planner_dependencies()
    
    def _register_planner_dependencies(self) -> None:
        """Register planning-specific dependencies with proper configuration injection."""
        from ..planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
        from ..planning.cloud_planner import CloudPlanner
        from ..planning.global_mission_planner import GlobalMissionPlanner
        
        # Register factory methods instead of direct singletons
        self.parent.register_factory(SE3MPCPlanner, self._create_se3_planner)
        self.parent.register_factory(CloudPlanner, self._create_cloud_planner)
        self.parent.register_factory(GlobalMissionPlanner, self._create_mission_planner)
    
    def _create_se3_planner(self) -> 'SE3MPCPlanner':
        """Create SE3 MPC planner with validated configuration."""
        from ..planning.se3_mpc_planner import SE3MPCPlanner, SE3MPCConfig
        from ..common.timing_alignment import get_timing_manager
        
        # Get timing manager to ensure proper dt alignment
        timing_manager = get_timing_manager()
        aligned_dt = timing_manager.get_planner_dt()
        
        # Create validated configuration
        config = SE3MPCConfig(
            prediction_horizon=6,  # Optimized for real-time
            dt=aligned_dt,  # Use aligned timing
            max_velocity=10.0,
            max_acceleration=15.0,
            max_jerk=20.0,
            max_thrust=25.0,
            min_thrust=2.0,
            max_tilt_angle=np.pi / 4,
            max_angular_velocity=4.0,
            position_weight=100.0,
            velocity_weight=10.0,
            acceleration_weight=1.0,
            thrust_weight=0.1,
            angular_weight=10.0,
            obstacle_weight=1000.0,
            safety_margin=1.5,
            max_iterations=15,
            convergence_tolerance=5e-2,
        )
        
        return SE3MPCPlanner(config)
    
    def _create_cloud_planner(self) -> 'CloudPlanner':
        """Create cloud planner with validated configuration."""
        from ..planning.cloud_planner import CloudPlanner
        return CloudPlanner()
    
    def _create_mission_planner(self) -> 'GlobalMissionPlanner':
        """Create mission planner with validated configuration."""
        from ..planning.global_mission_planner import GlobalMissionPlanner
        return GlobalMissionPlanner()
    
    def get_se3_planner(self, config: Optional['SE3MPCConfig'] = None) -> 'SE3MPCPlanner':
        """Get SE3 MPC planner instance with optional custom configuration."""
        from ..planning.se3_mpc_planner import SE3MPCPlanner
        
        if config is not None:
            # Create planner with custom config
            return SE3MPCPlanner(config)
        else:
            # Use factory-created planner with validated config
            return self.parent.resolve(SE3MPCPlanner)
    
    def get_cloud_planner(self) -> 'CloudPlanner':
        """Get cloud planner instance."""
        from ..planning.cloud_planner import CloudPlanner
        return self.parent.resolve(CloudPlanner)
    
    def get_mission_planner(self) -> 'GlobalMissionPlanner':
        """Get global mission planner instance."""
        from ..planning.global_mission_planner import GlobalMissionPlanner
        return self.parent.resolve(GlobalMissionPlanner)


class HardwareContainer:
    """Specialized container for hardware components."""
    
    def __init__(self, parent_container: DIContainer):
        self.parent = parent_container
        self._register_hardware_dependencies()
    
    def _register_hardware_dependencies(self) -> None:
        """Register hardware-specific dependencies with proper configuration injection."""
        from ..hardware.airsim_adapter import AirSimAdapter
        from ..hardware.pixhawk_interface import PixhawkInterface
        from ..hardware.vehicle_io import VehicleIO, VehicleIOFactory
        
        # Register factory methods instead of direct singletons
        self.parent.register_factory(AirSimAdapter, self._create_airsim_adapter)
        self.parent.register_factory(PixhawkInterface, self._create_pixhawk_interface)
        
        # Register vehicle I/O factory
        self.parent.register_instance(VehicleIOFactory, VehicleIOFactory())
    
    def _create_airsim_adapter(self) -> 'AirSimAdapter':
        """Create AirSim adapter with validated configuration."""
        from ..hardware.airsim_adapter import AirSimAdapter
        # AirSim adapter typically needs connection parameters
        # For now, return basic instance - configuration should be injected
        return AirSimAdapter()
    
    def _create_pixhawk_interface(self) -> 'PixhawkInterface':
        """Create Pixhawk interface with validated configuration."""
        from ..hardware.pixhawk_interface import PixhawkInterface
        # Pixhawk interface typically needs connection parameters
        # For now, return basic instance - configuration should be injected
        return PixhawkInterface()
    
    def get_airsim_adapter(self, connection_params: Optional[Dict[str, Any]] = None) -> 'AirSimAdapter':
        """Get AirSim adapter instance with optional connection parameters."""
        from ..hardware.airsim_adapter import AirSimAdapter
        
        if connection_params is not None:
            # Create adapter with custom connection params
            return AirSimAdapter(**connection_params)
        else:
            # Use factory-created adapter
            return self.parent.resolve(AirSimAdapter)
    
    def get_pixhawk_interface(self, connection_params: Optional[Dict[str, Any]] = None) -> 'PixhawkInterface':
        """Get Pixhawk interface instance with optional connection parameters."""
        from ..hardware.pixhawk_interface import PixhawkInterface
        
        if connection_params is not None:
            # Create interface with custom connection params
            return PixhawkInterface(**connection_params)
        else:
            # Use factory-created interface
            return self.parent.resolve(PixhawkInterface)
    
    def get_vehicle_io_factory(self) -> 'VehicleIOFactory':
        """Get vehicle I/O factory instance."""
        from ..hardware.vehicle_io import VehicleIOFactory
        return self.parent.resolve(VehicleIOFactory)


class ControlContainer:
    """Specialized container for control components."""
    
    def __init__(self, parent_container: DIContainer):
        self.parent = parent_container
        self._register_control_dependencies()
    
    def _register_control_dependencies(self) -> None:
        """Register control-specific dependencies with proper configuration injection."""
        from ..control.geometric_controller import GeometricController, GeometricControllerConfig
        from ..control.onboard_controller import OnboardController
        from ..control.trajectory_smoother import TrajectorySmoother
        
        # Register factory methods instead of direct singletons
        self.parent.register_factory(GeometricController, self._create_geometric_controller)
        self.parent.register_factory(OnboardController, self._create_onboard_controller)
        self.parent.register_factory(TrajectorySmoother, self._create_trajectory_smoother)
    
    def _create_geometric_controller(self) -> 'GeometricController':
        """Create geometric controller with validated configuration."""
        from ..control.geometric_controller import GeometricController, GeometricControllerConfig
        
        # Create validated configuration
        config = GeometricControllerConfig(
            kp_pos=np.array([20.0, 20.0, 25.0]),  # Optimized gains
            ki_pos=np.array([1.5, 1.5, 2.0]),
            kd_pos=np.array([10.0, 10.0, 12.0]),
            kp_att=np.array([18.0, 18.0, 8.0]),
            kd_att=np.array([7.0, 7.0, 3.5]),
            ff_pos=1.8,
            ff_vel=1.1,
            max_integral_pos=5.0,
            max_tilt_angle=np.pi / 3,
            mass=1.0,
            gravity=9.81,
            max_thrust=20.0,
            min_thrust=0.5,
            tracking_error_threshold=2.0,
            velocity_error_threshold=1.0,
        )
        
        return GeometricController(config, tuning_profile="sitl_optimized")
    
    def _create_onboard_controller(self) -> 'OnboardController':
        """Create onboard controller with validated configuration."""
        from ..control.onboard_controller import OnboardController
        # OnboardController is currently a placeholder - return basic instance
        return OnboardController()
    
    def _create_trajectory_smoother(self) -> 'TrajectorySmoother':
        """Create trajectory smoother with validated configuration."""
        from ..control.trajectory_smoother import TrajectorySmoother
        return TrajectorySmoother()
    
    def get_geometric_controller(self, config: Optional['GeometricControllerConfig'] = None, tuning_profile: str = "sitl_optimized") -> 'GeometricController':
        """Get geometric controller instance with optional custom configuration."""
        from ..control.geometric_controller import GeometricController
        
        if config is not None:
            # Create controller with custom config
            return GeometricController(config, tuning_profile)
        else:
            # Use factory-created controller with validated config
            return self.parent.resolve(GeometricController)
    
    def get_onboard_controller(self) -> 'OnboardController':
        """Get onboard controller instance."""
        from ..control.onboard_controller import OnboardController
        return self.parent.resolve(OnboardController)
    
    def get_trajectory_smoother(self) -> 'TrajectorySmoother':
        """Get trajectory smoother instance."""
        from ..control.trajectory_smoother import TrajectorySmoother
        return self.parent.resolve(TrajectorySmoother)


class CommunicationContainer:
    """Specialized container for communication components."""
    
    def __init__(self, parent_container: DIContainer):
        self.parent = parent_container
        self._register_communication_dependencies()
    
    def _register_communication_dependencies(self) -> None:
        """Register communication-specific dependencies with proper configuration injection."""
        from ..communication.zmq_server import ZmqServer
        from ..communication.zmq_client import ZmqClient
        from ..communication.heartbeat import HeartbeatManager
        
        # Register factory methods instead of direct singletons
        self.parent.register_factory(ZmqServer, self._create_zmq_server)
        self.parent.register_factory(ZmqClient, self._create_zmq_client)
        self.parent.register_factory(HeartbeatManager, self._create_heartbeat_manager)
    
    def _create_zmq_server(self) -> 'ZmqServer':
        """Create ZMQ server with validated configuration."""
        from ..communication.zmq_server import ZmqServer
        # ZMQ server typically needs port and security settings
        # For now, return basic instance - configuration should be injected
        return ZmqServer()
    
    def _create_zmq_client(self) -> 'ZmqClient':
        """Create ZMQ client with validated configuration."""
        from ..communication.zmq_client import ZmqClient
        # ZMQ client typically needs host, port, and security settings
        # For now, return basic instance - configuration should be injected
        return ZmqClient()
    
    def _create_heartbeat_manager(self) -> 'HeartbeatManager':
        """Create heartbeat manager with validated configuration."""
        from ..communication.heartbeat import HeartbeatManager
        return HeartbeatManager()
    
    def get_zmq_server(self, port: Optional[int] = None, security_config: Optional[Dict[str, Any]] = None) -> 'ZmqServer':
        """Get ZMQ server instance with optional configuration."""
        from ..communication.zmq_server import ZmqServer
        
        if port is not None or security_config is not None:
            # Create server with custom config
            kwargs = {}
            if port is not None:
                kwargs['port'] = port
            if security_config is not None:
                kwargs.update(security_config)
            return ZmqServer(**kwargs)
        else:
            # Use factory-created server
            return self.parent.resolve(ZmqServer)
    
    def get_zmq_client(self, host: Optional[str] = None, port: Optional[int] = None, security_config: Optional[Dict[str, Any]] = None) -> 'ZmqClient':
        """Get ZMQ client instance with optional configuration."""
        from ..communication.zmq_client import ZmqClient
        
        if host is not None or port is not None or security_config is not None:
            # Create client with custom config
            kwargs = {}
            if host is not None:
                kwargs['host'] = host
            if port is not None:
                kwargs['port'] = port
            if security_config is not None:
                kwargs.update(security_config)
            return ZmqClient(**kwargs)
        else:
            # Use factory-created client
            return self.parent.resolve(ZmqClient)
    
    def get_heartbeat_manager(self) -> 'HeartbeatManager':
        """Get heartbeat manager instance."""
        from ..communication.heartbeat import HeartbeatManager
        return self.parent.resolve(HeartbeatManager)


# Global container instance
# _global_container: Optional[DIContainer] = None
_global_container_ctx: contextvars.ContextVar = contextvars.ContextVar("_global_container_ctx", default=None)
_global_container_lock = threading.Lock()

def get_container() -> DIContainer:
    """Get the global dependency injection container."""
    container = _global_container_ctx.get()
    if container is None:
        with _global_container_lock:
            container = _global_container_ctx.get()
            if container is None:
                container = DIContainer()
                _global_container_ctx.set(container)
    return container

def set_container(container: DIContainer) -> None:
    """Set the global dependency injection container."""
    _global_container_ctx.set(container)

def reset_container() -> None:
    """Reset the global container."""
    _global_container_ctx.set(None) 
