"""
Credential Helper Functions for DART-Planner Security

Provides utility functions for storing specific types of credentials:
- MAVLink connection credentials
- API credentials
- Database credentials
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from .credential_manager import SecureCredentialManager

logger = logging.getLogger(__name__)


def store_mavlink_credentials(cred_manager: SecureCredentialManager,
                             connection_string: str,
                             auth_token: Optional[str] = None) -> None:
    """
    Store MAVLink connection credentials
    
    Args:
        cred_manager: Credential manager instance
        connection_string: MAVLink connection string (e.g., "udp://192.168.1.100:14550")
        auth_token: Optional authentication token
    """
    # Store connection string
    cred_manager.store_credential(
        name="mavlink_connection",
        value=connection_string,
        credential_type="mavlink_connection",
        metadata={
            "protocol": connection_string.split("://")[0] if "://" in connection_string else "unknown",
            "stored_at": datetime.now().isoformat()
        }
    )
    
    # Store auth token if provided
    if auth_token:
        cred_manager.store_credential(
            name="mavlink_auth_token",
            value=auth_token,
            credential_type="mavlink_auth",
            expires_hours=24,  # Auth tokens typically expire quickly
            metadata={
                "connection": connection_string,
                "stored_at": datetime.now().isoformat()
            }
        )
    
    logger.info(f"Stored MAVLink credentials for: {connection_string}")


def store_api_credentials(cred_manager: SecureCredentialManager,
                         service_name: str,
                         api_key: str,
                         api_secret: Optional[str] = None) -> None:
    """
    Store API credentials
    
    Args:
        cred_manager: Credential manager instance
        service_name: Name of the API service (e.g., "airsim", "pixhawk")
        api_key: API key
        api_secret: Optional API secret
    """
    # Store API key
    cred_manager.store_credential(
        name=f"{service_name}_api_key",
        value=api_key,
        credential_type="api_key",
        metadata={
            "service": service_name,
            "stored_at": datetime.now().isoformat()
        }
    )
    
    # Store API secret if provided
    if api_secret:
        cred_manager.store_credential(
            name=f"{service_name}_api_secret",
            value=api_secret,
            credential_type="api_secret",
            expires_hours=8760,  # 1 year
            metadata={
                "service": service_name,
                "api_key_name": f"{service_name}_api_key",
                "stored_at": datetime.now().isoformat()
            }
        )
    
    logger.info(f"Stored API credentials for service: {service_name}")


def store_database_credentials(cred_manager: SecureCredentialManager,
                              db_name: str,
                              username: str,
                              password: str,
                              host: str = "localhost",
                              port: int = 5432) -> None:
    """
    Store database credentials
    
    Args:
        cred_manager: Credential manager instance
        db_name: Database name
        username: Database username
        password: Database password
        host: Database host
        port: Database port
    """
    # Store database password
    cred_manager.store_credential(
        name=f"{db_name}_db_password",
        value=password,
        credential_type="database_password",
        metadata={
            "database": db_name,
            "username": username,
            "host": host,
            "port": port,
            "stored_at": datetime.now().isoformat()
        }
    )
    
    # Store connection string (without password)
    connection_string = f"postgresql://{username}@{host}:{port}/{db_name}"
    cred_manager.store_credential(
        name=f"{db_name}_db_connection",
        value=connection_string,
        credential_type="database_connection",
        metadata={
            "database": db_name,
            "host": host,
            "port": port,
            "stored_at": datetime.now().isoformat()
        }
    )
    
    logger.info(f"Stored database credentials for: {db_name}@{host}:{port}")


def store_jwt_credentials(cred_manager: SecureCredentialManager,
                         secret_key: str,
                         algorithm: str = "HS256",
                         expires_hours: int = 8760) -> None:
    """
    Store JWT credentials
    
    Args:
        cred_manager: Credential manager instance
        secret_key: JWT secret key
        algorithm: JWT algorithm
        expires_hours: Hours until expiry
    """
    cred_manager.store_credential(
        name="jwt_secret_key",
        value=secret_key,
        credential_type="jwt_secret",
        expires_hours=expires_hours,
        metadata={
            "algorithm": algorithm,
            "stored_at": datetime.now().isoformat()
        }
    )
    
    logger.info(f"Stored JWT credentials with algorithm: {algorithm}")


def store_ssl_credentials(cred_manager: SecureCredentialManager,
                         cert_file: str,
                         key_file: str,
                         ca_file: Optional[str] = None) -> None:
    """
    Store SSL certificate credentials
    
    Args:
        cred_manager: Credential manager instance
        cert_file: Path to certificate file
        key_file: Path to private key file
        ca_file: Optional path to CA certificate file
    """
    # Read and store certificate
    try:
        with open(cert_file, 'r') as f:
            cert_data = f.read()
        
        cred_manager.store_credential(
            name="ssl_certificate",
            value=cert_data,
            credential_type="ssl_cert",
            metadata={
                "cert_file": cert_file,
                "stored_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Failed to read certificate file {cert_file}: {e}")
        return
    
    # Read and store private key
    try:
        with open(key_file, 'r') as f:
            key_data = f.read()
        
        cred_manager.store_credential(
            name="ssl_private_key",
            value=key_data,
            credential_type="ssl_key",
            metadata={
                "key_file": key_file,
                "stored_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Failed to read private key file {key_file}: {e}")
        return
    
    # Read and store CA certificate if provided
    if ca_file:
        try:
            with open(ca_file, 'r') as f:
                ca_data = f.read()
            
            cred_manager.store_credential(
                name="ssl_ca_certificate",
                value=ca_data,
                credential_type="ssl_ca",
                metadata={
                    "ca_file": ca_file,
                    "stored_at": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to read CA certificate file {ca_file}: {e}")
    
    logger.info(f"Stored SSL credentials from: {cert_file}, {key_file}")


def get_mavlink_credentials(cred_manager: SecureCredentialManager) -> Optional[tuple[str, Optional[str]]]:
    """
    Get MAVLink credentials
    
    Args:
        cred_manager: Credential manager instance
        
    Returns:
        Tuple of (connection_string, auth_token) or None if not found
    """
    connection_string = cred_manager.get_credential("mavlink_connection")
    auth_token = cred_manager.get_credential("mavlink_auth_token")
    
    if connection_string:
        return connection_string, auth_token
    return None


def get_api_credentials(cred_manager: SecureCredentialManager, service_name: str) -> Optional[tuple[str, Optional[str]]]:
    """
    Get API credentials for a service
    
    Args:
        cred_manager: Credential manager instance
        service_name: Name of the API service
        
    Returns:
        Tuple of (api_key, api_secret) or None if not found
    """
    api_key = cred_manager.get_credential(f"{service_name}_api_key")
    api_secret = cred_manager.get_credential(f"{service_name}_api_secret")
    
    if api_key:
        return api_key, api_secret
    return None


def get_database_credentials(cred_manager: SecureCredentialManager, db_name: str) -> Optional[tuple[str, str, str, int]]:
    """
    Get database credentials
    
    Args:
        cred_manager: Credential manager instance
        db_name: Database name
        
    Returns:
        Tuple of (username, password, host, port) or None if not found
    """
    password = cred_manager.get_credential(f"{db_name}_db_password")
    connection_info = cred_manager.get_credential_info(f"{db_name}_db_connection")
    
    if password and connection_info:
        metadata = connection_info.get('metadata', {})
        username = metadata.get('username', '')
        host = metadata.get('host', 'localhost')
        port = metadata.get('port', 5432)
        return username, password, host, port
    
    return None


def get_jwt_credentials(cred_manager: SecureCredentialManager) -> Optional[tuple[str, str]]:
    """
    Get JWT credentials
    
    Args:
        cred_manager: Credential manager instance
        
    Returns:
        Tuple of (secret_key, algorithm) or None if not found
    """
    secret_key = cred_manager.get_credential("jwt_secret_key")
    secret_info = cred_manager.get_credential_info("jwt_secret_key")
    
    if secret_key and secret_info:
        algorithm = secret_info.get('metadata', {}).get('algorithm', 'HS256')
        return secret_key, algorithm
    
    return None


def rotate_api_credentials(cred_manager: SecureCredentialManager,
                          service_name: str,
                          new_api_key: str,
                          new_api_secret: Optional[str] = None) -> bool:
    """
    Rotate API credentials for a service
    
    Args:
        cred_manager: Credential manager instance
        service_name: Name of the API service
        new_api_key: New API key
        new_api_secret: Optional new API secret
        
    Returns:
        True if rotation was successful
    """
    success = True
    
    # Rotate API key
    if not cred_manager.rotate_credential(f"{service_name}_api_key", new_api_key):
        success = False
    
    # Rotate API secret if provided
    if new_api_secret:
        if not cred_manager.rotate_credential(f"{service_name}_api_secret", new_api_secret):
            success = False
    
    if success:
        logger.info(f"Rotated API credentials for service: {service_name}")
    else:
        logger.error(f"Failed to rotate API credentials for service: {service_name}")
    
    return success


def cleanup_expired_credentials(cred_manager: SecureCredentialManager) -> int:
    """
    Clean up expired credentials and log summary
    
    Args:
        cred_manager: Credential manager instance
        
    Returns:
        Number of credentials removed
    """
    removed_count = cred_manager.cleanup_expired()
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} expired credentials")
    else:
        logger.debug("No expired credentials found")
    
    return removed_count


def list_credential_summary(cred_manager: SecureCredentialManager) -> dict:
    """
    Get a summary of stored credentials
    
    Args:
        cred_manager: Credential manager instance
        
    Returns:
        Dictionary with credential summary
    """
    credentials = cred_manager.list_credentials()
    
    summary = {
        "total_credentials": len(credentials),
        "by_type": {},
        "expiring_soon": [],
        "expired": []
    }
    
    for name, info in credentials.items():
        if info is None:
            continue
            
        cred_type = info.get('credential_type', 'unknown')
        if cred_type not in summary["by_type"]:
            summary["by_type"][cred_type] = 0
        summary["by_type"][cred_type] += 1
        
        # Check expiration
        if info.get('expires_at'):
            days_until_expiry = info.get('days_until_expiry', 0)
            if days_until_expiry < 0:
                summary["expired"].append(name)
            elif days_until_expiry <= 7:  # Expiring within a week
                summary["expiring_soon"].append(name)
    
    return summary 