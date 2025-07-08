#!/usr/bin/env python3
"""
API tests for admin endpoints with authentication and authorization testing.

Tests both happy path scenarios and authentication/authorization failure cases.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from demos.web_demo.app import app
from dart_planner.security.auth import AuthManager, Role
from dart_planner.security.db.models import User, UserCreate, UserUpdate
from dart_planner.security.db.service import UserService


class TestAdminAPI:
    """Test cases for admin API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """Mock admin user for testing"""
        return User(
            id=1,
            username="admin",
            role=Role.ADMIN,
            is_active=True
        )
    
    @pytest.fixture
    def operator_user(self):
        """Mock operator user for testing"""
        return User(
            id=2,
            username="operator",
            role=Role.OPERATOR,
            is_active=True
        )
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock authentication manager"""
        with patch('demos.web_demo.app.auth_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_user_service(self):
        """Mock user service"""
        with patch('demos.web_demo.app.user_service') as mock:
            yield mock
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('demos.web_demo.app.get_db') as mock:
            yield mock
    
    def test_get_all_users_success(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test successful retrieval of all users by admin"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service response
        mock_users = [
            {"id": 1, "username": "admin", "role": "admin", "is_active": True},
            {"id": 2, "username": "operator", "role": "operator", "is_active": True},
            {"id": 3, "username": "pilot", "role": "pilot", "is_active": True}
        ]
        mock_user_service.get_all_users.return_value = mock_users
        
        # Make request
        response = client.get("/api/admin/users")
        
        # Assertions
        assert response.status_code == 200
        assert response.json() == mock_users
        mock_user_service.get_all_users.assert_called_once()
    
    def test_get_all_users_unauthorized(self, client, operator_user, mock_auth_manager):
        """Test unauthorized access to get all users"""
        # Mock authentication with non-admin user
        mock_auth_manager.get_current_user.return_value = operator_user
        
        # Make request
        response = client.get("/api/admin/users")
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_get_all_users_unauthenticated(self, client, mock_auth_manager):
        """Test unauthenticated access to get all users"""
        # Mock authentication failure
        mock_auth_manager.get_current_user.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
        
        # Make request
        response = client.get("/api/admin/users")
        
        # Should be unauthorized
        assert response.status_code == 401
    
    def test_create_user_success(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test successful user creation by admin"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service response
        new_user = {"id": 4, "username": "newuser", "role": "operator", "is_active": True}
        mock_user_service.create_user.return_value = new_user
        
        # Test data
        user_data = {
            "username": "newuser",
            "password": "securepassword123",
            "role": "operator"
        }
        
        # Make request
        response = client.post("/api/admin/users", json=user_data)
        
        # Assertions
        assert response.status_code == 200
        assert response.json() == new_user
        mock_user_service.create_user.assert_called_once()
    
    def test_create_user_duplicate_username(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test user creation with duplicate username"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service to raise exception
        mock_user_service.create_user.side_effect = ValueError("Username already exists")
        
        # Test data
        user_data = {
            "username": "existinguser",
            "password": "securepassword123",
            "role": "operator"
        }
        
        # Make request
        response = client.post("/api/admin/users", json=user_data)
        
        # Should handle the error gracefully
        assert response.status_code in [400, 422]
    
    def test_create_user_invalid_role(self, client, admin_user, mock_auth_manager):
        """Test user creation with invalid role"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Test data with invalid role
        user_data = {
            "username": "newuser",
            "password": "securepassword123",
            "role": "invalid_role"
        }
        
        # Make request
        response = client.post("/api/admin/users", json=user_data)
        
        # Should be validation error
        assert response.status_code == 422
    
    def test_create_user_weak_password(self, client, admin_user, mock_auth_manager):
        """Test user creation with weak password"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Test data with weak password
        user_data = {
            "username": "newuser",
            "password": "123",  # Too short
            "role": "operator"
        }
        
        # Make request
        response = client.post("/api/admin/users", json=user_data)
        
        # Should be validation error
        assert response.status_code == 422
    
    def test_create_user_unauthorized(self, client, operator_user, mock_auth_manager):
        """Test unauthorized user creation"""
        # Mock authentication with non-admin user
        mock_auth_manager.get_current_user.return_value = operator_user
        
        # Test data
        user_data = {
            "username": "newuser",
            "password": "securepassword123",
            "role": "operator"
        }
        
        # Make request
        response = client.post("/api/admin/users", json=user_data)
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_update_user_success(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test successful user role update by admin"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service response
        updated_user = {"id": 2, "username": "operator", "role": "pilot", "is_active": True}
        mock_user_service.update_user_role.return_value = updated_user
        
        # Test data
        update_data = {"role": "pilot"}
        
        # Make request
        response = client.put("/api/admin/users/2", json=update_data)
        
        # Assertions
        assert response.status_code == 200
        assert response.json() == updated_user
        mock_user_service.update_user_role.assert_called_once()
    
    def test_update_user_not_found(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test updating non-existent user"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service to raise exception
        mock_user_service.update_user_role.side_effect = ValueError("User not found")
        
        # Test data
        update_data = {"role": "pilot"}
        
        # Make request
        response = client.put("/api/admin/users/999", json=update_data)
        
        # Should handle the error gracefully
        assert response.status_code in [400, 404]
    
    def test_update_user_invalid_role(self, client, admin_user, mock_auth_manager):
        """Test user update with invalid role"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Test data with invalid role
        update_data = {"role": "invalid_role"}
        
        # Make request
        response = client.put("/api/admin/users/2", json=update_data)
        
        # Should be validation error
        assert response.status_code == 422
    
    def test_update_user_unauthorized(self, client, operator_user, mock_auth_manager):
        """Test unauthorized user update"""
        # Mock authentication with non-admin user
        mock_auth_manager.get_current_user.return_value = operator_user
        
        # Test data
        update_data = {"role": "pilot"}
        
        # Make request
        response = client.put("/api/admin/users/2", json=update_data)
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_delete_user_success(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test successful user deletion by admin"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service response
        mock_user_service.delete_user.return_value = {"message": "User deleted successfully"}
        
        # Make request
        response = client.delete("/api/admin/users/3")
        
        # Assertions
        assert response.status_code == 200
        assert response.json() == {"message": "User deleted successfully"}
        mock_user_service.delete_user.assert_called_once()
    
    def test_delete_user_not_found(self, client, admin_user, mock_auth_manager, mock_user_service, mock_db_session):
        """Test deleting non-existent user"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service to raise exception
        mock_user_service.delete_user.side_effect = ValueError("User not found")
        
        # Make request
        response = client.delete("/api/admin/users/999")
        
        # Should handle the error gracefully
        assert response.status_code in [400, 404]
    
    def test_delete_user_unauthorized(self, client, operator_user, mock_auth_manager):
        """Test unauthorized user deletion"""
        # Mock authentication with non-admin user
        mock_auth_manager.get_current_user.return_value = operator_user
        
        # Make request
        response = client.delete("/api/admin/users/3")
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_get_roles_success(self, client, admin_user, mock_auth_manager):
        """Test successful retrieval of available roles"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Make request
        response = client.get("/api/admin/roles")
        
        # Assertions
        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)
        assert "admin" in roles
        assert "operator" in roles
        assert "pilot" in roles
        assert "viewer" in roles
    
    def test_get_roles_unauthorized(self, client, operator_user, mock_auth_manager):
        """Test unauthorized access to roles"""
        # Mock authentication with non-admin user
        mock_auth_manager.get_current_user.return_value = operator_user
        
        # Make request
        response = client.get("/api/admin/roles")
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_get_roles_unauthenticated(self, client, mock_auth_manager):
        """Test unauthenticated access to roles"""
        # Mock authentication failure
        mock_auth_manager.get_current_user.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
        
        # Make request
        response = client.get("/api/admin/roles")
        
        # Should be unauthorized
        assert response.status_code == 401


class TestAdminAPIIntegration:
    """Integration tests for admin API with full authentication flow"""
    
    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_credentials(self):
        """Admin user credentials for testing"""
        return {
            "username": "admin",
            "password": "dart_admin_2025"
        }
    
    @pytest.fixture
    def operator_credentials(self):
        """Operator user credentials for testing"""
        return {
            "username": "operator",
            "password": "dart_ops_2025"
        }
    
    def test_full_admin_workflow(self, client, admin_credentials):
        """Test complete admin workflow: login, create user, update user, delete user"""
        # Step 1: Login as admin
        login_response = client.post("/api/login", json=admin_credentials)
        assert login_response.status_code == 200
        
        # Get cookies from login response
        cookies = login_response.cookies
        
        # Step 2: Get all users
        users_response = client.get("/api/admin/users", cookies=cookies)
        assert users_response.status_code == 200
        
        # Step 3: Create new user
        new_user_data = {
            "username": "testuser",
            "password": "testpass123",
            "role": "operator"
        }
        create_response = client.post("/api/admin/users", json=new_user_data, cookies=cookies)
        assert create_response.status_code == 200
        
        # Step 4: Update user role
        update_data = {"role": "pilot"}
        update_response = client.put("/api/admin/users/1", json=update_data, cookies=cookies)
        assert update_response.status_code == 200
        
        # Step 5: Delete user
        delete_response = client.delete("/api/admin/users/1", cookies=cookies)
        assert delete_response.status_code == 200
    
    def test_admin_access_control(self, client, operator_credentials):
        """Test that non-admin users cannot access admin endpoints"""
        # Login as operator
        login_response = client.post("/api/login", json=operator_credentials)
        assert login_response.status_code == 200
        
        cookies = login_response.cookies
        
        # Try to access admin endpoints
        admin_endpoints = [
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/users"),
            ("PUT", "/api/admin/users/1"),
            ("DELETE", "/api/admin/users/1"),
            ("GET", "/api/admin/roles")
        ]
        
        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = client.get(endpoint, cookies=cookies)
            elif method == "POST":
                response = client.post(endpoint, json={}, cookies=cookies)
            elif method == "PUT":
                response = client.put(endpoint, json={}, cookies=cookies)
            elif method == "DELETE":
                response = client.delete(endpoint, cookies=cookies)
            
            # All should be forbidden
            assert response.status_code == 403, f"Endpoint {endpoint} should be forbidden for operators"
    
    def test_authentication_required(self, client):
        """Test that all admin endpoints require authentication"""
        admin_endpoints = [
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/users"),
            ("PUT", "/api/admin/users/1"),
            ("DELETE", "/api/admin/users/1"),
            ("GET", "/api/admin/roles")
        ]
        
        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            # All should require authentication
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"


class TestAdminAPIErrorHandling:
    """Test error handling in admin API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """Mock admin user for testing"""
        return User(
            id=1,
            username="admin",
            role=Role.ADMIN,
            is_active=True
        )
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock authentication manager"""
        with patch('demos.web_demo.app.auth_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_user_service(self):
        """Mock user service"""
        with patch('demos.web_demo.app.user_service') as mock:
            yield mock
    
    def test_database_connection_error(self, client, admin_user, mock_auth_manager, mock_user_service):
        """Test handling of database connection errors"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock database error
        mock_user_service.get_all_users.side_effect = Exception("Database connection failed")
        
        # Make request
        response = client.get("/api/admin/users")
        
        # Should handle database error gracefully
        assert response.status_code == 500
    
    def test_invalid_json_payload(self, client, admin_user, mock_auth_manager):
        """Test handling of invalid JSON payloads"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Make request with invalid JSON
        response = client.post(
            "/api/admin/users",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return bad request
        assert response.status_code == 400
    
    def test_missing_required_fields(self, client, admin_user, mock_auth_manager):
        """Test handling of missing required fields"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Test data missing required fields
        incomplete_data = {"username": "testuser"}  # Missing password and role
        
        # Make request
        response = client.post("/api/admin/users", json=incomplete_data)
        
        # Should be validation error
        assert response.status_code == 422
    
    def test_rate_limiting(self, client, admin_user, mock_auth_manager, mock_user_service):
        """Test rate limiting on admin endpoints"""
        # Mock authentication
        mock_auth_manager.get_current_user.return_value = admin_user
        
        # Mock user service response
        mock_user_service.get_all_users.return_value = []
        
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get("/api/admin/users")
            responses.append(response.status_code)
        
        # All should succeed (rate limiting not implemented in this version)
        # In a production system, some might return 429 (Too Many Requests)
        assert all(status == 200 for status in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
