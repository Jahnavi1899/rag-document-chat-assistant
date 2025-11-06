from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base # Import the Base class we defined earlier
from sqlalchemy.dialects.postgresql import JSONB

# --- 1. Session Model (for tracking session metadata and cleanup) ---
class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationship to documents
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")

# --- 2. Document Model (Metadata) ---
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True, nullable=False)
    file_path = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    is_processed = Column(Boolean, default=False, nullable=False)

    # Session-based ownership
    session_id = Column(String(64), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    session = relationship("Session", back_populates="documents")

    # Relationship to the async job tracking the ingestion process
    job = relationship("CeleryJob", back_populates="document", uselist=False)

    # Composite index for common queries
    __table_args__ = (
        Index("idx_document_session_processed", "session_id", "is_processed"),
    )

# --- 3. Celery Job Tracking Model ---
class CeleryJob(Base):
    __tablename__ = "celery_jobs"
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key back to the document being processed
    document_id = Column(Integer, ForeignKey("documents.id"), unique=True, nullable=False)
    document = relationship("Document", back_populates="job")

    # Status fields
    celery_task_id = Column(String, unique=True, index=True, nullable=False) 
    status = Column(String, default="PENDING", nullable=False)             
    result = Column(Text, nullable=True)                                    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)

# --- 4. Chat History Model (for LangChain Memory) ---
class MessageStore(Base):
    __tablename__ = "message_store"
    
    id = Column(Integer, primary_key=True)
    # Session ID links the conversation to the document and user
    session_id = Column(String, index=True, nullable=False) 
    message = Column(JSONB, nullable=False)
    
    # Optional: Indexing for fast retrieval by session
    __table_args__ = (
        Index("idx_message_store_session_id", "session_id"),
    )

