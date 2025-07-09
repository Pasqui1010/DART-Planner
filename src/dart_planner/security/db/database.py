"""
Database session management for DART-Planner.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# Default to a user-specific directory for the database
# Can be overridden by the DART_DB_URL environment variable
DEFAULT_DB_URL = "sqlite:///" + os.path.expanduser("~/.dart_planner/auth.db")
DATABASE_URL = os.getenv("DART_DB_URL", DEFAULT_DB_URL)

# Ensure the database directory exists
db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
if "sqlite" in DATABASE_URL and not os.path.exists(db_dir):
    os.makedirs(db_dir)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=QueuePool if "sqlite" in DATABASE_URL else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating tables and seeding default users.
    This is an idempotent operation.
    """
    from .models import Base
    from ..auth import Role
    from .service import UserService

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user_service = UserService()
        
        # Check for and create admin user
        admin = user_service.get_user_by_username(db, "admin")
        if not admin:
            print("Creating default admin user...")
            user_service.create_user(db, "admin", "admin123", Role.ADMIN)
            print("✓ Admin user created.")

        # Check for and create pilot user
        pilot = user_service.get_user_by_username(db, "pilot")
        if not pilot:
            print("Creating default pilot user...")
            user_service.create_user(db, "pilot", "pilot123", Role.PILOT)
            print("✓ Pilot user created.")

        # Check for and create operator user
        operator = user_service.get_user_by_username(db, "operator")
        if not operator:
            print("Creating default operator user...")
            user_service.create_user(db, "operator", "operator123", Role.OPERATOR)
            print("✓ Operator user created.")

    finally:
        db.close() 
