# DART-Planner Security Implementation

## Overview

This document describes the comprehensive security system implemented for DART-Planner, providing authentication, authorization, input validation, and secure credential management for autonomous drone operations.

## Security Architecture

### Core Components

1. **Authentication System** (`src/security/auth.py`)
   - Token-based authentication with JWT
   - Role-based access control (RBAC)
   - Session management with timeouts
   - Rate limiting and brute-force protection

2. **Input Validation System** (`src/security/validation.py`)
   - Comprehensive validation for all drone inputs
   - Safety limit enforcement
   - SQL injection and XSS prevention
   - Trajectory and waypoint validation

3. **Credential Management** (`src/security/crypto.py`)
   - AES-256 encrypted credential storage
   - Hardware interface credentials
   - API key management
   - Secure import/export capabilities

4. **Secure Hardware Interface** (`src/hardware/secure_hardware_interface.py`)
   - Authenticated hardware communication
   - Command audit logging
   - Emergency stop functionality
   - Permission-based command filtering

## Authentication Levels

The system implements five authentication levels with progressive privileges:

### PUBLIC (`public`)
- **Access**: Read-only status information
- **Permissions**: None
- **Use Case**: Public monitoring interfaces

### OPERATOR (`operator`)
- **Access**: Mission planning and monitoring
- **Permissions**: 
  - `mission_planning`: Create and modify flight plans
  - `sensor_access`: Read telemetry data
  - `emergency_stop`: Trigger emergency stop
- **Use Case**: Mission operators and supervisors

### PILOT (`pilot`)
- **Access**: Full flight control
- **Permissions**: 
  - All OPERATOR permissions plus:
  - `flight_control`: Direct drone control commands
- **Use Case**: Licensed drone pilots

### ADMIN (`admin`)
- **Access**: System configuration and user management
- **Permissions**: 
  - All PILOT permissions plus:
  - `system_config`: Modify system settings
  - `user_management`: Create/modify users
- **Use Case**: System administrators

### EMERGENCY (`emergency`)
- **Access**: Emergency override capabilities
- **Permissions**: Override all safety systems
- **Use Case**: Emergency situations only

## Default User Accounts

**⚠️ SECURITY WARNING**: Change these default passwords immediately in production!

| Username | Password | Level | Purpose |
|----------|----------|-------|---------|
| `pilot` | `dart_pilot_2025` | PILOT | Flight operations |
| `operator` | `dart_ops_2025` | OPERATOR | Mission planning |
| `admin` | `dart_admin_2025` | ADMIN | System administration |

## API Security

### Authentication Flow

1. **Login** (`POST /api/login`)
   ```json
   {
     "username": "pilot",
     "password": "dart_pilot_2025"
   }
   ```
   
   **Response**:
   ```json
   {
     "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
     "auth_level": "pilot",
     "permissions": {
       "flight_control": true,
       "mission_planning": true,
       "sensor_access": true,
       "emergency_stop": true
     },
     "expires_at": "2025-01-20T10:30:00Z"
   }
   ```

2. **Authenticated Requests**
   - Include token in `Authorization` header: `Bearer <token>`
   - Or pass as query parameter: `?token=<token>`

3. **Logout** (`POST /api/logout`)
   - Invalidates the current session token

### Protected Endpoints

| Endpoint | Method | Required Level | Permission |
|----------|--------|----------------|------------|
| `/api/status` | GET | OPERATOR | - |
| `/api/start_demo` | POST | PILOT | `flight_control` |
| `/api/stop_demo` | POST | OPERATOR | `emergency_stop` |
| `/api/set_target` | POST | OPERATOR | `mission_planning` |

## Input Validation

### Safety Limits

The system enforces comprehensive safety limits:

```python
class SafetyLimits:
    # Spatial limits (meters)
    max_altitude: float = 120.0      # AGL limit
    min_altitude: float = 0.5        # Ground clearance
    max_range: float = 1000.0        # Max distance from home
    
    # Velocity limits (m/s)
    max_horizontal_velocity: float = 15.0
    max_vertical_velocity: float = 10.0
    
    # Attitude limits (radians)
    max_roll: float = math.radians(45)
    max_pitch: float = math.radians(45)
```

### Validation Examples

**Waypoint Validation**:
```python
from security import validate_waypoint

waypoint = {
    "position": {"x": 10.0, "y": 5.0, "z": 2.0},
    "velocity": {"x": 2.0, "y": 1.0, "z": 0.5},
    "id": "wp_001"
}

validated = validate_waypoint(waypoint)
```

**Trajectory Validation**:
```python
from security import validate_trajectory

trajectory = [
    {"position": {"x": 0.0, "y": 0.0, "z": 1.0}},
    {"position": {"x": 5.0, "y": 0.0, "z": 1.0}},
    {"position": {"x": 10.0, "y": 5.0, "z": 2.0}}
]

validated = validate_trajectory(trajectory)
```

## Secure Credential Management

### Storing Credentials

```python
from security import SecureCredentialManager

cred_manager = SecureCredentialManager(master_password="secure_password")

# Store MAVLink connection
cred_manager.store_credential(
    name="mavlink_connection",
    value="serial:///dev/ttyUSB0:57600",
    credential_type="connection_string"
)

# Store API key with expiration
cred_manager.store_credential(
    name="weather_api_key",
    value="sk-1234567890abcdef",
    credential_type="api_key",
    expires_hours=24
)
```

### Retrieving Credentials

```python
# Get connection string
connection = cred_manager.get_credential("mavlink_connection")

# Get credential info without sensitive value
info = cred_manager.get_credential_info("weather_api_key")
print(info["expires_at"])
```

### Credential Rotation

```python
# Rotate API key
success = cred_manager.rotate_credential("weather_api_key", "new_key_value")

# Export credentials for backup
export_data = cred_manager.export_credentials("backup_password")

# Import credentials
cred_manager.import_credentials(export_data, "backup_password")
```

## Hardware Interface Security

### Secure Hardware Communication

```python
from hardware import create_secure_interface
from security import SecureCredentialManager, AuthManager

# Create secure interface
interface = create_secure_interface("mavlink", credential_manager)

# Authenticate hardware connection
session = auth_manager.authenticate("pilot", "password", "127.0.0.1")
success = interface.authenticate_hardware_connection(session)

# Send secure command
command = {
    "type": "position",
    "target": {"x": 10.0, "y": 5.0, "z": 2.0},
    "priority": 5
}

success = interface.send_secure_command(command, session)
```

### Emergency Stop System

```python
# Engage emergency stop (any authenticated user)
success = interface.emergency_stop(session)

# Disengage emergency stop (PILOT level required)
success = interface.disengage_emergency_stop(pilot_session)
```

### Command Audit Log

```python
# Get command audit log (ADMIN level required)
audit_log = interface.get_command_audit_log(admin_session, limit=50)

for entry in audit_log:
    print(f"{entry['timestamp']}: {entry['user_id']} -> {entry['command_type']}")
```

## Security Best Practices

### Production Deployment

1. **Change Default Passwords**
   ```python
   # Update default user passwords
   auth_manager.users["pilot"]["password_hash"] = auth_manager._hash_password("new_secure_password")
   ```

2. **Use Environment Variables for Secrets**
   ```python
   import os
   auth_manager = AuthManager(secret_key=os.environ["DART_SECRET_KEY"])
   ```

3. **Enable HTTPS**
   - Use TLS certificates for web interface
   - Encrypt all network communication

4. **Regular Security Audits**
   - Review command audit logs
   - Monitor failed authentication attempts
   - Rotate credentials regularly

### Rate Limiting

The system implements automatic rate limiting:
- 5 failed authentication attempts trigger IP lockout
- 15-minute lockout duration
- Exponential backoff for repeated violations

### Session Management

- 8-hour session timeout by default
- Automatic session cleanup
- Secure token generation using JWT

## Testing

### Running Security Tests

```bash
# Run all security tests
python -m pytest tests/test_security.py -v

# Run specific test class
python -m pytest tests/test_security.py::TestAuthManager -v

# Run with coverage
python -m pytest tests/test_security.py --cov=src/security
```

### Test Coverage

The security test suite covers:
- Authentication and authorization flows
- Input validation edge cases
- Credential encryption/decryption
- Hardware interface security
- Session management
- Emergency stop functionality

## Security Monitoring

### Logging

Security events are logged at appropriate levels:

```python
# Critical security events
logger.critical("Emergency stop engaged by user pilot")
logger.critical("Multiple failed authentication attempts from 192.168.1.100")

# Security warnings
logger.warning("User operator denied flight control access")
logger.warning("Command rejected due to safety limits")

# Security info
logger.info("User pilot authenticated successfully")
logger.info("Hardware connection established")
```

### Metrics

Monitor these security metrics:
- Failed authentication attempts per IP
- Command rejection rate due to safety limits
- Emergency stop frequency
- Session timeout events
- Credential rotation frequency

## Integration Examples

### Flask Web Application

```python
from flask import Flask
from security import AuthManager, require_auth, AuthLevel

app = Flask(__name__)
auth_manager = AuthManager()

@app.route("/api/control", methods=["POST"])
@require_auth(AuthLevel.PILOT, permission="flight_control")
def control_drone():
    # User is authenticated and authorized
    session = request.auth_session
    return jsonify({"user": session.user_id})
```

### Hardware Integration

```python
# Secure MAVLink communication
mavlink_interface = create_secure_interface("mavlink")
success = mavlink_interface.authenticate_hardware_connection(pilot_session)

# Send takeoff command
takeoff_cmd = {"type": "takeoff", "altitude": 10.0}
mavlink_interface.send_secure_command(takeoff_cmd, pilot_session)
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check username/password
   - Verify rate limiting status
   - Check session expiration

2. **Permission Denied**
   - Verify user authentication level
   - Check specific permission requirements
   - Review audit logs for details

3. **Validation Error**
   - Check input format and types
   - Verify safety limit compliance
   - Review error messages for specifics

4. **Hardware Connection Failed**
   - Verify stored credentials
   - Check hardware interface permissions
   - Review connection logs

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger("SecureHardwareInterface").setLevel(logging.DEBUG)
logging.getLogger("AuthManager").setLevel(logging.DEBUG)
```

## Security Updates

This security implementation follows industry best practices based on:

- [OWASP Top 10](https://owasp.org/www-project-top-ten/) security risks
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [RFC 7519](https://tools.ietf.org/html/rfc7519) for JWT implementation
- [Miguel Grinberg's Flask Security Guide](https://blog.miguelgrinberg.com/post/api-authentication-with-tokens) for token authentication patterns

Regular security updates and patches should be applied to maintain system security. 