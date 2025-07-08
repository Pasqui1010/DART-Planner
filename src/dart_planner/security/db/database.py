"""
Database session management for DART-Planner.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 
