# app/schemas/document.py

from pydantic import BaseModel, Field
from datetime import datetime

# Used to structure the data we send back about the created Celery job
class CeleryJobStatus(BaseModel):
    job_id: str
    status: str
    message: str
    
    class Config:
        from_attributes = True

# Used to structure the data we send back after a document is uploaded
class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    status_url: str
    job_details: CeleryJobStatus
    
    class Config:
        from_attributes = True

class ChatInput(BaseModel):
    # This is a good way to structure text input for APIs
    question: str = Field(..., description="The user's question about the document.")