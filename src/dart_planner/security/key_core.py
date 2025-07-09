"""
Key Management Core Algorithms for DART-Planner

This module contains core algorithms and helper functions for secure key management.
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
from dataclasses import asdict
import logging

from jose import JWTError, jwt
from .key_config import KeyConfig, TokenType, TokenMetadata, KeyManagerConfig
from .secure_file_utils import (
    secure_json_write, 
    secure_json_read, 
    validate_path_security,
    create_secure_directory,
    check_file_security,
    SecurityError
)

logger = logging.getLogger(__name__)


def initialize_keys(config: KeyManagerConfig) -> Dict[str, KeyConfig]:
    """Initialize new signing keys."""
    current_time = datetime.utcnow()
    
    # Create primary key (valid for specified days)
    if config.algorithm == "RS256":
        # Generate RSA key pair for RS256
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        primary_key = KeyConfig(
            key_id=f"rsa_key_{int(current_time.timestamp())}",
            secret="",  # Not used for RS256
            algorithm="RS256",
            created_at=current_time,
            expires_at=current_time + timedelta(days=config.primary_key_days),
            is_active=True,
            max_usage=config.max_key_usage,
            private_key=private_pem,
            public_key=public_pem
        )
    else:
        # Use HS256 with secret key
        primary_key = KeyConfig(
            key_id=f"key_{int(current_time.timestamp())}",
            secret=secrets.token_hex(32),
            algorithm="HS256",
            created_at=current_time,
            expires_at=current_time + timedelta(days=config.primary_key_days),
            is_active=True,
            max_usage=config.max_key_usage
        )
    
    # Create backup key (valid for specified days)
    if config.algorithm == "RS256":
        # Generate another RSA key pair for backup
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        backup_key = KeyConfig(
            key_id=f"rsa_backup_{int(current_time.timestamp())}",
            secret="",  # Not used for RS256
            algorithm="RS256",
            created_at=current_time,
            expires_at=current_time + timedelta(days=config.backup_key_days),
            is_active=True,
            max_usage=config.max_key_usage,
            private_key=private_pem,
            public_key=public_pem
        )
    else:
        backup_key = KeyConfig(
            key_id=f"backup_{int(current_time.timestamp())}",
            secret=secrets.token_hex(32),
            algorithm="HS256",
            created_at=current_time,
            expires_at=current_time + timedelta(days=config.backup_key_days),
            is_active=True,
            max_usage=config.max_key_usage
        )
    
    return {
        primary_key.key_id: primary_key,
        backup_key.key_id: backup_key
    }


def load_keys_from_file(keys_file: str) -> Dict[str, KeyConfig]:
    """Load keys from file."""
    try:
        if not os.path.exists(keys_file):
            raise FileNotFoundError(f"Keys file not found: {keys_file}")
        
        # Validate file security
        check_file_security(keys_file)
        
        # Load keys
        keys_data = secure_json_read(keys_file)
        keys = {}
        
        for key_id, key_data in keys_data.items():
            # Convert string dates back to datetime objects
            if 'created_at' in key_data:
                key_data['created_at'] = datetime.fromisoformat(key_data['created_at'])
            if 'expires_at' in key_data and key_data['expires_at']:
                key_data['expires_at'] = datetime.fromisoformat(key_data['expires_at'])
            
            keys[key_id] = KeyConfig(**key_data)
        
        return keys
        
    except Exception as e:
        logger.error(f"Error loading keys from {keys_file}: {e}")
        raise


def save_keys_to_file(keys: Dict[str, KeyConfig], keys_file: str) -> None:
    """Save keys to file."""
    try:
        # Ensure directory exists with secure permissions
        keys_dir = Path(keys_file).parent
        create_secure_directory(keys_dir)
        
        # Convert keys to serializable format
        keys_data = {}
        for key_id, key_config in keys.items():
            key_dict = asdict(key_config)
            # Convert datetime objects to ISO format strings
            key_dict['created_at'] = key_config.created_at.isoformat()
            if key_config.expires_at:
                key_dict['expires_at'] = key_config.expires_at.isoformat()
            keys_data[key_id] = key_dict
        
        # Save securely
        secure_json_write(keys_file, keys_data)
        logger.debug(f"Saved {len(keys)} keys to {keys_file}")
        
    except Exception as e:
        logger.error(f"Error saving keys to {keys_file}: {e}")
        raise


def get_active_key(keys: Dict[str, KeyConfig], algorithm: str = "HS256") -> Optional[KeyConfig]:
    """Get the most recently created active key for the specified algorithm."""
    current_time = datetime.utcnow()
    active_keys = []
    
    for key_config in keys.values():
        if (key_config.algorithm == algorithm and 
            key_config.is_active and 
            (key_config.expires_at is None or key_config.expires_at > current_time) and
            (key_config.max_usage is None or key_config.usage_count < key_config.max_usage)):
            active_keys.append(key_config)
    
    if not active_keys:
        return None
    
    # Return the most recently created key
    return max(active_keys, key=lambda k: k.created_at)


def rotate_keys(keys: Dict[str, KeyConfig], config: KeyManagerConfig) -> Dict[str, KeyConfig]:
    """Rotate keys by creating new ones and marking old ones as inactive."""
    current_time = datetime.utcnow()
    
    # Mark expired keys as inactive
    for key_config in keys.values():
        if key_config.expires_at and key_config.expires_at <= current_time:
            key_config.is_active = False
            logger.info(f"Marked expired key {key_config.key_id} as inactive")
    
    # Create new keys
    new_keys = initialize_keys(config)
    
    # Merge with existing keys
    keys.update(new_keys)
    
    logger.info(f"Rotated keys: created {len(new_keys)} new keys")
    return keys


def create_jwt_token_core(
    payload: Dict[str, Any], 
    key_config: KeyConfig,
    token_type: TokenType = TokenType.JWT_ACCESS,
    expires_in: Optional[timedelta] = None,
    config: Optional[KeyManagerConfig] = None
) -> Tuple[str, TokenMetadata]:
    """Core function to create JWT token."""
    if config is None:
        config = KeyManagerConfig()
    
    # Set default expiry based on token type
    if expires_in is None:
        if token_type == TokenType.JWT_ACCESS:
            expires_in = timedelta(minutes=config.jwt_access_expiry_minutes)
        elif token_type == TokenType.JWT_REFRESH:
            expires_in = timedelta(hours=config.jwt_refresh_expiry_hours)
        else:
            expires_in = timedelta(minutes=15)  # Default
    
    # Create token metadata
    issued_at = datetime.utcnow()
    expires_at = issued_at + expires_in
    jti = secrets.token_hex(16)
    
    # Add standard claims with strict validation
    token_payload = {
        **payload,
        'iat': issued_at,
        'exp': expires_at,
        'jti': jti,
        'type': token_type.value,
        'iss': 'dart-planner',  # Issuer claim
        'aud': 'dart-planner-api'  # Audience claim
    }
    
    # Create token with appropriate key based on algorithm
    if key_config.algorithm == "RS256":
        # For RS256, use private key for signing
        if not key_config.private_key:
            raise ValueError("Private key required for RS256 algorithm")
        token = jwt.encode(token_payload, key_config.private_key, algorithm=key_config.algorithm)
    else:
        # For HS256, use secret key
        token = jwt.encode(token_payload, key_config.secret, algorithm=key_config.algorithm)
    
    # Increment usage count
    key_config.usage_count += 1
    
    # Create metadata
    metadata = TokenMetadata(
        token_type=token_type,
        key_id=key_config.key_id,
        issued_at=issued_at,
        expires_at=expires_at,
        user_id=payload.get('user_id', ''),
        scopes=payload.get('scopes', []),
        jti=jti
    )
    
    return token, metadata


def verify_jwt_token_core(token: str, keys: Dict[str, KeyConfig]) -> Tuple[Dict[str, Any], TokenMetadata]:
    """Core function to verify JWT token."""
    # Try to decode without verification first to get key_id
    try:
        unverified_payload = jwt.get_unverified_claims(token)
        key_id = unverified_payload.get('key_id')
    except JWTError:
        raise JWTError("Invalid token format")
    
    # Find the key used to sign the token
    if key_id and key_id in keys:
        key_config = keys[key_id]
    else:
        # Try to find an active key
        key_config = get_active_key(keys)
        if not key_config:
            raise JWTError("No valid signing key available")
    
    # Verify the token with appropriate key and strict claims validation
    try:
        if key_config.algorithm == "RS256":
            # For RS256, use public key for verification
            if not key_config.public_key:
                raise JWTError("Public key required for RS256 verification")
            payload = jwt.decode(
                token, 
                key_config.public_key, 
                algorithms=[key_config.algorithm],
                issuer="dart-planner",
                audience="dart-planner-api"
            )
        else:
            # For HS256, use secret key
            payload = jwt.decode(
                token, 
                key_config.secret, 
                algorithms=[key_config.algorithm],
                issuer="dart-planner",
                audience="dart-planner-api"
            )
    except JWTError as e:
        raise JWTError(f"Token verification failed: {e}")
    
    # Create metadata
    metadata = TokenMetadata(
        token_type=TokenType(payload.get('type', TokenType.JWT_ACCESS.value)),
        key_id=key_config.key_id,
        issued_at=datetime.fromtimestamp(payload['iat']),
        expires_at=datetime.fromtimestamp(payload['exp']),
        user_id=payload.get('user_id', ''),
        scopes=payload.get('scopes', []),
        jti=payload.get('jti', '')
    )
    
    return payload, metadata


def create_hmac_token_core(
    user_id: str, 
    scopes: List[str],
    key_config: KeyConfig,
    token_type: TokenType = TokenType.HMAC_API,
    expires_in: Optional[timedelta] = None,
    config: Optional[KeyManagerConfig] = None
) -> Tuple[str, TokenMetadata]:
    """Core function to create HMAC token."""
    if config is None:
        config = KeyManagerConfig()
    
    # Set default expiry based on token type
    if expires_in is None:
        if token_type == TokenType.HMAC_API:
            expires_in = timedelta(hours=config.hmac_api_expiry_hours)
        elif token_type == TokenType.HMAC_SESSION:
            expires_in = timedelta(hours=config.hmac_session_expiry_hours)
        else:
            expires_in = timedelta(hours=1)  # Default
    
    # Create token data
    issued_at = datetime.utcnow()
    expires_at = issued_at + expires_in
    jti = secrets.token_hex(16)
    
    token_data = {
        'user_id': user_id,
        'scopes': scopes,
        'type': token_type.value,
        'iat': int(issued_at.timestamp()),
        'exp': int(expires_at.timestamp()),
        'jti': jti,
        'key_id': key_config.key_id
    }
    
    # Create HMAC signature
    message = json.dumps(token_data, sort_keys=True)
    signature = hmac.new(
        key_config.secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Combine message and signature
    token = f"{message}.{signature}"
    
    # Increment usage count
    key_config.usage_count += 1
    
    # Create metadata
    metadata = TokenMetadata(
        token_type=token_type,
        key_id=key_config.key_id,
        issued_at=issued_at,
        expires_at=expires_at,
        user_id=user_id,
        scopes=scopes,
        jti=jti
    )
    
    return token, metadata


def verify_hmac_token_core(token: str, keys: Dict[str, KeyConfig]) -> Tuple[Dict[str, Any], TokenMetadata]:
    """Core function to verify HMAC token."""
    try:
        # Split token into message and signature
        message, signature = token.rsplit('.', 1)
        
        # Parse token data
        token_data = json.loads(message)
        
        # Get key
        key_id = token_data.get('key_id')
        if key_id and key_id in keys:
            key_config = keys[key_id]
        else:
            key_config = get_active_key(keys)
            if not key_config:
                raise ValueError("No valid signing key available")
        
        # Verify signature
        expected_signature = hmac.new(
            key_config.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid signature")
        
        # Check expiration
        exp_timestamp = token_data.get('exp')
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.utcnow():
            raise ValueError("Token expired")
        
        # Create metadata
        metadata = TokenMetadata(
            token_type=TokenType(token_data.get('type', TokenType.HMAC_API.value)),
            key_id=key_config.key_id,
            issued_at=datetime.fromtimestamp(token_data['iat']),
            expires_at=datetime.fromtimestamp(exp_timestamp),
            user_id=token_data.get('user_id', ''),
            scopes=token_data.get('scopes', []),
            jti=token_data.get('jti', '')
        )
        
        return token_data, metadata
        
    except (ValueError, json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid HMAC token: {e}")


def cleanup_expired_keys_core(keys: Dict[str, KeyConfig]) -> Dict[str, KeyConfig]:
    """Remove expired keys from the dictionary."""
    current_time = datetime.utcnow()
    expired_keys = []
    
    for key_id, key_config in keys.items():
        if (key_config.expires_at and key_config.expires_at <= current_time and
            key_config.usage_count == 0):  # Only remove unused expired keys
            expired_keys.append(key_id)
    
    for key_id in expired_keys:
        del keys[key_id]
        logger.info(f"Removed expired unused key: {key_id}")
    
    return keys 