# DART-Planner Security Hardening

## Overview

This document describes the comprehensive security hardening implemented in DART-Planner, including secure key management, short-lived tokens, HMAC authentication, and automatic key rotation.

## Security Improvements

### 1. Secure Key Management System

**Problem**: Raw environment variable secrets are vulnerable to exposure and don't support rotation.

**Solution**: Implemented a secure key management system with automatic rotation.

#### Features:
- **Multiple signing keys**: Primary and backup keys for redundancy
- **Automatic key rotation**: Keys rotate every 30 days with grace period
- **File watcher**: Real-time key updates without service restart
- **Key metadata tracking**: Usage statistics and expiration management

#### Implementation:
```python
from src.security.key_manager import SecureKeyManager, get_key_manager

# Initialize key manager (automatic)
key_manager = get_key_manager()

# Create short-lived JWT token
token, metadata = key_manager.create_jwt_token(
    payload={"sub": "user123", "scopes": ["pilot"]},
    token_type=TokenType.JWT_ACCESS,
    expires_in=timedelta(minutes=15)
)
```

### 2. Short-Lived Tokens

**Problem**: Long-lived tokens (30 minutes access, 7 days refresh) increase attack window.

**Solution**: Reduced token lifetimes for enhanced security.

#### New Token Lifetimes:
- **Access tokens**: 15 minutes (reduced from 30)
- **Refresh tokens**: 1 hour (reduced from 7 days)
- **API tokens**: 30 minutes (HMAC-based)

#### Benefits:
- Reduced attack window if tokens are compromised
- Forces regular re-authentication
- Limits damage from token theft

### 3. HMAC Token Support

**Problem**: JWT tokens can be large and complex for simple API access.

**Solution**: Added HMAC-based tokens for lightweight API authentication.

#### Features:
- **Compact format**: Smaller than JWT tokens
- **Fast verification**: HMAC-SHA256 for performance
- **API-specific**: Designed for machine-to-machine communication
- **Scope-based**: Fine-grained permission control

#### Usage:
```python
# Create HMAC token for API access
hmac_token, metadata = key_manager.create_hmac_token(
    user_id="api_client",
    scopes=["read_data", "write_data"],
    token_type=TokenType.HMAC_API,
    expires_in=timedelta(minutes=30)
)

# Verify HMAC token
payload, _ = key_manager.verify_hmac_token(hmac_token)
```

### 4. Token Revocation

**Problem**: Compromised tokens remain valid until expiration.

**Solution**: Implemented token revocation with JWT ID tracking.

#### Features:
- **Immediate revocation**: Tokens can be invalidated instantly
- **JWT ID tracking**: Each token has a unique identifier
- **Revocation list**: In-memory tracking of revoked tokens
- **Database integration**: Persistent revocation storage

#### Usage:
```python
# Revoke a token
key_manager.revoke_token(metadata.jti)

# Check if token is revoked
is_revoked = key_manager.is_token_revoked(metadata.jti)
```

### 5. Automatic Key Rotation

**Problem**: Static signing keys become security risks over time.

**Solution**: Automatic key rotation with file watcher support.

#### Features:
- **Scheduled rotation**: Keys rotate every 30 days
- **Grace period**: Old keys remain valid during transition
- **File watcher**: Real-time key updates
- **Backup keys**: Redundancy for high availability

#### Implementation:
```python
# Manual key rotation
new_key = key_manager.rotate_keys()

# File watcher (automatic)
key_manager = SecureKeyManager(enable_watcher=True)
# Keys automatically reload when file changes
```

## Configuration

### Key Management Configuration

Keys are stored in `~/.dart_planner/keys.json`:

```json
{
  "key_1703123456": {
    "key_id": "key_1703123456",
    "secret": "64_character_hex_string",
    "algorithm": "HS256",
    "created_at": "2023-12-21T10:30:56",
    "expires_at": "2024-01-20T10:30:56",
    "is_active": true,
    "usage_count": 1250,
    "max_usage": null
  },
  "backup_1703123456": {
    "key_id": "backup_1703123456",
    "secret": "64_character_hex_string",
    "algorithm": "HS256",
    "created_at": "2023-12-21T10:30:56",
    "expires_at": "2024-02-19T10:30:56",
    "is_active": true,
    "usage_count": 0,
    "max_usage": null
  }
}
```

### Environment Variables

For legacy compatibility:

```bash
# Legacy secret key (deprecated)
export DART_SECRET_KEY="your_legacy_secret_key"

# New key management (automatic)
# Keys are automatically managed in ~/.dart_planner/keys.json
```

## Testing Security Features

### Automated Test Suite

Run the comprehensive security test suite:

```bash
# Test all security features
python scripts/test_security_hardening.py

# Run E2E security tests
pytest tests/e2e/test_token_security_scenarios.py -v

# Test specific scenarios
pytest tests/e2e/test_token_security_scenarios.py::TestTokenSecurityScenarios::test_invalid_token_rejection -v
```

### Manual Testing

#### Test Key Rotation:
```python
from src.security.key_manager import get_key_manager

key_manager = get_key_manager()

# Check current keys
stats = key_manager.get_key_stats()
print(f"Active keys: {stats['active_keys']}")

# Rotate keys
new_key = key_manager.rotate_keys()
print(f"New primary key: {new_key.key_id}")
```

#### Test Token Expiration:
```python
# Create short-lived token
token, metadata = key_manager.create_jwt_token(
    payload={"sub": "test_user"},
    expires_in=timedelta(seconds=5)
)

# Verify token is valid
payload, _ = key_manager.verify_jwt_token(token)

# Wait for expiration
import time
time.sleep(6)

# Token should be expired
try:
    key_manager.verify_jwt_token(token)
except Exception as e:
    print(f"Token expired: {e}")
```

#### Test Token Revocation:
```python
# Create and revoke token
token, metadata = key_manager.create_jwt_token(
    payload={"sub": "test_user"}
)

# Revoke token
key_manager.revoke_token(metadata.jti)

# Verify revocation
assert key_manager.is_token_revoked(metadata.jti)
```

## Migration Guide

### From Legacy Environment Variables

1. **Backup existing tokens**: Export any active sessions
2. **Deploy new system**: Install updated DART-Planner
3. **Test migration**: Run security test suite
4. **Monitor**: Watch for any authentication issues
5. **Cleanup**: Remove legacy environment variables

### Gradual Rollout

1. **Phase 1**: Deploy with legacy fallback
2. **Phase 2**: Enable new key management
3. **Phase 3**: Reduce token lifetimes
4. **Phase 4**: Enable automatic rotation

## Security Best Practices

### Production Deployment

1. **Secure key storage**: Ensure `~/.dart_planner/keys.json` has restricted permissions
2. **Regular rotation**: Monitor key expiration and rotation
3. **Audit logging**: Log all authentication events
4. **Monitoring**: Alert on failed authentication attempts
5. **Backup**: Regularly backup key files

### Development

1. **Test tokens**: Use short-lived tokens for testing
2. **Mock authentication**: Use test keys for unit tests
3. **Security tests**: Run security test suite regularly
4. **Code review**: Review all authentication changes

### Monitoring

Monitor these security metrics:

- Failed authentication attempts
- Token revocation frequency
- Key rotation events
- Expired token usage attempts
- HMAC vs JWT token usage

## Troubleshooting

### Common Issues

#### Key Manager Initialization Failed
```bash
# Check permissions
ls -la ~/.dart_planner/keys.json

# Reinitialize keys
rm ~/.dart_planner/keys.json
python -m dart_planner_cli
```

#### Token Validation Errors
```python
# Check key rotation
key_manager = get_key_manager()
stats = key_manager.get_key_stats()
print(f"Active keys: {stats['active_keys']}")

# Verify token format
import jwt
header = jwt.get_unverified_header(token)
print(f"Token key ID: {header.get('kid')}")
```

#### File Watcher Not Working
```python
# Check file watcher status
key_manager = get_key_manager()
print(f"Watcher enabled: {key_manager.enable_watcher}")
print(f"Observer active: {key_manager.observer is not None}")
```

### Performance Considerations

- **Key lookup**: O(1) for active keys
- **Token verification**: O(1) for valid tokens
- **Revocation check**: O(1) for in-memory lookup
- **Key rotation**: Minimal impact with grace period

### Security Considerations

- **Key compromise**: Rotate keys immediately
- **Token theft**: Revoke compromised tokens
- **Brute force**: Rate limiting on authentication
- **Replay attacks**: JWT ID prevents reuse

## Future Enhancements

### Planned Features

1. **Hardware security modules**: TPM/HSM integration
2. **Distributed key management**: Multi-node key sharing
3. **Advanced revocation**: Bloom filters for efficiency
4. **Token introspection**: Real-time token validation
5. **OAuth2 integration**: Standard protocol support

### Research Areas

- **Post-quantum cryptography**: Future-proof algorithms
- **Zero-knowledge proofs**: Privacy-preserving authentication
- **Blockchain integration**: Decentralized identity management
- **Biometric authentication**: Multi-factor security

## References

- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [HMAC RFC 2104](https://tools.ietf.org/html/rfc2104)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-3/) 