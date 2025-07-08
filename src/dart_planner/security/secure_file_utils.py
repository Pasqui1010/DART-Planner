"""
Secure File Utilities for DART-Planner

Provides secure file operations for sensitive data like cryptographic keys,
ensuring proper file permissions and symlink validation.
"""

import os
import stat
import logging
from pathlib import Path
from typing import Optional, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


def validate_path_security(file_path: Union[str, Path]) -> None:
    """
    Validate that a file path is secure for storing sensitive data.
    
    Args:
        file_path: Path to validate
        
    Raises:
        SecurityError: If path is not secure
    """
    file_path = Path(file_path)
    
    # Check if path is a symlink
    if file_path.is_symlink():
        raise SecurityError(f"Path {file_path} is a symlink - not allowed for sensitive data")
    
    # Check parent directory
    parent_dir = file_path.parent
    if parent_dir.exists():
        # Check if parent directory is a symlink
        if parent_dir.is_symlink():
            raise SecurityError(f"Parent directory {parent_dir} is a symlink - not allowed for sensitive data")
        
        # Check parent directory permissions (should be 700 or stricter)
        parent_mode = stat.S_IMODE(parent_dir.stat().st_mode)
        if parent_mode & stat.S_IRWXG or parent_mode & stat.S_IRWXO:
            logger.warning(f"Parent directory {parent_dir} has loose permissions: {oct(parent_mode)}")
    
    # If file exists, check its permissions
    if file_path.exists():
        file_mode = stat.S_IMODE(file_path.stat().st_mode)
        if file_mode & stat.S_IRWXG or file_mode & stat.S_IRWXO:
            logger.warning(f"File {file_path} has loose permissions: {oct(file_mode)}")


def set_secure_permissions(file_path: Union[str, Path], 
                          file_perms: int = 0o600,
                          dir_perms: int = 0o700) -> None:
    """
    Set secure permissions on a file and its parent directory.
    
    Args:
        file_path: Path to the file
        file_perms: File permissions (default: 0o600 - owner read/write only)
        dir_perms: Directory permissions (default: 0o700 - owner read/write/execute only)
    """
    file_path = Path(file_path)
    
    # Set parent directory permissions
    parent_dir = file_path.parent
    if parent_dir.exists():
        try:
            os.chmod(parent_dir, dir_perms)
            logger.debug(f"Set directory permissions {oct(dir_perms)} on {parent_dir}")
        except OSError as e:
            logger.warning(f"Failed to set directory permissions on {parent_dir}: {e}")
    
    # Set file permissions
    if file_path.exists():
        try:
            os.chmod(file_path, file_perms)
            logger.debug(f"Set file permissions {oct(file_perms)} on {file_path}")
        except OSError as e:
            logger.warning(f"Failed to set file permissions on {file_path}: {e}")


def create_secure_directory(dir_path: Union[str, Path], 
                           perms: int = 0o700) -> Path:
    """
    Create a directory with secure permissions.
    
    Args:
        dir_path: Path to create
        perms: Directory permissions (default: 0o700)
        
    Returns:
        Path object for the created directory
    """
    dir_path = Path(dir_path)
    
    # Create directory if it doesn't exist
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory {dir_path}")
    
    # Validate security
    validate_path_security(dir_path)
    
    # Set secure permissions
    set_secure_permissions(dir_path, dir_perms=perms)
    
    return dir_path


@contextmanager
def secure_file_write(file_path: Union[str, Path], 
                     file_perms: int = 0o600,
                     dir_perms: int = 0o700,
                     validate_security: bool = True):
    """
    Context manager for secure file writing.
    
    Creates the file with secure permissions and validates the path.
    
    Args:
        file_path: Path to the file
        file_perms: File permissions (default: 0o600)
        dir_perms: Directory permissions (default: 0o700)
        validate_security: Whether to validate path security
        
    Yields:
        File object for writing
        
    Raises:
        SecurityError: If path validation fails
    """
    file_path = Path(file_path)
    
    # Validate path security if requested
    if validate_security:
        validate_path_security(file_path)
    
    # Ensure parent directory exists with secure permissions
    parent_dir = file_path.parent
    if not parent_dir.exists():
        create_secure_directory(parent_dir, dir_perms)
    
    # Open file for writing
    with open(file_path, 'w') as f:
        yield f
    
    # Set secure permissions after writing
    set_secure_permissions(file_path, file_perms, dir_perms)
    
    logger.debug(f"Securely wrote file {file_path} with permissions {oct(file_perms)}")


@contextmanager
def secure_file_read(file_path: Union[str, Path], 
                    validate_security: bool = True):
    """
    Context manager for secure file reading.
    
    Validates the path security before reading.
    
    Args:
        file_path: Path to the file
        validate_security: Whether to validate path security
        
    Yields:
        File object for reading
        
    Raises:
        SecurityError: If path validation fails
    """
    file_path = Path(file_path)
    
    # Validate path security if requested
    if validate_security:
        validate_path_security(file_path)
    
    # Open file for reading
    with open(file_path, 'r') as f:
        yield f


def secure_json_write(file_path: Union[str, Path], 
                     data: dict,
                     file_perms: int = 0o600,
                     dir_perms: int = 0o700,
                     validate_security: bool = True) -> None:
    """
    Securely write JSON data to a file.
    
    Args:
        file_path: Path to the file
        data: Data to write
        file_perms: File permissions (default: 0o600)
        dir_perms: Directory permissions (default: 0o700)
        validate_security: Whether to validate path security
    """
    import json
    
    with secure_file_write(file_path, file_perms, dir_perms, validate_security) as f:
        json.dump(data, f, indent=2, default=str)


def secure_json_read(file_path: Union[str, Path],
                    validate_security: bool = True) -> dict:
    """
    Securely read JSON data from a file.
    
    Args:
        file_path: Path to the file
        validate_security: Whether to validate path security
        
    Returns:
        Dictionary containing the JSON data
    """
    import json
    
    with secure_file_read(file_path, validate_security) as f:
        return json.load(f)


def secure_binary_write(file_path: Union[str, Path], 
                       data: bytes,
                       file_perms: int = 0o600,
                       dir_perms: int = 0o700,
                       validate_security: bool = True) -> None:
    """
    Securely write binary data to a file.
    
    Args:
        file_path: Path to the file
        data: Binary data to write
        file_perms: File permissions (default: 0o600)
        dir_perms: Directory permissions (default: 0o700)
        validate_security: Whether to validate path security
    """
    file_path = Path(file_path)
    
    # Validate path security if requested
    if validate_security:
        validate_path_security(file_path)
    
    # Ensure parent directory exists with secure permissions
    parent_dir = file_path.parent
    if not parent_dir.exists():
        create_secure_directory(parent_dir, dir_perms)
    
    # Write binary data
    with open(file_path, 'wb') as f:
        f.write(data)
    
    # Set secure permissions after writing
    set_secure_permissions(file_path, file_perms, dir_perms)
    
    logger.debug(f"Securely wrote binary file {file_path} with permissions {oct(file_perms)}")


def secure_binary_read(file_path: Union[str, Path],
                      validate_security: bool = True) -> bytes:
    """
    Securely read binary data from a file.
    
    Args:
        file_path: Path to the file
        validate_security: Whether to validate path security
        
    Returns:
        Binary data from the file
    """
    file_path = Path(file_path)
    
    # Validate path security if requested
    if validate_security:
        validate_path_security(file_path)
    
    # Read binary data
    with open(file_path, 'rb') as f:
        return f.read()


def check_file_security(file_path: Union[str, Path]) -> dict:
    """
    Check the security status of a file.
    
    Args:
        file_path: Path to check
        
    Returns:
        Dictionary with security information
    """
    file_path = Path(file_path)
    
    security_info = {
        "path": str(file_path),
        "exists": file_path.exists(),
        "is_symlink": False,
        "parent_is_symlink": False,
        "file_permissions": None,
        "parent_permissions": None,
        "secure": True,
        "issues": []
    }
    
    if not file_path.exists():
        security_info["secure"] = False
        security_info["issues"].append("File does not exist")
        return security_info
    
    # Check if file is a symlink
    if file_path.is_symlink():
        security_info["is_symlink"] = True
        security_info["secure"] = False
        security_info["issues"].append("File is a symlink")
    
    # Check parent directory
    parent_dir = file_path.parent
    if parent_dir.exists():
        if parent_dir.is_symlink():
            security_info["parent_is_symlink"] = True
            security_info["secure"] = False
            security_info["issues"].append("Parent directory is a symlink")
        
        # Check parent permissions
        try:
            parent_mode = stat.S_IMODE(parent_dir.stat().st_mode)
            security_info["parent_permissions"] = oct(parent_mode)
            if parent_mode & stat.S_IRWXG or parent_mode & stat.S_IRWXO:
                security_info["secure"] = False
                security_info["issues"].append("Parent directory has loose permissions")
        except OSError as e:
            security_info["issues"].append(f"Cannot check parent permissions: {e}")
    
    # Check file permissions
    try:
        file_mode = stat.S_IMODE(file_path.stat().st_mode)
        security_info["file_permissions"] = oct(file_mode)
        if file_mode & stat.S_IRWXG or file_mode & stat.S_IRWXO:
            security_info["secure"] = False
            security_info["issues"].append("File has loose permissions")
    except OSError as e:
        security_info["issues"].append(f"Cannot check file permissions: {e}")
    
    return security_info


def secure_backup_file(file_path: Union[str, Path],
                      backup_suffix: str = ".backup") -> Optional[Path]:
    """
    Create a secure backup of a file.
    
    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix for the backup file
        
    Returns:
        Path to the backup file, or None if backup failed
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"Cannot backup non-existent file: {file_path}")
        return None
    
    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)
    
    try:
        # Read the original file
        data = secure_binary_read(file_path)
        
        # Write to backup location with secure permissions
        secure_binary_write(backup_path, data)
        
        logger.info(f"Created secure backup: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return None 