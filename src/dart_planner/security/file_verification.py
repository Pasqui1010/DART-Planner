"""
File Verification Module for DART-Planner

Provides secure file verification using HMAC and SHA-256 checksums.
This module ensures file integrity and authenticity for critical system files.
"""

import os
import hashlib
import hmac
import json
import base64
import secrets
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

from .secure_file_utils import SecurityError, secure_json_read, secure_json_write

logger = logging.getLogger(__name__)

# Security constants
HMAC_ALGORITHM = hashlib.sha256
CHECKSUM_ALGORITHM = hashlib.sha256
VERIFICATION_FILE = "file_verification.json"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max file size for verification


@dataclass
class FileChecksum:
    """Represents a file checksum with metadata."""
    file_path: str
    checksum: str
    algorithm: str
    file_size: int
    last_modified: float
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'FileChecksum':
        """Create from dictionary."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


@dataclass
class FileHMAC:
    """Represents a file HMAC signature with metadata."""
    file_path: str
    hmac_signature: str
    key_id: str
    algorithm: str
    file_size: int
    last_modified: float
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'FileHMAC':
        """Create from dictionary."""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('expires_at'):
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class FileVerificationManager:
    """
    Manages file verification using HMAC and SHA-256 checksums.
    
    Features:
    - SHA-256 checksum verification for file integrity
    - HMAC signature verification for file authenticity
    - Automatic checksum expiration and rotation
    - Secure storage of verification data
    """
    
    def __init__(self, 
                 verification_dir: Optional[Path] = None,
                 secret_key: Optional[str] = None,
                 max_file_size: int = MAX_FILE_SIZE):
        """
        Initialize the file verification manager.
        
        Args:
            verification_dir: Directory to store verification data
            secret_key: Secret key for HMAC signatures
            max_file_size: Maximum file size for verification
        """
        self.verification_dir = verification_dir or Path("security/verification")
        self.verification_dir.mkdir(parents=True, exist_ok=True)
        
        # Get secret key from environment or use default
        self.secret_key = secret_key or os.getenv("DART_FILE_VERIFICATION_KEY")
        if not self.secret_key:
            logger.warning("No file verification key provided, using default")
            self.secret_key = "default_file_verification_key_2025"
        
        self.max_file_size = max_file_size
        self.verification_file = self.verification_dir / VERIFICATION_FILE
        
        # Load existing verification data
        self.checksums: Dict[str, FileChecksum] = {}
        self.hmacs: Dict[str, FileHMAC] = {}
        self._load_verification_data()
    
    def _load_verification_data(self) -> None:
        """Load verification data from storage."""
        try:
            if self.verification_file.exists():
                data = secure_json_read(self.verification_file)
                
                # Load checksums
                for file_path, checksum_data in data.get('checksums', {}).items():
                    self.checksums[file_path] = FileChecksum.from_dict(checksum_data)
                
                # Load HMACs
                for file_path, hmac_data in data.get('hmacs', {}).items():
                    self.hmacs[file_path] = FileHMAC.from_dict(hmac_data)
                
                logger.info(f"Loaded verification data for {len(self.checksums)} checksums and {len(self.hmacs)} HMACs")
        except Exception as e:
            logger.warning(f"Failed to load verification data: {e}")
    
    def _save_verification_data(self) -> None:
        """Save verification data to storage."""
        try:
            data = {
                'checksums': {path: checksum.to_dict() for path, checksum in self.checksums.items()},
                'hmacs': {path: hmac.to_dict() for path, hmac in self.hmacs.items()},
                'last_updated': datetime.utcnow().isoformat()
            }
            secure_json_write(self.verification_file, data)
            logger.debug("Verification data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save verification data: {e}")
            raise SecurityError(f"Failed to save verification data: {e}")
    
    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA-256 checksum of a file."""
        if not file_path.exists():
            raise SecurityError(f"File does not exist: {file_path}")
        
        if file_path.stat().st_size > self.max_file_size:
            raise SecurityError(f"File too large for verification: {file_path}")
        
        hash_sha256 = CHECKSUM_ALGORITHM()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _compute_hmac(self, file_path: Path, key_id: str) -> str:
        """Compute HMAC signature of a file."""
        if not file_path.exists():
            raise SecurityError(f"File does not exist: {file_path}")
        
        if file_path.stat().st_size > self.max_file_size:
            raise SecurityError(f"File too large for verification: {file_path}")
        
        # Create HMAC object
        hmac_obj = hmac.new(
            self.secret_key.encode('utf-8'),
            digestmod=HMAC_ALGORITHM
        )
        
        # Update with file content
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hmac_obj.update(chunk)
        
        # Add key_id to prevent key reuse
        hmac_obj.update(key_id.encode('utf-8'))
        
        return hmac_obj.hexdigest()
    
    def _get_file_metadata(self, file_path: Path) -> Tuple[int, float]:
        """Get file metadata."""
        stat = file_path.stat()
        return stat.st_size, stat.st_mtime
    
    def create_checksum(self, 
                       file_path: Union[str, Path], 
                       expires_in: Optional[timedelta] = None) -> FileChecksum:
        """
        Create SHA-256 checksum for a file.
        
        Args:
            file_path: Path to the file
            expires_in: Optional expiration time
            
        Returns:
            FileChecksum object
        """
        file_path = Path(file_path)
        file_size, last_modified = self._get_file_metadata(file_path)
        checksum = self._compute_checksum(file_path)
        
        created_at = datetime.utcnow()
        expires_at = None
        if expires_in:
            expires_at = created_at + expires_in
        
        file_checksum = FileChecksum(
            file_path=str(file_path),
            checksum=checksum,
            algorithm=CHECKSUM_ALGORITHM.__name__,
            file_size=file_size,
            last_modified=last_modified,
            created_at=created_at,
            expires_at=expires_at
        )
        
        self.checksums[str(file_path)] = file_checksum
        self._save_verification_data()
        
        logger.info(f"Created checksum for {file_path}")
        return file_checksum
    
    def create_hmac(self, 
                   file_path: Union[str, Path], 
                   key_id: Optional[str] = None,
                   expires_in: Optional[timedelta] = None) -> FileHMAC:
        """
        Create HMAC signature for a file.
        
        Args:
            file_path: Path to the file
            key_id: Optional key identifier
            expires_in: Optional expiration time
            
        Returns:
            FileHMAC object
        """
        file_path = Path(file_path)
        file_size, last_modified = self._get_file_metadata(file_path)
        
        if key_id is None:
            key_id = f"key_{int(datetime.utcnow().timestamp())}"
        
        hmac_signature = self._compute_hmac(file_path, key_id)
        
        created_at = datetime.utcnow()
        expires_at = None
        if expires_in:
            expires_at = created_at + expires_in
        
        file_hmac = FileHMAC(
            file_path=str(file_path),
            hmac_signature=hmac_signature,
            key_id=key_id,
            algorithm=HMAC_ALGORITHM.__name__,
            file_size=file_size,
            last_modified=last_modified,
            created_at=created_at,
            expires_at=expires_at
        )
        
        self.hmacs[str(file_path)] = file_hmac
        self._save_verification_data()
        
        logger.info(f"Created HMAC for {file_path}")
        return file_hmac
    
    def verify_checksum(self, file_path: Union[str, Path]) -> bool:
        """
        Verify SHA-256 checksum of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if checksum matches, False otherwise
        """
        file_path = Path(file_path)
        file_path_str = str(file_path)
        
        if file_path_str not in self.checksums:
            logger.warning(f"No checksum found for {file_path}")
            return False
        
        stored_checksum = self.checksums[file_path_str]
        
        # Check expiration
        if stored_checksum.expires_at and datetime.utcnow() > stored_checksum.expires_at:
            logger.warning(f"Checksum expired for {file_path}")
            return False
        
        # Check file size and modification time
        current_size, current_mtime = self._get_file_metadata(file_path)
        if (current_size != stored_checksum.file_size or 
            current_mtime != stored_checksum.last_modified):
            logger.warning(f"File metadata changed for {file_path}")
            return False
        
        # Compute current checksum
        current_checksum = self._compute_checksum(file_path)
        
        # Compare checksums
        is_valid = hmac.compare_digest(current_checksum, stored_checksum.checksum)
        
        if is_valid:
            logger.debug(f"Checksum verification successful for {file_path}")
        else:
            logger.warning(f"Checksum verification failed for {file_path}")
        
        return is_valid
    
    def verify_hmac(self, file_path: Union[str, Path]) -> bool:
        """
        Verify HMAC signature of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if HMAC matches, False otherwise
        """
        file_path = Path(file_path)
        file_path_str = str(file_path)
        
        if file_path_str not in self.hmacs:
            logger.warning(f"No HMAC found for {file_path}")
            return False
        
        stored_hmac = self.hmacs[file_path_str]
        
        # Check expiration
        if stored_hmac.expires_at and datetime.utcnow() > stored_hmac.expires_at:
            logger.warning(f"HMAC expired for {file_path}")
            return False
        
        # Check file size and modification time
        current_size, current_mtime = self._get_file_metadata(file_path)
        if (current_size != stored_hmac.file_size or 
            current_mtime != stored_hmac.last_modified):
            logger.warning(f"File metadata changed for {file_path}")
            return False
        
        # Compute current HMAC
        current_hmac = self._compute_hmac(file_path, stored_hmac.key_id)
        
        # Compare HMACs
        is_valid = hmac.compare_digest(current_hmac, stored_hmac.hmac_signature)
        
        if is_valid:
            logger.debug(f"HMAC verification successful for {file_path}")
        else:
            logger.warning(f"HMAC verification failed for {file_path}")
        
        return is_valid
    
    def verify_file(self, file_path: Union[str, Path]) -> Dict[str, bool]:
        """
        Verify both checksum and HMAC of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with verification results
        """
        file_path = Path(file_path)
        
        return {
            'checksum_valid': self.verify_checksum(file_path),
            'hmac_valid': self.verify_hmac(file_path),
            'file_exists': file_path.exists()
        }
    
    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Remove expired checksums and HMACs.
        
        Returns:
            Tuple of (checksums_removed, hmacs_removed)
        """
        now = datetime.utcnow()
        checksums_removed = 0
        hmacs_removed = 0
        
        # Remove expired checksums
        expired_checksums = [
            path for path, checksum in self.checksums.items()
            if checksum.expires_at and checksum.expires_at < now
        ]
        for path in expired_checksums:
            del self.checksums[path]
            checksums_removed += 1
        
        # Remove expired HMACs
        expired_hmacs = [
            path for path, hmac in self.hmacs.items()
            if hmac.expires_at and hmac.expires_at < now
        ]
        for path in expired_hmacs:
            del self.hmacs[path]
            hmacs_removed += 1
        
        if checksums_removed > 0 or hmacs_removed > 0:
            self._save_verification_data()
            logger.info(f"Cleaned up {checksums_removed} expired checksums and {hmacs_removed} expired HMACs")
        
        return checksums_removed, hmacs_removed
    
    def get_verification_status(self) -> Dict[str, any]:
        """
        Get verification status summary.
        
        Returns:
            Dictionary with verification statistics
        """
        now = datetime.utcnow()
        
        active_checksums = sum(
            1 for checksum in self.checksums.values()
            if not checksum.expires_at or checksum.expires_at > now
        )
        
        active_hmacs = sum(
            1 for hmac in self.hmacs.values()
            if not hmac.expires_at or hmac.expires_at > now
        )
        
        expired_checksums = len(self.checksums) - active_checksums
        expired_hmacs = len(self.hmacs) - active_hmacs
        
        return {
            'total_checksums': len(self.checksums),
            'active_checksums': active_checksums,
            'expired_checksums': expired_checksums,
            'total_hmacs': len(self.hmacs),
            'active_hmacs': active_hmacs,
            'expired_hmacs': expired_hmacs,
            'verification_file': str(self.verification_file),
            'last_updated': datetime.utcnow().isoformat()
        }


# Convenience functions for common operations
def create_file_verification(file_path: Union[str, Path], 
                           secret_key: Optional[str] = None,
                           expires_in: Optional[timedelta] = None) -> Tuple[FileChecksum, FileHMAC]:
    """
    Create both checksum and HMAC for a file.
    
    Args:
        file_path: Path to the file
        secret_key: Optional secret key for HMAC
        expires_in: Optional expiration time
        
    Returns:
        Tuple of (FileChecksum, FileHMAC)
    """
    manager = FileVerificationManager(secret_key=secret_key)
    checksum = manager.create_checksum(file_path, expires_in)
    hmac = manager.create_hmac(file_path, expires_in=expires_in)
    return checksum, hmac


def verify_file_integrity(file_path: Union[str, Path], 
                         secret_key: Optional[str] = None) -> Dict[str, bool]:
    """
    Verify file integrity using both checksum and HMAC.
    
    Args:
        file_path: Path to the file
        secret_key: Optional secret key for HMAC verification
        
    Returns:
        Dictionary with verification results
    """
    manager = FileVerificationManager(secret_key=secret_key)
    return manager.verify_file(file_path)


def cleanup_expired_verifications(secret_key: Optional[str] = None) -> Tuple[int, int]:
    """
    Clean up expired verifications.
    
    Args:
        secret_key: Optional secret key
        
    Returns:
        Tuple of (checksums_removed, hmacs_removed)
    """
    manager = FileVerificationManager(secret_key=secret_key)
    return manager.cleanup_expired() 