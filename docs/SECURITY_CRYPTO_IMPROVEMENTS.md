# Security and Crypto Improvements

## Overview

This document summarizes the latest security improvements in DART-Planner:
- File integrity and authenticity verification (HMAC/SHA-256)
- Secure random number generation
- Modularized credential and key management

## File Verification

### HMAC and SHA-256
- All critical files can be verified using HMAC signatures and SHA-256 checksums.
- Use `FileVerificationManager` in `security/file_verification.py`.

#### Example
```python
from dart_planner.security.file_verification import FileVerificationManager
manager = FileVerificationManager(secret_key="my_secret")
manager.create_checksum("config.yaml")
manager.create_hmac("config.yaml", key_id="main")
assert manager.verify_file("config.yaml")
```

## Secure RNG
- All cryptographic operations use `secrets` for secure random bytes.
- No use of `random` for security-sensitive code.

## Credential and Key Management
- Credentials are managed via `SecureCredentialManager`.
- Keys are derived using PBKDF2 or OS keystore integration.
- Key material is wiped from memory after use.

## Secure File Utilities

- Use `secure_json_write`, `secure_json_read`, and `secure_binary_write` for all sensitive file operations.
- These utilities enforce strict file permissions (0600 for files, 0700 for directories) and validate against symlink attacks.

### Example
```python
from dart_planner.security.secure_file_utils import secure_json_write, secure_json_read
secure_json_write("secret.json", {"key": "value"})
data = secure_json_read("secret.json")
```

- Always validate file paths and permissions before reading or writing secrets.
- Never store secrets in world-readable files.

## Best Practices
- Always verify file integrity before loading sensitive configs or keys.
- Use environment variables for secrets.
- Rotate keys and credentials regularly. 