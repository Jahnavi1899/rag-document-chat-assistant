# app/core/session.py
"""
Session management utilities for anonymous session-based access.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.core import models
from app.core.config import settings

# Session configuration
SESSION_COOKIE_NAME = "rag_session_id"
SESSION_TTL_DAYS = 7  # Sessions expire after 7 days
SESSION_ID_LENGTH = 32  # 32 bytes = 64 hex characters


def generate_session_id() -> str:
    """
    Generate a cryptographically secure random session ID.
    Returns a 64-character hex string.
    """
    return secrets.token_hex(SESSION_ID_LENGTH)


def create_session(db: Session) -> models.Session:
    """
    Create a new session in the database.

    Args:
        db: SQLAlchemy database session

    Returns:
        Created Session object
    """
    session_id = generate_session_id()
    expires_at = datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)

    session = models.Session(
        session_id=session_id,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_session(db: Session, session_id: str) -> Optional[models.Session]:
    """
    Retrieve a session by its ID.

    Args:
        db: SQLAlchemy database session
        session_id: The session ID to look up

    Returns:
        Session object if found and valid, None otherwise
    """
    session = db.query(models.Session).filter(
        models.Session.session_id == session_id
    ).first()

    return session


def validate_session(db: Session, session_id: str) -> Optional[models.Session]:
    """
    Validate a session ID and check if it's expired.
    Updates last_activity timestamp if valid.

    Args:
        db: SQLAlchemy database session
        session_id: The session ID to validate

    Returns:
        Session object if valid and not expired, None otherwise
    """
    if not session_id:
        return None

    session = get_session(db, session_id)

    if not session:
        return None

    # Check if session is expired
    if session.expires_at < datetime.utcnow():
        return None

    # Update last activity timestamp
    session.last_activity = datetime.utcnow()
    db.commit()

    return session


def extend_session(db: Session, session_id: str) -> Optional[models.Session]:
    """
    Extend the expiration time of a session (sliding expiration).

    Args:
        db: SQLAlchemy database session
        session_id: The session ID to extend

    Returns:
        Updated Session object if successful, None otherwise
    """
    session = get_session(db, session_id)

    if not session:
        return None

    # Extend expiration by SESSION_TTL_DAYS from now
    session.expires_at = datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)
    session.last_activity = datetime.utcnow()
    db.commit()
    db.refresh(session)

    return session


def delete_session(db: Session, session_id: str) -> bool:
    """
    Delete a session and all associated data (cascade delete).

    Args:
        db: SQLAlchemy database session
        session_id: The session ID to delete

    Returns:
        True if deleted, False if not found
    """
    session = get_session(db, session_id)

    if not session:
        return False

    db.delete(session)
    db.commit()

    return True


def get_or_create_session(db: Session, session_id: Optional[str]) -> models.Session:
    """
    Get an existing valid session or create a new one.

    Args:
        db: SQLAlchemy database session
        session_id: Optional session ID from cookie

    Returns:
        Valid Session object (existing or newly created)
    """
    if session_id:
        session = validate_session(db, session_id)
        if session:
            return session

    # Create new session if none provided or invalid
    return create_session(db)
