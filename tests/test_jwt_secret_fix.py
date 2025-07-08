"""
Test JWT secret key fallback fix

Verifies that the system fails hard when DART_SECRET_KEY is not set,
instead of falling back to hardcoded development keys.
"""

import pytest
import os
from unittest.mock import patch
from dart_planner.common.errors import SecurityError


class TestJWTSecretKeyFix:
    """Test that JWT secret key fallback is properly fixed"""
    
    def setup_method(self):
        """Set up test environment"""
        # Remove DART_SECRET_KEY from environment for testing
        self.original_secret_key = os.environ.pop("DART_SECRET_KEY", None)
    
    def teardown_method(self):
        """Clean up test environment"""
        # Restore original environment
        if self.original_secret_key:
            os.environ["DART_SECRET_KEY"] = self.original_secret_key
    
    def test_auth_module_fails_without_secret_key(self):
        """Test that auth.py fails hard when DART_SECRET_KEY is not set"""
        # Remove DART_SECRET_KEY from environment
        if "DART_SECRET_KEY" in os.environ:
            del os.environ["DART_SECRET_KEY"]
        
        # Import should fail with SecurityError
        with pytest.raises(SecurityError, match="DART_SECRET_KEY environment variable must be set"):
            import dart_planner.security.auth
    
    def test_middleware_fails_without_secret_key(self):
        """Test that middleware.py fails hard when DART_SECRET_KEY is not set"""
        # Remove DART_SECRET_KEY from environment
        if "DART_SECRET_KEY" in os.environ:
            del os.environ["DART_SECRET_KEY"]
        
        # Import should fail with ValueError
        with pytest.raises(ValueError, match="DART_SECRET_KEY environment variable must be set"):
            import dart_planner.gateway.middleware
    
    def test_auth_module_works_with_secret_key(self):
        """Test that auth.py works when DART_SECRET_KEY is set"""
        # Set a test secret key
        os.environ["DART_SECRET_KEY"] = "test_secret_key_for_testing_only"
        
        # Import should succeed
        try:
            import dart_planner.security.auth
            # If we get here, the import succeeded
            assert True
        except Exception as e:
            pytest.fail(f"Import failed unexpectedly: {e}")
    
    def test_middleware_works_with_secret_key(self):
        """Test that middleware.py works when DART_SECRET_KEY is set"""
        # Set a test secret key
        os.environ["DART_SECRET_KEY"] = "test_secret_key_for_testing_only"
        
        # Import should succeed
        try:
            import dart_planner.gateway.middleware
            # If we get here, the import succeeded
            assert True
        except Exception as e:
            pytest.fail(f"Import failed unexpectedly: {e}")
    
    def test_no_hardcoded_fallback_keys(self):
        """Test that no hardcoded development keys are used"""
        # Check that the hardcoded keys are not present in the source
        import dart_planner.security.auth as auth_module
        import dart_planner.gateway.middleware as middleware_module
        
        # Get source code
        auth_source = auth_module.__file__
        middleware_source = middleware_module.__file__
        
        # Read source files
        with open(auth_source, 'r') as f:
            auth_code = f.read()
        
        with open(middleware_source, 'r') as f:
            middleware_code = f.read()
        
        # Check that hardcoded development keys are not present
        hardcoded_keys = [
            "dev_secret_key_do_not_use_in_production",
            "default_zmq_secret",
            "test_secret_key"
        ]
        
        for key in hardcoded_keys:
            assert key not in auth_code, f"Hardcoded key '{key}' found in auth.py"
            assert key not in middleware_code, f"Hardcoded key '{key}' found in middleware.py"
    
    def test_environment_variable_requirement(self):
        """Test that environment variable is properly required"""
        # Test with empty string
        os.environ["DART_SECRET_KEY"] = ""
        
        with pytest.raises(SecurityError, match="DART_SECRET_KEY environment variable must be set"):
            import dart_planner.security.auth
        
        # Test with whitespace-only string
        os.environ["DART_SECRET_KEY"] = "   "
        
        with pytest.raises(SecurityError, match="DART_SECRET_KEY environment variable must be set"):
            import dart_planner.security.auth
    
    def test_production_environment_handling(self):
        """Test that production environment is handled correctly"""
        # Set production environment
        os.environ["DART_ENVIRONMENT"] = "production"
        
        # Remove secret key
        if "DART_SECRET_KEY" in os.environ:
            del os.environ["DART_SECRET_KEY"]
        
        # Should still fail with the same error (no special production handling)
        with pytest.raises(SecurityError, match="DART_SECRET_KEY environment variable must be set"):
            import dart_planner.security.auth
    
    def test_development_environment_handling(self):
        """Test that development environment is handled correctly"""
        # Set development environment
        os.environ["DART_ENVIRONMENT"] = "development"
        
        # Remove secret key
        if "DART_SECRET_KEY" in os.environ:
            del os.environ["DART_SECRET_KEY"]
        
        # Should still fail (no fallback to development keys)
        with pytest.raises(SecurityError, match="DART_SECRET_KEY environment variable must be set"):
            import dart_planner.security.auth


class TestSecureSerializerSecretKey:
    """Test SecureSerializer secret key handling"""
    
    def test_secure_serializer_requires_secret(self):
        """Test that SecureSerializer requires DART_ZMQ_SECRET"""
        # Remove DART_ZMQ_SECRET from environment
        original_zmq_secret = os.environ.pop("DART_ZMQ_SECRET", None)
        
        try:
            # Import should fail
            with pytest.raises(RuntimeError, match="DART_ZMQ_SECRET environment variable must be set"):
                from dart_planner.communication.secure_serializer import SecureSerializer
                SecureSerializer()
        finally:
            # Restore environment
            if original_zmq_secret:
                os.environ["DART_ZMQ_SECRET"] = original_zmq_secret
    
    def test_secure_serializer_works_with_secret(self):
        """Test that SecureSerializer works when DART_ZMQ_SECRET is set"""
        # Set test secret
        os.environ["DART_ZMQ_SECRET"] = "test_zmq_secret_for_testing"
        
        try:
            from dart_planner.communication.secure_serializer import SecureSerializer
            serializer = SecureSerializer()
            assert serializer.secret_key == "test_zmq_secret_for_testing"
        finally:
            # Clean up
            if "DART_ZMQ_SECRET" in os.environ:
                del os.environ["DART_ZMQ_SECRET"]


if __name__ == "__main__":
    pytest.main([__file__]) 