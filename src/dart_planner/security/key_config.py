"""
Key Management Configuration for DART-Planner

This module contains configuration classes and enums for the secure key management system.
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
from dataclasses import dataclass, asdict
from enum import Enum
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
from .secure_file_utils import (
    secure_json_write, 
    secure_json_read, 
    validate_path_security,
    create_secure_directory,
    check_file_security,
    SecurityError
)


class TokenType(str, Enum):
    """Token types for different use cases."""
    JWT_ACCESS = "jwt_access"
    JWT_REFRESH = "jwt_refresh"
    HMAC_API = "hmac_api"
    HMAC_SESSION = "hmac_session"


@dataclass
class KeyConfig:
    """Configuration for signing keys."""
    key_id: str
    secret: str  # For HS256
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    usage_count: int = 0
    max_usage: Optional[int] = None
    # For RS256 asymmetric keys
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.expires_at, str):
            self.expires_at = datetime.fromisoformat(self.expires_at)


@dataclass
class TokenMetadata:
    """Metadata for token validation."""
    token_type: TokenType
    key_id: str
    issued_at: datetime
    expires_at: datetime
    user_id: str
    scopes: List[str]
    jti: str  # JWT ID for revocation tracking


@dataclass
class KeyManagerConfig:
    """Configuration for the secure key manager."""
    keys_file: Optional[str] = None
    enable_watcher: bool = True
    algorithm: str = "RS256"  # Default to RS256 for enhanced security
    primary_key_days: int = 30
    backup_key_days: int = 60
    jwt_access_expiry_minutes: int = 15
    jwt_refresh_expiry_hours: int = 24
    hmac_api_expiry_hours: int = 1
    hmac_session_expiry_hours: int = 8
    max_key_usage: Optional[int] = 10000
    cleanup_interval_hours: int = 24 