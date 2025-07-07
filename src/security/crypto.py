"""
Secure Credential Management for DART-Planner

Provides encrypted storage and retrieval of sensitive credentials
for hardware interfaces, API keys, and authentication tokens.
"""

import os
import json
import base64
import secrets
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class Credential:
    """Secure credential storage structure"""
    name: str
    value: str
    credential_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SecureCredentialManager:
    """
    Secure credential management system
    
    Encrypts and stores sensitive credentials like API keys, hardware
    authentication tokens, and connection strings using industry-standard
    encryption (AES-256 via Fernet).
    """
    
    def __init__(self, credentials_file: str = "credentials.encrypted", 
                 master_password: Optional[str] = None):
        self.credentials_file = Path(credentials_file)
        self.credentials: Dict[str, Credential] = {}
        self._encryption_key: Optional[bytes] = None
        
        # Initialize encryption key
        if master_password:
            self._set_master_password(master_password)
        else:
            self._load_or_generate_key()
        
        # Load existing credentials
        self.load_credentials()
    
    def _set_master_password(self, password: str) -> None:
        """Derive encryption key from master password"""
        # Use a fixed salt for password-based key derivation
        # In production, store salt separately
        salt = b'dart_planner_salt_2025'  # 22 bytes
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self._encryption_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _load_or_generate_key(self) -> None:
        """Load existing key or generate new one"""
        key_file = Path("encryption.key")
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                self._encryption_key = f.read()
        else:
            # Generate new key
            self._encryption_key = Fernet.generate_key()
            
            # Store key securely (in production, use HSM or key management service)
            with open(key_file, 'wb') as f:
                f.write(self._encryption_key)
            
            # Set restrictive file permissions
            os.chmod(key_file, 0o600)
    
    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher instance"""
        if not self._encryption_key:
            raise RuntimeError("Encryption key not initialized")
        return Fernet(self._encryption_key)
    
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
        
        # Encrypt and save
        cipher = self._get_cipher()
        encrypted_data = cipher.encrypt(json.dumps(data).encode())
        
        # Create directory if it doesn't exist
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Set restrictive permissions
        os.chmod(self.credentials_file, 0o600)
    
    def load_credentials(self) -> None:
        """Load and decrypt credentials from file"""
        if not self.credentials_file.exists():
            return
        
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
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
            # In production, this should be logged and handled more gracefully
            print(f"Warning: Could not load credentials: {e}")
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
        # First verify old password by attempting to decrypt
        try:
            old_key = self._encryption_key
            self._set_master_password(old_password)
            
            # Try to decrypt existing data to verify old password
            if self.credentials_file.exists():
                with open(self.credentials_file, 'rb') as f:
                    encrypted_data = f.read()
                
                cipher = self._get_cipher()
                cipher.decrypt(encrypted_data)  # This will fail if password is wrong
            
            # Old password verified, set new password and re-encrypt
            self._set_master_password(new_password)
            self.save_credentials()
            
            return True
            
        except Exception:
            # Restore old key
            self._encryption_key = old_key
            return False
    
    def export_credentials(self, export_password: str) -> str:
        """Export credentials as encrypted JSON string"""
        # Create temporary encryption with export password
        export_salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=export_salt,
            iterations=100000,
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
                iterations=100000,
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