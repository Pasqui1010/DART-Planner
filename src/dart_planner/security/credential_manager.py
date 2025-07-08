"""
Credential Management Module for DART-Planner Security

Provides secure storage and management of credentials including:
- API keys, database passwords, authentication tokens
- Expiration management and rotation
- Import/export functionality
"""

import json
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet

from .key_derivation import generate_secure_key, wipe_memory
from .os_keyring import OSKeyringManager, get_keyring_manager
from .secure_file_utils import secure_json_write, secure_json_read, SecurityError

logger = logging.getLogger(__name__)


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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Credential':
        """Create from dictionary"""
        # Parse datetime fields
        created_at = datetime.fromisoformat(data['created_at'])
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        return cls(
            name=data['name'],
            value=data['value'],
            credential_type=data['credential_type'],
            created_at=created_at,
            expires_at=expires_at,
            metadata=data.get('metadata', {})
        )
    
    def is_expired(self) -> bool:
        """Check if credential is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def days_until_expiry(self) -> Optional[int]:
        """Get days until expiry (negative if expired)"""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now()
        return delta.days


class SecureCredentialManager:
    """
    Secure credential manager using OS keyring for key storage
    and encrypted file storage for credentials.
    """
    
    def __init__(self, credentials_file: str = "credentials.encrypted", 
                 use_os_keyring: bool = True):
        """
        Initialize credential manager
        
        Args:
            credentials_file: Path to encrypted credentials file
            use_os_keyring: Whether to use OS keyring for key storage
        """
        self.credentials_file = Path(credentials_file)
        self.use_os_keyring = use_os_keyring
        self.credentials: Dict[str, Credential] = {}
        self._cipher: Optional[Fernet] = None
        self._keyring_manager: Optional[OSKeyringManager] = None
        
        # Initialize keyring manager if enabled
        if self.use_os_keyring:
            try:
                self._keyring_manager = get_keyring_manager()
                logger.info("OS keyring manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OS keyring: {e}")
                self.use_os_keyring = False
        
        # Initialize encryption
        self._initialize_encryption()
        
        # Load existing credentials
        if self.credentials_file.exists():
            self.load_credentials()
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption cipher"""
        try:
            if self.use_os_keyring and self._keyring_manager:
                # Try to get key from OS keyring
                key = self._keyring_manager.get_key("credential_manager_key")
                if key is None:
                    # Generate new key and store in OS keyring
                    key = generate_secure_key()
                    self._keyring_manager.store_key("credential_manager_key", key)
            else:
                # Fallback to file-based key storage
                key_file = Path("credential_manager.key")
                if key_file.exists():
                    key = key_file.read_bytes()
                else:
                    key = generate_secure_key()
                    key_file.write_bytes(key)
            
            self._cipher = Fernet(key)
            logger.info("Encryption cipher initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise SecurityError(f"Encryption initialization failed: {e}")
    
    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt data using Fernet"""
        if self._cipher is None:
            raise SecurityError("Encryption not initialized")
        return self._cipher.encrypt(data.encode('utf-8'))
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt data using Fernet"""
        if self._cipher is None:
            raise SecurityError("Encryption not initialized")
        return self._cipher.decrypt(encrypted_data).decode('utf-8')
    
    def store_credential(self, name: str, value: str, credential_type: str,
                        expires_hours: Optional[int] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a credential securely
        
        Args:
            name: Credential name/identifier
            value: Credential value (password, token, etc.)
            credential_type: Type of credential (api_key, password, token, etc.)
            expires_hours: Hours until expiry (None for no expiry)
            metadata: Additional metadata
        """
        expires_at = None
        if expires_hours is not None:
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
        
        logger.info(f"Stored credential: {name} (type: {credential_type})")
    
    def get_credential(self, name: str) -> Optional[str]:
        """
        Retrieve a credential value
        
        Args:
            name: Credential name/identifier
            
        Returns:
            Credential value or None if not found/expired
        """
        credential = self.credentials.get(name)
        if credential is None:
            return None
        
        if credential.is_expired():
            logger.warning(f"Credential {name} is expired")
            return None
        
        return credential.value
    
    def get_credential_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get credential information (without the actual value)
        
        Args:
            name: Credential name/identifier
            
        Returns:
            Credential info dictionary or None if not found
        """
        credential = self.credentials.get(name)
        if credential is None:
            return None
        
        info = credential.to_dict()
        # Remove the actual value for security
        info.pop('value', None)
        return info
    
    def remove_credential(self, name: str) -> bool:
        """
        Remove a credential
        
        Args:
            name: Credential name/identifier
            
        Returns:
            True if credential was removed, False if not found
        """
        if name in self.credentials:
            del self.credentials[name]
            self.save_credentials()
            logger.info(f"Removed credential: {name}")
            return True
        return False
    
    def list_credentials(self) -> Dict[str, Dict[str, Any]]:
        """
        List all credentials (without values)
        
        Returns:
            Dictionary of credential information
        """
        return {
            name: self.get_credential_info(name)
            for name in self.credentials.keys()
        }
    
    def rotate_credential(self, name: str, new_value: str) -> bool:
        """
        Rotate a credential with a new value
        
        Args:
            name: Credential name/identifier
            new_value: New credential value
            
        Returns:
            True if credential was rotated, False if not found
        """
        if name not in self.credentials:
            return False
        
        old_credential = self.credentials[name]
        new_credential = Credential(
            name=name,
            value=new_value,
            credential_type=old_credential.credential_type,
            created_at=datetime.now(),
            expires_at=old_credential.expires_at,
            metadata=old_credential.metadata
        )
        
        self.credentials[name] = new_credential
        self.save_credentials()
        
        logger.info(f"Rotated credential: {name}")
        return True
    
    def save_credentials(self) -> None:
        """Save credentials to encrypted file"""
        try:
            # Convert credentials to dictionary format
            data = {
                name: credential.to_dict()
                for name, credential in self.credentials.items()
            }
            
            # Encrypt and save
            json_data = json.dumps(data, indent=2)
            encrypted_data = self._encrypt_data(json_data)
            
            secure_json_write(self.credentials_file, encrypted_data)
            logger.debug(f"Saved {len(self.credentials)} credentials")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise SecurityError(f"Failed to save credentials: {e}")
    
    def load_credentials(self) -> None:
        """Load credentials from encrypted file"""
        try:
            if not self.credentials_file.exists():
                logger.info("No credentials file found")
                return
            
            # Load and decrypt
            encrypted_data = secure_json_read(self.credentials_file)
            json_data = self._decrypt_data(encrypted_data)
            data = json.loads(json_data)
            
            # Convert back to credential objects
            self.credentials = {
                name: Credential.from_dict(cred_data)
                for name, cred_data in data.items()
            }
            
            logger.info(f"Loaded {len(self.credentials)} credentials")
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise SecurityError(f"Failed to load credentials: {e}")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired credentials
        
        Returns:
            Number of credentials removed
        """
        expired_names = [
            name for name, credential in self.credentials.items()
            if credential.is_expired()
        ]
        
        for name in expired_names:
            del self.credentials[name]
        
        if expired_names:
            self.save_credentials()
            logger.info(f"Removed {len(expired_names)} expired credentials")
        
        return len(expired_names)
    
    def export_credentials(self, export_password: str) -> str:
        """
        Export credentials to encrypted backup
        
        Args:
            export_password: Password to encrypt the export
            
        Returns:
            Base64-encoded encrypted export data
        """
        import base64
        from cryptography.fernet import Fernet
        
        # Create export data
        export_data = {
            name: credential.to_dict()
            for name, credential in self.credentials.items()
        }
        
        # Encrypt with export password
        json_data = json.dumps(export_data, indent=2)
        
        # Derive key from export password
        from .key_derivation import derive_key_from_passphrase
        export_key, salt = derive_key_from_passphrase(export_password)
        
        # Encrypt data
        export_cipher = Fernet(export_key)
        encrypted_data = export_cipher.encrypt(json_data.encode('utf-8'))
        
        # Combine salt and encrypted data
        combined_data = salt + encrypted_data
        return base64.b64encode(combined_data).decode('utf-8')
    
    def import_credentials(self, import_data: str, import_password: str,
                          overwrite: bool = False) -> bool:
        """
        Import credentials from encrypted backup
        
        Args:
            import_data: Base64-encoded encrypted import data
            import_password: Password to decrypt the import
            overwrite: Whether to overwrite existing credentials
            
        Returns:
            True if import was successful
        """
        import base64
        from cryptography.fernet import Fernet
        
        try:
            # Decode import data
            combined_data = base64.b64decode(import_data)
            
            # Extract salt and encrypted data
            salt = combined_data[:32]
            encrypted_data = combined_data[32:]
            
            # Derive key from import password
            from .key_derivation import derive_key_from_passphrase
            import_key, _ = derive_key_from_passphrase(import_password, salt)
            
            # Decrypt data
            import_cipher = Fernet(import_key)
            json_data = import_cipher.decrypt(encrypted_data).decode('utf-8')
            data = json.loads(json_data)
            
            # Import credentials
            imported_count = 0
            for name, cred_data in data.items():
                if name in self.credentials and not overwrite:
                    logger.warning(f"Skipping existing credential: {name}")
                    continue
                
                credential = Credential.from_dict(cred_data)
                self.credentials[name] = credential
                imported_count += 1
            
            self.save_credentials()
            logger.info(f"Imported {imported_count} credentials")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import credentials: {e}")
            return False
    
    # Convenience methods for common credential types
    def store_mavlink_credentials(self, connection_string: str, auth_token: Optional[str] = None) -> None:
        """Store MAVLink connection credentials"""
        from .credential_helpers import store_mavlink_credentials
        store_mavlink_credentials(self, connection_string, auth_token)
    
    def store_api_credentials(self, service_name: str, api_key: str, api_secret: Optional[str] = None) -> None:
        """Store API credentials"""
        from .credential_helpers import store_api_credentials
        store_api_credentials(self, service_name, api_key, api_secret)
    
    def store_database_credentials(self, db_name: str, username: str, password: str, 
                                  host: str = "localhost", port: int = 5432) -> None:
        """Store database credentials"""
        from .credential_helpers import store_database_credentials
        store_database_credentials(self, db_name, username, password, host, port)
    
    def store_jwt_credentials(self, secret_key: str, algorithm: str = "HS256", expires_hours: int = 8760) -> None:
        """Store JWT credentials"""
        from .credential_helpers import store_jwt_credentials
        store_jwt_credentials(self, secret_key, algorithm, expires_hours)
    
    def store_ssl_credentials(self, cert_file: str, key_file: str, ca_file: Optional[str] = None) -> None:
        """Store SSL certificate credentials"""
        from .credential_helpers import store_ssl_credentials
        store_ssl_credentials(self, cert_file, key_file, ca_file)
    
    def get_mavlink_credentials(self) -> Optional[tuple[str, Optional[str]]]:
        """Get MAVLink credentials"""
        from .credential_helpers import get_mavlink_credentials
        return get_mavlink_credentials(self)
    
    def get_api_credentials(self, service_name: str) -> Optional[tuple[str, Optional[str]]]:
        """Get API credentials"""
        from .credential_helpers import get_api_credentials
        return get_api_credentials(self, service_name)
    
    def get_database_credentials(self, db_name: str) -> Optional[tuple[str, str, str, int]]:
        """Get database credentials"""
        from .credential_helpers import get_database_credentials
        return get_database_credentials(self, db_name)
    
    def get_jwt_credentials(self) -> Optional[tuple[str, str]]:
        """Get JWT credentials"""
        from .credential_helpers import get_jwt_credentials
        return get_jwt_credentials(self)
    
    def rotate_api_credentials(self, service_name: str, new_api_key: str, new_api_secret: Optional[str] = None) -> bool:
        """Rotate API credentials"""
        from .credential_helpers import rotate_api_credentials
        return rotate_api_credentials(self, service_name, new_api_key, new_api_secret)
    
    def cleanup_expired_credentials(self) -> int:
        """Cleanup expired credentials"""
        from .credential_helpers import cleanup_expired_credentials
        return cleanup_expired_credentials(self)
    
    def list_credential_summary(self) -> dict:
        """List credential summary"""
        from .credential_helpers import list_credential_summary
        return list_credential_summary(self)
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            # Wipe sensitive data from memory
            for credential in self.credentials.values():
                wipe_memory(credential.value.encode('utf-8'))
        except:
            pass 