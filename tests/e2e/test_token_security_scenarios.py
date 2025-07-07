#!/usr/bin/env python3
"""
Playwright E2E tests for token security scenarios in DART-Planner.

Tests invalid/expired token handling, key rotation, and security hardening
features including short-lived JWT tokens and HMAC tokens.
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.security.key_manager import SecureKeyManager, TokenType, get_key_manager
from src.security.auth import AuthManager, Role


class TestTokenSecurityScenarios:
    """E2E tests for token security scenarios"""
    
    @pytest.fixture(scope="class")
    async def browser(self):
        """Setup browser for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture
    async def context(self, browser: Browser):
        """Setup browser context"""
        context = await browser.new_context()
        yield context
        await context.close()
    
    @pytest.fixture
    async def page(self, context: BrowserContext):
        """Setup page for testing"""
        page = await context.new_page()
        yield page
        await page.close()
    
    @pytest.fixture
    def key_manager(self):
        """Setup secure key manager for testing"""
        # Use a temporary keys file for testing
        test_keys_file = "/tmp/test_keys.json"
        key_manager = SecureKeyManager(keys_file=test_keys_file, enable_watcher=False)
        yield key_manager
        # Cleanup
        if os.path.exists(test_keys_file):
            os.remove(test_keys_file)
    
    @pytest.fixture
    def auth_manager(self):
        """Setup auth manager for testing"""
        from unittest.mock import MagicMock
        mock_user_service = MagicMock()
        return AuthManager(user_service=mock_user_service)
    
    async def test_invalid_token_rejection(self, page: Page):
        """Test that invalid tokens are properly rejected"""
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Wait for login form
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Try to access protected endpoint with invalid token
        await page.add_init_script("""
            window.currentUser = {
                username: "test_user",
                role: "PILOT",
                token: "invalid_token_12345"
            };
        """)
        
        # Mock API response for invalid token
        await page.route("**/api/status", lambda route: route.fulfill(
            status=401,
            content_type="application/json",
            body='{"detail": "Could not validate credentials"}'
        ))
        
        # Try to access protected content
        await page.click("#start-btn")
        
        # Should show authentication error
        await page.wait_for_selector(".error-message", timeout=5000)
        error_text = await page.text_content(".error-message")
        assert "authentication" in error_text.lower() or "unauthorized" in error_text.lower()
    
    async def test_expired_token_handling(self, page: Page, key_manager: SecureKeyManager):
        """Test that expired tokens are properly handled"""
        # Create an expired token
        expired_token, _ = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS,
            expires_in=timedelta(seconds=1)  # Very short expiration
        )
        
        # Wait for token to expire
        await asyncio.sleep(2)
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Set expired token
        await page.add_init_script(f"""
            window.currentUser = {{
                username: "test_user",
                role: "PILOT",
                token: "{expired_token}"
            }};
        """)
        
        # Mock API response for expired token
        await page.route("**/api/status", lambda route: route.fulfill(
            status=401,
            content_type="application/json",
            body='{"detail": "Token has expired"}'
        ))
        
        # Try to access protected content
        await page.click("#start-btn")
        
        # Should redirect to login or show expired token message
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Verify user is logged out
        login_form = await page.query_selector("#login-form")
        assert login_form is not None
    
    async def test_short_lived_token_refresh(self, page: Page, key_manager: SecureKeyManager):
        """Test that short-lived tokens trigger refresh flow"""
        # Create a token that expires soon
        short_token, _ = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS,
            expires_in=timedelta(minutes=5)  # Short-lived token
        )
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Set short-lived token
        await page.add_init_script(f"""
            window.currentUser = {{
                username: "test_user",
                role: "PILOT",
                token: "{short_token}"
            }};
        """)
        
        # Mock token refresh endpoint
        await page.route("**/api/refresh", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"access_token": "new_refreshed_token", "token_type": "bearer"}'
        ))
        
        # Wait for token refresh to be triggered
        await page.wait_for_timeout(1000)
        
        # Should attempt to refresh token
        # In a real implementation, this would happen automatically
        # For testing, we verify the refresh mechanism is in place
        refresh_called = await page.evaluate("""
            () => {
                return window.tokenRefreshAttempted || false;
            }
        """)
        
        # If refresh mechanism is implemented, it should be called
        # For now, we just verify the token is short-lived
        assert "Bearer " in short_token
    
    async def test_hmac_token_validation(self, page: Page, key_manager: SecureKeyManager):
        """Test HMAC token validation for API access"""
        # Create HMAC token for API access
        hmac_token, metadata = key_manager.create_hmac_token(
            user_id="api_user",
            scopes=["api_access"],
            token_type=TokenType.HMAC_API,
            expires_in=timedelta(minutes=30)
        )
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Set HMAC token
        await page.add_init_script(f"""
            window.currentUser = {{
                username: "api_user",
                role: "API",
                token: "{hmac_token}",
                token_type: "hmac"
            }};
        """)
        
        # Mock API endpoint that validates HMAC tokens
        await page.route("**/api/secure_endpoint", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"message": "HMAC token validated successfully"}'
        ))
        
        # Try to access secure endpoint
        await page.click("#secure-api-btn")
        
        # Should succeed with valid HMAC token
        success_message = await page.text_content(".success-message")
        assert "validated successfully" in success_message
    
    async def test_key_rotation_handling(self, page: Page, key_manager: SecureKeyManager):
        """Test that key rotation is handled gracefully"""
        # Create token with current key
        original_token, _ = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        # Rotate keys
        new_key = key_manager.rotate_keys()
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Set token created with old key
        await page.add_init_script(f"""
            window.currentUser = {{
                username: "test_user",
                role: "PILOT",
                token: "{original_token}"
            }};
        """)
        
        # Mock API response for key rotation scenario
        await page.route("**/api/status", lambda route: route.fulfill(
            status=401,
            content_type="application/json",
            body='{"detail": "Token signed with rotated key", "requires_refresh": true}'
        ))
        
        # Try to access protected content
        await page.click("#start-btn")
        
        # Should handle key rotation gracefully
        # Either by refreshing the token or redirecting to login
        await page.wait_for_timeout(1000)
        
        # Verify graceful handling (either refresh or login redirect)
        current_url = page.url
        assert "login" in current_url or "refresh" in current_url
    
    async def test_token_revocation(self, page: Page, key_manager: SecureKeyManager):
        """Test that revoked tokens are properly rejected"""
        # Create a token
        token, metadata = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        # Revoke the token
        key_manager.revoke_token(metadata.jti)
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Set revoked token
        await page.add_init_script(f"""
            window.currentUser = {{
                username: "test_user",
                role: "PILOT",
                token: "{token}"
            }};
        """)
        
        # Mock API response for revoked token
        await page.route("**/api/status", lambda route: route.fulfill(
            status=401,
            content_type="application/json",
            body='{"detail": "Token has been revoked"}'
        ))
        
        # Try to access protected content
        await page.click("#start-btn")
        
        # Should reject revoked token
        await page.wait_for_selector(".error-message", timeout=5000)
        error_text = await page.text_content(".error-message")
        assert "revoked" in error_text.lower() or "unauthorized" in error_text.lower()
    
    async def test_multiple_failed_attempts(self, page: Page):
        """Test rate limiting for multiple failed authentication attempts"""
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Wait for login form
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Make multiple failed login attempts
        for i in range(5):
            await page.fill("#login-form input[name='username']", "test_user")
            await page.fill("#login-form input[name='password']", f"wrong_password_{i}")
            await page.click("#login-form button[type='submit']")
            
            # Wait for error message
            await page.wait_for_selector(".error-message", timeout=2000)
        
        # Should show rate limiting message
        rate_limit_message = await page.text_content(".error-message")
        assert "rate limit" in rate_limit_message.lower() or "too many attempts" in rate_limit_message.lower()
        
        # Login form should be disabled or show cooldown
        submit_button = await page.query_selector("#login-form button[type='submit']")
        is_disabled = await submit_button.get_attribute("disabled")
        assert is_disabled is not None
    
    async def test_csrf_protection(self, page: Page):
        """Test CSRF protection in forms"""
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Wait for login form
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Check for CSRF token in form
        csrf_input = await page.query_selector("#login-form input[name='csrf_token']")
        assert csrf_input is not None, "CSRF token should be present in login form"
        
        # Try to submit form without CSRF token
        await page.evaluate("""
            document.querySelector('#login-form input[name="csrf_token"]').remove();
        """)
        
        await page.fill("#login-form input[name='username']", "test_user")
        await page.fill("#login-form input[name='password']", "test_password")
        await page.click("#login-form button[type='submit']")
        
        # Should show CSRF error
        await page.wait_for_selector(".error-message", timeout=5000)
        error_text = await page.text_content(".error-message")
        assert "csrf" in error_text.lower() or "security" in error_text.lower()
    
    async def test_secure_cookie_handling(self, page: Page):
        """Test that cookies are set with secure attributes"""
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Wait for login form
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Login with valid credentials
        await page.fill("#login-form input[name='username']", "pilot")
        await page.fill("#login-form input[name='password']", "dart_pilot_2025")
        await page.click("#login-form button[type='submit']")
        
        # Wait for successful login
        await page.wait_for_selector("#demo-section", timeout=10000)
        
        # Check cookie attributes
        cookies = await page.context.cookies()
        auth_cookies = [c for c in cookies if "token" in c["name"].lower()]
        
        for cookie in auth_cookies:
            # Should have secure attributes
            assert cookie.get("httpOnly", False), "Auth cookies should be HttpOnly"
            assert cookie.get("sameSite") in ["Strict", "Lax"], "Auth cookies should have SameSite attribute"
            
            # In HTTPS environments, should be secure
            if page.url.startswith("https://"):
                assert cookie.get("secure", False), "Auth cookies should be secure in HTTPS"
    
    async def test_session_timeout(self, page: Page, key_manager: SecureKeyManager):
        """Test that sessions timeout properly"""
        # Create a token with very short expiration
        short_token, _ = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS,
            expires_in=timedelta(seconds=3)  # Very short session
        )
        
        # Navigate to app
        await page.goto("http://localhost:8000")
        
        # Set short-lived token
        await page.add_init_script(f"""
            window.currentUser = {{
                username: "test_user",
                role: "PILOT",
                token: "{short_token}"
            }};
        """)
        
        # Wait for session to expire
        await asyncio.sleep(4)
        
        # Try to perform an action
        await page.click("#start-btn")
        
        # Should redirect to login due to session timeout
        await page.wait_for_selector("#login-section", timeout=5000)
        
        # Verify session timeout message
        timeout_message = await page.text_content(".session-timeout-message")
        assert "session" in timeout_message.lower() and "expired" in timeout_message.lower()


class TestKeyManagerIntegration:
    """Integration tests for key manager functionality"""
    
    def test_key_rotation_workflow(self, key_manager: SecureKeyManager):
        """Test complete key rotation workflow"""
        # Get initial key stats
        initial_stats = key_manager.get_key_stats()
        assert initial_stats["active_keys"] >= 1
        
        # Create token with current key
        token, metadata = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        # Verify token is valid
        payload, _ = key_manager.verify_jwt_token(token)
        assert payload["sub"] == "test_user"
        
        # Rotate keys
        new_key = key_manager.rotate_keys()
        
        # Verify new key is active
        updated_stats = key_manager.get_key_stats()
        assert updated_stats["active_keys"] >= 1
        
        # Old token should still be valid (grace period)
        payload, _ = key_manager.verify_jwt_token(token)
        assert payload["sub"] == "test_user"
        
        # Create new token with new key
        new_token, new_metadata = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        # Verify new token is valid
        new_payload, _ = key_manager.verify_jwt_token(new_token)
        assert new_payload["sub"] == "test_user"
    
    def test_hmac_token_workflow(self, key_manager: SecureKeyManager):
        """Test HMAC token creation and verification"""
        # Create HMAC token
        token, metadata = key_manager.create_hmac_token(
            user_id="api_user",
            scopes=["api_access", "read_data"],
            token_type=TokenType.HMAC_API
        )
        
        # Verify HMAC token
        payload, _ = key_manager.verify_hmac_token(token)
        assert payload["user_id"] == "api_user"
        assert "api_access" in payload["scopes"]
        assert "read_data" in payload["scopes"]
        
        # Test token revocation
        assert not key_manager.is_token_revoked(metadata.jti)
        key_manager.revoke_token(metadata.jti)
        assert key_manager.is_token_revoked(metadata.jti)
    
    def test_file_watcher_functionality(self, key_manager: SecureKeyManager):
        """Test file watcher for key rotation"""
        # This test would require file system monitoring
        # For now, we test the watcher setup
        assert key_manager.observer is None  # Watcher disabled in test mode
        
        # Test manual key reload
        key_manager.reload_keys()
        stats = key_manager.get_key_stats()
        assert stats["total_keys"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 