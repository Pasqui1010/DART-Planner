"""
Tests for the FastAPI Gateway and SecureMiddleware
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Make sure our app is importable
import sys
import os

# The app needs to be imported after the path is set
from demos.web_demo.app import app, auth_manager
from dart_planner.security.validation import ValidationError
from dart_planner.security.auth import Role, User

# Use a test client for making requests to the FastAPI app
client = TestClient(app)

# --- Test Data and Mocks ---

@pytest.fixture
def mock_auth_manager():
    """Fixture to mock the AuthManager for controlled testing."""
    with patch('app.auth_manager', spec=True) as mock_auth:
        yield mock_auth

@pytest.fixture
def valid_pilot_token(mock_auth_manager):
    """Fixture to simulate a valid pilot session."""
    mock_session = MagicMock()
    mock_session.user_id = "test_pilot"
    mock_session.auth_level.value = 2 # PILOT
    mock_auth_manager.validate_token.return_value = mock_session
    return "valid_pilot_token"

@pytest.fixture
def valid_operator_token(mock_auth_manager):
    """Fixture to simulate a valid operator session."""
    mock_session = MagicMock()
    mock_session.user_id = "test_operator"
    mock_session.auth_level.value = 1 # OPERATOR
    mock_auth_manager.validate_token.return_value = mock_session
    return "valid_operator_token"

# --- Middleware Tests ---

def test_missing_token_is_rejected(mock_auth_manager):
    """Requests without an Authorization header should be rejected."""
    response = client.post("/api/start_demo")
    assert response.status_code == 401
    assert "Missing or invalid Bearer token" in response.json()["detail"]

def test_invalid_token_is_rejected(mock_auth_manager):
    """Requests with an invalid token should be rejected."""
    mock_auth_manager.validate_token.return_value = None
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post("/api/start_demo", headers=headers)
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]

# --- Endpoint Permission Tests ---

def test_start_demo_requires_pilot(valid_operator_token):
    """Test that starting the demo requires PILOT level permissions."""
    headers = {"Authorization": f"Bearer {valid_operator_token}"}
    response = client.post("/api/start_demo", headers=headers)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]

def test_start_demo_allowed_for_pilot(valid_pilot_token):
    """Test that a pilot can successfully start the demo."""
    headers = {"Authorization": f"Bearer {valid_pilot_token}"}
    # We expect a 200 OK, assuming the demo runner itself works
    with patch('app.demo_runner.start_demo') as mock_start:
        response = client.post("/api/start_demo", headers=headers)
        assert response.status_code == 200
        mock_start.assert_called_once()

def test_set_target_allowed_for_operator(valid_operator_token):
    """Test that an operator can set a target."""
    headers = {"Authorization": f"Bearer {valid_operator_token}"}
    # Mock the validator to avoid dependency on its logic
    with patch('app.input_validator.validate_coordinate') as mock_validate:
        mock_validate.return_value = {"x": 1, "y": 2, "z": 3}
        response = client.post("/api/set_target", headers=headers, json={"x": 1, "y": 2, "z": 3})
        assert response.status_code == 200

# --- Input Validation Tests ---

def test_set_target_with_invalid_payload_is_rejected(valid_operator_token):
    """Test that the middleware (or endpoint) rejects invalid data."""
    headers = {"Authorization": f"Bearer {valid_operator_token}"}
    # This payload is missing required fields for a coordinate
    with patch('app.input_validator.validate_coordinate', side_effect=ValidationError("Invalid coordinate")) as mock_validate:
        response = client.post("/api/set_target", headers=headers, json={"foo": "bar"})
        assert response.status_code == 422 # Unprocessable Entity
        assert "Validation Error" in response.json()["detail"]

def test_login_endpoint_works_unprotected():
    """The /api/login endpoint should be accessible without a token."""
    with patch('app.auth_manager.authenticate') as mock_auth:
        mock_session = MagicMock()
        mock_session.token = "new_token"
        mock_session.user_id = "test_user"
        mock_session.auth_level.name = "PILOT"
        mock_auth.return_value = mock_session
        
        response = client.post("/api/login", json={"username": "user", "password": "pw"})
        assert response.status_code == 200
        assert "token" in response.json()

def test_docs_are_accessible_unprotected():
    """The OpenAPI docs should be accessible without a token."""
    response = client.get("/docs")
    assert response.status_code == 200 
