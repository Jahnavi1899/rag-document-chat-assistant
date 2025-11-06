# app/core/tasks.py
import os
from datetime import datetime, timezone
import time

from sqlalchemy.orm import Session
from app.core.celery_worker import celery_app
from app.core.database import SessionLocal  # We need SessionLocal to talk to the DB from the worker
from app.core import models 

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings # Open-source embeddings
from langchain_community.vectorstores import Chroma # Simple Vector Store

# Define the model to use for generating embeddings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" 
STORAGE_PATH = "storage/documents" # Same path where FastAPI saved the file

@celery_app.task(name="document.process_rag_ingestion")
def process_rag_ingestion(document_id: int):
    """
    RAG ingestion task: Load PDF -> Split -> Embed -> Store in Vector DB.
    """
    db: Session = SessionLocal()
    
    try:
        document = db.query(models.Document).filter(models.Document.id == document_id).first()
        job = db.query(models.CeleryJob).filter(models.CeleryJob.document_id == document_id).first()

        if not document or not job:
            return {"status": "FAILURE", "error": f"Document or Job not found for ID: {document_id}"}
        
        # 1. Update status
        job.status = "STARTED: Loading and Splitting"
        db.commit()

        # 2. Document Loading and Splitting (The RAG Prep)
        full_file_path = os.path.join(document.file_path)
        
        # Instantiate Loader (assuming PDF; can be extended for .txt, .docx)
        loader = PyPDFLoader(full_file_path)
        
        # Load and split the document into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = loader.load_and_split(text_splitter)

        job.status = f"STARTED: Embedding {len(chunks)} chunks"
        db.commit()

        # 3. Embedding and Vector Storage
        # NOTE: This part is CPU/time-intensive.
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
        # Use the document ID to create a unique collection name in ChromaDB
        # This links the vectors back to the specific document in Postgres
        collection_name = f"doc_{document.id}"

        # Create and persist the vector store (this generates the embeddings)
        Chroma.from_documents(
            documents=chunks, 
            embedding=embeddings, 
            collection_name=collection_name,
            persist_directory=f"{STORAGE_PATH}/chroma_db"
        )

        # 4. Final Status Update
        document.is_processed = True
        document.summary = f"RAG Index created with {len(chunks)} chunks." # Replace with real summary later
        
        job.status = "SUCCESS"
        job.end_time = datetime.now()
        job.result = f"Indexed {len(chunks)} chunks into collection {collection_name}."
        
        db.commit()
        
        print(f"SUCCESS: Document ID {document_id} RAG ingestion complete.")
        return {"status": "SUCCESS", "document_id": document_id, "chunks_indexed": len(chunks)}
        
    except Exception as e:
        # Handle Failure
        if job:
            job.status = "FAILURE"
            job.end_time = datetime.now(timezone.utc)
            job.result = f"RAG error: {str(e)}"
            db.commit()
            
        print(f"FATAL ERROR processing document {document_id}: {e}")
        return {"status": "FAILURE", "error": str(e)}
        
    finally:
        db.close()


@celery_app.task(name="session.cleanup_expired_sessions")
def cleanup_expired_sessions():
    """
    Cleanup task to remove expired sessions and their associated data.
    Should be run periodically (e.g., daily) via Celery Beat.
    """
    import shutil

    db: Session = SessionLocal()

    try:
        # Find all expired sessions
        expired_sessions = db.query(models.Session).filter(
            models.Session.expires_at < datetime.utcnow()
        ).all()

        total_cleaned = 0
        for session in expired_sessions:
            session_id = session.session_id

            # Get all documents for this session
            documents = db.query(models.Document).filter(
                models.Document.session_id == session_id
            ).all()

            # Delete physical files and ChromaDB collections
            for doc in documents:
                # Delete physical file
                if doc.file_path and os.path.exists(doc.file_path):
                    try:
                        os.remove(doc.file_path)
                        print(f"Deleted file: {doc.file_path}")
                    except Exception as e:
                        print(f"Error deleting file {doc.file_path}: {e}")

                # Delete ChromaDB collection
                collection_name = f"doc_{doc.id}"
                chroma_path = os.path.join(STORAGE_PATH, "chroma_db", collection_name)
                if os.path.exists(chroma_path):
                    try:
                        shutil.rmtree(chroma_path)
                        print(f"Deleted ChromaDB collection: {collection_name}")
                    except Exception as e:
                        print(f"Error deleting ChromaDB collection {collection_name}: {e}")

            # Delete the session (cascade will delete documents, jobs, message_store)
            db.delete(session)
            total_cleaned += 1

        db.commit()

        print(f"Session cleanup complete: Removed {total_cleaned} expired sessions")
        return {"status": "SUCCESS", "sessions_cleaned": total_cleaned}

    except Exception as e:
        db.rollback()
        print(f"FATAL ERROR in session cleanup: {e}")
        return {"status": "FAILURE", "error": str(e)}

    finally:
        db.close()