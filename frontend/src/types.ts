export interface APIError{
    detail: string;
}

export interface ChatPayload{
    question: string;
}

export interface UploadResponse{
    document_id: number;
    filename: string;
    status_url: string;
    job_details:{
        job_id: string;
        status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
        message: string;
    }
}

export interface JobStatusResponse{
    job_id: string;
    status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
    message: string;
}

export interface Message{
    role: 'user' | 'ai';
    content: string;
}

export interface DocumentInfo {
  id: number;
  filename: string;
}

