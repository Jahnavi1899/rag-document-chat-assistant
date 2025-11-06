import React, { useState, useCallback } from 'react';
import { Message, ChatPayload } from './types';

const API_BASE_PATH = "/api/v1";
// const HARDCODED_DOCUMENT_ID = 3;

interface ChatComponentProps {
    documentId: number;
    documentName: string | null; 
}

const ChatComponent: React.FC<ChatComponentProps> = ({ documentId, documentName }) => {
    const [question, setQuestion] = useState('');
    // currentStream holds the tokens currently being displayed
    const [currentStream, setCurrentStream] = useState('');
    // history holds finalized messages (user + AI)
    const [history, setHistory] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const streamResponse = useCallback(async () => {
        if (!question || isLoading) return;

        setIsLoading(true);
        setError(null);
        
        const userMessage: Message = { role: 'user', content: question };
        setHistory(prev => [...prev, userMessage]); // Add user message to history
        setCurrentStream(''); // Clear previous stream

        const payload: ChatPayload = { question };
        const url = `${API_BASE_PATH}/documents/${documentId}/chat`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                credentials: 'include'  // Include session cookies
            });

            if (!response.ok || !response.body) {
                const errorText = await response.text();
                throw new Error(`API Error: ${response.status} - ${errorText.substring(0, 100)}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let done = false;
            let fullResponse = '';

            // Consume the stream chunk by chunk
            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;

                const chunk = decoder.decode(value, { stream: !done });
                
                // Update the state immediately to stream the text
                setCurrentStream(prev => {
                    fullResponse = prev + chunk;
                    return fullResponse;
                });
            }
            
            // After stream ends, finalize the message and save to history
            const aiMessage: Message = { role: 'ai', content: fullResponse };
            setHistory(prev => [...prev, aiMessage]);
            setCurrentStream('');
            setQuestion('');

        } catch (err) {
            setError((err as Error).message);
        } finally {
            setIsLoading(false);
        }
    }, [question, isLoading, documentId]);

    return (
        <div style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px' }}>
            <p>Chatting with Document: {documentName}</p>
            {error && (
                <div style={{ color: 'red', marginBottom: '10px', padding: '5px' }}>
                    Error: {error}
                </div>
            )}
            <div style={{ height: '300px', overflowY: 'scroll', border: '1px solid #ddd', padding: '10px', marginBottom: '20px' }}>
                {history.map((msg, index) => (
                    <div key={index} style={{ marginBottom: '10px', padding: '5px', borderRadius: '4px', backgroundColor: msg.role === 'user' ? '#e1f5fe' : '#f1f8e9', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                        <strong>{msg.role === 'user' ? 'You' : 'AI'}:</strong> {msg.content}
                    </div>
                ))}
                {/* Display the current streaming response */}
                {currentStream && (
                    <div style={{ marginBottom: '10px', padding: '5px', borderRadius: '4px', backgroundColor: '#f1f8e9', textAlign: 'left' }}>
                        <strong>AI (Streaming):</strong> {currentStream}
                    </div>
                )}
                {isLoading && <div><div style={{ margin: '5px' }}></div>Generating...</div>}
            </div>

            <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') streamResponse(); }}
                placeholder="Ask a question about the document..."
                style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
                disabled={isLoading}
            />
            <button onClick={streamResponse} disabled={isLoading || !question} style={{ padding: '10px', width: '100%', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                Send
            </button>
        </div>
    );
};

export default ChatComponent;