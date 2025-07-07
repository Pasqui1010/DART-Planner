"""
Service layer for database operations related to users and tokens.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from . import models, database
from ..auth import Role, User as PydanticUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    """Handles all database interactions for users and tokens."""

    def get_password_hash(self, password: str) -> str:
        """Hashes a password using bcrypt."""
        return pwd_context.hash(password)

    async def get_user_by_username(self, db: Session, username: str) -> Optional[models.User]:
        """Fetches a user by their username."""
        return db.query(models.User).filter(models.User.username == username).first()

    async def get_user(self, db: Session, user_id: int) -> Optional[models.User]:
        """Fetches a user by their ID."""
        return db.query(models.User).filter(models.User.id == user_id).first()

    async def get_all_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
        """Fetches all users with pagination."""
        return db.query(models.User).offset(skip).limit(limit).all()

    async def create_user(self, db: Session, username: str, password: str, role: Role) -> models.User:
        """Creates a new user in the database."""
        hashed_password = self.get_password_hash(password)
        db_user = models.User(username=username, hashed_password=hashed_password, role=role)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    async def delete_user(self, db: Session, user_id: int) -> Optional[models.User]:
        """Deletes a user from the database."""
        user = await self.get_user(db, user_id)
        if user:
            db.delete(user)
            db.commit()
        return user

    async def update_user_role(self, db: Session, user_id: int, new_role: Role) -> Optional[models.User]:
        """Updates a user's role."""
        user = await self.get_user(db, user_id)
        if user:
            user.role = new_role
            db.commit()
            db.refresh(user)
        return user

    async def revoke_token(self, db: Session, jti: str, user_id: int):
        """Adds a token's JTI to the revocation list."""
        revoked_token = models.RevokedToken(jti=jti, user_id=user_id)
        db.add(revoked_token)
        db.commit()

    async def is_token_revoked(self, db: Session, jti: str) -> bool:
        """Checks if a token's JTI is in the revocation list."""
        return db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first() is not None 