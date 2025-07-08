"""
Tests for DIContainerV2

Tests the new dependency injection container with staged registration,
static graph validation, and lifecycle management.
"""

import os
import pytest
import threading
from unittest.mock import Mock, MagicMock
from typing import Optional

# Set test environment for SecureSerializer
os.environ["DART_ENVIRONMENT"] = "testing"

from dart_planner.common.di_container_v2 import (
    DIContainerV2, ContainerConfig, RegistrationStage, LifecyclePhase,
    DependencyError, DependencyMetadata, create_container, container_context,
    BootstrapStageBuilder, RuntimeStageBuilder
)


class TestService:
    """Test service class."""
    def __init__(self, config: Optional['TestConfig'] = None):
        self.config = config
        self.name = "TestService"


class TestConfig:
    """Test configuration class."""
    def __init__(self):
        self.value = "test_config"


class TestController:
    """Test controller class."""
    def __init__(self, service: TestService):
        self.service = service


class TestPlanner:
    """Test planner class."""
    def __init__(self, service: TestService, controller: TestController):
        self.service = service
        self.controller = controller


class TestCircularA:
    """Test class with circular dependency."""
    def __init__(self, b: 'TestCircularB'):
        self.b = b


class TestCircularB:
    """Test class with circular dependency."""
    def __init__(self, a: TestCircularA):
        self.a = a


class TestDIContainerV2:
    """Test DIContainerV2 functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ContainerConfig(
            enable_validation=True,
            enable_lifecycle_management=True,
            strict_mode=True
        )
        self.container = DIContainerV2(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.container.clear()
    
    def test_initialization(self):
        """Test container initialization."""
        assert self.container.get_stage() == RegistrationStage.BOOTSTRAP
        assert not self.container._finalized
        assert self.container.config.enable_validation is True
    
    def test_register_singleton(self):
        """Test singleton registration."""
        self.container.register_singleton(TestService, TestService)
        
        # Verify registration
        assert self.container.has_dependency(TestService)
        metadata = self.container.get_metadata(TestService)
        assert metadata.singleton is True
        assert metadata.stage == RegistrationStage.RUNTIME
    
    def test_register_factory(self):
        """Test factory registration."""
        self.container.register_factory(TestService, TestService)
        
        # Verify registration
        assert self.container.has_dependency(TestService)
        metadata = self.container.get_metadata(TestService)
        assert metadata.singleton is False
    
    def test_register_instance(self):
        """Test instance registration."""
        instance = TestService()
        self.container.register_instance(TestService, instance)
        
        # Verify registration
        assert self.container.has_dependency(TestService)
        resolved = self.container.resolve(TestService)
        assert resolved is instance
    
    def test_resolve_dependency(self):
        """Test dependency resolution."""
        self.container.register_singleton(TestService, TestService)
        
        # Resolve dependency
        instance = self.container.resolve(TestService)
        assert isinstance(instance, TestService)
    
    def test_resolve_optional(self):
        """Test optional dependency resolution."""
        # Resolve non-existent dependency
        result = self.container.resolve_optional(TestService)
        assert result is None
        
        # Register and resolve
        self.container.register_singleton(TestService, TestService)
        result = self.container.resolve_optional(TestService)
        assert isinstance(result, TestService)
    
    def test_staged_registration(self):
        """Test staged registration."""
        # Register in bootstrap stage
        self.container.register_singleton(TestConfig, TestConfig, RegistrationStage.BOOTSTRAP)
        
        # Advance to runtime stage
        self.container.advance_stage(RegistrationStage.RUNTIME)
        assert self.container.get_stage() == RegistrationStage.RUNTIME
        
        # Register in runtime stage
        self.container.register_singleton(TestService, TestService, RegistrationStage.RUNTIME)
        
        # Try to register in bootstrap stage from runtime (should fail)
        with pytest.raises(DependencyError, match="Cannot register"):
            self.container.register_singleton(TestController, TestController, RegistrationStage.BOOTSTRAP)
    
    def test_finalization(self):
        """Test container finalization."""
        # Register dependencies
        self.container.register_singleton(TestConfig, TestConfig)
        self.container.register_singleton(TestService, TestService)
        
        # Finalize container
        self.container.finalize()
        assert self.container._finalized
        
        # Try to register after finalization (should fail)
        with pytest.raises(DependencyError, match="Cannot register"):
            self.container.register_singleton(TestController, TestController)
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        # Register circular dependencies
        self.container.register_singleton(TestCircularA, TestCircularA)
        self.container.register_singleton(TestCircularB, TestCircularB)
        
        # Try to resolve (should detect circular dependency)
        with pytest.raises(DependencyError, match="Circular dependency"):
            self.container.resolve(TestCircularA)
    
    def test_circular_dependency_allowed(self):
        """Test circular dependency when allowed."""
        config = ContainerConfig(allow_circular_dependencies=True, strict_mode=False)
        container = DIContainerV2(config)
        
        # Register circular dependencies
        container.register_singleton(TestCircularA, TestCircularA)
        container.register_singleton(TestCircularB, TestCircularB)
        
        # Should not raise error
        container.finalize()
    
    def test_dependency_order(self):
        """Test dependency resolution order."""
        # Register dependencies with dependencies
        self.container.register_singleton(TestConfig, TestConfig)
        self.container.register_singleton(TestService, TestService)
        self.container.register_singleton(TestController, TestController)
        
        # Finalize to validate graph
        self.container.finalize()
        
        # Get graph info
        graph_info = self.container.get_graph_info()
        assert 'resolution_order' in graph_info
        assert len(graph_info['resolution_order']) > 0
    
    def test_lifecycle_management(self):
        """Test lifecycle management."""
        self.container.register_singleton(TestService, TestService)
        
        # Resolve dependency
        instance = self.container.resolve(TestService)
        
        # Check lifecycle
        manager = self.container._lifecycle_managers[TestService]
        assert manager.get_phase() == LifecyclePhase.READY
        assert manager.is_ready()
    
    def test_thread_safety(self):
        """Test thread safety of container operations."""
        # Register dependency
        self.container.register_singleton(TestService, TestService)
        
        # Create multiple threads that resolve the dependency
        results = []
        errors = []
        
        def resolve_dependency():
            try:
                result = self.container.resolve(TestService)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=resolve_dependency)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors and all results should be the same instance
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result is results[0] for result in results)


class TestContainerBuilder:
    """Test container builder pattern."""
    
    def test_builder_pattern(self):
        """Test container builder pattern."""
        builder = create_container()
        
        # Bootstrap stage
        bootstrap = builder.bootstrap_stage()
        bootstrap.register_config(TestConfig)
        
        # Runtime stage
        runtime = builder.runtime_stage()
        runtime.register_service(TestService, TestService)
        runtime.register_controller(TestController)
        
        # Build container
        container = builder.build()
        
        # Verify container
        assert container._finalized
        assert container.has_dependency(TestConfig)
        assert container.has_dependency(TestService)
        assert container.has_dependency(TestController)
    
    def test_bootstrap_stage_builder(self):
        """Test bootstrap stage builder."""
        builder = create_container()
        bootstrap = builder.bootstrap_stage()
        
        # Register dependencies
        bootstrap.register_config(TestConfig)
        bootstrap.register_logging(TestService)
        
        # Verify registrations
        container = builder.container
        assert container.has_dependency(TestConfig)
        assert container.has_dependency(TestService)
        
        # Check stages
        config_metadata = container.get_metadata(TestConfig)
        assert config_metadata.stage == RegistrationStage.BOOTSTRAP
    
    def test_runtime_stage_builder(self):
        """Test runtime stage builder."""
        builder = create_container()
        runtime = builder.runtime_stage()
        
        # Register dependencies
        runtime.register_service(TestService, TestService)
        runtime.register_controller(TestController)
        runtime.register_planner(TestPlanner)
        
        # Verify registrations
        container = builder.container
        assert container.has_dependency(TestService)
        assert container.has_dependency(TestController)
        assert container.has_dependency(TestPlanner)
        
        # Check stages
        service_metadata = container.get_metadata(TestService)
        assert service_metadata.stage == RegistrationStage.RUNTIME


class TestContainerContext:
    """Test container context manager."""
    
    def test_container_context(self):
        """Test container context manager."""
        container = DIContainerV2()
        container.register_singleton(TestService, TestService)
        
        with container_context(container) as ctx:
            # Container should be in running state
            for manager in container._lifecycle_managers.values():
                assert manager.get_phase() == LifecyclePhase.RUNNING
            
            # Resolve dependency
            instance = ctx.resolve(TestService)
            assert isinstance(instance, TestService)
        
        # Container should be in stopped state
        for manager in container._lifecycle_managers.values():
            assert manager.get_phase() == LifecyclePhase.STOPPED


class TestConfiguration:
    """Test container configuration."""
    
    def test_configuration_validation_disabled(self):
        """Test container with validation disabled."""
        config = ContainerConfig(enable_validation=False)
        container = DIContainerV2(config)
        
        # Register circular dependencies (should not be detected)
        container.register_singleton(TestCircularA, TestCircularA)
        container.register_singleton(TestCircularB, TestCircularB)
        
        # Should finalize without error
        container.finalize()
    
    def test_configuration_lifecycle_disabled(self):
        """Test container with lifecycle management disabled."""
        config = ContainerConfig(enable_lifecycle_management=False)
        container = DIContainerV2(config)
        
        container.register_singleton(TestService, TestService)
        instance = container.resolve(TestService)
        
        # Should not have lifecycle managers
        assert len(container._lifecycle_managers) == 0
    
    def test_configuration_strict_mode_disabled(self):
        """Test container with strict mode disabled."""
        config = ContainerConfig(strict_mode=False)
        container = DIContainerV2(config)
        
        # Register circular dependencies
        container.register_singleton(TestCircularA, TestCircularA)
        container.register_singleton(TestCircularB, TestCircularB)
        
        # Should not detect circular dependencies in resolution
        container.finalize()


class TestErrorHandling:
    """Test error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ContainerConfig(
            enable_validation=True,
            enable_lifecycle_management=True,
            strict_mode=True
        )
        self.container = DIContainerV2(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.container.clear()
    
    def test_resolve_unregistered_dependency(self):
        """Test resolving unregistered dependency."""
        with pytest.raises(DependencyError, match="Dependency not registered"):
            self.container.resolve(TestService)
    
    def test_advance_stage_invalid(self):
        """Test advancing to invalid stage."""
        with pytest.raises(DependencyError, match="Cannot advance"):
            self.container.advance_stage(RegistrationStage.BOOTSTRAP)
    
    def test_register_after_finalization(self):
        """Test registering after finalization."""
        self.container.finalize()
        
        with pytest.raises(DependencyError, match="Cannot register"):
            self.container.register_singleton(TestService, TestService)
    
    def test_factory_function_error(self):
        """Test factory function that raises an error."""
        def error_factory():
            raise ValueError("Factory error")
        
        self.container.register_factory(TestService, TestService, factory_func=error_factory)
        
        with pytest.raises(ValueError, match="Factory error"):
            self.container.resolve(TestService)


class TestGraphValidation:
    """Test graph validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ContainerConfig(
            enable_validation=True,
            enable_lifecycle_management=True,
            strict_mode=True
        )
        self.container = DIContainerV2(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.container.clear()
    
    def test_graph_validation_success(self):
        """Test successful graph validation."""
        # Register valid dependencies
        self.container.register_singleton(TestConfig, TestConfig)
        self.container.register_singleton(TestService, TestService)
        self.container.register_singleton(TestController, TestController)
        
        # Validate graph
        assert self.container.validate_graph()
    
    def test_graph_validation_failure(self):
        """Test graph validation failure."""
        # Register circular dependencies
        self.container.register_singleton(TestCircularA, TestCircularA)
        self.container.register_singleton(TestCircularB, TestCircularB)
        
        # Validate graph (should fail)
        assert not self.container.validate_graph()
    
    def test_get_graph_info(self):
        """Test getting graph information."""
        # Register dependencies
        self.container.register_singleton(TestConfig, TestConfig)
        self.container.register_singleton(TestService, TestService)
        
        # Get graph info
        info = self.container.get_graph_info()
        
        # Verify info structure
        assert 'node_count' in info
        assert 'cycles' in info
        assert 'resolution_order' in info
        assert 'current_stage' in info
        assert 'finalized' in info
        
        assert info['node_count'] >= 0
        assert isinstance(info['cycles'], list)
        assert isinstance(info['resolution_order'], list) 