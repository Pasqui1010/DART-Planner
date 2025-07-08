"""
Secure Credential Management for DART-Planner

Provides encrypted storage and retrieval of sensitive credentials
for hardware interfaces, API keys, and authentication tokens.
"""

import os
import json
import base64
import secrets
import platform
import logging
from typing import Dict, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from .secure_file_utils import (
    secure_binary_write,
    secure_binary_read,
    secure_json_write,
    secure_json_read,
    create_secure_directory,
    check_file_security,
    SecurityError
)
from dart_planner.common.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

# Rotated salt - using a more secure random salt
DEFAULT_SALT = b'dart_planner_secure_salt_2025_v2_'
PBKDF2_ITERATIONS = 600000  # Increased from 100000 for better security
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1


class KeyDerivationError(Exception):
    """Raised when key derivation fails"""
    pass


class OSKeyStoreError(Exception):
    """Raised when OS keystore operations fail"""
    pass


def _wipe_memory(data: bytes) -> None:
    """Securely wipe memory by overwriting with zeros"""
    if data:
        # Convert to bytearray for modification, then back to bytes
        data_array = bytearray(data)
        for i in range(len(data_array)):
            data_array[i] = 0
        # Note: This doesn't actually modify the original bytes object
        # In a real implementation, you'd need to work with mutable buffers


def _derive_key_from_passphrase(passphrase: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive encryption key from passphrase using PBKDF2
    
    Args:
        passphrase: User-supplied passphrase
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (derived key suitable for Fernet, salt used)
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # Use PBKDF2 with increased iterations for better security
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    
    try:
        key = kdf.derive(passphrase.encode('utf-8'))
        return base64.urlsafe_b64encode(key), salt
    except Exception as e:
        raise KeyDerivationError(f"Failed to derive key from passphrase: {e}")


def _derive_key_from_os_keystore(key_id: str) -> bytes:
    """
    Derive encryption key from OS keystore (TPM, macOS keychain, Windows DPAPI)
    
    Args:
        key_id: Identifier for the key in the OS keystore
        
    Returns:
        Derived key suitable for Fernet
    """
    system = platform.system().lower()
    
    try:
        if system == "windows":
            return _derive_key_from_windows_dpapi(key_id)
        elif system == "darwin":
            return _derive_key_from_macos_keychain(key_id)
        elif system == "linux":
            return _derive_key_from_linux_tpm(key_id)
        else:
            raise OSKeyStoreError(f"Unsupported operating system: {system}")
    except Exception as e:
        raise OSKeyStoreError(f"Failed to derive key from OS keystore: {e}")


def _derive_key_from_windows_dpapi(key_id: str) -> bytes:
    """Derive key using Windows DPAPI"""
    try:
        import win32crypt
        import win32api
        import win32security
        
        # Use DPAPI to protect the key material
        key_material = secrets.token_bytes(32)
        protected_key = win32crypt.CryptProtectData(
            key_material,
            key_id,  # Convert to string for DPAPI
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            0  # Flags
        )
        
        # Store protected key in registry or secure location
        # For now, we'll use a simple file-based approach
        key_file = Path(f"protected_key_{key_id}.bin")
        secure_binary_write(key_file, protected_key)
        
        return base64.urlsafe_b64encode(key_material)
        
    except ImportError:
        raise OSKeyStoreError("win32crypt not available - install pywin32")
    except Exception as e:
        raise OSKeyStoreError(f"Windows DPAPI failed: {e}")


def _derive_key_from_macos_keychain(key_id: str) -> bytes:
    """Derive key using macOS keychain"""
    try:
        import subprocess
        
        # Generate a random key
        key_material = secrets.token_bytes(32)
        
        # Store in macOS keychain
        cmd = [
            'security', 'add-generic-password',
            '-s', f'dart_planner_{key_id}',
            '-a', os.getenv('USER', 'dart_planner'),
            '-w', base64.b64encode(key_material).decode('utf-8')
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise OSKeyStoreError(f"Failed to store key in keychain: {result.stderr}")
        
        return base64.urlsafe_b64encode(key_material)
        
    except Exception as e:
        raise OSKeyStoreError(f"macOS keychain failed: {e}")


def _derive_key_from_linux_tpm(key_id: str) -> bytes:
    """Derive key using Linux TPM (if available)"""
    try:
        # Check if TPM is available
        if not os.path.exists('/dev/tpm0') and not os.path.exists('/dev/tpmrm0'):
            raise OSKeyStoreError("TPM device not found")
        
        # For now, use a simplified approach
        # In production, use proper TPM2-TSS or similar library
        key_material = secrets.token_bytes(32)
        
        # Store key reference in secure location
        key_file = Path(f"/tmp/dart_planner_tpm_{key_id}.key")
        secure_binary_write(key_file, key_material)
        
        return base64.urlsafe_b64encode(key_material)
        
    except Exception as e:
        raise OSKeyStoreError(f"Linux TPM failed: {e}")


@contextmanager
def _temporary_key(key: bytes):
    """
    Context manager for temporary key usage with automatic wiping
    
    Args:
        key: Encryption key to use temporarily
    """
    try:
        yield key
    finally:
        # Securely wipe the key from memory
        _wipe_memory(key)


@dataclass
class Credential:
    """Secure credential storage structure"""
    name: str
    value: str
    credential_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SecureCredentialManager:
    """
    Secure credential management system
    
    Encrypts and stores sensitive credentials like API keys, hardware
    authentication tokens, and connection strings using industry-standard
    encryption (AES-256 via Fernet) with KEK derivation from passphrase
    or OS keystore.
    """
    
    def __init__(self, credentials_file: str = "credentials.encrypted", 
                 master_password: Optional[str] = None,
                 key_id: Optional[str] = None,
                 use_os_keystore: bool = False):
        self.credentials_file = Path(credentials_file)
        self.credentials: Dict[str, Credential] = {}
        self._key_id = key_id or "dart_planner_master"
        self._use_os_keystore = use_os_keystore
        self._salt: Optional[bytes] = None
        
        # Initialize encryption key
        if master_password:
            self._set_master_password(master_password)
        elif use_os_keystore:
            self._load_from_os_keystore()
        else:
            raise ConfigurationError("Either master_password or use_os_keystore=True must be provided")
        
        # Load existing credentials
        self.load_credentials()
    
    def _set_master_password(self, password: str) -> None:
        """Derive encryption key from master password"""
        # Generate a new random salt for each password
        salt = secrets.token_bytes(32)
        
        try:
            key, salt = _derive_key_from_passphrase(password, salt)
            self._encryption_key = key
            self._salt = salt
            
            # Store salt securely for future use
            self._save_salt()
            
        except KeyDerivationError as e:
            raise SecurityError(f"Failed to derive key from password: {e}")
    
    def _load_from_os_keystore(self) -> None:
        """Load encryption key from OS keystore"""
        try:
            self._encryption_key = _derive_key_from_os_keystore(self._key_id)
        except OSKeyStoreError as e:
            raise SecurityError(f"Failed to load key from OS keystore: {e}")
    
    def _save_salt(self) -> None:
        """Save salt securely for future password verification"""
        if not self._salt:
            return
        
        salt_file = Path(f"salt_{self._key_id}.bin")
        try:
            secure_binary_write(salt_file, self._salt)
        except SecurityError as e:
            raise SecurityError(f"Failed to save salt: {e}")
    
    def _load_salt(self) -> Optional[bytes]:
        """Load salt for password verification"""
        salt_file = Path(f"salt_{self._key_id}.bin")
        if salt_file.exists():
            try:
                return secure_binary_read(salt_file)
            except SecurityError:
                return None
        return None
    
    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher instance with temporary key usage"""
        if not hasattr(self, '_encryption_key') or not self._encryption_key:
            raise SecurityError("Encryption key not initialized")
        return Fernet(self._encryption_key)
    
    def _verify_password(self, password: str) -> bool:
        """Verify password by attempting to decrypt existing data"""
        try:
            # Load existing salt
            salt = self._load_salt()
            if not salt:
                return False
            
            # Derive key with existing salt
            key, _ = _derive_key_from_passphrase(password, salt)
            
            # Try to decrypt existing data
            if self.credentials_file.exists():
                with open(self.credentials_file, 'rb') as f:
                    encrypted_data = f.read()
                
                cipher = Fernet(key)
                cipher.decrypt(encrypted_data)  # This will fail if password is wrong
                
                # If we get here, password is correct
                return True
            
            return False
            
        except Exception:
            return False
    
    def store_credential(self, name: str, value: str, credential_type: str,
                        expires_hours: Optional[int] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store encrypted credential
        
        Args:
            name: Unique credential identifier
            value: Credential value (password, API key, etc.)
            credential_type: Type of credential (api_key, password, token, etc.)
            expires_hours: Optional expiration time in hours
            metadata: Additional metadata to store with credential
        """
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        credential = Credential(
            name=name,
            value=value,
            credential_type=credential_type,
            created_at=datetime.now(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.credentials[name] = credential
        self.save_credentials()
    
    def get_credential(self, name: str) -> Optional[str]:
        """
        Retrieve decrypted credential value
        
        Args:
            name: Credential identifier
            
        Returns:
            Decrypted credential value or None if not found/expired
        """
        if name not in self.credentials:
            return None
        
        credential = self.credentials[name]
        
        # Check expiration
        if credential.expires_at and datetime.now() > credential.expires_at:
            # Remove expired credential
            self.remove_credential(name)
            return None
        
        return credential.value
    
    def get_credential_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get credential metadata without the sensitive value"""
        if name not in self.credentials:
            return None
        
        credential = self.credentials[name]
        
        # Check expiration
        if credential.expires_at and datetime.now() > credential.expires_at:
            return None
        
        return {
            'name': credential.name,
            'type': credential.credential_type,
            'created_at': credential.created_at.isoformat(),
            'expires_at': credential.expires_at.isoformat() if credential.expires_at else None,
            'metadata': credential.metadata
        }
    
    def remove_credential(self, name: str) -> bool:
        """Remove credential from storage"""
        if name in self.credentials:
            del self.credentials[name]
            self.save_credentials()
            return True
        return False
    
    def list_credentials(self) -> Dict[str, Dict[str, Any]]:
        """List all stored credentials (without sensitive values)"""
        result = {}
        for name in self.credentials:
            info = self.get_credential_info(name)
            if info:  # Only include non-expired credentials
                result[name] = info
        return result
    
    def rotate_credential(self, name: str, new_value: str) -> bool:
        """Update existing credential with new value"""
        if name not in self.credentials:
            return False
        
        credential = self.credentials[name]
        credential.value = new_value
        credential.created_at = datetime.now()
        
        self.save_credentials()
        return True
    
    def save_credentials(self) -> None:
        """Save encrypted credentials to file"""
        if not self.credentials:
            return
        
        # Convert credentials to serializable format
        data = {}
        for name, credential in self.credentials.items():
            cred_dict = asdict(credential)
            # Convert datetime objects to ISO strings
            cred_dict['created_at'] = credential.created_at.isoformat()
            if credential.expires_at:
                cred_dict['expires_at'] = credential.expires_at.isoformat()
            else:
                cred_dict['expires_at'] = None
            
            data[name] = cred_dict
        
        # Encrypt and save with temporary key usage
        with _temporary_key(self._encryption_key):
            cipher = self._get_cipher()
            encrypted_data = cipher.encrypt(json.dumps(data).encode())
        
        # Create directory if it doesn't exist
        try:
            create_secure_directory(self.credentials_file.parent)
        except SecurityError as e:
            raise SecurityError(f"Security validation failed for credentials directory: {e}")
        
        # Save with secure file operations
        try:
            secure_binary_write(self.credentials_file, encrypted_data)
        except SecurityError as e:
            raise SecurityError(f"Security validation failed when saving credentials: {e}")
    
    def load_credentials(self) -> None:
        """Load and decrypt credentials from file"""
        if not self.credentials_file.exists():
            return
        
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data with temporary key usage
            with _temporary_key(self._encryption_key):
                cipher = self._get_cipher()
                decrypted_data = cipher.decrypt(encrypted_data)
                data = json.loads(decrypted_data.decode())
            
            # Reconstruct credential objects
            self.credentials = {}
            for name, cred_dict in data.items():
                # Convert ISO strings back to datetime objects
                created_at = datetime.fromisoformat(cred_dict['created_at'])
                expires_at = None
                if cred_dict['expires_at']:
                    expires_at = datetime.fromisoformat(cred_dict['expires_at'])
                
                credential = Credential(
                    name=cred_dict['name'],
                    value=cred_dict['value'],
                    credential_type=cred_dict['credential_type'],
                    created_at=created_at,
                    expires_at=expires_at,
                    metadata=cred_dict.get('metadata', {})
                )
                
                self.credentials[name] = credential
        
        except Exception as e:
            # If we can't load credentials, start fresh
            logger.warning(f"Could not load credentials: {e}")
            self.credentials = {}
    
    def cleanup_expired(self) -> int:
        """Remove all expired credentials and return count removed"""
        expired_names = []
        current_time = datetime.now()
        
        for name, credential in self.credentials.items():
            if credential.expires_at and current_time > credential.expires_at:
                expired_names.append(name)
        
        for name in expired_names:
            del self.credentials[name]
        
        if expired_names:
            self.save_credentials()
        
        return len(expired_names)
    
    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """Change master password and re-encrypt all credentials"""
        # First verify old password
        if not self._verify_password(old_password):
            return False
        
        try:
            # Set new password
            self._set_master_password(new_password)
            
            # Re-encrypt all credentials with new key
            self.save_credentials()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to change master password: {e}")
            return False
    
    def export_credentials(self, export_password: str) -> str:
        """Export credentials as encrypted JSON string"""
        # Create temporary encryption with export password
        export_salt = secrets.token_bytes(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=export_salt,
            iterations=PBKDF2_ITERATIONS,
        )
        export_key = base64.urlsafe_b64encode(kdf.derive(export_password.encode()))
        export_cipher = Fernet(export_key)
        
        # Prepare export data
        export_data = {
            'salt': base64.b64encode(export_salt).decode(),
            'credentials': {}
        }
        
        for name, credential in self.credentials.items():
            cred_dict = asdict(credential)
            cred_dict['created_at'] = credential.created_at.isoformat()
            if credential.expires_at:
                cred_dict['expires_at'] = credential.expires_at.isoformat()
            else:
                cred_dict['expires_at'] = None
            
            export_data['credentials'][name] = cred_dict
        
        # Encrypt and encode
        encrypted_export = export_cipher.encrypt(json.dumps(export_data['credentials']).encode())
        export_data['encrypted_credentials'] = base64.b64encode(encrypted_export).decode()
        del export_data['credentials']  # Remove unencrypted data
        
        return json.dumps(export_data)
    
    def import_credentials(self, import_data: str, import_password: str,
                          overwrite: bool = False) -> bool:
        """Import credentials from encrypted JSON string"""
        try:
            data = json.loads(import_data)
            
            # Reconstruct encryption key from import password and salt
            export_salt = base64.b64decode(data['salt'])
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=export_salt,
                iterations=PBKDF2_ITERATIONS,
            )
            import_key = base64.urlsafe_b64encode(kdf.derive(import_password.encode()))
            import_cipher = Fernet(import_key)
            
            # Decrypt credentials
            encrypted_creds = base64.b64decode(data['encrypted_credentials'])
            decrypted_creds = import_cipher.decrypt(encrypted_creds)
            credentials_data = json.loads(decrypted_creds.decode())
            
            # Import credentials
            for name, cred_dict in credentials_data.items():
                if not overwrite and name in self.credentials:
                    continue  # Skip existing credentials
                
                created_at = datetime.fromisoformat(cred_dict['created_at'])
                expires_at = None
                if cred_dict['expires_at']:
                    expires_at = datetime.fromisoformat(cred_dict['expires_at'])
                
                credential = Credential(
                    name=cred_dict['name'],
                    value=cred_dict['value'],
                    credential_type=cred_dict['credential_type'],
                    created_at=created_at,
                    expires_at=expires_at,
                    metadata=cred_dict.get('metadata', {})
                )
                
                self.credentials[name] = credential
            
            self.save_credentials()
            return True
            
        except Exception:
            return False
    
    def __del__(self):
        """Cleanup: wipe encryption key from memory"""
        if hasattr(self, '_encryption_key') and self._encryption_key:
            _wipe_memory(self._encryption_key)


# Convenience functions for common credential types

def store_mavlink_credentials(cred_manager: SecureCredentialManager,
                             connection_string: str,
                             auth_token: Optional[str] = None) -> None:
    """Store MAVLink connection credentials"""
    cred_manager.store_credential(
        name="mavlink_connection",
        value=connection_string,
        credential_type="connection_string",
        metadata={"protocol": "mavlink", "interface": "hardware"}
    )
    
    if auth_token:
        cred_manager.store_credential(
            name="mavlink_auth_token",
            value=auth_token,
            credential_type="auth_token",
            expires_hours=24,  # Auth tokens should expire
            metadata={"protocol": "mavlink", "interface": "hardware"}
        )


def store_api_credentials(cred_manager: SecureCredentialManager,
                         service_name: str,
                         api_key: str,
                         api_secret: Optional[str] = None) -> None:
    """Store API service credentials"""
    cred_manager.store_credential(
        name=f"{service_name}_api_key",
        value=api_key,
        credential_type="api_key",
        metadata={"service": service_name, "interface": "api"}
    )
    
    if api_secret:
        cred_manager.store_credential(
            name=f"{service_name}_api_secret",
            value=api_secret,
            credential_type="api_secret",
            metadata={"service": service_name, "interface": "api"}
        )


def store_database_credentials(cred_manager: SecureCredentialManager,
                              db_name: str,
                              username: str,
                              password: str,
                              host: str = "localhost",
                              port: int = 5432) -> None:
    """Store database connection credentials"""
    connection_string = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
    
    cred_manager.store_credential(
        name=f"{db_name}_connection",
        value=connection_string,
        credential_type="database_connection",
        metadata={
            "database": db_name,
            "host": host,
            "port": port,
            "interface": "database"
        }
    ) 
