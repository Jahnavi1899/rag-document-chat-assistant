import { useState } from 'react';
import { UploadResponse, JobStatusResponse } from './types';

interface UploadComponentProps {
    onProcessingStart: () => void;
    onProcessingComplete: (documentId: number, fileName: string) => void;
    onProcessingFailure: () => void;
}

// Polling interval in milliseconds (e.g., check status every 2 seconds)
const POLLING_INTERVAL = 2000; 
const API_BASE_PATH = "/api/v1";

const UploadComponent: React.FC<UploadComponentProps> = ({ onProcessingStart, onProcessingComplete, onProcessingFailure }) => {
    const [file, setFile] = useState<File | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [status, setStatus] = useState<JobStatusResponse | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // --- Handlers ---

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files.length > 0) {
            setFile(event.target.files[0]);
            setStatus(null);
            setError(null);
            setJobId(null);
        }
    };

    const startPolling = (statusUrl: string, documentId: number, fileName: string) => {
        onProcessingStart();
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(statusUrl, {
                    credentials: 'include'  // Include session cookies
                });
                if (!response.ok) {
                    throw new Error(`Status check failed: ${response.status}`);
                }
                const data: JobStatusResponse = await response.json();
                
                setStatus(data);

                // Stop polling if the job is complete or failed
               if (data.status === 'SUCCESS' || data.status === 'FAILURE') {
                    clearInterval(intervalId);
                    setIsLoading(false);
                    
                    if (data.status === 'SUCCESS') {
                        // Notify parent of successful completion and pass the document ID
                        // localStorage.setItem('processed_doc_id', documentId.toString());
                        onProcessingComplete(documentId, fileName); 
                        console.log(`Document indexed successfully: ${data.message}`);
                    } else {
                        // Notify parent of failure
                        onProcessingFailure();
                    }
                }
            } catch (err) {
                setError(`Polling error: ${(err as Error).message}`);
                clearInterval(intervalId);
                setIsLoading(false);
            }
        }, POLLING_INTERVAL);
    };

    const handleUpload = async () => {
        if (!file) {
            setError("Please select a file to upload.");
            return;
        }

        setIsLoading(true);
        setError(null);
        setJobId(null);

        const formData = new FormData();
        // The 'file' key must match the FastAPI endpoint parameter name (@app.post("/upload", file: UploadFile = File(...)))
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE_PATH}/documents/upload`, {
                method: 'POST',
                body: formData,
                credentials: 'include'  // Include session cookies
            });

            if (response.status !== 202) { // Expect 202 Accepted for Celery task dispatch
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(`Upload failed: ${errorData.detail}`);
            }

            const data: UploadResponse = await response.json();
            setJobId(data.job_details.job_id);
            setStatus(data.job_details);
            
            // Start monitoring the task status
            startPolling(data.status_url, data.document_id, data.filename);

        } catch (err) {
            setError(`Upload error: ${(err as Error).message}`);
            setIsLoading(false);
        }
    };

    const statusColor = status 
        ? status.status === 'SUCCESS' ? 'green' 
        : status.status === 'FAILURE' ? 'red' 
        : 'orange' 
        : 'black';

    return (
        <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', marginBottom: '20px' }}>
            <h3>Document Ingestion</h3>
            <input 
                type="file" 
                accept=".pdf,.txt" 
                onChange={handleFileChange} 
                disabled={isLoading}
            />
            <button onClick={handleUpload} disabled={isLoading || !file} style={{ marginLeft: '10px', padding: '10px', backgroundColor: isLoading ? '#ccc' : '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}>
                {isLoading ? 'Processing...' : 'Start RAG Indexing'}
            </button>

            {/* Status Display */}
            {error && <p style={{ color: 'red' }}>Error: {error}</p>}
            {status && (
                <div style={{ marginTop: '15px' }}>
                    <p><strong>File:</strong> {file?.name}</p>
                    <p><strong>Job ID:</strong> {jobId}</p>
                    <p style={{ color: statusColor }}>
                        <strong>Status:</strong> {status.status}
                    </p>
                    <p style={{ fontSize: '0.9em', color: '#555' }}>
                        {status.message}
                    </p>
                </div>
            )}
        </div>
    );
};

export default UploadComponent;