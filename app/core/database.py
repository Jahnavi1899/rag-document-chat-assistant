from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

# 1. Database Connection Engine
# Use the DATABASE_URL loaded from settings
# We are using the 'psycopg2' driver, hence 'postgresql+psycopg2'
# 'pool_pre_ping=True' is good practice for containerized apps
# to ensure connections are healthy.
engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True
)

# 2. Session Local
# Each request or task will get its own 'SessionLocal' instance
# to ensure thread safety. We will use this in FastAPI dependencies.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base for Data Models
# This is the base class that all of our SQLAlchemy ORM models (tables) 
# will inherit from.
Base = declarative_base()


# Dependency to get a DB session (used by FastAPI endpoints)
def get_db():
    """Dependency that yields a new SQLAlchemy session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Note: We will add the actual data models (tables) later, but this 
# boilerplate allows us to test the connection now.