from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import shutil
import os
import asyncio
from uuid import uuid4

from app.core.database import engine, get_db, Base
from app.core.config import settings
from app.core import models
from app.core.middleware import SessionMiddleware
from app.schemas.document import DocumentUploadResponse, CeleryJobStatus, ChatPayload, DocumentInfo
from app.core.tasks import process_rag_ingestion

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import PostgresChatMessageHistory

global_embeddings = None

# Configuration constants
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
STORAGE_PATH = "storage/documents"
MAX_HISTORY_MESSAGES = 10  # Limit chat history to last 10 messages


def create_tables():
    """Create all database tables defined by SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="RAG Document Chat Assistant",
    version="0.2.0",
    description="Session-based RAG document chat system"
)

# Add session middleware (must be added before CORS)
app.add_middleware(SessionMiddleware)

# Configure CORS - update allow_origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local Vite dev server
        "http://localhost:3000",  # Alternative local port
        "*"  # TODO: Replace with specific frontend domain in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["*"]
)

# Run the table creation on startup
@app.on_event("startup")
def startup_event():
    """Initialize database tables and RAG components on application startup."""
    print("FastAPI application startup: Attempting to connect to PostgreSQL...")
    try:
        create_tables()
        print("Successfully connected to PostgreSQL and created tables.")
    except Exception as e:
        print(f"ERROR: Could not connect to PostgreSQL. {e}")
        raise RuntimeError(f"Database connection failure during startup: {e}")

    try:
        global global_embeddings

        # Initialize embeddings model (loaded once and reused)
        print("Initializing embeddings model (this may take time)...")
        global_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        print("Embeddings model initialized successfully.")

        # Ensure storage directory exists
        os.makedirs(STORAGE_PATH, exist_ok=True)
        print(f"Storage directory verified: {STORAGE_PATH}")

    except Exception as e:
        print(f"FATAL RAG INITIALIZATION ERROR: {e}")
        raise RuntimeError(f"Failed to load RAG components: {e}")

# Test Endpoint for DB connectivity
@app.get("/health/db")
def check_db_health(db: Session = Depends(get_db)):
    """Simple health check that ensures the DB is responsive."""
    try:
        db.execute(text('SELECT 1'))
        return {"status": "ok", "service": "PostgreSQL", "message": "Database connection verified."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PostgreSQL connection failed: {e}")

# Simple main health check
@app.get("/health")
def main_health_check():
    return {"status": "ok", "service": "FastAPI", "message": "API is running."}

@app.post("/api/v1/documents/upload", response_model=DocumentUploadResponse, status_code=202)
def upload_document(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Accepts a document upload, saves it, creates metadata, and
    dispatches an asynchronous RAG ingestion job.
    Session is automatically managed by middleware.
    """
    # Get session from middleware (attached to request.state)
    session_id = request.state.session_id
    db = request.state.db

    # Validate file type
    if not file.filename.endswith(('.pdf', '.txt')):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported"
        )

    # Save the physical file locally (use a unique name)
    unique_filename = f"{uuid4()}_{file.filename}"
    file_location = os.path.join(STORAGE_PATH, unique_filename)

    try:
        # Ensure storage directory exists
        os.makedirs(STORAGE_PATH, exist_ok=True)

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create Document metadata record in PostgreSQL
        document = models.Document(
            filename=file.filename,
            file_path=file_location,
            session_id=session_id,
            is_processed=False
        )
        db.add(document)
        db.commit()
        db.refresh(document)  # Refresh to get the auto-generated ID

        # Dispatch Celery Task
        task = process_rag_ingestion.delay(document.id)

        # Create CeleryJob tracking record in PostgreSQL
        job = models.CeleryJob(
            document_id=document.id,
            celery_task_id=task.id,
            status=task.status
        )
        db.add(job)
        db.commit()

        # Return 202 Accepted status with job details
        return DocumentUploadResponse(
            document_id=document.id,
            filename=document.filename,
            status_url=f"/api/v1/jobs/status/{task.id}",
            job_details=CeleryJobStatus(
                job_id=task.id,
                status=task.status,
                message="Task dispatched to worker."
            )
        )

    except Exception as e:
        db.rollback()
        # Clean up the file if database operation failed
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@app.get("/api/v1/jobs/status/{task_id}", response_model=CeleryJobStatus)
def get_job_status(request: Request, task_id: str):
    """
    Allows the client to poll for the current status of a RAG ingestion job.
    Validates that the job belongs to the current session.
    """
    session_id = request.state.session_id
    db = request.state.db

    # Get the job and verify it belongs to the current session
    job = db.query(models.CeleryJob).join(models.Document).filter(
        models.CeleryJob.celery_task_id == task_id,
        models.Document.session_id == session_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found or does not belong to your session"
        )

    return CeleryJobStatus(
        job_id=job.celery_task_id,
        status=job.status,
        message=job.result or "Job is currently in progress."
    )

def format_docs(docs):
    """Formats a list of retrieved Document objects into a single string for the prompt context."""
    return "\n\n".join(doc.page_content for doc in docs)

@app.post("/api/v1/documents/{document_id}/chat")
async def chat_with_document(
    request: Request,
    document_id: int,
    payload: ChatPayload
):
    """
    Implements the full RAG pipeline with session-based access control.
    Uses streaming responses for real-time token delivery.
    """
    session_id = request.state.session_id
    db = request.state.db
    question = payload.question

    # Verify document belongs to session and is processed
    document = db.query(models.Document).filter(
        models.Document.id == document_id,
        models.Document.session_id == session_id,
        models.Document.is_processed == True
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found, not processed, or does not belong to your session"
        )

    try:
        # Load the Vector Store for this document
        collection_name = f"doc_{document_id}"
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=global_embeddings,
            persist_directory=f"{STORAGE_PATH}/chroma_db"
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

        # Initialize LLM (using a valid OpenAI model)
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        # Chat history management (session-scoped)
        chat_session_id = f"{session_id}_doc_{document_id}"
        message_history = PostgresChatMessageHistory(
            connection_string=settings.DATABASE_URL,
            session_id=chat_session_id,
            table_name=models.MessageStore.__tablename__
        )

        # Load chat history and limit to MAX_HISTORY_MESSAGES
        loaded_history = message_history.messages[-MAX_HISTORY_MESSAGES:] if message_history.messages else []
        
        # --- 4. Sub-Chain 1: Question Rephrasing (Condenser) ---
        # This sub-chain uses the history to create a standalone query.
        condenser_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system", 
                    """Given the chat history and the latest user question, formulate a standalone question 
                    "that can be fully understood without the chat history. Return ONLY the question string and nothing else."""
                ),
                MessagesPlaceholder(variable_name="chat_history"), 
                ("human", "{question}"),
            ]
        )

        # Condenser Runnable: uses LLM to rephrase the question
        condenser_chain = (
            condenser_prompt 
            | llm.with_config(run_name="Condenser_LLM")
            | StrOutputParser()
        )

        # --- 5. Main Retrieval Logic ---
        # Logic to decide which question to use for retrieval: 
        # If history exists, use the condensed query; otherwise, use the original question.
        async def get_retrieval_query(chain_input: dict):
            if not chain_input["chat_history"]:
                # If no history, just use the original question (input)
                return chain_input["question"]
            else:
                # If history exists, run the condenser chain to get the standalone query
                return await condenser_chain.ainvoke(chain_input)
                
        # --- 6. Final RAG Chain Composition ---
        
        # The main question-answering prompt template
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    # Ensure the instruction is direct and firm:
                    """You are an expert Q&A system. Use ONLY the following pieces of retrieved context 
                    to answer the question. If the answer is not contained in the context, you MUST
                    state: 'I don't have enough information in the document to answer that.' 
                    "CONTEXT:\n{context}""",
                ),
                ("human", "{question}"),
            ]
        )

        # The full RAG chain defines the sequence: 
        final_rag_chain = (
            # 1. RunnablePassthrough: Input is {"question": question, "chat_history": history}
            # We assign the necessary variables and retrieve context based on the result of get_retrieval_query
            RunnablePassthrough.assign(
                chat_history=lambda x: loaded_history, # Inject history
                # Retrieve context using the function that generates the query
                context=get_retrieval_query | retriever | format_docs 
            )
            # 2. Assemble the final prompt (Input: {context, question})
            | qa_prompt
            # 3. Generation (LLM Call)
            | llm.with_config(run_name="Final_QA_LLM") 
            # 4. Parsing
            | StrOutputParser()
        )

        async def stream_response_generator():
            """Generate streaming response and save to chat history."""
            full_response = ""
            async for chunk in final_rag_chain.astream({"question": question, "chat_history": loaded_history}):
                if chunk:
                    full_response += chunk
                    yield chunk.encode("utf-8")

            # Save the conversation to chat history
            message_history.add_user_message(question)
            message_history.add_ai_message(full_response)

        return StreamingResponse(
            stream_response_generator(),
            media_type="text/plain"
        )

    except Exception as e:
        error_message = "An error occurred during chat processing."
        if "API_KEY" in str(e) or "authentication" in str(e):
            error_message = "LLM API Key configuration error. Please check OPENAI_API_KEY."

        raise HTTPException(status_code=500, detail=error_message)
    
@app.get("/api/v1/documents", response_model=list[DocumentInfo])
def list_documents(request: Request):
    """
    Retrieves metadata for all processed documents belonging to the current session.
    """
    session_id = request.state.session_id
    db = request.state.db

    documents = db.query(models.Document).filter(
        models.Document.session_id == session_id,
        models.Document.is_processed == True
    ).order_by(models.Document.upload_time.desc()).all()

    return [
        DocumentInfo(id=d.id, filename=d.filename, is_processed=d.is_processed)
        for d in documents
    ]