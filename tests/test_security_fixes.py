"""
Tests for Security Fixes Implementation

Tests the critical security improvements:
1. Environment variable secret key handling
2. Activated input validation in middleware
3. Socket.IO token-based authentication
4. Dependency resolution
"""

import os
import pytest
import json
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse

# Test environment variable secret key handling
class TestSecretKeyEnvironment:
    """Test secure secret key loading from environment variables"""
    
    def test_secret_key_loaded_from_environment(self):
        """Test that secret key is properly loaded from environment variable"""
        test_key = "test_secure_secret_key_123"
        
        with patch.dict(os.environ, {"DART_SECRET_KEY": test_key}):
            # Import after setting environment variable
            import importlib
            import sys
            
            # Clear any cached modules
            modules_to_reload = [
                'src.gateway.middleware',
                'gateway.middleware'
            ]
            for module in modules_to_reload:
                if module in sys.modules:
                    del sys.modules[module]
            
            # Now import should use the environment variable
            try:
                from src.gateway.middleware import SECRET_KEY, auth_manager
                assert SECRET_KEY == test_key
                # Verify auth manager was initialized with the correct key
                assert auth_manager.secret_key == test_key
            except ImportError:
                # Fallback for different import paths
                from gateway.middleware import SECRET_KEY, auth_manager
                assert SECRET_KEY == test_key
                assert auth_manager.secret_key == test_key
    
    def test_missing_secret_key_raises_error(self):
        """Test that missing secret key raises appropriate error"""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure DART_SECRET_KEY is not set
            if "DART_SECRET_KEY" in os.environ:
                del os.environ["DART_SECRET_KEY"]
            
            # Clear cached modules
            import sys
            modules_to_reload = [
                'src.gateway.middleware',
                'gateway.middleware'
            ]
            for module in modules_to_reload:
                if module in sys.modules:
                    del sys.modules[module]
            
            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                try:
                    from src.gateway.middleware import SECRET_KEY
                except ImportError:
                    from gateway.middleware import SECRET_KEY
            
            assert "DART_SECRET_KEY environment variable not set" in str(exc_info.value)


class TestInputValidationActivation:
    """Test that generic input validation is properly activated"""
    
    @pytest.fixture
    def mock_validator(self):
        """Mock input validator for testing"""
        validator = MagicMock()
        validator.validate_generic.return_value = {"validated": True}
        return validator
    
    @patch('src.gateway.middleware.input_validator')
    def test_input_validation_called_on_post(self, mock_input_validator):
        """Test that input validation is called for POST requests"""
        from src.gateway.middleware import SecureMiddleware
        
        # Mock the validator
        mock_input_validator.validate_generic.return_value = {"test": "data"}
        
        # Create a simple app for testing
        app = Starlette()
        
        @app.route('/test', methods=['POST'])
        async def test_endpoint(request):
            return JSONResponse({"status": "ok"})
        
        # Add middleware
        app.add_middleware(SecureMiddleware)
        
        # Mock auth manager to pass authentication
        with patch('src.gateway.middleware.auth_manager') as mock_auth:
            mock_session = MagicMock()
            mock_auth.validate_token.return_value = mock_session
            
            client = TestClient(app)
            
            # Make POST request with JSON data
            response = client.post(
                '/test',
                json={"test": "data"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Verify validation was called
            mock_input_validator.validate_generic.assert_called_once_with({"test": "data"})
    
    def test_validation_error_handling(self):
        """Test that validation errors are properly handled and returned"""
        from src.gateway.middleware import SecureMiddleware
        from src.security.validation import ValidationError
        
        app = Starlette()
        
        @app.route('/test', methods=['POST'])
        async def test_endpoint(request):
            return JSONResponse({"status": "ok"})
        
        app.add_middleware(SecureMiddleware)
        
        # Mock validation to raise ValidationError
        with patch('src.gateway.middleware.input_validator') as mock_validator, \
             patch('src.gateway.middleware.auth_manager') as mock_auth:
            
            mock_validator.validate_generic.side_effect = ValidationError("Test validation error", "test_field")
            mock_session = MagicMock()
            mock_auth.validate_token.return_value = mock_session
            
            client = TestClient(app)
            
            response = client.post(
                '/test',
                json={"invalid": "data"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Should return 422 with validation error
            assert response.status_code == 422
            assert "Validation Error" in response.json()["detail"]


class TestSocketIOAuthentication:
    """Test Socket.IO token-based authentication"""
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock auth manager for testing"""
        auth_manager = MagicMock()
        mock_session = MagicMock()
        mock_session.username = "test_user"
        auth_manager.validate_token.return_value = mock_session
        return auth_manager, mock_session
    
    @pytest.mark.asyncio
    async def test_socketio_connect_with_valid_token(self, mock_auth_manager):
        """Test Socket.IO connection with valid authentication token"""
        auth_manager, mock_session = mock_auth_manager
        
        # Mock environment with token
        environ = {
            'QUERY_STRING': 'token=valid_test_token'
        }
        
        # Mock Socket.IO server
        mock_sio = MagicMock()
        mock_sio.save_session = MagicMock()
        mock_sio.emit = MagicMock()
        
        # Import and patch the handler
        with patch('demos.web_demo.app.auth_manager', auth_manager), \
             patch('demos.web_demo.app.sio', mock_sio), \
             patch('demos.web_demo.app.demo_runner') as mock_demo:
            
            mock_demo.get_status_data.return_value = {"status": "test"}
            
            # Import the handler function
            from demos.web_demo.app import handle_connect
            
            # Call the handler
            result = await handle_connect("test_sid", environ)
            
            # Verify authentication was called
            auth_manager.validate_token.assert_called_once_with("valid_test_token")
            
            # Verify session was saved
            mock_sio.save_session.assert_called_once_with("test_sid", {'user_session': mock_session})
            
            # Verify telemetry was sent
            mock_sio.emit.assert_called_once()
            
            # Should return True for successful connection
            assert result is True
    
    @pytest.mark.asyncio
    async def test_socketio_connect_with_invalid_token(self, mock_auth_manager):
        """Test Socket.IO connection rejection with invalid token"""
        auth_manager, _ = mock_auth_manager
        auth_manager.validate_token.return_value = None  # Invalid token
        
        environ = {
            'QUERY_STRING': 'token=invalid_token'
        }
        
        mock_sio = MagicMock()
        mock_sio.disconnect = MagicMock()
        
        with patch('demos.web_demo.app.auth_manager', auth_manager), \
             patch('demos.web_demo.app.sio', mock_sio):
            
            from demos.web_demo.app import handle_connect
            
            result = await handle_connect("test_sid", environ)
            
            # Should disconnect and return False
            mock_sio.disconnect.assert_called_once_with("test_sid")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_socketio_connect_without_token(self):
        """Test Socket.IO connection rejection when no token provided"""
        environ = {
            'QUERY_STRING': ''  # No token
        }
        
        mock_sio = MagicMock()
        mock_sio.disconnect = MagicMock()
        
        with patch('demos.web_demo.app.sio', mock_sio):
            from demos.web_demo.app import handle_connect
            
            result = await handle_connect("test_sid", environ)
            
            # Should disconnect and return False
            mock_sio.disconnect.assert_called_once_with("test_sid")
            assert result is False


class TestDependencyResolution:
    """Test that required dependencies are properly specified"""
    
    def test_python_socketio_in_requirements(self):
        """Test that python-socketio is added to requirements"""
        with open('requirements/base.txt', 'r') as f:
            requirements = f.read()
        
        assert 'python-socketio>=5.8.0' in requirements
        
    def test_requirements_format(self):
        """Test that requirements file is properly formatted"""
        with open('requirements/base.txt', 'r') as f:
            lines = f.readlines()
        
        # Find the python-socketio line
        socketio_lines = [line for line in lines if 'python-socketio' in line]
        assert len(socketio_lines) == 1
        
        # Verify version constraint
        socketio_line = socketio_lines[0].strip()
        assert '>=' in socketio_line
        assert '5.8.0' in socketio_line


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 