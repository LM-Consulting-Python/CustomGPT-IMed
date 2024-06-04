import React, { useState, useEffect } from 'react';
import { useThread } from './hooks/useThread';
import { postMessage } from '../services/api';

const ThreadComponent = ({ assistantId }) => {
    const [run, setRun] = useState(undefined);
    const { threadId, messages, actionMessages, setActionMessages, clearThread } = useThread(assistantId, run, setRun);

    const handleSendMessage = async (messageContent) => {
        if (threadId && run && run.id) {
            try {
                await postMessage(threadId, messageContent);
                const updatedRun = await fetchRun(threadId, run.id);
                setRun(updatedRun);
            } catch (error) {
                console.error("Error sending message:", error);
            }
        } else {
            console.error("Thread ID or Run ID is not defined");
        }
    };

    return (
        <div>
            <h1>Thread ID: {threadId}</h1>
            {messages && messages.length > 0 ? (
                messages.map((message) => (
                    <div key={message.id}>
                        <p>{message.content}</p>
                    </div>
                ))
            ) : (
                <p>Nenhuma mensagem encontrada.</p>
            )}
            <button onClick={clearThread}>New Chat</button>
            <input type="text" placeholder="Type a message" onKeyDown={(e) => {
                if (e.key === 'Enter') {
                    handleSendMessage(e.target.value);
                    e.target.value = '';
                }
            }} />
        </div>
    );
};

export default ThreadComponent;
