"""
Key Derivation Module for DART-Planner Security

Provides secure key derivation functions using various methods:
- PBKDF2 for passphrase-based derivation
- OS-specific key derivation (Windows DPAPI, macOS Keychain, Linux TPM)
"""

import os
import base64
import secrets
import platform
import logging
from typing import Optional
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .secure_file_utils import secure_binary_write, SecurityError

logger = logging.getLogger(__name__)

# Security parameters
PBKDF2_ITERATIONS = 600000  # Increased for better security
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1


class KeyDerivationError(Exception):
    """Raised when key derivation fails"""
    pass


class OSKeyStoreError(Exception):
    """Raised when OS keystore operations fail"""
    pass


def derive_key_from_passphrase(passphrase: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive encryption key from passphrase using PBKDF2
    
    Args:
        passphrase: User-supplied passphrase
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (derived key suitable for Fernet, salt used)
        
    Raises:
        KeyDerivationError: If key derivation fails
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


def derive_key_from_scrypt(passphrase: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive encryption key from passphrase using Scrypt
    
    Args:
        passphrase: User-supplied passphrase
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (derived key suitable for Fernet, salt used)
        
    Raises:
        KeyDerivationError: If key derivation fails
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # Use Scrypt for memory-hard key derivation
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    
    try:
        key = kdf.derive(passphrase.encode('utf-8'))
        return base64.urlsafe_b64encode(key), salt
    except Exception as e:
        raise KeyDerivationError(f"Failed to derive key using Scrypt: {e}")


def derive_key_from_os_keystore(key_id: str) -> bytes:
    """
    Derive encryption key from OS keystore (TPM, macOS keychain, Windows DPAPI)
    
    Args:
        key_id: Identifier for the key in the OS keystore
        
    Returns:
        Derived key suitable for Fernet
        
    Raises:
        OSKeyStoreError: If OS keystore operations fail
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
    """
    Derive key using Windows DPAPI
    
    Args:
        key_id: Identifier for the key
        
    Returns:
        Derived key suitable for Fernet
        
    Raises:
        OSKeyStoreError: If DPAPI operations fail
    """
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
        
        # Store protected key in secure location
        key_file = Path(f"protected_key_{key_id}.bin")
        secure_binary_write(key_file, protected_key)
        
        return base64.urlsafe_b64encode(key_material)
        
    except ImportError:
        raise OSKeyStoreError("win32crypt not available - install pywin32")
    except Exception as e:
        raise OSKeyStoreError(f"Windows DPAPI failed: {e}")


def _derive_key_from_macos_keychain(key_id: str) -> bytes:
    """
    Derive key using macOS keychain
    
    Args:
        key_id: Identifier for the key
        
    Returns:
        Derived key suitable for Fernet
        
    Raises:
        OSKeyStoreError: If keychain operations fail
    """
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
    """
    Derive key using Linux TPM (if available)
    
    Args:
        key_id: Identifier for the key
        
    Returns:
        Derived key suitable for Fernet
        
    Raises:
        OSKeyStoreError: If TPM operations fail
    """
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


def generate_secure_key() -> bytes:
    """
    Generate a cryptographically secure random key
    
    Returns:
        Secure random key suitable for Fernet
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32))


def wipe_memory(data: bytes) -> None:
    """
    Securely wipe memory by overwriting with zeros
    
    Note: This is a simplified implementation. In a real implementation,
    you'd need to work with mutable buffers to actually overwrite memory.
    
    Args:
        data: Data to wipe (will be converted to bytearray)
    """
    if data:
        # Convert to bytearray for modification, then back to bytes
        data_array = bytearray(data)
        for i in range(len(data_array)):
            data_array[i] = 0
        # Note: This doesn't actually modify the original bytes object
        # In a real implementation, you'd need to work with mutable buffers


def validate_key_strength(key: bytes) -> bool:
    """
    Validate that a key meets minimum strength requirements
    
    Args:
        key: Key to validate
        
    Returns:
        True if key meets strength requirements
    """
    if len(key) < 32:
        return False
    
    # Check for sufficient entropy (simplified)
    unique_bytes = len(set(key))
    if unique_bytes < 16:  # At least 16 unique bytes
        return False
    
    return True 