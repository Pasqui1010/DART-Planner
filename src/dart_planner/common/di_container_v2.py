"""
Advanced dependency injection container with staged registration and validation.

This module provides a modern DI container with:
- Staged registration (bootstrap, runtime, dynamic)
- Static graph validation
- Lifecycle management
- No global singletons
- Cycle detection
- Dependency resolution tracking
"""

import logging
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Type, TypeVar

T = TypeVar('T')


class RegistrationStage(Enum):
    """Stages of dependency registration."""
    BOOTSTRAP = "bootstrap"      # Core system dependencies
    RUNTIME = "runtime"          # Application dependencies
    DYNAMIC = "dynamic"          # Runtime-created dependencies


class LifecyclePhase(Enum):
    """Lifecycle phases for dependencies."""
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class DependencyMetadata:
    """Metadata for a registered dependency."""
    interface: Type[Any]
    implementation: Type[Any]
    stage: RegistrationStage
    lifecycle_phase: LifecyclePhase = LifecyclePhase.INITIALIZING
    singleton: bool = True
    lazy: bool = True
    priority: int = 0
    dependencies: Set[Type[Any]] = field(default_factory=set)
    factory_func: Optional[Callable[..., Any]] = None
    instance: Optional[Any] = None
    error: Optional[Exception] = None


class DependencyProvider(ABC, Generic[T]):
    """Abstract base class for dependency providers."""
    
    def __init__(self, interface: Type[T], metadata: DependencyMetadata) -> None:
        self.interface = interface
        self.metadata = metadata
    
    @abstractmethod
    def get(self) -> T:
        """Get the dependency instance."""
        pass
    
    def get_type(self) -> Type[T]:
        """Get the dependency type."""
        return self.interface


class SingletonProvider(DependencyProvider[T]):
    """Provider for singleton dependencies."""
    
    def __init__(self, interface: Type[T], metadata: DependencyMetadata) -> None:
        super().__init__(interface, metadata)
        self._instance: Optional[T] = None
    
    def get(self) -> T:
        """Get or create the singleton instance."""
        if self._instance is None:
            self._instance = self._create_instance()
        return self._instance
    
    def _create_instance(self) -> T:
        """Create a new instance of the dependency."""
        if self.metadata.factory_func:
            return self.metadata.factory_func()
        else:
            return self.metadata.implementation()


class FactoryProvider(DependencyProvider[T]):
    """Provider for factory dependencies."""
    
    def get(self) -> T:
        """Create a new instance of the dependency."""
        if self.metadata.factory_func:
            return self.metadata.factory_func()
        else:
            return self.metadata.implementation()


class InstanceProvider(DependencyProvider[T]):
    """Provider for pre-created instances."""
    
    def __init__(self, interface: Type[T], metadata: DependencyMetadata, instance: T) -> None:
        super().__init__(interface, metadata)
        self._instance = instance
    
    def get(self) -> T:
        """Get the pre-created instance."""
        return self._instance


@dataclass
class ContainerConfig:
    """Configuration for the dependency injection container."""
    enable_validation: bool = True
    enable_lifecycle_management: bool = True
    enable_metrics: bool = True
    max_resolution_depth: int = 100
    allow_circular_dependencies: bool = False
    strict_mode: bool = True


class DependencyGraph:
    """Dependency graph for cycle detection and resolution order."""
    
    def __init__(self) -> None:
        self.edges: Dict[Type[Any], Set[Type[Any]]] = {}
    
    def add_dependency(self, dependent: Type[Any], dependency: Type[Any]) -> None:
        """Add a dependency edge to the graph."""
        if dependent not in self.edges:
            self.edges[dependent] = set()
        self.edges[dependent].add(dependency)
    
    def detect_cycles(self) -> List[List[Type[Any]]]:
        """Detect cycles in the dependency graph."""
        cycles: List[List[Type[Any]]] = []
        visited: Set[Type[Any]] = set()
        rec_stack: Set[Type[Any]] = set()
        
        def dfs(node: Type[Any], path: List[Type[Any]]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.edges.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            
            rec_stack.remove(node)
            path.pop()
        
        for node in self.edges:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def get_dependency_order(self) -> List[Type[Any]]:
        """Get topological sort of dependencies."""
        result: List[Type[Any]] = []
        visited: Set[Type[Any]] = set()
        temp_visited: Set[Type[Any]] = set()
        
        def visit(node: Type[Any]) -> None:
            if node in temp_visited:
                return  # Already visiting this node
            if node in visited:
                return  # Already processed
            
            temp_visited.add(node)
            
            for neighbor in self.edges.get(node, set()):
                visit(neighbor)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in self.edges:
            if node not in visited:
                visit(node)
        
        return result


class DIContainerV2:
    """
    Advanced dependency injection container with staged registration and validation.
    
    Features:
    - Staged registration (bootstrap, runtime, dynamic)
    - Static graph validation
    - Lifecycle management
    - No global singletons
    - Cycle detection
    - Dependency resolution tracking
    """
    
    def __init__(self, config: Optional[ContainerConfig] = None) -> None:
        self.config = config or ContainerConfig()
        self._providers: Dict[Type[Any], DependencyProvider[Any]] = {}
        self._metadata: Dict[Type[Any], DependencyMetadata] = {}
        self._graph = DependencyGraph()
        self._current_stage = RegistrationStage.BOOTSTRAP
        self._finalized = False
        self._lock = threading.RLock()
        self._resolution_stack: List[Type[Any]] = []
        self._lifecycle_managers: Dict[Type[Any], 'LifecycleManager'] = {}
        
        self.logger = logging.getLogger(f"{__name__}.{id(self)}")
        
        # Register core dependencies
        self._register_core_dependencies()
    
    def _register_core_dependencies(self) -> None:
        """Register core system dependencies."""
        # Import here to avoid circular dependencies
        from ..config.frozen_config import ConfigurationManager
        from ..config.airframe_config import AirframeConfigManager
        
        # Register configuration managers
        self.register_singleton(ConfigurationManager, ConfigurationManager, stage=RegistrationStage.BOOTSTRAP)
        self.register_singleton(AirframeConfigManager, AirframeConfigManager, stage=RegistrationStage.BOOTSTRAP)
        
        # Register communication services
        from ..communication.zmq_server import ZmqServer
        from ..communication.zmq_client import ZmqClient
        from ..communication.heartbeat import HeartbeatMonitor
        
        self.register_singleton(ZmqServer, ZmqServer, stage=RegistrationStage.RUNTIME)
        self.register_singleton(ZmqClient, ZmqClient, stage=RegistrationStage.RUNTIME)
        self.register_singleton(HeartbeatMonitor, HeartbeatMonitor, stage=RegistrationStage.RUNTIME)
        
        # Register control services
        from ..control.geometric_controller import GeometricController
        from ..control.trajectory_smoother import TrajectorySmoother
        from ..control.onboard_controller import OnboardController
        
        self.register_singleton(GeometricController, GeometricController, stage=RegistrationStage.RUNTIME)
        self.register_singleton(TrajectorySmoother, TrajectorySmoother, stage=RegistrationStage.RUNTIME)
        self.register_singleton(OnboardController, OnboardController, stage=RegistrationStage.RUNTIME)
        
        # Register planning services
        from ..planning.se3_mpc_planner import SE3MPCPlanner
        from ..planning.cloud_planner import CloudPlanner
        from ..planning.global_mission_planner import GlobalMissionPlanner
        
        self.register_singleton(SE3MPCPlanner, SE3MPCPlanner, stage=RegistrationStage.RUNTIME)
        self.register_singleton(CloudPlanner, CloudPlanner, stage=RegistrationStage.RUNTIME)
        self.register_singleton(GlobalMissionPlanner, GlobalMissionPlanner, stage=RegistrationStage.RUNTIME)
        
        # Register hardware services (optional)
        try:
            from ..hardware.airsim_adapter import AirSimAdapter
            self.register_singleton(AirSimAdapter, AirSimAdapter, stage=RegistrationStage.RUNTIME)
        except ImportError:
            self.logger.warning("AirSim adapter not available - skipping registration")
        
        try:
            from ..hardware.pixhawk_interface import PixhawkInterface
            self.register_singleton(PixhawkInterface, PixhawkInterface, stage=RegistrationStage.RUNTIME)
        except ImportError:
            self.logger.warning("Pixhawk interface not available - skipping registration")
        
        try:
            from ..hardware.vehicle_io import VehicleIOFactory
            self.register_singleton(VehicleIOFactory, VehicleIOFactory, stage=RegistrationStage.RUNTIME)
        except ImportError:
            self.logger.warning("Vehicle IO factory not available - skipping registration")
    
    def register_singleton(self, interface: Type[T], implementation: Type[T], 
                          stage: RegistrationStage = RegistrationStage.RUNTIME,
                          priority: int = 0, factory_func: Optional[Callable[[], T]] = None) -> None:
        """Register a singleton dependency."""
        self._register_dependency(
            interface, implementation, stage, priority, True, factory_func
        )
    
    def register_factory(self, interface: Type[T], implementation: Type[T],
                        stage: RegistrationStage = RegistrationStage.RUNTIME,
                        priority: int = 0, factory_func: Optional[Callable[[], T]] = None) -> None:
        """Register a factory dependency."""
        self._register_dependency(
            interface, implementation, stage, priority, False, factory_func
        )
    
    def register_instance(self, interface: Type[T], instance: T,
                         stage: RegistrationStage = RegistrationStage.RUNTIME,
                         priority: int = 0) -> None:
        """Register a pre-created instance."""
        metadata = DependencyMetadata(
            interface=interface,
            implementation=type(instance),
            stage=stage,
            priority=priority,
            singleton=True,
            lazy=False,
            instance=instance
        )
        
        provider = InstanceProvider(interface, metadata, instance)
        self._add_provider(interface, provider, metadata)
    
    def _register_dependency(self, interface: Type[T], implementation: Type[T],
                           stage: RegistrationStage, priority: int, singleton: bool,
                           factory_func: Optional[Callable[[], T]]) -> None:
        """Internal method to register a dependency."""
        with self._lock:
            if self._finalized and stage != RegistrationStage.DYNAMIC:
                raise DependencyError(f"Cannot register {interface.__name__} after finalization")
            
            if stage.value < self._current_stage.value:
                raise DependencyError(f"Cannot register {interface.__name__} in {stage.value} stage from {self._current_stage.value} stage")
            
            metadata = DependencyMetadata(
                interface=interface,
                implementation=implementation,
                stage=stage,
                priority=priority,
                singleton=singleton,
                factory_func=factory_func
            )
            
            # Create appropriate provider
            if singleton:
                provider: DependencyProvider[T] = SingletonProvider(interface, metadata)
            else:
                provider = FactoryProvider(interface, metadata)
            
            self._add_provider(interface, provider, metadata)
    
    def _add_provider(self, interface: Type[Any], provider: DependencyProvider[Any], metadata: DependencyMetadata) -> None:
        """Add a provider to the container."""
        self._providers[interface] = provider
        self._metadata[interface] = metadata
        
        # Add to dependency graph
        if self.config.enable_validation:
            self._analyze_dependencies(interface, metadata)
        
        # Create lifecycle manager if enabled
        if self.config.enable_lifecycle_management:
            self._lifecycle_managers[interface] = LifecycleManager(metadata)
        
        self.logger.debug(f"Registered {interface.__name__} -> {metadata.implementation.__name__} (stage: {metadata.stage.value})")
    
    def _analyze_dependencies(self, interface: Type[Any], metadata: DependencyMetadata) -> None:
        """Analyze dependencies for graph construction."""
        # This would analyze the implementation class to find its dependencies
        # For now, we'll use a simplified approach
        try:
            # Check constructor parameters
            import inspect
            sig = inspect.signature(metadata.implementation.__init__)
            for param_name, param in sig.parameters.items():
                if param_name != 'self' and param.annotation != inspect.Parameter.empty:
                    if param.annotation in self._providers:
                        self._graph.add_dependency(interface, param.annotation)
                        metadata.dependencies.add(param.annotation)
        except Exception as e:
            self.logger.warning(f"Could not analyze dependencies for {interface.__name__}: {e}")
    
    def resolve(self, dependency_type: Type[T]) -> T:
        """Resolve a dependency by type."""
        with self._lock:
            if dependency_type not in self._providers:
                raise DependencyError(f"Dependency not registered: {dependency_type.__name__}")
            
            # Check for circular dependencies
            if self.config.strict_mode and dependency_type in self._resolution_stack:
                cycle = self._resolution_stack[self._resolution_stack.index(dependency_type):] + [dependency_type]
                raise DependencyError(f"Circular dependency detected: {' -> '.join(t.__name__ for t in cycle)}")
            
            # Track resolution stack
            self._resolution_stack.append(dependency_type)
            
            try:
                provider = self._providers[dependency_type]
                instance = provider.get()
                
                # Update lifecycle if needed
                if self.config.enable_lifecycle_management and dependency_type in self._lifecycle_managers:
                    self._lifecycle_managers[dependency_type].set_phase(LifecyclePhase.READY)
                
                return instance
            finally:
                self._resolution_stack.pop()
    
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
    
    def get_registered_types(self) -> List[Type[Any]]:
        """Get all registered dependency types."""
        with self._lock:
            return list(self._providers.keys())
    
    def validate_graph(self) -> bool:
        """Validate the dependency graph."""
        if not self.config.enable_validation:
            return True
        
        try:
            # Detect cycles
            cycles = self._graph.detect_cycles()
            if cycles and not self.config.allow_circular_dependencies:
                cycle_str = '; '.join([' -> '.join(t.__name__ for t in cycle) for cycle in cycles])
                raise DependencyError(f"Circular dependencies detected: {cycle_str}")
            
            # Get dependency order
            order = self._graph.get_dependency_order()
            self.logger.info(f"Dependency resolution order: {[t.__name__ for t in order]}")
            
            return True
        except Exception as e:
            self.logger.error(f"Graph validation failed: {e}")
            return False
    
    def finalize(self) -> None:
        """Finalize the container and validate the dependency graph."""
        with self._lock:
            if self._finalized:
                return
            
            self._current_stage = RegistrationStage.DYNAMIC
            
            if not self.validate_graph():
                raise DependencyError("Dependency graph validation failed")
            
            self._finalized = True
            self.logger.info("Container finalized successfully")
    
    def advance_stage(self, stage: RegistrationStage) -> None:
        """Advance to the next registration stage."""
        with self._lock:
            if stage.value <= self._current_stage.value:
                raise DependencyError(f"Cannot advance to {stage.value} from {self._current_stage.value}")
            self._current_stage = stage
            self.logger.info(f"Advanced to stage: {stage.value}")
    
    def get_stage(self) -> RegistrationStage:
        """Get the current registration stage."""
        return self._current_stage
    
    def clear(self) -> None:
        """Clear all registered dependencies."""
        with self._lock:
            self._providers.clear()
            self._metadata.clear()
            self._graph = DependencyGraph()
            self._current_stage = RegistrationStage.BOOTSTRAP
            self._finalized = False
            self._resolution_stack.clear()
            self._lifecycle_managers.clear()
            self.logger.info("Container cleared")
    
    def get_metadata(self, dependency_type: Type[Any]) -> Optional[DependencyMetadata]:
        """Get metadata for a dependency type."""
        return self._metadata.get(dependency_type)
    
    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the dependency graph."""
        return {
            "node_count": len(self._providers),
            "has_cycles": len(self._graph.detect_cycles()) > 0,
            "resolution_order": [t.__name__ for t in self._graph.get_dependency_order()],
            "current_stage": self._current_stage.value,
            "finalized": self._finalized
        }
    
    # Compatibility methods for legacy API
    def create_planner_container(self):
        """Compatibility method for legacy API."""
        return PlannerContainer(self)
    
    def create_control_container(self):
        """Compatibility method for legacy API."""
        return ControlContainer(self)
    
    def create_communication_container(self):
        """Compatibility method for legacy API."""
        return CommunicationContainer(self)
    
    def create_hardware_container(self):
        """Compatibility method for legacy API."""
        return HardwareContainer(self)


class PlannerContainer:
    """Compatibility container for planner dependencies."""
    
    def __init__(self, container: DIContainerV2):
        self.container = container
    
    def get_se3_planner(self, config=None):
        """
        Get SE3 MPC planner.
        If a config is provided, it instantiates the planner directly.
        This is a workaround for testing and legacy compatibility.
        """
        from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner
        if config:
            # If config is provided, bypass the container to create a specific instance for testing.
            return SE3MPCPlanner(config)
        return self.container.resolve(SE3MPCPlanner)


class ControlContainer:
    """Compatibility container for control dependencies."""
    
    def __init__(self, container: DIContainerV2):
        self.container = container
    
    def get_geometric_controller(self, tuning_profile: str = "sitl_optimized"):
        """Get geometric controller with specified tuning profile."""
        from dart_planner.control.geometric_controller import GeometricController
        # The tuning profile is now passed directly to the constructor.
        # We can't use the simple resolve anymore, we have to instantiate it.
        # This highlights the weakness of this compatibility layer.
        return GeometricController(tuning_profile=tuning_profile)
    
    def get_trajectory_smoother(self):
        """Get trajectory smoother."""
        from dart_planner.control.trajectory_smoother import TrajectorySmoother
        return self.container.resolve(TrajectorySmoother)


class CommunicationContainer:
    """Compatibility container for communication dependencies."""
    
    def __init__(self, container: DIContainerV2):
        self.container = container
    
    def get_zmq_server(self, port: int = 5555, bind_address: str = "127.0.0.1"):
        """Get ZMQ server."""
        from dart_planner.communication.zmq_server import ZmqServer
        return ZmqServer(port=port, bind_address=bind_address)
    
    def get_zmq_client(self, server_address: str = "tcp://localhost:5555"):
        """Get ZMQ client."""
        from dart_planner.communication.zmq_client import ZmqClient
        return ZmqClient(server_address=server_address)


class HardwareContainer:
    """Compatibility container for hardware dependencies."""
    
    def __init__(self, container: DIContainerV2):
        self.container = container
    
    def get_airsim_adapter(self):
        """Get AirSim adapter."""
        from dart_planner.hardware.airsim_adapter import AirSimAdapter
        return self.container.resolve(AirSimAdapter)


class LifecycleManager:
    """Manages the lifecycle of a dependency."""
    
    def __init__(self, metadata: DependencyMetadata) -> None:
        self.metadata = metadata
    
    def set_phase(self, phase: LifecyclePhase) -> None:
        """Set the lifecycle phase."""
        self.metadata.lifecycle_phase = phase
    
    def get_phase(self) -> LifecyclePhase:
        """Get the current lifecycle phase."""
        return self.metadata.lifecycle_phase
    
    def is_ready(self) -> bool:
        """Check if the dependency is ready."""
        return self.metadata.lifecycle_phase in [LifecyclePhase.READY, LifecyclePhase.RUNNING]


class ContainerBuilder:
    """Builder for creating DI containers with staged registration."""
    
    def __init__(self, config: Optional[ContainerConfig] = None) -> None:
        self.container = DIContainerV2(config)
    
    def bootstrap_stage(self) -> 'BootstrapStageBuilder':
        """Start bootstrap stage registration."""
        return BootstrapStageBuilder(self.container)
    
    def runtime_stage(self) -> 'RuntimeStageBuilder':
        """Start runtime stage registration."""
        return RuntimeStageBuilder(self.container)
    
    def build(self) -> DIContainerV2:
        """Build and finalize the container."""
        self.container.finalize()
        return self.container


class BootstrapStageBuilder:
    """Builder for bootstrap stage dependencies."""
    
    def __init__(self, container: DIContainerV2) -> None:
        self.container = container
    
    def register_config(self, config_class: Type[Any]) -> 'BootstrapStageBuilder':
        """Register a configuration class."""
        self.container.register_singleton(config_class, config_class, stage=RegistrationStage.BOOTSTRAP)
        return self
    
    def register_logging(self, logging_class: Type[Any]) -> 'BootstrapStageBuilder':
        """Register a logging class."""
        self.container.register_singleton(logging_class, logging_class, stage=RegistrationStage.BOOTSTRAP)
        return self
    
    def done(self) -> ContainerBuilder:
        """Complete bootstrap stage."""
        self.container.advance_stage(RegistrationStage.RUNTIME)
        return ContainerBuilder(self.container.config)


class RuntimeStageBuilder:
    """Builder for runtime stage dependencies."""
    
    def __init__(self, container: DIContainerV2) -> None:
        self.container = container
    
    def register_service(self, interface: Type[Any], implementation: Type[Any], 
                        singleton: bool = True) -> 'RuntimeStageBuilder':
        """Register a service."""
        if singleton:
            self.container.register_singleton(interface, implementation, stage=RegistrationStage.RUNTIME)
        else:
            self.container.register_factory(interface, implementation, stage=RegistrationStage.RUNTIME)
        return self
    
    def register_controller(self, controller_class: Type[Any]) -> 'RuntimeStageBuilder':
        """Register a controller."""
        self.container.register_singleton(controller_class, controller_class, stage=RegistrationStage.RUNTIME)
        return self
    
    def register_planner(self, planner_class: Type[Any]) -> 'RuntimeStageBuilder':
        """Register a planner."""
        self.container.register_singleton(planner_class, planner_class, stage=RegistrationStage.RUNTIME)
        return self
    
    def done(self) -> ContainerBuilder:
        """Complete runtime stage."""
        return ContainerBuilder(self.container.config)


def create_container(config: Optional[ContainerConfig] = None) -> ContainerBuilder:
    """Create a new container builder."""
    return ContainerBuilder(config)


@contextmanager
def container_context(container: DIContainerV2):
    """Context manager for container lifecycle."""
    try:
        yield container
    finally:
        container.clear()


class DependencyError(Exception):
    """Exception raised for dependency injection errors."""
    pass


# Singleton default container for migration
_default_container: Optional[DIContainerV2] = None

def get_container() -> DIContainerV2:
    """Get the default container instance."""
    global _default_container
    if _default_container is None:
        builder = create_container()
        # Optionally, register more services here if needed
        _default_container = builder.build()
    return _default_container 