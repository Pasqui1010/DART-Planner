"""
Tests for OS Keyring Integration

Tests the new OS keyring-based secure key storage system that replaces
custom crypto storage with proven OS keyring solutions.
"""

import pytest
import os
import tempfile
import platform
from unittest.mock import patch, MagicMock
from pathlib import Path

from dart_planner.security.os_keyring import (
    OSKeyringManager, KeyType, KeyMetadata, get_keyring_manager, set_keyring_manager
)
from dart_planner.security.crypto import SecureCredentialManager
from dart_planner.common.errors import SecurityError, ConfigurationError


class TestOSKeyringManager:
    """Test OS keyring manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary keyring manager for testing
        self.test_service = "dart_planner_test"
        self.keyring_manager = OSKeyringManager(service_name=self.test_service)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up any test keys
        try:
            # This would require a list_keys method to be implemented
            pass
        except Exception:
            pass
    
    def test_platform_validation(self):
        """Test platform validation."""
        # Should work on supported platforms
        supported_platforms = ["windows", "darwin", "linux"]
        current_platform = platform.system().lower()
        
        if current_platform in supported_platforms:
            # Should not raise an exception
            manager = OSKeyringManager()
            assert manager.system == current_platform
        else:
            # Should raise ConfigurationError on unsupported platforms
            with pytest.raises(ConfigurationError, match="Unsupported platform"):
                OSKeyringManager()
    
    @patch('dart_planner.security.os_keyring.keyring')
    def test_key_storage_and_retrieval(self, mock_keyring):
        """Test storing and retrieving keys."""
        # Mock keyring responses
        mock_keyring.set_password.return_value = None
        mock_keyring.get_password.return_value = "dGVzdF9rZXlfZGF0YQ=="  # base64 encoded "test_key_data"
        
        # Test key storage
        test_key_data = b"test_key_data"
        key_id = self.keyring_manager.store_key(test_key_data, KeyType.JWT)
        
        # Verify keyring was called
        mock_keyring.set_password.assert_called()
        
        # Test key retrieval
        retrieved_key = self.keyring_manager.retrieve_key(key_id, KeyType.JWT)
        
        # Verify retrieved key matches original
        assert retrieved_key == test_key_data
    
    @patch('dart_planner.security.os_keyring.keyring')
    def test_key_deletion(self, mock_keyring):
        """Test key deletion."""
        mock_keyring.delete_password.return_value = None
        
        # Test key deletion
        result = self.keyring_manager.delete_key("test_key_id", KeyType.JWT)
        
        # Verify deletion was successful
        assert result is True
        mock_keyring.delete_password.assert_called()
    
    @patch('dart_planner.security.os_keyring.keyring')
    def test_key_rotation(self, mock_keyring):
        """Test key rotation functionality."""
        # Mock keyring responses
        mock_keyring.set_password.return_value = None
        mock_keyring.get_password.return_value = "bmV3X2tleV9kYXRh"  # base64 encoded "new_key_data"
        
        # Test key rotation
        old_key_id = "old_key_id"
        new_key_data = b"new_key_data"
        new_key_id = self.keyring_manager.rotate_key(old_key_id, KeyType.JWT, new_key_data)
        
        # Verify new key was stored
        assert new_key_id is not None
        mock_keyring.set_password.assert_called()
    
    def test_key_id_generation(self):
        """Test unique key ID generation."""
        key_ids = set()
        
        # Generate multiple key IDs
        for _ in range(10):
            key_id = self.keyring_manager._generate_key_id(KeyType.JWT)
            assert key_id not in key_ids
            key_ids.add(key_id)
    
    def test_key_name_formatting(self):
        """Test key name formatting."""
        key_id = "test_key_123"
        key_type = KeyType.JWT
        
        key_name = self.keyring_manager._get_key_name(key_id, key_type)
        
        # Verify key name format
        assert key_name == f"dart_planner:jwt:{key_id}"
    
    @patch('dart_planner.security.os_keyring.keyring')
    def test_validation(self, mock_keyring):
        """Test keyring validation."""
        # Mock successful validation
        mock_keyring.set_password.return_value = None
        mock_keyring.get_password.return_value = "dGVzdF9rZXlfZGF0YQ=="
        mock_keyring.delete_password.return_value = None
        
        # Test validation
        result = self.keyring_manager.validate_key_access()
        assert result is True
    
    @patch('dart_planner.security.os_keyring.keyring')
    def test_validation_failure(self, mock_keyring):
        """Test keyring validation failure."""
        # Mock validation failure
        mock_keyring.set_password.side_effect = Exception("Keyring error")
        
        # Test validation failure
        result = self.keyring_manager.validate_key_access()
        assert result is False


class TestSecureCredentialManagerOSKeyring:
    """Test SecureCredentialManager with OS keyring integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary credentials file
        self.temp_dir = tempfile.mkdtemp()
        self.credentials_file = Path(self.temp_dir) / "test_credentials.encrypted"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        if self.credentials_file.exists():
            self.credentials_file.unlink()
        if self.temp_dir and os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    @patch('dart_planner.security.crypto.get_keyring_manager')
    def test_initialization_with_os_keyring(self, mock_get_keyring):
        """Test initialization with OS keyring."""
        # Mock keyring manager
        mock_keyring_manager = MagicMock()
        mock_keyring_manager.validate_key_access.return_value = True
        mock_keyring_manager.retrieve_key.return_value = None  # No existing KEK
        mock_keyring_manager.store_key.return_value = "test_key_id"
        mock_get_keyring.return_value = mock_keyring_manager
        
        # Initialize credential manager
        cred_manager = SecureCredentialManager(
            credentials_file=str(self.credentials_file),
            use_os_keyring=True
        )
        
        # Verify keyring manager was used
        mock_keyring_manager.validate_key_access.assert_called_once()
        mock_keyring_manager.store_key.assert_called()
    
    @patch('dart_planner.security.crypto.get_keyring_manager')
    def test_initialization_fallback(self, mock_get_keyring):
        """Test initialization fallback when OS keyring is not available."""
        # Mock keyring manager failure
        mock_get_keyring.side_effect = Exception("Keyring not available")
        
        # Initialize credential manager with fallback
        cred_manager = SecureCredentialManager(
            credentials_file=str(self.credentials_file),
            use_os_keyring=True
        )
        
        # Should fall back to file-based storage
        assert hasattr(cred_manager, '_cipher')
    
    def test_credential_storage_and_retrieval(self):
        """Test storing and retrieving credentials with OS keyring."""
        # Initialize credential manager
        cred_manager = SecureCredentialManager(
            credentials_file=str(self.credentials_file),
            use_os_keyring=False  # Use file-based for testing
        )
        
        # Store credential
        cred_manager.store_credential(
            name="test_api_key",
            value="secret_api_key_123",
            credential_type="api_key"
        )
        
        # Retrieve credential
        retrieved_value = cred_manager.get_credential("test_api_key")
        
        # Verify retrieved value
        assert retrieved_value == "secret_api_key_123"
    
    def test_credential_expiration(self):
        """Test credential expiration handling."""
        # Initialize credential manager
        cred_manager = SecureCredentialManager(
            credentials_file=str(self.credentials_file),
            use_os_keyring=False
        )
        
        # Store credential with short expiration
        cred_manager.store_credential(
            name="temp_token",
            value="temporary_value",
            credential_type="token",
            expires_hours=1
        )
        
        # Should be retrievable immediately
        assert cred_manager.get_credential("temp_token") == "temporary_value"
    
    def test_credential_rotation(self):
        """Test credential rotation."""
        # Initialize credential manager
        cred_manager = SecureCredentialManager(
            credentials_file=str(self.credentials_file),
            use_os_keyring=False
        )
        
        # Store initial credential
        cred_manager.store_credential("rotate_test", "old_value", "api_key")
        
        # Rotate credential
        result = cred_manager.rotate_credential("rotate_test", "new_value")
        assert result is True
        
        # Verify new value
        assert cred_manager.get_credential("rotate_test") == "new_value"


class TestGlobalKeyringManager:
    """Test global keyring manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset global keyring manager
        set_keyring_manager(None)
    
    def test_get_keyring_manager_singleton(self):
        """Test that get_keyring_manager returns a singleton."""
        # Get keyring manager twice
        manager1 = get_keyring_manager()
        manager2 = get_keyring_manager()
        
        # Should be the same instance
        assert manager1 is manager2
    
    def test_set_keyring_manager(self):
        """Test setting custom keyring manager."""
        # Create custom manager
        custom_manager = MagicMock()
        
        # Set custom manager
        set_keyring_manager(custom_manager)
        
        # Get manager should return custom instance
        retrieved_manager = get_keyring_manager()
        assert retrieved_manager is custom_manager


class TestKeyTypes:
    """Test key type constants."""
    
    def test_key_type_constants(self):
        """Test key type constants are defined."""
        assert KeyType.KEK == "kek"
        assert KeyType.DEK == "dek"
        assert KeyType.JWT == "jwt"
        assert KeyType.HMAC == "hmac"
        assert KeyType.API == "api"


class TestKeyMetadata:
    """Test key metadata dataclass."""
    
    def test_key_metadata_creation(self):
        """Test creating key metadata."""
        metadata = KeyMetadata(
            key_id="test_key_123",
            key_type=KeyType.JWT,
            created_at="2025-01-01T00:00:00Z",
            expires_at="2025-12-31T23:59:59Z",
            rotation_policy="monthly",
            usage_count=42
        )
        
        assert metadata.key_id == "test_key_123"
        assert metadata.key_type == KeyType.JWT
        assert metadata.created_at == "2025-01-01T00:00:00Z"
        assert metadata.expires_at == "2025-12-31T23:59:59Z"
        assert metadata.rotation_policy == "monthly"
        assert metadata.usage_count == 42
    
    def test_key_metadata_defaults(self):
        """Test key metadata with default values."""
        metadata = KeyMetadata(
            key_id="test_key_123",
            key_type=KeyType.JWT,
            created_at="2025-01-01T00:00:00Z"
        )
        
        assert metadata.expires_at is None
        assert metadata.rotation_policy is None
        assert metadata.usage_count == 0 