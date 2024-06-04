let currentThreadId;
let currentAssistantId;
let socket;
let currentResponseElement = null;

async function fetchAssistants() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/get-assistants');
        if (response.ok) {
            const data = await response.json();
            console.log("Assistants fetched:", data);
            const select = document.getElementById('assistants');
            select.innerHTML = data.data.map(assistant => 
                `<option value="${assistant.id}">${assistant.name}</option>`
            ).join('');
        } else {
            console.error('Failed to fetch assistants', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error fetching assistants:', error);
    }
}

async function loadAssistantConfig() {
    const assistantId = document.getElementById('assistants').value;
    currentAssistantId = assistantId;
    if (assistantId) {
        try {
            const response = await fetch(`http://127.0.0.1:8000/api/assistants/${assistantId}`);
            if (response.ok) {
                const assistant = await response.json();
                document.getElementById('botName').value = assistant.name;
                const detailsDiv = document.getElementById('assistantDetails');
                detailsDiv.innerHTML = `
                    <p><strong>ID:</strong> ${assistant.id}</p>
                    <p><strong>Nome:</strong> ${assistant.name}</p>
                    <p><strong>Modelo:</strong> ${assistant.model}</p>
                    <p><strong>Instruções:</strong> ${assistant.instructions}</p>
                    <p><strong>Ferramentas:</strong> ${assistant.tools.map(tool => tool.type).join(', ')}</p>
                    <p><strong>Temperatura:</strong> ${assistant.temperature}</p>
                    <p><strong>Top P:</strong> ${assistant.top_p}</p>
                `;

                const threadPayload = { assistant_id: assistantId };
                console.log("Enviando payload para criar thread:", threadPayload);

                const threadResponse = await fetch("http://127.0.0.1:8000/api/new", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(threadPayload)
                });

                if (threadResponse.ok) {
                    const threadData = await threadResponse.json();
                    currentThreadId = threadData.thread_id;
                    await fetchMessages(currentThreadId);
                    initializeWebSocket();
                } else {
                    const errorData = await threadResponse.json();
                    console.error('Failed to create thread', threadResponse.status, response.statusText, errorData);
                }
            } else {
                console.error('Failed to load assistant config', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Error loading assistant config:', error);
        }
    }
}

async function fetchMessages(threadId) {
    try {
        const response = await fetch(`http://127.0.0.1:8000/api/threads/${threadId}`);
        if (response.ok) {
            const messages = await response.json();
            const chatBody = document.getElementById('chatBody');
            chatBody.innerHTML = ''; // Clear previous messages
            messages.data.forEach(msg => {
                const messageElement = document.createElement('div');
                messageElement.innerHTML = `${msg.role}: ${msg.content[0].text.value}`;
                messageElement.style.textAlign = msg.role === 'user' ? 'right' : 'left';
                messageElement.style.backgroundColor = msg.role === 'user' ? '#007BFF' : '#333';
                messageElement.style.color = 'white';
                messageElement.style.padding = '5px';
                messageElement.style.margin = '5px 0';
                messageElement.style.borderRadius = '5px';
                chatBody.appendChild(messageElement);
            });
        } else {
            console.error('Failed to fetch messages', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error fetching messages:', error);
    }
}

function initializeWebSocket() {
    socket = new WebSocket("ws://localhost:8000/ws/chat");

    socket.onopen = function(event) {
        console.log("Connected to WebSocket server.");
    };

    socket.onmessage = function(event) {
        console.log("Received message: ", event.data);
        appendToCurrentResponse(event.data);
    };

    socket.onclose = function(event) {
        console.log("Disconnected from WebSocket server.");
    };

    socket.onerror = function(error) {
        console.error("WebSocket error: ", error);
    };
}

function appendToCurrentResponse(html) {
    if (currentResponseElement) {
        currentResponseElement.innerHTML += html; // Append HTML content
    } else {
        displayMessage('assistant', html);
    }
}

function displayMessage(role, content) {
    const chatBody = document.getElementById('chatBody');
    const messageElement = document.createElement('div');
    messageElement.innerHTML = content; // Set innerHTML for formatted content
    messageElement.classList.add('message', role);
    chatBody.appendChild(messageElement);
    chatBody.scrollTop = chatBody.scrollHeight;
    if (role === 'assistant') {
        currentResponseElement = messageElement;
    } else {
        currentResponseElement = null;
    }
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value;

    if (!message.trim() || !currentThreadId) return;

    const messagePayload = JSON.stringify({
        assistant_id: currentAssistantId,
        message: message
    });

    socket.send(messagePayload);
    displayMessage('user', `<strong style="color: #FF5733;">${message}</strong>`); // Display user message in bold and in a different color
    input.value = ''; // Clear input after sending
}

function goBack() {
    window.history.back();
}

document.addEventListener('DOMContentLoaded', fetchAssistants);
