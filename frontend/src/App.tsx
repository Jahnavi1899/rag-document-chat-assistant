// frontend/src/App.tsx (Updated)

import { useState, useEffect } from 'react';
import UploadComponent from './UploadComponent';
import ChatComponent from './ChatComponent';
import { DocumentInfo } from './types';

function App() {
    const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
    const [availableDocuments, setAvailableDocuments] = useState<DocumentInfo[]>([]);
    const [processedDocumentId, setProcessedDocumentId] = useState<number | null>(null);
    const [processedDocumentName, setProcessedDocumentName] = useState<string | null>(null);
    const [processingStatus, setProcessingStatus] = useState<'IDLE' | 'PENDING' | 'SUCCESS' | 'FAILURE'>('IDLE');

    // useEffect(() => {
    //     const savedId = localStorage.getItem('processed_doc_id');
    //     if (savedId) {
    //         // Convert the string back to a number
    //         const docId = parseInt(savedId);
    //         if (!isNaN(docId)) {
    //             setProcessedDocumentId(docId);
    //             // Set status directly to SUCCESS to enable chat immediately
    //             setProcessingStatus('SUCCESS'); 
    //         }
    //     }
    // }, []);

    const fetchDocuments = async () => {
        try {
            const response = await fetch('/api/v1/documents', {
                credentials: 'include'  // Include session cookies
            });
            if (response.ok) {
                const data: DocumentInfo[] = await response.json();
                setAvailableDocuments(data);

                if(data.length > 0){
                    // If there are available documents, set the first one as selected by default
                    setSelectedDocumentId(data[0].id);
                }
                else{
                    setSelectedDocumentId(null);
                }
            }
        } catch (error) {
            console.error("Failed to fetch document list:", error);
        }
    };

    useEffect(() => {
        // Fetch list of all indexed documents on mount
        fetchDocuments();
    }, []);

    const currentChatId = processedDocumentId || selectedDocumentId;
    const currentChatName = availableDocuments.find(doc => doc.id === currentChatId)?.filename || 
    (currentChatId === processedDocumentId ? processedDocumentName : '');

    return (
        <div className="App" style={{ margin: '40px auto', padding: '20px' }}>
            <header style={{ textAlign: 'center', marginBottom: '30px' }}>
                <h1>AI Document Intelligence Platform</h1>
            </header>
            
            <UploadComponent
                onProcessingStart={() => setProcessingStatus('PENDING')}
                onProcessingComplete={(docId, fileName) => {
                    setProcessedDocumentId(docId);
                    setProcessedDocumentName(fileName);
                    setProcessingStatus('SUCCESS');
                    setSelectedDocumentId(docId);
                    // Refresh document list after successful upload
                    fetchDocuments();
                }}
                onProcessingFailure={() => setProcessingStatus('FAILURE')}
            />
            <div style={{ padding: '10px', border: '1px dashed #bbb', marginBottom: '20px' }}>
                <label htmlFor="doc-selector">Chat with a previous document:</label>
                <select id="doc-selector" value={currentChatId || ''} onChange={(e) => setSelectedDocumentId(parseInt(e.target.value))} style={{ marginLeft: '10px' }}>
                    <option value="" disabled>--- Select Document ---</option>
                    {availableDocuments.map(doc => (
                        <option key={doc.id} value={doc.id}>
                            {doc.filename} (ID: {doc.id})
                        </option>
                    ))}
                </select>
            </div>
   
            <h2 style={{ marginTop: '30px', borderBottom: '1px solid #ddd', paddingBottom: '10px' }}>
                Conversation
            </h2>
            
           {currentChatId !== null ? (
                <ChatComponent documentId={currentChatId} documentName={currentChatName} /> 
            ) : processingStatus === 'PENDING' ? (
                <p style={{ color: 'orange' }}>Indexing document... Chat will be enabled shortly.</p>
            ) : (
                <p style={{ color: 'gray' }}>Upload a new document or select a previous one to begin the chat.</p>
            )}
        </div>
    );
}

export default App;