"""
Tests for rate limiting functionality.

Verifies that rate limiting works correctly for login endpoints
and other sensitive operations.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch

from dart_planner.security.rate_limiter import (
    RateLimiter, 
    RateLimitConfig, 
    check_login_rate_limit, 
    record_login_success,
    get_login_rate_limit_status
)


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default config."""
        limiter = RateLimiter()
        assert limiter.config.max_attempts == 5
        assert limiter.config.window_minutes == 15
        assert limiter.config.lockout_minutes == 30
    
    def test_rate_limiter_custom_config(self):
        """Test rate limiter with custom configuration."""
        config = RateLimitConfig(
            max_attempts=3,
            window_minutes=10,
            lockout_minutes=20,
            enable_exponential_backoff=False
        )
        limiter = RateLimiter(config)
        assert limiter.config.max_attempts == 3
        assert limiter.config.window_minutes == 10
        assert limiter.config.lockout_minutes == 20
    
    def test_allowed_requests(self):
        """Test that requests are allowed within limits."""
        limiter = RateLimiter(RateLimitConfig(max_attempts=3, window_minutes=1))
        identifier = "test_ip_1"
        
        # First 3 requests should be allowed
        for i in range(3):
            is_allowed, reason = limiter.is_allowed(identifier)
            assert is_allowed, f"Request {i+1} should be allowed"
            assert reason is None
    
    def test_rate_limit_exceeded(self):
        """Test that requests are blocked after exceeding limits."""
        limiter = RateLimiter(RateLimitConfig(max_attempts=2, window_minutes=1))
        identifier = "test_ip_2"
        
        # First 2 requests should be allowed
        for i in range(2):
            is_allowed, reason = limiter.is_allowed(identifier)
            assert is_allowed, f"Request {i+1} should be allowed"
        
        # Third request should be blocked
        is_allowed, reason = limiter.is_allowed(identifier)
        assert not is_allowed
        assert reason is not None
        assert "Too many attempts" in reason
    
    def test_lockout_duration(self):
        """Test that lockout duration is applied correctly."""
        limiter = RateLimiter(RateLimitConfig(
            max_attempts=1, 
            window_minutes=1, 
            lockout_minutes=5,
            enable_exponential_backoff=False
        ))
        identifier = "test_ip_3"
        
        # First request allowed
        is_allowed, _ = limiter.is_allowed(identifier)
        assert is_allowed
        
        # Second request should trigger lockout
        is_allowed, reason = limiter.is_allowed(identifier)
        assert not is_allowed
        assert reason is not None
        assert "5 minutes" in reason
    
    def test_exponential_backoff(self):
        """Test exponential backoff for repeated violations."""
        limiter = RateLimiter(RateLimitConfig(
            max_attempts=1,
            window_minutes=1,
            lockout_minutes=2,
            enable_exponential_backoff=True,
            backoff_multiplier=2.0
        ))
        identifier = "test_ip_4"
        
        # First violation: 2 minutes
        limiter.is_allowed(identifier)  # First request
        is_allowed, reason = limiter.is_allowed(identifier)  # Second request
        assert not is_allowed
        assert reason is not None
        assert "2 minutes" in reason
        
        # Simulate multiple violations
        for i in range(3):
            limiter._entries[identifier].attempts = 2 + i
            limiter._entries[identifier].locked_until = None
            is_allowed, reason = limiter.is_allowed(identifier)
            assert not is_allowed
            assert reason is not None
            # Should have exponential backoff: 2, 4, 8 minutes
            expected_minutes = 2 * (2 ** i)
            assert f"{expected_minutes} minutes" in reason
    
    def test_window_reset(self):
        """Test that rate limiting resets after window expires."""
        limiter = RateLimiter(RateLimitConfig(max_attempts=2, window_minutes=1))
        identifier = "test_ip_5"
        
        # Use up the limit
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        
        # Third request should be blocked
        is_allowed, _ = limiter.is_allowed(identifier)
        assert not is_allowed
        
        # Simulate window expiration by setting first_attempt to past
        limiter._entries[identifier].first_attempt = datetime.now() - timedelta(minutes=2)
        
        # Should be allowed again
        is_allowed, reason = limiter.is_allowed(identifier)
        assert is_allowed
        assert reason is None
    
    def test_success_reset(self):
        """Test that successful authentication resets rate limiting."""
        limiter = RateLimiter(RateLimitConfig(max_attempts=2, window_minutes=1))
        identifier = "test_ip_6"
        
        # Use up the limit
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        
        # Third request should be blocked
        is_allowed, _ = limiter.is_allowed(identifier)
        assert not is_allowed
        
        # Record successful authentication
        limiter.record_success(identifier)
        
        # Should be allowed again
        is_allowed, reason = limiter.is_allowed(identifier)
        assert is_allowed
        assert reason is None
    
    def test_get_status(self):
        """Test getting rate limiting status."""
        limiter = RateLimiter(RateLimitConfig(max_attempts=3, window_minutes=1))
        identifier = "test_ip_7"
        
        # No status initially
        status = limiter.get_status(identifier)
        assert status is None
        
        # Make some attempts
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        
        # Get status
        status = limiter.get_status(identifier)
        assert status is not None
        assert status["attempts"] == 2
        assert status["max_attempts"] == 3
        assert status["window_minutes"] == 1
        assert status["first_attempt"] is not None
        assert status["last_attempt"] is not None
    
    def test_cleanup_expired_entries(self):
        """Test cleanup of expired entries."""
        limiter = RateLimiter()
        identifier = "test_ip_8"
        
        # Create an entry
        limiter.is_allowed(identifier)
        
        # Simulate old entry
        limiter._entries[identifier].last_attempt = datetime.now() - timedelta(hours=2)
        limiter._entries[identifier].locked_until = datetime.now() - timedelta(hours=1)
        
        # Force cleanup
        limiter._cleanup_expired_entries()
        
        # Entry should be removed
        assert identifier not in limiter._entries


class TestLoginRateLimiting:
    """Test login-specific rate limiting functions."""
    
    def test_check_login_rate_limit(self):
        """Test login rate limit checking."""
        identifier = "test_login_ip"
        
        # First few attempts should be allowed
        for i in range(5):
            is_allowed, reason = check_login_rate_limit(identifier)
            assert is_allowed, f"Login attempt {i+1} should be allowed"
            assert reason is None
        
        # Sixth attempt should be blocked
        is_allowed, reason = check_login_rate_limit(identifier)
        assert not is_allowed
        assert reason is not None
        assert "Too many attempts" in reason
    
    def test_record_login_success(self):
        """Test recording successful login."""
        identifier = "test_success_ip"
        
        # Use up the limit
        for _ in range(3):
            check_login_rate_limit(identifier)
        
        # Should be blocked
        is_allowed, _ = check_login_rate_limit(identifier)
        assert not is_allowed
        
        # Record success
        record_login_success(identifier)
        
        # Should be allowed again
        is_allowed, reason = check_login_rate_limit(identifier)
        assert is_allowed
        assert reason is None
    
    def test_get_login_rate_limit_status(self):
        """Test getting login rate limit status."""
        identifier = "test_status_ip"
        
        # No status initially
        status = get_login_rate_limit_status(identifier)
        assert status is None
        
        # Make some attempts
        check_login_rate_limit(identifier)
        check_login_rate_limit(identifier)
        
        # Get status
        status = get_login_rate_limit_status(identifier)
        assert status is not None
        assert status["attempts"] == 2
        assert status["max_attempts"] == 5
        assert status["window_minutes"] == 15


class TestRateLimiterThreadSafety:
    """Test rate limiter thread safety."""
    
    def test_concurrent_access(self):
        """Test that rate limiter is thread-safe."""
        import threading
        
        limiter = RateLimiter(RateLimitConfig(max_attempts=10, window_minutes=1))
        identifier = "concurrent_test_ip"
        results = []
        
        def make_request():
            is_allowed, reason = limiter.is_allowed(identifier)
            results.append(is_allowed)
        
        # Create multiple threads making requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should be allowed (within limit)
        assert all(results)
        assert len(results) == 5 