#!/usr/bin/env python3
"""
Test script for DART-Planner security hardening features.

Tests the new secure key management system, short-lived tokens,
HMAC tokens, and key rotation functionality.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports

from dart_planner.security.key_manager import SecureKeyManager, TokenType, get_key_manager
from dart_planner.security.auth import AuthManager, Role


def test_key_manager_initialization():
    """Test secure key manager initialization"""
    print("🔐 Testing Secure Key Manager Initialization...")
    
    # Use temporary keys file for testing
    test_keys_file = "/tmp/test_security_keys.json"
    
    try:
        # Initialize key manager
        key_manager = SecureKeyManager(keys_file=test_keys_file, enable_watcher=False)
        
        # Check initial state
        stats = key_manager.get_key_stats()
        print(f"  ✅ Key manager initialized successfully")
        print(f"  📊 Key stats: {stats}")
        
        # Verify keys were created
        assert stats["total_keys"] >= 2, "Should have at least 2 keys (primary + backup)"
        assert stats["active_keys"] >= 1, "Should have at least 1 active key"
        
        return key_manager
        
    except Exception as e:
        print(f"  ❌ Key manager initialization failed: {e}")
        raise


def test_jwt_token_creation(key_manager):
    """Test JWT token creation with short expiration"""
    print("\n🎫 Testing JWT Token Creation...")
    
    try:
        # Create short-lived access token
        token, metadata = key_manager.create_jwt_token(
            payload={"sub": "test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS,
            expires_in=timedelta(minutes=15)  # Short-lived
        )
        
        print(f"  ✅ JWT token created successfully")
        print(f"  📝 Token type: {metadata.token_type}")
        print(f"  🔑 Key ID: {metadata.key_id}")
        print(f"  ⏰ Expires at: {metadata.expires_at}")
        print(f"  🆔 JTI: {metadata.jti}")
        
        # Verify token is valid
        payload, _ = key_manager.verify_jwt_token(token)
        assert payload["sub"] == "test_user"
        assert "pilot" in payload["scopes"]
        
        print(f"  ✅ Token verification successful")
        
        return token, metadata
        
    except Exception as e:
        print(f"  ❌ JWT token creation failed: {e}")
        raise


def test_hmac_token_creation(key_manager):
    """Test HMAC token creation for API access"""
    print("\n🔐 Testing HMAC Token Creation...")
    
    try:
        # Create HMAC token for API access
        token, metadata = key_manager.create_hmac_token(
            user_id="api_user",
            scopes=["api_access", "read_data", "write_data"],
            token_type=TokenType.HMAC_API,
            expires_in=timedelta(minutes=30)
        )
        
        print(f"  ✅ HMAC token created successfully")
        print(f"  📝 Token type: {metadata.token_type}")
        print(f"  👤 User ID: {metadata.user_id}")
        print(f"  🔑 Key ID: {metadata.key_id}")
        print(f"  ⏰ Expires at: {metadata.expires_at}")
        
        # Verify HMAC token
        payload, _ = key_manager.verify_hmac_token(token)
        assert payload["user_id"] == "api_user"
        assert "api_access" in payload["scopes"]
        assert "read_data" in payload["scopes"]
        assert "write_data" in payload["scopes"]
        
        print(f"  ✅ HMAC token verification successful")
        
        return token, metadata
        
    except Exception as e:
        print(f"  ❌ HMAC token creation failed: {e}")
        raise


def test_token_expiration(key_manager):
    """Test token expiration handling"""
    print("\n⏰ Testing Token Expiration...")
    
    try:
        # Create token with very short expiration
        token, metadata = key_manager.create_jwt_token(
            payload={"sub": "expire_test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS,
            expires_in=timedelta(seconds=2)  # Very short
        )
        
        print(f"  ✅ Short-lived token created (expires in 2 seconds)")
        
        # Token should be valid immediately
        payload, _ = key_manager.verify_jwt_token(token)
        assert payload["sub"] == "expire_test_user"
        print(f"  ✅ Token is valid immediately")
        
        # Wait for expiration
        print(f"  ⏳ Waiting for token to expire...")
        time.sleep(3)
        
        # Token should be expired now
        try:
            key_manager.verify_jwt_token(token)
            print(f"  ❌ Token should have expired but didn't")
            return False
        except Exception as e:
            if "expired" in str(e).lower():
                print(f"  ✅ Token expired correctly: {e}")
                return True
            else:
                print(f"  ❌ Unexpected error on expired token: {e}")
                return False
                
    except Exception as e:
        print(f"  ❌ Token expiration test failed: {e}")
        raise


def test_token_revocation(key_manager):
    """Test token revocation functionality"""
    print("\n🚫 Testing Token Revocation...")
    
    try:
        # Create a token
        token, metadata = key_manager.create_jwt_token(
            payload={"sub": "revoke_test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        print(f"  ✅ Token created for revocation test")
        
        # Token should be valid initially
        payload, _ = key_manager.verify_jwt_token(token)
        assert payload["sub"] == "revoke_test_user"
        print(f"  ✅ Token is valid before revocation")
        
        # Revoke the token
        revoked = key_manager.revoke_token(metadata.jti)
        assert revoked, "Token should be revoked successfully"
        print(f"  ✅ Token revoked successfully")
        
        # Check if token is revoked
        is_revoked = key_manager.is_token_revoked(metadata.jti)
        assert is_revoked, "Token should be marked as revoked"
        print(f"  ✅ Token is marked as revoked")
        
        # Try to revoke again (should return False)
        revoked_again = key_manager.revoke_token(metadata.jti)
        assert not revoked_again, "Revoking same token again should return False"
        print(f"  ✅ Duplicate revocation handled correctly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Token revocation test failed: {e}")
        raise


def test_key_rotation(key_manager):
    """Test key rotation functionality"""
    print("\n🔄 Testing Key Rotation...")
    
    try:
        # Get initial stats
        initial_stats = key_manager.get_key_stats()
        print(f"  📊 Initial key stats: {initial_stats}")
        
        # Create token with current key
        token, metadata = key_manager.create_jwt_token(
            payload={"sub": "rotation_test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        print(f"  ✅ Token created with current key: {metadata.key_id}")
        
        # Rotate keys
        new_key = key_manager.rotate_keys()
        print(f"  ✅ Keys rotated, new primary key: {new_key.key_id}")
        
        # Get updated stats
        updated_stats = key_manager.get_key_stats()
        print(f"  📊 Updated key stats: {updated_stats}")
        
        # Old token should still be valid (grace period)
        payload, _ = key_manager.verify_jwt_token(token)
        assert payload["sub"] == "rotation_test_user"
        print(f"  ✅ Old token still valid after rotation")
        
        # Create new token with new key
        new_token, new_metadata = key_manager.create_jwt_token(
            payload={"sub": "rotation_test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS
        )
        
        print(f"  ✅ New token created with new key: {new_metadata.key_id}")
        
        # Verify new token
        new_payload, _ = key_manager.verify_jwt_token(new_token)
        assert new_payload["sub"] == "rotation_test_user"
        print(f"  ✅ New token verification successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Key rotation test failed: {e}")
        raise


def test_legacy_compatibility():
    """Test compatibility with legacy environment variable approach"""
    print("\n🔄 Testing Legacy Compatibility...")
    
    try:
        # Set legacy environment variable
        legacy_key = "legacy_test_secret_key_12345"
        # Use test-specific secret key for security testing
        os.environ["DART_SECRET_KEY"] = "test_secret_key_security_testing_only"
        
        # Import auth manager (should use legacy key as fallback)
        from dart_planner.security.auth import AuthManager, SECRET_KEY
        
        print(f"  ✅ Legacy SECRET_KEY loaded: {SECRET_KEY[:20]}...")
        
        # Create auth manager
        from unittest.mock import MagicMock
        mock_user_service = MagicMock()
        auth_manager = AuthManager(user_service=mock_user_service)
        
        print(f"  ✅ AuthManager created with legacy compatibility")
        
        # Test legacy token creation
        legacy_token = auth_manager.create_access_token({"sub": "legacy_user"})
        print(f"  ✅ Legacy token creation successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Legacy compatibility test failed: {e}")
        raise


def test_security_improvements():
    """Test overall security improvements"""
    print("\n🛡️ Testing Security Improvements...")
    
    try:
        # Test short-lived tokens
        key_manager = get_key_manager()
        
        # Create tokens with different expiration times
        short_token, short_metadata = key_manager.create_jwt_token(
            payload={"sub": "security_test_user", "scopes": ["pilot"]},
            token_type=TokenType.JWT_ACCESS,
            expires_in=timedelta(minutes=15)  # Short-lived
        )
        
        refresh_token, refresh_metadata = key_manager.create_jwt_token(
            payload={"sub": "security_test_user"},
            token_type=TokenType.JWT_REFRESH,
            expires_in=timedelta(hours=1)  # Short refresh token
        )
        
        print(f"  ✅ Short-lived access token: {short_metadata.expires_at}")
        print(f"  ✅ Short-lived refresh token: {refresh_metadata.expires_at}")
        
        # Verify expiration times are reasonable
        access_duration = short_metadata.expires_at - short_metadata.issued_at
        refresh_duration = refresh_metadata.expires_at - refresh_metadata.issued_at
        
        assert access_duration <= timedelta(minutes=30), "Access tokens should be short-lived"
        assert refresh_duration <= timedelta(hours=2), "Refresh tokens should be short-lived"
        
        print(f"  ✅ Token expiration times are secure")
        
        # Test key rotation readiness
        stats = key_manager.get_key_stats()
        assert stats["active_keys"] >= 1, "Should have active keys for rotation"
        
        print(f"  ✅ Key rotation system is ready")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security improvements test failed: {e}")
        raise


def main():
    """Run all security hardening tests"""
    print("🛡️ DART-Planner Security Hardening Test Suite")
    print("=" * 50)
    
    test_results = []
    
    try:
        # Test 1: Key Manager Initialization
        key_manager = test_key_manager_initialization()
        test_results.append(("Key Manager Initialization", True))
        
        # Test 2: JWT Token Creation
        jwt_token, jwt_metadata = test_jwt_token_creation(key_manager)
        test_results.append(("JWT Token Creation", True))
        
        # Test 3: HMAC Token Creation
        hmac_token, hmac_metadata = test_hmac_token_creation(key_manager)
        test_results.append(("HMAC Token Creation", True))
        
        # Test 4: Token Expiration
        expiration_success = test_token_expiration(key_manager)
        test_results.append(("Token Expiration", expiration_success))
        
        # Test 5: Token Revocation
        revocation_success = test_token_revocation(key_manager)
        test_results.append(("Token Revocation", revocation_success))
        
        # Test 6: Key Rotation
        rotation_success = test_key_rotation(key_manager)
        test_results.append(("Key Rotation", rotation_success))
        
        # Test 7: Legacy Compatibility
        legacy_success = test_legacy_compatibility()
        test_results.append(("Legacy Compatibility", legacy_success))
        
        # Test 8: Security Improvements
        security_success = test_security_improvements()
        test_results.append(("Security Improvements", security_success))
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        return False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security hardening tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
