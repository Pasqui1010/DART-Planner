"""
Rate limiting implementation for DART-Planner security.

Provides IP-based rate limiting for login endpoints and other sensitive operations
to prevent brute force attacks and abuse.
"""

import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_attempts: int = 5  # Maximum attempts per window
    window_minutes: int = 15  # Time window in minutes
    lockout_minutes: int = 30  # Lockout duration after max attempts
    enable_exponential_backoff: bool = True
    backoff_multiplier: float = 2.0


@dataclass
class RateLimitEntry:
    """Rate limit entry for tracking attempts."""
    attempts: int = 0
    first_attempt: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    locked_until: Optional[datetime] = None


class RateLimiter:
    """
    Thread-safe rate limiter for protecting sensitive endpoints.
    
    Features:
    - IP-based rate limiting
    - Configurable attempt limits and time windows
    - Automatic lockout with exponential backoff
    - Thread-safe operations
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a request is allowed based on rate limiting.
        
        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        with self._lock:
            self._cleanup_expired_entries()
            
            now = datetime.now()
            entry = self._entries[identifier]
            
            # Check if currently locked out
            if entry.locked_until and now < entry.locked_until:
                remaining = (entry.locked_until - now).total_seconds()
                return False, f"Rate limit exceeded. Try again in {int(remaining)} seconds"
            
            # Reset if window has expired
            if (entry.first_attempt and 
                now - entry.first_attempt > timedelta(minutes=self.config.window_minutes)):
                entry.attempts = 0
                entry.first_attempt = None
                entry.locked_until = None
            
            # Check if within limits
            if entry.attempts >= self.config.max_attempts:
                # Apply lockout
                lockout_duration = self._calculate_lockout_duration(entry.attempts)
                entry.locked_until = now + timedelta(minutes=lockout_duration)
                
                logger.warning(f"Rate limit exceeded for {identifier}. Locked for {lockout_duration} minutes")
                return False, f"Too many attempts. Locked for {lockout_duration} minutes"
            
            # Record attempt
            if entry.first_attempt is None:
                entry.first_attempt = now
            entry.last_attempt = now
            entry.attempts += 1
            
            return True, None
    
    def record_success(self, identifier: str) -> None:
        """
        Record a successful authentication to reset rate limiting.
        
        Args:
            identifier: Unique identifier
        """
        with self._lock:
            if identifier in self._entries:
                # Reset on successful authentication
                self._entries[identifier] = RateLimitEntry()
                logger.info(f"Rate limit reset for {identifier} after successful authentication")
    
    def _calculate_lockout_duration(self, attempts: int) -> int:
        """Calculate lockout duration with exponential backoff."""
        if not self.config.enable_exponential_backoff:
            return self.config.lockout_minutes
        
        # Exponential backoff: base_duration * (multiplier ^ (attempts - max_attempts))
        excess_attempts = attempts - self.config.max_attempts
        duration = self.config.lockout_minutes * (self.config.backoff_multiplier ** excess_attempts)
        
        # Cap at reasonable maximum (24 hours)
        return min(int(duration), 1440)
    
    def _cleanup_expired_entries(self) -> None:
        """Remove expired rate limit entries to prevent memory leaks."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        cutoff = datetime.now() - timedelta(hours=1)  # Keep entries for 1 hour
        
        expired_keys = []
        for key, entry in self._entries.items():
            if (entry.last_attempt and entry.last_attempt < cutoff and
                (not entry.locked_until or entry.locked_until < datetime.now())):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._entries[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")
    
    def get_status(self, identifier: str) -> Optional[Dict]:
        """
        Get rate limiting status for an identifier.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Status dictionary or None if no entry exists
        """
        with self._lock:
            if identifier not in self._entries:
                return None
            
            entry = self._entries[identifier]
            now = datetime.now()
            
            status = {
                "attempts": entry.attempts,
                "max_attempts": self.config.max_attempts,
                "window_minutes": self.config.window_minutes,
                "first_attempt": entry.first_attempt.isoformat() if entry.first_attempt else None,
                "last_attempt": entry.last_attempt.isoformat() if entry.last_attempt else None,
            }
            
            if entry.locked_until:
                if now < entry.locked_until:
                    status["locked_until"] = entry.locked_until.isoformat()
                    status["remaining_seconds"] = int((entry.locked_until - now).total_seconds())
                else:
                    status["locked_until"] = None
                    status["remaining_seconds"] = 0
            
            return status


# Global rate limiter instance for login endpoints
login_rate_limiter = RateLimiter(RateLimitConfig(
    max_attempts=5,
    window_minutes=15,
    lockout_minutes=30,
    enable_exponential_backoff=True
))


def check_login_rate_limit(identifier: str) -> Tuple[bool, Optional[str]]:
    """
    Check if login attempt is allowed for the given identifier.
    
    Args:
        identifier: Unique identifier (typically IP address)
        
    Returns:
        Tuple of (is_allowed, reason_if_blocked)
    """
    return login_rate_limiter.is_allowed(identifier)


def record_login_success(identifier: str) -> None:
    """
    Record successful login to reset rate limiting.
    
    Args:
        identifier: Unique identifier
    """
    login_rate_limiter.record_success(identifier)


def get_login_rate_limit_status(identifier: str) -> Optional[Dict]:
    """
    Get login rate limiting status for an identifier.
    
    Args:
        identifier: Unique identifier
        
    Returns:
        Status dictionary or None if no entry exists
    """
    return login_rate_limiter.get_status(identifier) 