export const createNewThread = async (assistantId) => {
    try {
        let response = await fetch("http://localhost:8000/api/new", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ assistant_id: assistantId })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (err) {
        console.error("Failed to create a new thread:", err.message);
        return null;
    }
};

export const fetchThread = async (threadId) => {
    try {
        let response = await fetch(`http://localhost:8000/api/threads/${threadId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (err) {
        console.error(`Failed to fetch thread ${threadId}:`, err.message);
        return null;
    }
};

export const postMessage = async (threadId, message) => {
    try {
        let response = await fetch(`http://localhost:8000/api/threads/${threadId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ content: message })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (err) {
        console.error(`Failed to post message to thread ${threadId}:`, err.message);
        return null;
    }
};
