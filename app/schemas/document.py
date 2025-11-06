# app/schemas/document.py

from pydantic import BaseModel, Field
from datetime import datetime

class CeleryJobStatus(BaseModel):
    job_id: str
    status: str
    message: str
    
    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    status_url: str
    job_details: CeleryJobStatus
    
    class Config:
        from_attributes = True

class ChatInput(BaseModel):
    question: str = Field(..., description="The user's question about the document.")

class ChatPayload(BaseModel):
    question: str

class DocumentInfo(BaseModel):
    id: int
    filename: str
    is_processed: bool
