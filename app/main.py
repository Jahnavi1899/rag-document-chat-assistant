from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from app.core.database import engine, get_db, Base
from app.core.config import settings
from sqlalchemy import text
from app.core import models
from app.schemas.document import DocumentUploadResponse, CeleryJobStatus, ChatInput
from app.core.tasks import process_rag_ingestion
import shutil
import os 
from uuid import uuid4
import json
from redis import Redis
from app.core.config import settings

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import PostgresChatMessageHistory

# This line is crucial: it attempts to create tables defined 
# by 'Base' (we have none yet, but it verifies connection)
# NOTE: In a production setting, you would use Alembic for migrations,
# but for development, this is a quick way to ensure the DB is accessible.
def create_tables():
    # Attempt to create tables defined by Base (currently none)
    # This also acts as a basic connection test
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.DB_NAME.upper(), 
    version="0.1.0"
)

# Mock user for simplicity (In a real app, this would come from auth)
MOCK_USER_ID = 1 
# Define the model names 
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" 
STORAGE_PATH = "storage/documents" 
redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
REDIS_CACHE_TTL = 3600 # 1 hour
MAX_HISTORY_MESSAGES = 10 # keep the last 100 messages as context for chat history

# Run the table creation on startup
@app.on_event("startup")
def startup_event():
    print("FastAPI application startup: Attempting to connect to PostgreSQL...")
    try:
        create_tables()
        print("Successfully connected to PostgreSQL.")
    except Exception as e:
        print(f"ERROR: Could not connect to PostgreSQL. {e}")
        # In a real app, you might want to fail startup here
        raise HTTPException(status_code=500, detail="Database connection failure during startup.")

# Test Endpoint for DB connectivity
@app.get("/health/db")
def check_db_health(db: Session = Depends(get_db)):
    """Simple health check that ensures the DB is responsive."""
    try:
        # Execute a simple query to confirm the connection is active
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
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    Accepts a document upload, saves it, creates metadata, and 
    dispatches an asynchronous RAG ingestion job.
    """
    
    # 1. Ensure Mock User exists (setup for ForeignKey)
    user = db.query(models.User).filter(models.User.id == MOCK_USER_ID).first()
    if not user:
        # Create a mock user if one doesn't exist for testing
        user = models.User(id=MOCK_USER_ID, username="user1")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Save the physical file locally (use a unique name)
    unique_filename = f"{uuid4()}_{file.filename}"
    file_location = os.path.join("storage/documents", unique_filename)
    
    try:
        with open(file_location, "wb") as buffer:
            # Use shutil to copy the uploaded file stream to the disk
            shutil.copyfileobj(file.file, buffer)
            
        # 3. Create Document metadata record in PostgreSQL
        document = models.Document(
            filename=file.filename,
            file_path=file_location,
            owner_id=user.id,
            is_processed=False
        )
        db.add(document)
        db.commit()
        db.refresh(document) # why this refersh is there?

        # 4. Dispatch Celery Task
        # Send the document ID as the argument. The task will look up the rest.
        task = process_rag_ingestion.delay(document.id) 
        
        # 5. Create CeleryJob tracking record in PostgreSQL
        job = models.CeleryJob(
            document_id=document.id,
            celery_task_id=task.id,
            status=task.status
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 6. Return 202 Accepted status with job details
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
        raise HTTPException(status_code=500, detail=f"File processing failed: {e}")

# --- NEW ENDPOINT FOR JOB STATUS CHECK (POLLING) ---

@app.get("/api/v1/jobs/status/{task_id}", response_model=CeleryJobStatus)
def get_job_status(task_id: str, db: Session = Depends(get_db)):
    """
    Allows the client to poll for the current status of a RAG ingestion job.
    """
    job = db.query(models.CeleryJob).filter(models.CeleryJob.celery_task_id == task_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    return CeleryJobStatus(
        job_id=job.celery_task_id,
        status=job.status,
        message=job.result or "Job is currently in progress."
    )


def format_docs(docs):
    """Formats a list of retrieved Document objects into a single string for the prompt context."""
    return "\n\n".join(doc.page_content for doc in docs)


@app.post("/api/v1/documents/{document_id}/chat")
def chat_with_document(
    document_id: int, 
    question: str,
    db: Session = Depends(get_db)
):
    """
    Implements the full RAG pipeline using pure LCEL (Runnable) components, 
    bypassing unstable wrapper chains.
    """
    
    # 1. Verification (Crucial Backend Step)
    document = db.query(models.Document).filter(
        models.Document.id == document_id, 
        models.Document.owner_id == MOCK_USER_ID
    ).first()

    if not document or not document.is_processed:
        raise HTTPException(status_code=400, detail="Document not found or not processed.")

    try:
        # Check Redis Cache first
        # cache_key = f"rag_cache:{document_id}:{question}"
        # cached_answer = redis_client.get(cache_key)
        # if cached_answer:
        #     print(f"Cache hit for key: {cache_key}")
        #     return {"answer": cached_answer}
        
        # 2. Initialize RAG Components
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        collection_name = f"doc_{document_id}"
        
        # Load the Vector Store (Retriever Source)
        vectorstore = Chroma(
            collection_name=collection_name, 
            embedding_function=embeddings, 
            persist_directory=f"{STORAGE_PATH}/chroma_db"
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4}) # Retrieve top 4 chunks
        print("Step 2 complete")
        # 3. Define the LLM and Prompt
        llm = ChatOpenAI(model_name="gpt-5-nano", temperature=0) 

        # Define the template for the final LLM call (Augmentation)
        # template = """
        # You are an expert Q&A system. Use the following context to answer the user's question. 
        # If the answer is not in the context, state clearly, "I don't have enough information in the document to answer that."

        # CONTEXT:
        # {context}

        # QUESTION:
        # {question}
        # """
        
        # qa_prompt = ChatPromptTemplate.from_template(template) # Using the core method
        session_id = f"{MOCK_USER_ID}_doc_{document_id}"
        message_history = PostgresChatMessageHistory(
            connection_string=settings.DATABASE_URL, 
            session_id=session_id, 
            table_name=models.MessageStore.__tablename__
        )

        # Load chat history for injecting into the chains
        loaded_history = message_history.messages
        
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
        def get_retrieval_query(chain_input: dict):
            if not chain_input["chat_history"]:
                # If no history, just use the original question (input)
                return chain_input["question"]
            else:
                # If history exists, run the condenser chain to get the standalone query
                return condenser_chain.invoke(chain_input)
                
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
        
        # 7. Run the Query
        final_answer = final_rag_chain.invoke({"question": question, "chat_history": loaded_history})
        
        # 8. Save the new messages (CRITICAL MEMORY STEP)
        message_history.add_user_message(question)
        message_history.add_ai_message(final_answer) 
        
        return {"answer": final_answer}
        
    except Exception as e:
        # Robust Error Handling (Employer skill)
        error_message = f"RAG Chat failed: {e}"
        if "API_KEY" in str(e) or "authentication" in str(e):
             error_message = "LLM API Key configuration error. Please check OPENAI_API_KEY."
        
        raise HTTPException(status_code=500, detail=error_message)