"""
Tests for Frozen Configuration System

Tests the immutable configuration objects with Pydantic validation
and startup validation to prevent runtime modification.
"""

import pytest
import os
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import patch

from dart_planner.config.frozen_config import (
    DARTPlannerFrozenConfig, SecurityConfig, RealTimeConfig, HardwareConfig,
    CommunicationConfig, LoggingConfig, SimulationConfig, ConfigurationManager,
    get_frozen_config, freeze_configuration, validate_startup_configuration,
    temporary_config, ConfigurationError
)


class TestFrozenConfigModels:
    """Test frozen configuration models."""
    
    def test_security_config_validation(self):
        """Test security configuration validation."""
        # Valid configuration
        config = SecurityConfig(
            enable_authentication=True,
            jwt_secret_key="test_secret_key_that_is_long_enough_for_validation",
            jwt_expiration_minutes=30
        )
        assert config.enable_authentication is True
        assert config.jwt_expiration_minutes == 30
        
        # Invalid JWT expiration
        with pytest.raises(ValueError, match="JWT expiration must be between"):
            SecurityConfig(jwt_expiration_minutes=0)
        
        # Invalid BCrypt rounds
        with pytest.raises(ValueError, match="BCrypt rounds must be between"):
            SecurityConfig(bcrypt_rounds=5)
    
    def test_real_time_config_validation(self):
        """Test real-time configuration validation."""
        # Valid configuration
        config = RealTimeConfig(
            control_loop_frequency_hz=400.0,
            planning_loop_frequency_hz=25.0,
            max_control_latency_ms=2.0
        )
        assert config.control_loop_frequency_hz == 400.0
        assert config.planning_loop_frequency_hz == 25.0
        
        # Invalid frequency relationship
        with pytest.raises(ValueError, match="Control loop frequency must be higher"):
            RealTimeConfig(
                control_loop_frequency_hz=25.0,
                planning_loop_frequency_hz=400.0
            )
        
        # Invalid latency
        with pytest.raises(ValueError, match="Control latency must be less than"):
            RealTimeConfig(
                control_loop_frequency_hz=100.0,  # 10ms period
                max_control_latency_ms=15.0  # 15ms latency > 10ms period
            )
    
    def test_hardware_config_validation(self):
        """Test hardware configuration validation."""
        # Valid configuration
        config = HardwareConfig(
            max_velocity_mps=15.0,
            max_acceleration_mps2=10.0,
            max_altitude_m=50.0,
            emergency_landing_altitude_m=2.0
        )
        assert config.max_velocity_mps == 15.0
        assert config.max_altitude_m == 50.0
        
        # Invalid geofence polygon
        with pytest.raises(ValueError, match="Geofence polygon must have at least 3 points"):
            HardwareConfig(geofence_polygon=[[0, 0], [1, 1]])
        
        # Invalid polygon point
        with pytest.raises(ValueError, match="Geofence polygon points must have 2 coordinates"):
            HardwareConfig(geofence_polygon=[[0, 0, 0], [1, 1], [2, 2]])
    
    def test_communication_config_validation(self):
        """Test communication configuration validation."""
        # Valid configuration
        config = CommunicationConfig(
            heartbeat_interval_ms=100,
            heartbeat_timeout_ms=500
        )
        assert config.heartbeat_interval_ms == 100
        assert config.heartbeat_timeout_ms == 500
        
        # Invalid heartbeat timeout
        with pytest.raises(ValueError, match="Heartbeat timeout must be greater than"):
            CommunicationConfig(
                heartbeat_interval_ms=500,
                heartbeat_timeout_ms=100
            )
    
    def test_logging_config_validation(self):
        """Test logging configuration validation."""
        # Valid configuration
        config = LoggingConfig(log_level="INFO")
        assert config.log_level == "INFO"
        
        # Invalid log level
        with pytest.raises(ValueError, match="Log level must be one of"):
            LoggingConfig(log_level="INVALID")
    
    def test_simulation_config_validation(self):
        """Test simulation configuration validation."""
        # Valid configuration
        config = SimulationConfig(enable_airsim=True)
        assert config.enable_airsim is True
        
        # Multiple simulations enabled
        with pytest.raises(ValueError, match="Only one simulation environment can be enabled"):
            SimulationConfig(
                enable_airsim=True,
                enable_sitl=True
            )
    
    def test_main_config_validation(self):
        """Test main configuration validation."""
        # Valid configuration
        config = DARTPlannerFrozenConfig(
            environment="development",
            debug=False,
            custom_settings={"test_key": "test_value"}
        )
        assert config.environment == "development"
        assert config.debug is False
        assert ("test_key", "test_value") in config.custom_settings
        
        # Invalid environment
        with pytest.raises(ValueError, match="Environment must be one of"):
            DARTPlannerFrozenConfig(environment="invalid")
        
        # Production with debug enabled
        with pytest.raises(ValueError, match="Debug mode cannot be enabled in production"):
            DARTPlannerFrozenConfig(
                environment="production",
                debug=True
            )
    
    def test_config_immutability(self):
        """Test that configuration objects are immutable."""
        config = SecurityConfig(
            jwt_secret_key="test_secret_key_that_is_long_enough_for_validation"
        )
        
        # Try to modify a field (should raise error)
        with pytest.raises(TypeError):
            config.enable_authentication = False
        
        # Try to add a new field (should raise error)
        with pytest.raises(TypeError):
            config.new_field = "value"


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigurationManager()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config_defaults(self):
        """Test loading configuration with defaults."""
        config = self.config_manager.load_config()
        
        assert isinstance(config, DARTPlannerFrozenConfig)
        assert config.environment == "development"
        assert config.debug is False
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.real_time, RealTimeConfig)
    
    def test_load_config_from_json(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "environment": "testing",
            "debug": True,
            "security": {
                "enable_authentication": False,
                "jwt_secret_key": "test_secret_key_that_is_long_enough_for_validation"
            }
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        manager = ConfigurationManager(str(config_file))
        config = manager.load_config()
        
        assert config.environment == "testing"
        assert config.debug is True
        assert config.security.enable_authentication is False
    
    def test_load_config_from_yaml(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "environment": "testing",
            "debug": True,
            "real_time": {
                "control_loop_frequency_hz": 500.0
            }
        }
        
        config_file = Path(self.temp_dir) / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        manager = ConfigurationManager(str(config_file))
        config = manager.load_config()
        
        assert config.environment == "testing"
        assert config.debug is True
        assert config.real_time.control_loop_frequency_hz == 500.0
    
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            'DART_ENVIRONMENT': 'production',
            'DART_DEBUG': 'false',
            'DART_JWT_SECRET_KEY': 'test_secret_key_that_is_long_enough_for_validation',
            'DART_CONTROL_FREQUENCY_HZ': '600.0',
            'DART_MAX_VELOCITY_MPS': '20.0'
        }):
            config = self.config_manager.load_config()
            
            assert config.environment == "production"
            assert config.debug is False
            assert config.security.jwt_secret_key == "test_secret_key_that_is_long_enough_for_validation"
            assert config.real_time.control_loop_frequency_hz == 600.0
            assert config.hardware.max_velocity_mps == 20.0
    
    def test_config_freeze(self):
        """Test configuration freezing."""
        config = self.config_manager.load_config()
        
        # Initially not frozen
        assert not self.config_manager.is_frozen()
        
        # Freeze configuration
        self.config_manager.freeze_config()
        assert self.config_manager.is_frozen()
        
        # Should return same config instance
        frozen_config = self.config_manager.get_config()
        assert frozen_config is config
    
    def test_validate_startup_success(self):
        """Test successful startup validation."""
        config = self.config_manager.load_config()
        
        # Should pass validation
        assert self.config_manager.validate_startup()
    
    def test_validate_startup_production_debug(self):
        """Test startup validation with production debug mode."""
        config_data = {
            "environment": "production",
            "debug": True
        }
        
        # Should fail validation
        with pytest.raises(ConfigurationError, match="Debug mode cannot be enabled in production"):
            config = DARTPlannerFrozenConfig(**config_data)
    
    def test_validate_startup_production_no_jwt(self):
        """Test startup validation with production but no JWT secret."""
        config_data = {
            "environment": "production",
            "security": {
                "jwt_secret_key": None
            }
        }
        
        # Should fail validation
        with pytest.raises(ConfigurationError, match="JWT secret key must be set in production"):
            config = DARTPlannerFrozenConfig(**config_data)
    
    def test_validate_real_time_requirements(self):
        """Test real-time requirements validation."""
        # Invalid frequency relationship
        config_data = {
            "real_time": {
                "control_loop_frequency_hz": 25.0,
                "planning_loop_frequency_hz": 400.0
            }
        }
        
        with pytest.raises(ConfigurationError, match="Control loop frequency must be higher"):
            config = DARTPlannerFrozenConfig(**config_data)
            self.config_manager._validate_real_time_requirements(config)
    
    def test_validate_hardware_constraints(self):
        """Test hardware constraints validation."""
        # Invalid altitude relationship
        config_data = {
            "hardware": {
                "max_altitude_m": 10.0,
                "emergency_landing_altitude_m": 15.0
            }
        }
        
        with pytest.raises(ConfigurationError, match="Emergency landing altitude must be less than"):
            config = DARTPlannerFrozenConfig(**config_data)
            self.config_manager._validate_hardware_constraints(config)


class TestGlobalConfiguration:
    """Test global configuration functions."""
    
    def test_get_frozen_config(self):
        """Test getting frozen configuration."""
        config = get_frozen_config()
        assert isinstance(config, DARTPlannerFrozenConfig)
    
    def test_freeze_configuration(self):
        """Test freezing global configuration."""
        freeze_configuration()
        
        # Should be frozen
        manager = ConfigurationManager()
        assert manager.is_frozen()
    
    def test_validate_startup_configuration(self):
        """Test validating startup configuration."""
        # Should pass with default configuration
        assert validate_startup_configuration()


class TestTemporaryConfig:
    """Test temporary configuration context manager."""
    
    def test_temporary_config(self):
        """Test temporary configuration changes."""
        original_config = get_frozen_config()
        
        with temporary_config({"environment": "testing", "debug": True}) as temp_config:
            assert temp_config.environment == "testing"
            assert temp_config.debug is True
            
            # Original config should be unchanged
            assert original_config.environment == "development"
            assert original_config.debug is False
        
        # After context, should be back to original
        current_config = get_frozen_config()
        assert current_config.environment == "development"
        assert current_config.debug is False
    
    def test_temporary_config_nested(self):
        """Test temporary configuration with nested updates."""
        with temporary_config({
            "security": {"enable_authentication": False},
            "real_time": {"control_loop_frequency_hz": 500.0}
        }) as temp_config:
            assert temp_config.security.enable_authentication is False
            assert temp_config.real_time.control_loop_frequency_hz == 500.0


class TestConfigurationErrorHandling:
    """Test configuration error handling."""
    
    def test_invalid_json_file(self):
        """Test loading invalid JSON file."""
        config_file = Path(self.temp_dir) / "invalid.json"
        with open(config_file, 'w') as f:
            f.write("invalid json content")
        
        manager = ConfigurationManager(str(config_file))
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            manager.load_config()
    
    def test_unsupported_file_format(self):
        """Test loading unsupported file format."""
        config_file = Path(self.temp_dir) / "config.txt"
        with open(config_file, 'w') as f:
            f.write("plain text")
        
        manager = ConfigurationManager(str(config_file))
        with pytest.raises(ConfigurationError, match="Unsupported configuration file format"):
            manager.load_config()
    
    def test_missing_required_field(self):
        """Test missing required field in production."""
        with patch.dict(os.environ, {'DART_ENVIRONMENT': 'production'}):
            with pytest.raises(ValueError, match="JWT secret key must be provided"):
                DARTPlannerFrozenConfig()


class TestConfigurationPerformance:
    """Test configuration performance."""
    
    def test_config_loading_performance(self):
        """Test configuration loading performance."""
        import time
        
        start_time = time.time()
        config = get_frozen_config()
        load_time = time.time() - start_time
        
        # Should load quickly (less than 100ms)
        assert load_time < 0.1
    
    def test_config_validation_performance(self):
        """Test configuration validation performance."""
        import time
        
        config = get_frozen_config()
        
        start_time = time.time()
        for _ in range(100):
            config.validate_startup()
        validation_time = time.time() - start_time
        
        # Should validate quickly (less than 1 second for 100 validations)
        assert validation_time < 1.0


class TestConfigurationSerialization:
    """Test configuration serialization."""
    
    def test_config_to_dict(self):
        """Test converting configuration to dictionary."""
        config = get_frozen_config()
        config_dict = config.dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['environment'] == config.environment
        assert config_dict['security']['enable_authentication'] == config.security.enable_authentication
    
    def test_config_to_json(self):
        """Test converting configuration to JSON."""
        config = get_frozen_config()
        config_json = config.json()
        
        assert isinstance(config_json, str)
        config_dict = json.loads(config_json)
        assert config_dict['environment'] == config.environment
    
    def test_config_copy(self):
        """Test copying configuration."""
        config = get_frozen_config()
        config_copy = config.copy()
        
        assert config_copy is not config
        assert config_copy.environment == config.environment
        assert config_copy.security.enable_authentication == config.security.enable_authentication 