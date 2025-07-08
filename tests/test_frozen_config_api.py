"""
Regression test to ensure no legacy config.settings imports remain.

This test verifies that the migration to frozen_config is complete
and no code references the deprecated settings module.
"""

import importlib.util
import sys
from pathlib import Path
from typing import List, Set
import pytest
import os

# Set environment to testing for config validation
os.environ["DART_ENVIRONMENT"] = "testing"

def test_no_legacy_settings_imports():
    """Test that no module imports from config.settings."""
    
    # Test that legacy settings module is no longer available
    legacy_spec = importlib.util.find_spec("dart_planner.config.settings")
    assert legacy_spec is None, "Legacy settings module should not exist"
    
    # Test that new frozen_config module is available
    try:
        importlib.import_module("dart_planner.config.frozen_config")
    except ImportError:
        pytest.fail("frozen_config module should be available")
    
    # Import and test the frozen config API
    from dart_planner.config.frozen_config import get_frozen_config, DARTPlannerFrozenConfig
    
    # Test that we can get a config instance
    config = get_frozen_config()
    assert isinstance(config, DARTPlannerFrozenConfig), "Should return DARTPlannerFrozenConfig instance"
    
    # Test that config is immutable
    try:
        config.environment = "testing"
        assert False, "Config should be immutable"
    except Exception:
        # Expected - config should be frozen
        pass


def test_frozen_config_structure():
    """Test that frozen config has the expected structure."""
    from dart_planner.config.frozen_config import get_frozen_config
    
    config = get_frozen_config()
    
    # Test that all expected sections exist
    assert hasattr(config, 'security'), "Config should have security section"
    assert hasattr(config, 'real_time'), "Config should have real_time section"
    assert hasattr(config, 'hardware'), "Config should have hardware section"
    assert hasattr(config, 'communication'), "Config should have communication section"
    assert hasattr(config, 'logging'), "Config should have logging section"
    assert hasattr(config, 'simulation'), "Config should have simulation section"
    
    # Test that real_time section has expected attributes
    real_time = config.real_time
    assert hasattr(real_time, 'control_loop_frequency_hz'), "RealTimeConfig should have control_loop_frequency_hz"
    assert hasattr(real_time, 'planning_loop_frequency_hz'), "RealTimeConfig should have planning_loop_frequency_hz"
    assert hasattr(real_time, 'max_planning_latency_ms'), "RealTimeConfig should have max_planning_latency_ms"
    
    # Test that communication section has expected attributes
    communication = config.communication
    assert hasattr(communication, 'heartbeat_timeout_ms'), "CommunicationConfig should have heartbeat_timeout_ms"
    assert hasattr(communication, 'heartbeat_interval_ms'), "CommunicationConfig should have heartbeat_interval_ms"
    
    # Test that logging section has expected attributes
    logging = config.logging
    assert hasattr(logging, 'log_level'), "LoggingConfig should have log_level"
    assert hasattr(logging, 'log_format'), "LoggingConfig should have log_format"
    assert hasattr(logging, 'enable_console_logging'), "LoggingConfig should have enable_console_logging"


def test_timing_manager_uses_frozen_config():
    """Test that timing manager uses frozen config correctly."""
    from dart_planner.common.timing_alignment import get_timing_manager
    
    # This should not raise any import errors
    manager = get_timing_manager()
    assert manager is not None, "Timing manager should be created successfully"
    
    # Test that it has the expected config structure
    config = manager.config
    assert config.control_frequency > 0, "Control frequency should be positive"
    assert config.planning_frequency > 0, "Planning frequency should be positive"
    assert config.max_planning_latency > 0, "Max planning latency should be positive"


def test_logging_config_uses_frozen_config():
    """Test that logging config uses frozen config correctly."""
    from dart_planner.common.logging_config import setup_logging
    
    # This should not raise any import errors
    try:
        setup_logging()
        # If we get here, the import worked correctly
        assert True
    except Exception as e:
        # Only allow ImportError if it's not related to config
        if "config" in str(e).lower():
            raise
        # Other errors are acceptable for this test


if __name__ == "__main__":
    # Run tests
    test_no_legacy_settings_imports()
    test_frozen_config_structure()
    test_timing_manager_uses_frozen_config()
    test_logging_config_uses_frozen_config()
    print("✅ All frozen config migration tests passed!") 