from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base # Import the Base class we defined earlier
from sqlalchemy.dialects.postgresql import JSONB

# --- 1. User Model ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    # Documents relationship defines how to get all documents uploaded by this user
    documents = relationship("Document", back_populates="owner")

# --- 2. Document Model (Metadata) ---
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True, nullable=False)
    file_path = Column(String, nullable=False)  # Local path where the raw file is stored
    summary = Column(Text, nullable=True)       # The LLM-generated summary
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    is_processed = Column(Boolean, default=False, nullable=False)
    
    # Foreign Key relationship
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="documents")
    
    # Relationship to the async job tracking the ingestion process
    job = relationship("CeleryJob", back_populates="document", uselist=False)

# --- 3. Celery Job Tracking Model ---
class CeleryJob(Base):
    __tablename__ = "celery_jobs"
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key back to the document being processed
    document_id = Column(Integer, ForeignKey("documents.id"), unique=True, nullable=False)
    document = relationship("Document", back_populates="job")

    # Status fields
    celery_task_id = Column(String, unique=True, index=True, nullable=False) # The ID used by Celery/Redis
    status = Column(String, default="PENDING", nullable=False)             # PENDING, STARTED, SUCCESS, FAILURE
    result = Column(Text, nullable=True)                                    # Store error messages or completion details
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)

# --- 4. Chat History Model (for LangChain Memory) ---
class MessageStore(Base):
    __tablename__ = "message_store"
    
    id = Column(Integer, primary_key=True)
    # Session ID links the conversation to the document and user
    session_id = Column(String, index=True, nullable=False) 
    
    # Store messages as JSONB (PostgreSQL's high-performance JSON type)
    message = Column(JSONB, nullable=False)
    
    # Optional: Indexing for fast retrieval by session
    __table_args__ = (
        Index("idx_message_store_session_id", "session_id"),
    )