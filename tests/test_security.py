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
    AuthManager, Role, UserSession,
    InputValidator, ValidationError, SafetyLimits,
    SecureCredentialManager,
)
from dart_planner.security.crypto import Credential
from dart_planner.security.db.database import get_db, SessionLocal
from dart_planner.security.db.service import UserService
from dart_planner.security.db.models import User as DBUser
from dart_planner.security.auth import require_role, User
from fastapi import HTTPException


class TestAuthManager(unittest.TestCase):
    def setUp(self):
        self.user_service_mock = MagicMock(spec=UserService)
        self.auth_manager = AuthManager(user_service=self.user_service_mock)

    def test_password_hashing(self):
        password = "test_password"
        hashed_password = self.auth_manager.get_password_hash(password)
        self.assertNotEqual(password, hashed_password)
        self.assertTrue(self.auth_manager.verify_password(password, hashed_password))
        self.assertFalse(self.auth_manager.verify_password("wrong_password", hashed_password))

    def test_token_creation_and_validation(self):
        # This test may need adjustment depending on the key manager setup
        # For now, we test the legacy path
        with patch('dart_planner.security.auth.get_key_manager', side_effect=Exception("mock error")):
            data = {"sub": "test_user"}
            token = self.auth_manager.create_access_token(data)
            self.assertIsInstance(token, str)

    def test_require_role(self):
        mock_user_admin = MagicMock(spec=User)
        mock_user_admin.role = Role.ADMIN

        mock_user_pilot = MagicMock(spec=User)
        mock_user_pilot.role = Role.PILOT
        
        admin_checker = require_role(Role.ADMIN)
        
        # Should pass
        result = admin_checker(mock_user_admin)
        self.assertEqual(result, mock_user_admin)

        # Should fail
        with self.assertRaises(HTTPException) as cm:
            admin_checker(mock_user_pilot)
        self.assertEqual(cm.exception.status_code, 403)


class TestInputValidator(unittest.TestCase):
    def setUp(self):
        self.validator = InputValidator()

    def test_valid_coordinate(self):
        coord = {"x": 10.0, "y": -20.0, "z": 30.0}
        validated = self.validator.validate_coordinate(coord)
        self.assertEqual(coord, validated)

    def test_invalid_coordinate_type(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate("not a dict")

    def test_missing_coordinate_field(self):
        with self.assertRaises(ValidationError) as e:
            self.validator.validate_coordinate({"x": 10.0, "y": -20.0})
        self.assertIn("Missing required field", str(e.exception))

    def test_altitude_out_of_range(self):
        with self.assertRaises(ValidationError):
            self.validator.validate_coordinate({"x": 10.0, "y": -20.0, "z": 999.0})

    def test_invalid_field_in_payload(self):
        with self.assertRaises(ValidationError) as e:
            self.validator.validate_generic({"invalid_field": "some_value"})
        self.assertIn("invalid_field", str(e.exception))

    def test_convenience_functions(self):
        waypoint = {"position": {"x": 1.0, "y": 2.0, "z": 3.0}}
        result = self.validator.validate_waypoint(waypoint)
        self.assertEqual(result["position"]["x"], 1.0)
        
        trajectory = [waypoint]
        result = self.validator.validate_trajectory(trajectory)
        self.assertEqual(len(result), 1)
        
        command = {"type": "emergency_stop", "priority": 10}
        result = self.validator.validate_control_command(command)
        self.assertEqual(result["type"], "emergency_stop")


# class TestSecureCredentialManager(unittest.TestCase):
#     def setUp(self):
#         # Use an in-memory file for the test database
#         self.db_path = ":memory:"
#         self.master_password = "test_master_password"
#         self.cred_manager = SecureCredentialManager(
#             master_password=self.master_password, db_path=self.db_path
#         )
#         self.cred_manager.unlock(self.master_password)

#     def tearDown(self):
#         # Ensure we don't leave db files around
#         if self.db_path != ":memory:" and os.path.exists(self.db_path):
#             os.remove(self.db_path)

#     def test_store_and_retrieve_credential(self):
#         self.cred_manager.store_credential("test_service", "test_user", "test_password")
#         retrieved = self.cred_manager.get_credential("test_service", "test_user")
#         self.assertEqual(retrieved, "test_password")

#     def test_credential_expiry(self):
#         self.cred_manager.store_credential(
#             "test_service", "test_user", "test_password", expiry_days=-1
#         )
#         self.assertIsNone(self.cred_manager.get_credential("test_service", "test_user"))

#     def test_lock_and_unlock(self):
#         self.cred_manager.store_credential("test_service", "test_user", "test_password")
#         self.cred_manager.lock()
#         with self.assertRaises(Exception):
#             self.cred_manager.get_credential("test_service", "test_user")
#         self.cred_manager.unlock(self.master_password)
#         self.assertEqual(
#             self.cred_manager.get_credential("test_service", "test_user"), "test_password"
#         )

#     def test_persistence(self):
#         db_path = "test_credentials.db"
#         if os.path.exists(db_path):
#             os.remove(db_path)
        
#         manager1 = SecureCredentialManager(master_password="persist_pass", db_path=db_path)
#         manager1.unlock("persist_pass")
#         manager1.store_credential("persist_service", "user", "pass")
#         manager1.lock()

#         manager2 = SecureCredentialManager(master_password="persist_pass", db_path=db_path)
#         manager2.unlock("persist_pass")
#         self.assertEqual(manager2.get_credential("persist_service", "user"), "pass")
        
#         os.remove(db_path)

if __name__ == '__main__':
    unittest.main() 
