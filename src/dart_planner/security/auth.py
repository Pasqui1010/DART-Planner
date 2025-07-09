"""
Core authentication and authorization logic for DART-Planner.

This module handles user authentication, role-based access control (RBAC),
and JWT token management with unified FastAPI dependencies.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from functools import wraps

logger = logging.getLogger(__name__)

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from enum import Enum

from .db.database import get_db

# --- Configuration ---
# Use secure key manager for enhanced security
from .key_manager import get_key_manager, TokenType

# Use asymmetric algorithm for enhanced security
ALGORITHM = "RS256"

# Short-lived token configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Reduced from 30 to 15 minutes
REFRESH_TOKEN_EXPIRE_HOURS = 1    # Reduced from 7 days to 1 hour

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# --- Roles and Models ---

class Role(str, Enum):
    """Enumeration for user roles."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    PILOT = "pilot"  # Added for flight control operations

class User(BaseModel):
    """User model for API responses."""
    id: int
    username: str
    role: Role
    is_active: bool

    class Config:
        from_attributes = True

class UserSession(BaseModel):
    """User session model for web interface."""
    id: int
    username: str
    role: Role
    is_active: bool
    permissions: List[str] = []

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    """Model for creating new users."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: Role = Role.VIEWER
    is_active: bool = True

class UserUpdate(BaseModel):
    """Model for updating users."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[Role] = None
    is_active: Optional[bool] = None

class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Data model for token payload."""
    username: Optional[str] = None
    scopes: List[str] = []

class AuthManager:
    """Manages authentication, user, and token operations."""

    def __init__(self, user_service):
        self.user_service = user_service

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against a hashed one."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hashes a plain password."""
        return pwd_context.hash(password)

    def _create_token(self, data: dict, expires_delta: timedelta) -> str:
        """Helper to create a JWT using secure key manager."""
        key_manager = get_key_manager()
        try:
            token, _ = key_manager.create_jwt_token(
                payload=data,
                token_type=TokenType.JWT_ACCESS,
                expires_in=expires_delta
            )
            return token
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            raise HTTPException(status_code=500, detail="Token creation failed")

    def create_access_token(self, data: dict) -> str:
        """Creates a new short-lived access token."""
        expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        return self._create_token(data, expires)

    def create_refresh_token(self, data: dict) -> str:
        """Creates a new short-lived refresh token."""
        expires = timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
        return self._create_token(data, expires)

    async def login_for_access_token(self, form_data: OAuth2PasswordRequestForm, db: Session) -> Token:
        """Authenticates user and returns access and refresh tokens."""
        user = await self.user_service.get_user_by_username(db, form_data.username)
        if not user or not self.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = self.create_access_token(data={"sub": user.username, "scopes": [user.role.value]})
        refresh_token = self.create_refresh_token(data={"sub": user.username})

        return Token(access_token=access_token, refresh_token=refresh_token)
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
        """Decodes token and retrieves the current user using secure key manager."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        key_manager = get_key_manager()
        try:
            payload, metadata = key_manager.verify_jwt_token(token)
        except JWTError:
            raise credentials_exception
        except Exception as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(status_code=500, detail="Authentication service unavailable")

        # Check if token is revoked
        if key_manager.is_token_revoked(metadata.jti):
            raise credentials_exception

        token_data = TokenData(username=payload.get("sub"), scopes=payload.get("scopes", []))

        user = await self.user_service.get_user_by_username(db, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user

    async def get_current_active_user(self, current_user: User) -> User:
        """Get current active user."""
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

    def get_user_permissions(self, role: Role) -> List[str]:
        """Get permissions for a given role."""
        from .permissions import get_role_permissions, Permission
        permissions = get_role_permissions(role)
        return [perm.value for perm in permissions]

    def has_permission(self, user: User, permission: str) -> bool:
        """Check if user has a specific permission."""
        from .permissions import has_legacy_permission
        return has_legacy_permission(user.role, permission)

# --- Dependency Functions ---

def require_role(required_role: Role):
    """Dependency to enforce role-based access."""
    def role_checker(current_user: User):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role",
            )
        return current_user
    return role_checker

def require_permission(permission: str):
    """Dependency to enforce permission-based access."""
    def permission_checker(current_user: User, db: Session = Depends(get_db)):
        # Inject correct user service and auth manager
        from .db.service import UserService
        user_service = UserService()
        auth_manager = AuthManager(user_service=user_service)
        if not auth_manager.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required for this operation",
            )
        return current_user
    return permission_checker

def require_any_role(*roles: Role):
    """Dependency to enforce access for any of the specified roles."""
    def role_checker(current_user: User):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role",
            )
        return current_user
    return role_checker

# --- Cookie-based Authentication for Web UI ---

async def get_current_user_from_cookies(request: Request, db: Session = Depends()) -> Optional[UserSession]:
    """Get current user from cookies (for web UI)."""
    access_token = request.cookies.get("access_token")
    if not access_token or not access_token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    token = access_token.replace("Bearer ", "")
    auth_manager = AuthManager(user_service=None)  # We'll need to inject this properly
    
    try:
        user = await auth_manager.get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        # Convert to UserSession with permissions
        permissions = auth_manager.get_user_permissions(user.role)
        return UserSession(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            permissions=permissions
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

# --- Legacy compatibility functions ---

def require_auth(role: Role):
    """Legacy compatibility function - use require_role instead."""
    return require_role(role)

def require_auth_level(level: Role):
    """Legacy compatibility function - use require_role instead."""
    return require_role(level) 
