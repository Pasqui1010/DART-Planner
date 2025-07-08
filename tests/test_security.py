"""
Tests for DART-Planner Security System

Tests authentication, authorization, input validation, and credential management
to ensure secure operation of the autonomous drone navigation system.
"""

import unittest
import tempfile
import os
import json
import math
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys

from dart_planner.security import (
    AuthManager, AuthLevel, UserSession,
    InputValidator, ValidationError, SafetyLimits,
    SecureCredentialManager, Credential,
    validate_waypoint, validate_trajectory, validate_control_command
)


class TestAuthManager(unittest.TestCase):
    """Test authentication and authorization functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.auth_manager = AuthManager(secret_key="test_secret_key")
        
    def test_password_hashing(self):
        """Test secure password hashing and verification"""
        password = "test_password_123"
        hash1 = self.auth_manager._hash_password(password)
        hash2 = self.auth_manager._hash_password(password)
        
        # Hashes should be different due to salt
        self.assertNotEqual(hash1, hash2)
        
        # Both should verify correctly
        self.assertTrue(self.auth_manager._verify_password(password, hash1))
        self.assertTrue(self.auth_manager._verify_password(password, hash2))
        
        # Wrong password should fail
        self.assertFalse(self.auth_manager._verify_password("wrong_password", hash1))
    
    def test_successful_authentication(self):
        """Test successful user authentication"""
        session = self.auth_manager.authenticate("pilot", "dart_pilot_2025", "127.0.0.1")
        
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, "pilot")
        self.assertEqual(session.auth_level, AuthLevel.PILOT)
        self.assertTrue(session.permissions.get("flight_control", False))
        self.assertIsNotNone(session.token)
    
    def test_failed_authentication(self):
        """Test failed authentication scenarios"""
        # Wrong password
        session = self.auth_manager.authenticate("pilot", "wrong_password", "127.0.0.1")
        self.assertIsNone(session)
        
        # Non-existent user
        session = self.auth_manager.authenticate("unknown_user", "any_password", "127.0.0.1")
        self.assertIsNone(session)
    
    def test_rate_limiting(self):
        """Test rate limiting after failed attempts"""
        client_ip = "192.168.1.100"
        
        # Make 5 failed attempts
        for _ in range(5):
            session = self.auth_manager.authenticate("pilot", "wrong_password", client_ip)
            self.assertIsNone(session)
        
        # Should be rate limited now
        self.assertTrue(self.auth_manager._is_rate_limited(client_ip))
        
        # Even correct credentials should fail
        session = self.auth_manager.authenticate("pilot", "dart_pilot_2025", client_ip)
        self.assertIsNone(session)
    
    def test_token_validation(self):
        """Test token validation and session management"""
        session = self.auth_manager.authenticate("pilot", "dart_pilot_2025", "127.0.0.1")
        token = session.token
        
        # Valid token should return session
        validated_session = self.auth_manager.validate_token(token)
        self.assertIsNotNone(validated_session)
        self.assertEqual(validated_session.user_id, "pilot")
        
        # Invalid token should return None
        invalid_session = self.auth_manager.validate_token("invalid_token")
        self.assertIsNone(invalid_session)
    
    def test_session_timeout(self):
        """Test session timeout functionality"""
        # Create session with short timeout
        self.auth_manager.session_timeout = timedelta(seconds=1)
        session = self.auth_manager.authenticate("pilot", "dart_pilot_2025", "127.0.0.1")
        token = session.token
        
        # Should be valid immediately
        validated_session = self.auth_manager.validate_token(token)
        self.assertIsNotNone(validated_session)
        
        # Manually expire the session
        session.last_active = datetime.now() - timedelta(seconds=2)
        
        # Should be invalid after timeout
        validated_session = self.auth_manager.validate_token(token)
        self.assertIsNone(validated_session)
    
    def test_permissions_check(self):
        """Test permission checking system"""
        # Pilot should have flight control
        pilot_session = self.auth_manager.authenticate("pilot", "dart_pilot_2025", "127.0.0.1")
        self.assertTrue(self.auth_manager.check_permission(pilot_session, "flight_control"))
        
        # Operator should not have flight control
        operator_session = self.auth_manager.authenticate("operator", "dart_ops_2025", "127.0.0.1")
        self.assertFalse(self.auth_manager.check_permission(operator_session, "flight_control"))
        self.assertTrue(self.auth_manager.check_permission(operator_session, "mission_planning"))
    
    def test_logout(self):
        """Test session logout functionality"""
        session = self.auth_manager.authenticate("pilot", "dart_pilot_2025", "127.0.0.1")
        token = session.token
        
        # Should be valid initially
        self.assertIsNotNone(self.auth_manager.validate_token(token))
        
        # Logout should invalidate
        result = self.auth_manager.logout(token)
        self.assertTrue(result)
        
        # Should be invalid after logout
        self.assertIsNone(self.auth_manager.validate_token(token))


class TestInputValidator(unittest.TestCase):
    """Test input validation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.validator = InputValidator()
        self.safety_limits = SafetyLimits()
    
    def test_coordinate_validation_success(self):
        """Test successful coordinate validation"""
        valid_coord = {"x": 10.0, "y": -5.5, "z": 2.0}
        result = self.validator.validate_coordinate(valid_coord, "position")
        
        self.assertEqual(result["x"], 10.0)
        self.assertEqual(result["y"], -5.5)
        self.assertEqual(result["z"], 2.0)
    
    def test_coordinate_validation_failures(self):
        """Test coordinate validation failure cases"""
        # Missing field
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate({"x": 1.0, "y": 2.0}, "position")
        
        # Non-numeric value
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate({"x": "invalid", "y": 2.0, "z": 3.0}, "position")
        
        # Altitude too high
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate({"x": 1.0, "y": 2.0, "z": 200.0}, "position")
        
        # Range too far
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate({"x": 2000.0, "y": 2.0, "z": 3.0}, "position")
        
        # NaN/Inf values
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate({"x": float('nan'), "y": 2.0, "z": 3.0}, "position")
    
    def test_waypoint_validation(self):
        """Test waypoint validation"""
        valid_waypoint = {
            "position": {"x": 10.0, "y": 5.0, "z": 2.0},
            "velocity": {"x": 2.0, "y": 1.0, "z": 0.5},
            "id": "wp_001",
            "timestamp": 123456789.0
        }
        
        result = self.validator.validate_waypoint(valid_waypoint)
        
        self.assertEqual(result["position"]["x"], 10.0)
        self.assertEqual(result["velocity"]["x"], 2.0)
        self.assertEqual(result["id"], "wp_001")
        self.assertEqual(result["timestamp"], 123456789.0)
    
    def test_waypoint_validation_failures(self):
        """Test waypoint validation failures"""
        # Missing position
        with self.assertRaises(ValidationError):
            self.validator.validate_waypoint({"velocity": {"x": 1, "y": 2, "z": 3}})
        
        # Excessive velocity
        with self.assertRaises(ValidationError):
            self.validator.validate_waypoint({
                "position": {"x": 1, "y": 2, "z": 3},
                "velocity": {"x": 100, "y": 100, "z": 5}  # Too fast
            })
    
    def test_trajectory_validation(self):
        """Test trajectory validation"""
        valid_trajectory = [
            {"position": {"x": 0.0, "y": 0.0, "z": 1.0}},
            {"position": {"x": 5.0, "y": 0.0, "z": 1.0}},
            {"position": {"x": 10.0, "y": 5.0, "z": 2.0}}
        ]
        
        result = self.validator.validate_trajectory(valid_trajectory)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["position"]["x"], 0.0)
        self.assertEqual(result[2]["position"]["z"], 2.0)
    
    def test_trajectory_validation_failures(self):
        """Test trajectory validation failures"""
        # Empty trajectory
        with self.assertRaises(ValidationError):
            self.validator.validate_trajectory([])
        
        # Too many waypoints
        long_trajectory = [{"position": {"x": i, "y": 0, "z": 1}} for i in range(200)]
        with self.assertRaises(ValidationError):
            self.validator.validate_trajectory(long_trajectory)
    
    def test_control_command_validation(self):
        """Test control command validation"""
        valid_command = {
            "type": "position",
            "target": {"x": 5.0, "y": 3.0, "z": 2.0},
            "timestamp": 123456789.0,
            "priority": 5
        }
        
        result = self.validator.validate_control_command(valid_command)
        self.assertEqual(result["type"], "position")
        self.assertEqual(result["target"]["x"], 5.0)
        self.assertEqual(result["priority"], 5)
    
    def test_control_command_failures(self):
        """Test control command validation failures"""
        # Invalid type
        with self.assertRaises(ValidationError):
            self.validator.validate_control_command({"type": "invalid_type"})
        
        # Missing target for position command
        with self.assertRaises(ValidationError):
            self.validator.validate_control_command({"type": "position"})
    
    def test_attitude_validation(self):
        """Test attitude validation"""
        valid_attitude = {"roll": 0.1, "pitch": -0.2, "yaw": 1.5}
        result = self.validator.validate_attitude(valid_attitude)
        
        self.assertAlmostEqual(result["roll"], 0.1)
        self.assertAlmostEqual(result["pitch"], -0.2)
        self.assertAlmostEqual(result["yaw"], 1.5)
    
    def test_attitude_validation_failures(self):
        """Test attitude validation failures"""
        # Excessive roll
        with self.assertRaises(ValidationError):
            self.validator.validate_attitude({"roll": math.radians(60), "pitch": 0, "yaw": 0})
        
        # Missing field
        with self.assertRaises(ValidationError):
            self.validator.validate_attitude({"roll": 0.1, "pitch": 0.2})
    
    def test_string_sanitization(self):
        """Test string input sanitization"""
        # Normal string
        result = self.validator.sanitize_string_input("normal_string_123", 100)
        self.assertEqual(result, "normal_string_123")
        
        # String with dangerous characters
        dangerous_input = "<script>alert('xss')</script>"
        result = self.validator.sanitize_string_input(dangerous_input, 100)
        self.assertNotIn("<script>", result)
        self.assertNotIn("</script>", result)
        
        # String with SQL injection attempt
        with self.assertRaises(ValidationError):
            self.validator.sanitize_string_input("'; DROP TABLE users; --", 100)
    
    def test_sensor_data_validation(self):
        """Test sensor data validation"""
        # IMU data
        imu_data = {
            "accelerometer": {"x": 0.1, "y": -0.2, "z": 9.8},
            "gyroscope": {"x": 0.01, "y": 0.02, "z": -0.01},
            "timestamp": 123456789.0
        }
        
        result = self.validator.validate_sensor_data(imu_data, "imu")
        self.assertEqual(result["accelerometer"]["z"], 9.8)
        self.assertEqual(result["timestamp"], 123456789.0)
        
        # GPS data
        gps_data = {
            "latitude": 40.7589,
            "longitude": -73.9851,
            "altitude": 10.5,
            "timestamp": 123456789.0
        }
        
        result = self.validator.validate_sensor_data(gps_data, "gps")
        self.assertEqual(result["latitude"], 40.7589)
        self.assertEqual(result["longitude"], -73.9851)
    
    def test_convenience_functions(self):
        """Test convenience validation functions"""
        waypoint = {"position": {"x": 1.0, "y": 2.0, "z": 3.0}}
        result = validate_waypoint(waypoint)
        self.assertEqual(result["position"]["x"], 1.0)
        
        trajectory = [waypoint]
        result = validate_trajectory(trajectory)
        self.assertEqual(len(result), 1)
        
        command = {"type": "emergency_stop"}
        result = validate_control_command(command)
        self.assertEqual(result["type"], "emergency_stop")


class TestSecureCredentialManager(unittest.TestCase):
    """Test secure credential management"""
    
    def setUp(self):
        """Set up test environment with temporary file"""
        self.temp_dir = tempfile.mkdtemp()
        self.cred_file = os.path.join(self.temp_dir, "test_creds.encrypted")
        self.cred_manager = SecureCredentialManager(
            credentials_file=self.cred_file,
            master_password="test_master_password"
        )
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_credential_storage_and_retrieval(self):
        """Test storing and retrieving credentials"""
        # Store credential
        self.cred_manager.store_credential(
            name="test_api_key",
            value="secret_key_12345",
            credential_type="api_key",
            metadata={"service": "test_service"}
        )
        
        # Retrieve credential
        retrieved_value = self.cred_manager.get_credential("test_api_key")
        self.assertEqual(retrieved_value, "secret_key_12345")
        
        # Get credential info
        info = self.cred_manager.get_credential_info("test_api_key")
        self.assertEqual(info["type"], "api_key")
        self.assertEqual(info["metadata"]["service"], "test_service")
    
    def test_credential_expiration(self):
        """Test credential expiration"""
        # Store credential with short expiration
        self.cred_manager.store_credential(
            name="temp_token",
            value="temporary_value",
            credential_type="token",
            expires_hours=1
        )
        
        # Should be retrievable immediately
        self.assertIsNotNone(self.cred_manager.get_credential("temp_token"))
        
        # Manually expire it
        credential = self.cred_manager.credentials["temp_token"]
        credential.expires_at = datetime.now() - timedelta(hours=1)
        
        # Should be None after expiration
        self.assertIsNone(self.cred_manager.get_credential("temp_token"))
    
    def test_credential_rotation(self):
        """Test credential rotation"""
        # Store initial credential
        self.cred_manager.store_credential("rotate_test", "old_value", "api_key")
        
        # Rotate credential
        result = self.cred_manager.rotate_credential("rotate_test", "new_value")
        self.assertTrue(result)
        
        # Verify new value
        self.assertEqual(self.cred_manager.get_credential("rotate_test"), "new_value")
        
        # Try to rotate non-existent credential
        result = self.cred_manager.rotate_credential("non_existent", "value")
        self.assertFalse(result)
    
    def test_credential_persistence(self):
        """Test credential persistence across manager instances"""
        # Store credential
        self.cred_manager.store_credential("persist_test", "persist_value", "api_key")
        
        # Create new manager instance with same file
        new_manager = SecureCredentialManager(
            credentials_file=self.cred_file,
            master_password="test_master_password"
        )
        
        # Should be able to retrieve the credential
        self.assertEqual(new_manager.get_credential("persist_test"), "persist_value")
    
    def test_cleanup_expired(self):
        """Test cleanup of expired credentials"""
        # Store some credentials with different expiration times
        self.cred_manager.store_credential("valid", "value1", "api_key")
        self.cred_manager.store_credential("expired1", "value2", "token", expires_hours=1)
        self.cred_manager.store_credential("expired2", "value3", "token", expires_hours=1)
        
        # Manually expire some credentials
        self.cred_manager.credentials["expired1"].expires_at = datetime.now() - timedelta(hours=1)
        self.cred_manager.credentials["expired2"].expires_at = datetime.now() - timedelta(hours=1)
        
        # Cleanup should remove 2 expired credentials
        removed_count = self.cred_manager.cleanup_expired()
        self.assertEqual(removed_count, 2)
        
        # Valid credential should still exist
        self.assertIsNotNone(self.cred_manager.get_credential("valid"))
    
    def test_export_import(self):
        """Test credential export and import"""
        # Store some test credentials
        self.cred_manager.store_credential("export_test1", "value1", "api_key")
        self.cred_manager.store_credential("export_test2", "value2", "token")
        
        # Export credentials
        export_password = "export_password_123"
        export_data = self.cred_manager.export_credentials(export_password)
        
        # Create new manager and import
        new_manager = SecureCredentialManager(
            credentials_file=os.path.join(self.temp_dir, "import_test.encrypted"),
            master_password="different_password"
        )
        
        result = new_manager.import_credentials(export_data, export_password)
        self.assertTrue(result)
        
        # Verify imported credentials
        self.assertEqual(new_manager.get_credential("export_test1"), "value1")
        self.assertEqual(new_manager.get_credential("export_test2"), "value2")


if __name__ == '__main__':
    unittest.main() 
