"""
OS Keyring Integration for DART-Planner

Replaces custom crypto storage with proven OS keyring solutions:
- Windows: Windows Credential Manager
- macOS: macOS Keychain
- Linux: Secret Service API (GNOME Keyring/KDE Wallet)
"""

import os
import platform
import logging
import secrets
import base64
from typing import Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    import win32crypt
    import win32api
    import win32security
    WINDOWS_CRYPTO_AVAILABLE = True
except ImportError:
    WINDOWS_CRYPTO_AVAILABLE = False

from dart_planner.common.errors import SecurityError, ConfigurationError

logger = logging.getLogger(__name__)

# Keyring service name for DART-Planner
DART_KEYRING_SERVICE = "dart_planner"
DART_KEYRING_NAMESPACE = "dart_planner"

# Key types
class KeyType:
    KEK = "kek"  # Key Encryption Key
    DEK = "dek"  # Data Encryption Key
    JWT = "jwt"  # JWT signing key
    HMAC = "hmac"  # HMAC key
    API = "api"  # API key


@dataclass
class KeyMetadata:
    """Metadata for stored keys."""
    key_id: str
    key_type: str
    created_at: str
    expires_at: Optional[str] = None
    rotation_policy: Optional[str] = None
    usage_count: int = 0


class OSKeyringManager:
    """
    Secure key management using OS keyring services.
    
    Provides platform-specific secure storage:
    - Windows: Windows Credential Manager
    - macOS: macOS Keychain
    - Linux: Secret Service API
    """
    
    def __init__(self, service_name: str = DART_KEYRING_SERVICE):
        if not KEYRING_AVAILABLE:
            raise ConfigurationError("keyring package not available. Install with: pip install keyring")
        
        self.service_name = service_name
        self.system = platform.system().lower()
        self._validate_platform_support()
        
        logger.info(f"Initialized OS keyring manager for {self.system}")
    
    def _validate_platform_support(self) -> None:
        """Validate that the platform is supported."""
        supported_platforms = ["windows", "darwin", "linux"]
        if self.system not in supported_platforms:
            raise ConfigurationError(f"Unsupported platform: {self.system}")
        
        # Test keyring backend
        try:
            keyring.get_keyring()
        except Exception as e:
            raise ConfigurationError(f"Keyring backend not available: {e}")
    
    def _generate_key_id(self, key_type: str) -> str:
        """Generate a unique key ID."""
        timestamp = str(int(os.urandom(4).hex(), 16))
        random_suffix = secrets.token_hex(4)
        return f"{key_type}_{timestamp}_{random_suffix}"
    
    def _get_key_name(self, key_id: str, key_type: str) -> str:
        """Get the keyring key name."""
        return f"{DART_KEYRING_NAMESPACE}:{key_type}:{key_id}"
    
    def store_key(self, key_data: bytes, key_type: str, 
                  expires_at: Optional[str] = None,
                  rotation_policy: Optional[str] = None) -> str:
        """
        Store a key securely in the OS keyring.
        
        Args:
            key_data: The key data to store
            key_type: Type of key (KEK, DEK, JWT, etc.)
            expires_at: Optional expiration timestamp
            rotation_policy: Optional rotation policy
            
        Returns:
            Key ID for the stored key
        """
        try:
            # Generate unique key ID
            key_id = self._generate_key_id(key_type)
            key_name = self._get_key_name(key_id, key_type)
            
            # Encode key data
            encoded_key = base64.b64encode(key_data).decode('utf-8')
            
            # Create metadata
            metadata = KeyMetadata(
                key_id=key_id,
                key_type=key_type,
                created_at=str(int(os.urandom(4).hex(), 16)),
                expires_at=expires_at,
                rotation_policy=rotation_policy
            )
            
            # Store key data
            keyring.set_password(self.service_name, key_name, encoded_key)
            
            # Store metadata
            metadata_name = f"{key_name}:metadata"
            import json
            keyring.set_password(self.service_name, metadata_name, json.dumps(metadata.__dict__))
            
            logger.info(f"Stored {key_type} key {key_id} in OS keyring")
            return key_id
            
        except Exception as e:
            raise SecurityError(f"Failed to store key in OS keyring: {e}")
    
    def retrieve_key(self, key_id: str, key_type: str) -> Optional[bytes]:
        """
        Retrieve a key from the OS keyring.
        
        Args:
            key_id: The key ID
            key_type: Type of key
            
        Returns:
            Key data or None if not found
        """
        try:
            key_name = self._get_key_name(key_id, key_type)
            
            # Retrieve key data
            encoded_key = keyring.get_password(self.service_name, key_name)
            if not encoded_key:
                return None
            
            # Decode key data
            key_data = base64.b64decode(encoded_key.encode('utf-8'))
            
            # Update usage count
            self._update_key_usage(key_id, key_type)
            
            logger.debug(f"Retrieved {key_type} key {key_id} from OS keyring")
            return key_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve key {key_id}: {e}")
            return None
    
    def _update_key_usage(self, key_id: str, key_type: str) -> None:
        """Update key usage count."""
        try:
            key_name = self._get_key_name(key_id, key_type)
            metadata_name = f"{key_name}:metadata"
            
            metadata_json = keyring.get_password(self.service_name, metadata_name)
            if metadata_json:
                import json
                metadata = json.loads(metadata_json)
                metadata['usage_count'] = metadata.get('usage_count', 0) + 1
                keyring.set_password(self.service_name, metadata_name, json.dumps(metadata))
        except Exception as e:
            logger.warning(f"Failed to update key usage count: {e}")
    
    def delete_key(self, key_id: str, key_type: str) -> bool:
        """
        Delete a key from the OS keyring.
        
        Args:
            key_id: The key ID
            key_type: Type of key
            
        Returns:
            True if deleted successfully
        """
        try:
            key_name = self._get_key_name(key_id, key_type)
            
            # Delete key data
            keyring.delete_password(self.service_name, key_name)
            
            # Delete metadata
            metadata_name = f"{key_name}:metadata"
            keyring.delete_password(self.service_name, metadata_name)
            
            logger.info(f"Deleted {key_type} key {key_id} from OS keyring")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete key {key_id}: {e}")
            return False
    
    def list_keys(self, key_type: Optional[str] = None) -> Dict[str, KeyMetadata]:
        """
        List all stored keys.
        
        Args:
            key_type: Optional filter by key type
            
        Returns:
            Dictionary of key IDs to metadata
        """
        try:
            # Note: keyring doesn't provide a list method, so we need to track keys separately
            # For now, return empty dict - in production, maintain a key registry
            logger.warning("Key listing not implemented - maintain separate key registry")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return {}
    
    def rotate_key(self, key_id: str, key_type: str, new_key_data: bytes) -> str:
        """
        Rotate a key by creating a new version.
        
        Args:
            key_id: The key ID to rotate
            key_type: Type of key
            new_key_data: New key data
            
        Returns:
            New key ID
        """
        try:
            # Store new key
            new_key_id = self.store_key(new_key_data, key_type)
            
            # Mark old key for deletion (implement grace period)
            logger.info(f"Rotated {key_type} key {key_id} -> {new_key_id}")
            
            return new_key_id
            
        except Exception as e:
            raise SecurityError(f"Failed to rotate key: {e}")
    
    def validate_key_access(self) -> bool:
        """
        Validate that the keyring is accessible and working.
        
        Returns:
            True if keyring is accessible
        """
        try:
            # Test with a temporary key
            test_key = os.urandom(32)
            test_id = self.store_key(test_key, "test")
            retrieved_key = self.retrieve_key(test_id, "test")
            self.delete_key(test_id, "test")
            
            return retrieved_key == test_key
            
        except Exception as e:
            logger.error(f"Keyring validation failed: {e}")
            return False


class WindowsCredentialManager:
    """Windows-specific credential management using DPAPI."""
    
    def __init__(self):
        if not WINDOWS_CRYPTO_AVAILABLE:
            raise ConfigurationError("Windows crypto not available. Install pywin32")
    
    def protect_data(self, data: bytes, description: str) -> bytes:
        """Protect data using Windows DPAPI."""
        try:
            return win32crypt.CryptProtectData(
                data,
                description,
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0  # Flags
            )
        except Exception as e:
            raise SecurityError(f"Failed to protect data with DPAPI: {e}")
    
    def unprotect_data(self, protected_data: bytes) -> bytes:
        """Unprotect data using Windows DPAPI."""
        try:
            return win32crypt.CryptUnprotectData(
                protected_data,
                None,  # Description
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                0  # Flags
            )[0]  # Return only the data, not the description
        except Exception as e:
            raise SecurityError(f"Failed to unprotect data with DPAPI: {e}")


# Global keyring manager instance
_keyring_manager: Optional[OSKeyringManager] = None

def get_keyring_manager() -> OSKeyringManager:
    """Get the global keyring manager instance."""
    global _keyring_manager
    if _keyring_manager is None:
        _keyring_manager = OSKeyringManager()
    return _keyring_manager

def set_keyring_manager(manager: Optional[OSKeyringManager]) -> None:
    """Set the global keyring manager instance."""
    global _keyring_manager
    _keyring_manager = manager 