"""
Legacy Crypto Module for DART-Planner Security

This module has been modularized into separate components:
- key_derivation.py: Key derivation functions
- credential_manager.py: Credential management
- credential_helpers.py: Helper functions for specific credential types

This module now provides backward compatibility and re-exports the main components.
"""

import logging
from typing import Optional

# Re-export main components for backward compatibility
from .key_derivation import (
    derive_key_from_passphrase,
    derive_key_from_os_keystore,
    generate_secure_key,
    wipe_memory,
    KeyDerivationError,
    OSKeyStoreError
)

from .credential_manager import (
    SecureCredentialManager,
    Credential
)

from .credential_helpers import (
    store_mavlink_credentials,
    store_api_credentials,
    store_database_credentials,
    store_jwt_credentials,
    store_ssl_credentials,
    get_mavlink_credentials,
    get_api_credentials,
    get_database_credentials,
    get_jwt_credentials,
    rotate_api_credentials,
    cleanup_expired_credentials,
    list_credential_summary
)

logger = logging.getLogger(__name__)

# Backward compatibility aliases
def _derive_key_from_passphrase(passphrase: str, salt: Optional[bytes] = None):
    """Backward compatibility alias"""
    return derive_key_from_passphrase(passphrase, salt)

def _derive_key_from_os_keystore(key_id: str):
    """Backward compatibility alias"""
    return derive_key_from_os_keystore(key_id)

def _wipe_memory(data: bytes) -> None:
    """Backward compatibility alias"""
    return wipe_memory(data)

# Legacy constants for backward compatibility
DEFAULT_SALT = b'dart_planner_secure_salt_2025_v2_'
PBKDF2_ITERATIONS = 600000
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1

logger.info("Crypto module loaded - using modularized components") 
