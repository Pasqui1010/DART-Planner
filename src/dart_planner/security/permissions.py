"""
Centralized permission management for DART-Planner.

This module defines all permissions and role-based access control (RBAC)
mappings in a single location to eliminate duplication across the codebase.
"""

from enum import Enum
from typing import Dict, List, Set
from .auth import Role


# --- Permission Definitions ---
class Permission(str, Enum):
    """All available permissions in the system."""
    
    # User Management
    USER_CREATE = "user_create"
    USER_READ = "user_read"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_MANAGE_ROLES = "user_manage_roles"
    
    # System Configuration
    SYSTEM_CONFIG_READ = "system_config_read"
    SYSTEM_CONFIG_UPDATE = "system_config_update"
    SYSTEM_CONFIG_DELETE = "system_config_delete"
    
    # Flight Control
    FLIGHT_CONTROL_ARM = "flight_control_arm"
    FLIGHT_CONTROL_DISARM = "flight_control_disarm"
    FLIGHT_CONTROL_TAKEOFF = "flight_control_takeoff"
    FLIGHT_CONTROL_LAND = "flight_control_land"
    FLIGHT_CONTROL_EMERGENCY_STOP = "flight_control_emergency_stop"
    FLIGHT_CONTROL_SET_MODE = "flight_control_set_mode"
    FLIGHT_CONTROL_POSITION = "flight_control_position"
    FLIGHT_CONTROL_VELOCITY = "flight_control_velocity"
    FLIGHT_CONTROL_ATTITUDE = "flight_control_attitude"
    
    # Mission Planning
    MISSION_CREATE = "mission_create"
    MISSION_READ = "mission_read"
    MISSION_UPDATE = "mission_update"
    MISSION_DELETE = "mission_delete"
    MISSION_UPLOAD = "mission_upload"
    MISSION_START = "mission_start"
    MISSION_PAUSE = "mission_pause"
    MISSION_STOP = "mission_stop"
    
    # Monitoring and Logging
    TELEMETRY_READ = "telemetry_read"
    LOGS_READ = "logs_read"
    LOGS_WRITE = "logs_write"
    SYSTEM_STATUS_READ = "system_status_read"
    
    # Hardware Access
    HARDWARE_CONNECT = "hardware_connect"
    HARDWARE_DISCONNECT = "hardware_disconnect"
    HARDWARE_CONFIG_READ = "hardware_config_read"
    HARDWARE_CONFIG_UPDATE = "hardware_config_update"
    
    # Security
    SECURITY_AUDIT_READ = "security_audit_read"
    SECURITY_AUDIT_WRITE = "security_audit_write"
    SECURITY_KEYS_MANAGE = "security_keys_manage"


# --- Permission Sets by Role ---
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # User Management - Full access
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE_ROLES,
        
        # System Configuration - Full access
        Permission.SYSTEM_CONFIG_READ,
        Permission.SYSTEM_CONFIG_UPDATE,
        Permission.SYSTEM_CONFIG_DELETE,
        
        # Flight Control - Full access
        Permission.FLIGHT_CONTROL_ARM,
        Permission.FLIGHT_CONTROL_DISARM,
        Permission.FLIGHT_CONTROL_TAKEOFF,
        Permission.FLIGHT_CONTROL_LAND,
        Permission.FLIGHT_CONTROL_EMERGENCY_STOP,
        Permission.FLIGHT_CONTROL_SET_MODE,
        Permission.FLIGHT_CONTROL_POSITION,
        Permission.FLIGHT_CONTROL_VELOCITY,
        Permission.FLIGHT_CONTROL_ATTITUDE,
        
        # Mission Planning - Full access
        Permission.MISSION_CREATE,
        Permission.MISSION_READ,
        Permission.MISSION_UPDATE,
        Permission.MISSION_DELETE,
        Permission.MISSION_UPLOAD,
        Permission.MISSION_START,
        Permission.MISSION_PAUSE,
        Permission.MISSION_STOP,
        
        # Monitoring and Logging - Full access
        Permission.TELEMETRY_READ,
        Permission.LOGS_READ,
        Permission.LOGS_WRITE,
        Permission.SYSTEM_STATUS_READ,
        
        # Hardware Access - Full access
        Permission.HARDWARE_CONNECT,
        Permission.HARDWARE_DISCONNECT,
        Permission.HARDWARE_CONFIG_READ,
        Permission.HARDWARE_CONFIG_UPDATE,
        
        # Security - Full access
        Permission.SECURITY_AUDIT_READ,
        Permission.SECURITY_AUDIT_WRITE,
        Permission.SECURITY_KEYS_MANAGE,
    },
    
    Role.PILOT: {
        # Flight Control - Full access
        Permission.FLIGHT_CONTROL_ARM,
        Permission.FLIGHT_CONTROL_DISARM,
        Permission.FLIGHT_CONTROL_TAKEOFF,
        Permission.FLIGHT_CONTROL_LAND,
        Permission.FLIGHT_CONTROL_EMERGENCY_STOP,
        Permission.FLIGHT_CONTROL_SET_MODE,
        Permission.FLIGHT_CONTROL_POSITION,
        Permission.FLIGHT_CONTROL_VELOCITY,
        Permission.FLIGHT_CONTROL_ATTITUDE,
        
        # Mission Planning - Full access
        Permission.MISSION_CREATE,
        Permission.MISSION_READ,
        Permission.MISSION_UPDATE,
        Permission.MISSION_DELETE,
        Permission.MISSION_UPLOAD,
        Permission.MISSION_START,
        Permission.MISSION_PAUSE,
        Permission.MISSION_STOP,
        
        # Monitoring and Logging - Read access
        Permission.TELEMETRY_READ,
        Permission.LOGS_READ,
        Permission.SYSTEM_STATUS_READ,
        
        # Hardware Access - Connect only
        Permission.HARDWARE_CONNECT,
        Permission.HARDWARE_DISCONNECT,
        Permission.HARDWARE_CONFIG_READ,
    },
    
    Role.OPERATOR: {
        # Mission Planning - Full access
        Permission.MISSION_CREATE,
        Permission.MISSION_READ,
        Permission.MISSION_UPDATE,
        Permission.MISSION_DELETE,
        Permission.MISSION_UPLOAD,
        Permission.MISSION_START,
        Permission.MISSION_PAUSE,
        Permission.MISSION_STOP,
        
        # Emergency Control
        Permission.FLIGHT_CONTROL_EMERGENCY_STOP,
        
        # Monitoring and Logging - Read access
        Permission.TELEMETRY_READ,
        Permission.LOGS_READ,
        Permission.SYSTEM_STATUS_READ,
        
        # Hardware Access - Read only
        Permission.HARDWARE_CONFIG_READ,
    },
    
    Role.VIEWER: {
        # Monitoring and Logging - Read access only
        Permission.TELEMETRY_READ,
        Permission.SYSTEM_STATUS_READ,
        Permission.LOGS_READ,
    }
}


# --- Permission Groups for Convenience ---
PERMISSION_GROUPS: Dict[str, Set[Permission]] = {
    "user_management": {
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE_ROLES,
    },
    
    "system_configuration": {
        Permission.SYSTEM_CONFIG_READ,
        Permission.SYSTEM_CONFIG_UPDATE,
        Permission.SYSTEM_CONFIG_DELETE,
    },
    
    "flight_control": {
        Permission.FLIGHT_CONTROL_ARM,
        Permission.FLIGHT_CONTROL_DISARM,
        Permission.FLIGHT_CONTROL_TAKEOFF,
        Permission.FLIGHT_CONTROL_LAND,
        Permission.FLIGHT_CONTROL_EMERGENCY_STOP,
        Permission.FLIGHT_CONTROL_SET_MODE,
        Permission.FLIGHT_CONTROL_POSITION,
        Permission.FLIGHT_CONTROL_VELOCITY,
        Permission.FLIGHT_CONTROL_ATTITUDE,
    },
    
    "mission_planning": {
        Permission.MISSION_CREATE,
        Permission.MISSION_READ,
        Permission.MISSION_UPDATE,
        Permission.MISSION_DELETE,
        Permission.MISSION_UPLOAD,
        Permission.MISSION_START,
        Permission.MISSION_PAUSE,
        Permission.MISSION_STOP,
    },
    
    "monitoring": {
        Permission.TELEMETRY_READ,
        Permission.LOGS_READ,
        Permission.SYSTEM_STATUS_READ,
    },
    
    "hardware_access": {
        Permission.HARDWARE_CONNECT,
        Permission.HARDWARE_DISCONNECT,
        Permission.HARDWARE_CONFIG_READ,
        Permission.HARDWARE_CONFIG_UPDATE,
    },
    
    "security": {
        Permission.SECURITY_AUDIT_READ,
        Permission.SECURITY_AUDIT_WRITE,
        Permission.SECURITY_KEYS_MANAGE,
    }
}


# --- Helper Functions ---
def get_role_permissions(role: Role) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(role)


def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
    """Check if a role has any of the specified permissions."""
    role_permissions = get_role_permissions(role)
    return any(perm in role_permissions for perm in permissions)


def has_all_permissions(role: Role, permissions: List[Permission]) -> bool:
    """Check if a role has all of the specified permissions."""
    role_permissions = get_role_permissions(role)
    return all(perm in role_permissions for perm in permissions)


def get_permissions_by_group(group_name: str) -> Set[Permission]:
    """Get all permissions in a specific group."""
    return PERMISSION_GROUPS.get(group_name, set())


def get_roles_with_permission(permission: Permission) -> List[Role]:
    """Get all roles that have a specific permission."""
    return [
        role for role in Role
        if has_permission(role, permission)
    ]


# --- Legacy Compatibility ---
# Map old permission strings to new Permission enum values
LEGACY_PERMISSION_MAP = {
    "user_management": PERMISSION_GROUPS["user_management"],
    "system_configuration": PERMISSION_GROUPS["system_configuration"],
    "flight_control": PERMISSION_GROUPS["flight_control"],
    "mission_planning": PERMISSION_GROUPS["mission_planning"],
    "emergency_stop": {Permission.FLIGHT_CONTROL_EMERGENCY_STOP},
    "view_logs": {Permission.LOGS_READ},
    "view_telemetry": {Permission.TELEMETRY_READ},
}


def get_legacy_permissions(permission_string: str) -> Set[Permission]:
    """Get permissions for legacy permission string."""
    return LEGACY_PERMISSION_MAP.get(permission_string, set())


def has_legacy_permission(role: Role, permission_string: str) -> bool:
    """Check if role has legacy permission string."""
    legacy_permissions = get_legacy_permissions(permission_string)
    return has_any_permission(role, list(legacy_permissions)) 
