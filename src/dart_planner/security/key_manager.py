"""
Secure Key Management System for DART-Planner

Implements short-lived JWT tokens, HMAC tokens, and automatic key rotation
via file watcher for enhanced security.
"""

import os
import json
import secrets
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import threading
import logging

# Optional watchdog imports for file watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

from jose import JWTError, jwt
from .key_config import TokenType, KeyConfig, TokenMetadata, KeyManagerConfig
from .key_core import (
    initialize_keys, load_keys_from_file, save_keys_to_file,
    get_active_key, rotate_keys, create_jwt_token_core, verify_jwt_token_core,
    create_hmac_token_core, verify_hmac_token_core, cleanup_expired_keys_core
)
from .secure_file_utils import (
    secure_json_write, 
    secure_json_read, 
    validate_path_security,
    create_secure_directory,
    check_file_security,
    SecurityError
)

logger = logging.getLogger(__name__)


if WATCHDOG_AVAILABLE:
    class KeyRotationHandler(FileSystemEventHandler):
        """File system event handler for key rotation."""
        
        def __init__(self, key_manager):
            self.key_manager = key_manager
            self.last_modified = 0
        
        def on_modified(self, event):
            if event.is_directory:
                return
            
            # Prevent multiple rapid reloads
            current_time = time.time()
            if current_time - self.last_modified < 1.0:
                return
            
            self.last_modified = current_time
            
            if event.src_path == self.key_manager.keys_file:
                logger.info(f"Key file modified: {event.src_path}")
                self.key_manager.reload_keys()
else:
    # Dummy class when watchdog is not available
    class KeyRotationHandler:
        """Dummy file system event handler when watchdog is not available."""
        
        def __init__(self, key_manager):
            self.key_manager = key_manager


class SecureKeyManager:
    """
    Secure key management with automatic rotation and short-lived tokens.
    
    Features:
    - Multiple signing keys with automatic rotation
    - Short-lived JWT tokens (5-15 minutes)
    - HMAC tokens for API access
    - File watcher for key updates
    - Token revocation tracking
    """
    
    def __init__(self, config: Optional[KeyManagerConfig] = None):
        """
        Initialize the secure key manager.
        
        Args:
            config: Configuration for the key manager
        """
        self.config = config or KeyManagerConfig()
        self.keys_file = self.config.keys_file or os.path.expanduser("~/.dart_planner/keys.json")
        self.keys: Dict[str, KeyConfig] = {}
        self.observer: Optional[Observer] = None
        self.enable_watcher = self.config.enable_watcher
        
        # Ensure keys directory exists with secure permissions
        try:
            create_secure_directory(Path(self.keys_file).parent)
        except SecurityError as e:
            logger.error(f"Security validation failed for keys directory: {e}")
            raise
        
        # Load or initialize keys
        self.load_or_initialize_keys()
        
        # Start file watcher if enabled
        if self.enable_watcher:
            self.start_file_watcher()
    
    def load_or_initialize_keys(self):
        """Load existing keys or initialize new ones."""
        try:
            if os.path.exists(self.keys_file):
                self.keys = load_keys_from_file(self.keys_file)
                logger.info(f"Loaded {len(self.keys)} existing keys from {self.keys_file}")
            else:
                self.keys = initialize_keys(self.config)
                save_keys_to_file(self.keys, self.keys_file)
                logger.info(f"Initialized new keys in {self.keys_file}")
        except Exception as e:
            logger.error(f"Error loading keys: {e}")
            self.keys = initialize_keys(self.config)
            save_keys_to_file(self.keys, self.keys_file)
    
    def initialize_keys(self):
        """Initialize new signing keys."""
        self.keys = initialize_keys(self.config)
        save_keys_to_file(self.keys, self.keys_file)
    
    def load_keys(self):
        """Load keys from file."""
        self.keys = load_keys_from_file(self.keys_file)
    
    def save_keys(self):
        """Save keys to file."""
        # Temporarily disable file watcher to prevent reload loop
        if self.observer:
            self.observer.unschedule_all()
        
        try:
            save_keys_to_file(self.keys, self.keys_file)
        finally:
            # Re-enable file watcher
            if self.observer:
                self.start_file_watcher()
    
    def reload_keys(self):
        """Reload keys from file (called by file watcher)."""
        try:
            self.load_keys()
            logger.info("Keys reloaded successfully")
        except Exception as e:
            logger.error(f"Error reloading keys: {e}")
    
    def start_file_watcher(self):
        """Start file watcher for key rotation."""
        if not self.enable_watcher or not WATCHDOG_AVAILABLE:
            if not WATCHDOG_AVAILABLE:
                logger.warning("File watcher disabled: watchdog not available")
            return
        
        try:
            if self.observer:
                self.observer.unschedule_all()
                self.observer.stop()
            
            self.observer = Observer()
            handler = KeyRotationHandler(self)
            self.observer.schedule(handler, str(Path(self.keys_file).parent), recursive=False)
            self.observer.start()
            logger.info(f"File watcher started for {self.keys_file}")
        except Exception as e:
            logger.error(f"Error starting file watcher: {e}")
    
    def stop_file_watcher(self):
        """Stop file watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")
    
    def get_active_key(self, algorithm: str = "HS256") -> Optional[KeyConfig]:
        """Get the most recently created active key."""
        return get_active_key(self.keys, algorithm)
    
    def rotate_keys(self):
        """Rotate keys by creating new ones and marking old ones as inactive."""
        self.keys = rotate_keys(self.keys, self.config)
        save_keys_to_file(self.keys, self.keys_file)
        logger.info("Keys rotated successfully")
        return self.get_active_key()
    
    def create_jwt_token(self, 
                        payload: Dict[str, Any], 
                        token_type: TokenType = TokenType.JWT_ACCESS,
                        expires_in: Optional[timedelta] = None) -> Tuple[str, TokenMetadata]:
        """
        Create a short-lived JWT token.
        
        Args:
            payload: Token payload data
            token_type: Type of token to create
            expires_in: Token expiration time (defaults based on token type)
        
        Returns:
            Tuple of (token_string, token_metadata)
        """
        key = self.get_active_key()
        if not key:
            from dart_planner.common.errors import SecurityError
            raise SecurityError("No active signing key available")
        
        return create_jwt_token_core(payload, key, token_type, expires_in, self.config)
    
    def verify_jwt_token(self, token: str) -> Tuple[Dict[str, Any], TokenMetadata]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Tuple of (payload, metadata)
        
        Raises:
            JWTError: If token is invalid
        """
        return verify_jwt_token_core(token, self.keys)
    
    def create_hmac_token(self, 
                         user_id: str, 
                         scopes: List[str],
                         token_type: TokenType = TokenType.HMAC_API,
                         expires_in: Optional[timedelta] = None) -> Tuple[str, TokenMetadata]:
        """
        Create an HMAC-based token for API access.
        
        Args:
            user_id: User identifier
            scopes: List of permissions
            token_type: Type of token
            expires_in: Token expiration time
        
        Returns:
            Tuple of (token_string, token_metadata)
        """
        key = self.get_active_key()
        if not key:
            from dart_planner.common.errors import SecurityError
            raise SecurityError("No active signing key available")
        
        if expires_in is None:
            expires_in = timedelta(minutes=30)
        
        now = datetime.utcnow()
        expires_at = now + expires_in
        jti = secrets.token_hex(16)
        
        # Create token data
        token_data = {
            "user_id": user_id,
            "scopes": scopes,
            "type": token_type.value,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": jti,
            "kid": key.key_id
        }
        
        # Create HMAC signature
        message = json.dumps(token_data, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            key.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine data and signature
        token = f"{message}.{signature}"
        
        # Update key usage
        key.usage_count += 1
        
        # Create metadata
        metadata = TokenMetadata(
            token_type=token_type,
            key_id=key.key_id,
            issued_at=now,
            expires_at=expires_at,
            user_id=user_id,
            scopes=scopes,
            jti=jti
        )
        
        return token, metadata
    
    def verify_hmac_token(self, token: str) -> Tuple[Dict[str, Any], TokenMetadata]:
        """
        Verify and decode an HMAC token.
        
        Args:
            token: HMAC token string
        
        Returns:
            Tuple of (payload, metadata)
        
        Raises:
            ValueError: If token is invalid
        """
        try:
            message, signature = token.rsplit('.', 1)
            token_data = json.loads(message)
        except (ValueError, json.JSONDecodeError):
            from dart_planner.common.errors import SecurityError
            raise SecurityError("Invalid HMAC token format")
        
        # Check expiration
        exp_timestamp = token_data.get("exp")
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
            from dart_planner.common.errors import SecurityError
            raise SecurityError("Token expired")
        
        # Get key
        key_id = token_data.get("kid")
        key = self.keys.get(key_id)
        if not key:
            from dart_planner.common.errors import SecurityError
            raise SecurityError("Token signed with unknown key")
        
        # Verify signature
        expected_signature = hmac.new(
            key.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            from dart_planner.common.errors import SecurityError
            raise SecurityError("Invalid token signature")
        
        # Create metadata
        metadata = TokenMetadata(
            token_type=TokenType(token_data.get("type", TokenType.HMAC_API.value)),
            key_id=key_id,
            issued_at=datetime.fromtimestamp(token_data["iat"]),
            expires_at=datetime.fromtimestamp(token_data["exp"]),
            user_id=token_data.get("user_id", ""),
            scopes=token_data.get("scopes", []),
            jti=token_data.get("jti", "")
        )
        
        return token_data, metadata
    
    def revoke_token(self, jti: str) -> bool:
        """
        Revoke a token by its JWT ID.
        
        Args:
            jti: JWT ID to revoke
        
        Returns:
            True if token was revoked, False if already revoked
        """
        # This would typically store the JTI in a database
        # For now, we'll use a simple in-memory set
        if not hasattr(self, '_revoked_tokens'):
            self._revoked_tokens = set()
        
        if jti in self._revoked_tokens:
            return False
        
        self._revoked_tokens.add(jti)
        return True
    
    def is_token_revoked(self, jti: str) -> bool:
        """
        Check if a token is revoked.
        
        Args:
            jti: JWT ID to check
        
        Returns:
            True if token is revoked
        """
        if not hasattr(self, '_revoked_tokens'):
            self._revoked_tokens = set()
        
        return jti in self._revoked_tokens
    
    def cleanup_expired_keys(self):
        """Remove expired keys from memory."""
        current_time = datetime.utcnow()
        expired_keys = [
            key_id for key_id, key in self.keys.items()
            if key.expires_at and key.expires_at < current_time
        ]
        
        for key_id in expired_keys:
            del self.keys[key_id]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired keys")
    
    def get_key_stats(self) -> Dict[str, Any]:
        """Get statistics about key usage."""
        current_time = datetime.utcnow()
        
        active_keys = [
            key for key in self.keys.values()
            if key.is_active and (key.expires_at is None or key.expires_at > current_time)
        ]
        
        # Get file security information
        file_security = check_file_security(self.keys_file)
        
        return {
            "total_keys": len(self.keys),
            "active_keys": len(active_keys),
            "expired_keys": len(self.keys) - len(active_keys),
            "total_usage": sum(key.usage_count for key in self.keys.values()),
            "oldest_key": min((key.created_at for key in self.keys.values()), default=None),
            "newest_key": max((key.created_at for key in self.keys.values()), default=None),
            "file_security": file_security
        }
    
    def check_security(self) -> Dict[str, Any]:
        """Check the security status of the key storage."""
        return check_file_security(self.keys_file)
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_file_watcher()


# Global key manager instance
_key_manager: Optional[SecureKeyManager] = None


def get_key_manager() -> SecureKeyManager:
    """Get the global key manager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = SecureKeyManager()
    return _key_manager


def set_key_manager(key_manager: SecureKeyManager):
    """Set the global key manager instance."""
    global _key_manager
    if _key_manager:
        _key_manager.stop_file_watcher()
    _key_manager = key_manager 
