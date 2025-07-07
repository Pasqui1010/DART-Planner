# DART-Planner Admin Panel Usage Guide

This guide covers the usage of the DART-Planner admin panel for user management, system configuration, and monitoring.

## Table of Contents

1. [Accessing the Admin Panel](#accessing-the-admin-panel)
2. [User Management](#user-management)
3. [System Configuration](#system-configuration)
4. [Monitoring and Logs](#monitoring-and-logs)
5. [Security Features](#security-features)
6. [Troubleshooting](#troubleshooting)

## Accessing the Admin Panel

### Prerequisites

- Admin role permissions
- Valid authentication credentials
- Web browser with JavaScript enabled

### Login Process

1. Navigate to the DART-Planner web interface
2. Click on "Admin Panel" in the navigation menu
3. Enter your admin credentials:
   - Username: Your admin username
   - Password: Your admin password
4. Click "Login"

### Authentication

The admin panel uses JWT-based authentication with secure cookies. Sessions expire after 30 minutes of inactivity.

## User Management

### Viewing Users

1. Navigate to "User Management" section
2. View the list of all registered users
3. Information displayed includes:
   - User ID
   - Username
   - Role
   - Active status
   - Last login time

### Creating New Users

1. Click "Add User" button
2. Fill in the required information:
   - **Username**: 3-50 characters, alphanumeric
   - **Password**: Minimum 8 characters
   - **Role**: Select from available roles
   - **Active Status**: Enable/disable user account
3. Click "Create User"

### Available Roles

- **Admin**: Full system access
- **Pilot**: Flight control and mission planning
- **Operator**: Mission planning and monitoring
- **Viewer**: Read-only access to telemetry

### Editing Users

1. Click on a user in the user list
2. Modify the desired fields:
   - Username
   - Password (optional)
   - Role
   - Active status
3. Click "Update User"

### Deleting Users

1. Select a user from the list
2. Click "Delete User"
3. Confirm the deletion

**Warning**: Deleting a user is permanent and cannot be undone.

## System Configuration

### Airframe Configuration

1. Navigate to "System Configuration" → "Airframe"
2. Select from available airframe types:
   - Generic Quadcopter
   - DJI F450/F550
   - Racing Drone
   - Heavy Lift Hexacopter
   - Indoor Micro Drone
   - Fixed-Wing Aircraft
   - VTOL Aircraft

3. Configure airframe-specific parameters:
   - Physical parameters (mass, dimensions)
   - Motor and propeller limits
   - Flight envelope constraints
   - Safety limits
   - Control parameters

### Control Parameters

Adjust control gains for optimal performance:

- **Position Control (Kp)**: [x, y, z] gains for position tracking
- **Velocity Control (Kp)**: [x, y, z] gains for velocity tracking
- **Attitude Control (Kp)**: [roll, pitch, yaw] proportional gains
- **Attitude Control (Kd)**: [roll, pitch, yaw] derivative gains

### Safety Limits

Configure safety parameters:

- **Maximum Altitude**: Highest allowed flight altitude
- **Minimum Altitude**: Lowest allowed flight altitude
- **Maximum Distance**: Maximum distance from takeoff point
- **Maximum Velocity**: Maximum allowed velocity
- **Maximum Acceleration**: Maximum allowed acceleration

## Monitoring and Logs

### Real-time Telemetry

1. Navigate to "Monitoring" → "Telemetry"
2. View real-time data:
   - Position (x, y, z)
   - Velocity (vx, vy, vz)
   - Attitude (roll, pitch, yaw)
   - Battery level
   - GPS status
   - System health

### System Logs

1. Navigate to "Monitoring" → "Logs"
2. Filter logs by:
   - Date range
   - Log level (DEBUG, INFO, WARNING, ERROR)
   - Component (controller, planner, hardware)
   - User actions

3. Export logs for analysis:
   - CSV format for data analysis
   - JSON format for programmatic access
   - PDF format for reports

### Performance Metrics

Monitor system performance:

- **Control Loop Frequency**: Actual vs. target frequency
- **Position Tracking Error**: RMS position error
- **Velocity Tracking Error**: RMS velocity error
- **Attitude Tracking Error**: RMS attitude error
- **Battery Efficiency**: Power consumption vs. flight time

## Security Features

### Authentication

- JWT-based token authentication
- Secure cookie storage
- Automatic session expiration
- Rate limiting on login attempts

### Authorization

- Role-based access control (RBAC)
- Permission-based endpoint protection
- Audit logging of all admin actions

### Audit Trail

All admin actions are logged with:
- Timestamp
- User ID
- Action performed
- Target resource
- IP address
- User agent

### Security Best Practices

1. **Password Policy**: Enforce strong passwords
2. **Session Management**: Regular session rotation
3. **Access Control**: Principle of least privilege
4. **Monitoring**: Regular security audits
5. **Updates**: Keep system updated

## Troubleshooting

### Common Issues

#### Login Problems

**Issue**: Cannot log in to admin panel
**Solutions**:
1. Verify username and password
2. Check if account is active
3. Clear browser cookies
4. Check for rate limiting

#### Permission Errors

**Issue**: "Operation not permitted" errors
**Solutions**:
1. Verify user has required role
2. Check specific permissions
3. Contact system administrator

#### Configuration Issues

**Issue**: Airframe configuration not applying
**Solutions**:
1. Validate configuration parameters
2. Check for syntax errors in YAML
3. Restart the system
4. Check configuration file permissions

#### Performance Issues

**Issue**: Slow admin panel response
**Solutions**:
1. Check system resources
2. Review log files for errors
3. Optimize database queries
4. Check network connectivity

### Error Messages

| Error Code | Description | Solution |
|------------|-------------|----------|
| 401 | Unauthorized | Check credentials and session |
| 403 | Forbidden | Verify user permissions |
| 422 | Validation Error | Check input data format |
| 500 | Internal Server Error | Check server logs |

### Getting Help

1. **Documentation**: Check this guide and API documentation
2. **Logs**: Review system logs for detailed error information
3. **Support**: Contact the development team with:
   - Error message
   - Steps to reproduce
   - System configuration
   - Log files

## API Reference

### User Management Endpoints

```
GET    /api/admin/users          # List all users
POST   /api/admin/users          # Create new user
PUT    /api/admin/users/{id}     # Update user
DELETE /api/admin/users/{id}     # Delete user
GET    /api/admin/roles          # List available roles
```

### System Configuration Endpoints

```
GET    /api/admin/config/airframe     # Get airframe config
PUT    /api/admin/config/airframe     # Update airframe config
GET    /api/admin/config/validate     # Validate configuration
```

### Monitoring Endpoints

```
GET    /api/admin/telemetry           # Get real-time telemetry
GET    /api/admin/logs               # Get system logs
GET    /api/admin/metrics            # Get performance metrics
```

### Authentication Endpoints

```
POST   /api/login                    # User login
POST   /api/logout                   # User logout
GET    /api/me                       # Get current user info
```

## Best Practices

### User Management

1. **Regular Audits**: Review user accounts regularly
2. **Role Assignment**: Assign minimal required permissions
3. **Password Policy**: Enforce strong password requirements
4. **Account Cleanup**: Remove inactive accounts

### Configuration Management

1. **Backup Configurations**: Keep backups of working configurations
2. **Test Changes**: Test configuration changes in simulation first
3. **Documentation**: Document custom configurations
4. **Validation**: Always validate configurations before applying

### Security

1. **Regular Updates**: Keep system and dependencies updated
2. **Access Monitoring**: Monitor admin panel access
3. **Incident Response**: Have a plan for security incidents
4. **Training**: Train users on security best practices

### Performance

1. **Resource Monitoring**: Monitor system resources
2. **Optimization**: Optimize database queries and API calls
3. **Caching**: Use caching for frequently accessed data
4. **Load Testing**: Test system under expected load 