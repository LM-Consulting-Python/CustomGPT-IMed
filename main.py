from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    Body,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
import openai
from typing import List
import json
import markdown

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.DEBUG)

api_key = "sk-proj-wEpukkf8vD58injlnnP4T3BlbkFJENhIyp8Aw5jRvWfzJWVS"
openai.api_key = api_key


class CreateAssistantRequest(BaseModel):
    name: str
    instructions: str
    model: str
    temperature: float
    top_p: float


class CreateMessage(BaseModel):
    content: str


class NewThreadRequest(BaseModel):
    assistant_id: str


class ChatRequest(BaseModel):
    thread_id: str
    message: str


@app.on_event("startup")
async def startup_event():
    async with httpx.AsyncClient() as client:
        try:
            # Create a new thread automatically when the app starts
            thread_response = await client.post(
                "https://api.openai.com/v1/threads",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "OpenAI-Beta": "assistants=v2",
                },
                json={
                    "messages": [{"role": "user", "content": "Initializing thread."}]
                },
            )
            if thread_response.status_code == 200:
                logging.info("Thread created successfully at startup.")
            else:
                logging.error(
                    f"Failed to create thread at startup: {thread_response.status_code} - {thread_response.text}"
                )
        except Exception as e:
            logging.error(f"Error during startup thread creation: {str(e)}")


@app.get("/api/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str):
    try:
        run = await openai.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )

        return {
            "run_id": run.id,
            "thread_id": thread_id,
            "status": run.status,
            "required_action": run.required_action,
            "last_error": run.last_error,
        }
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/threads/{thread_id}/runs/{run_id}/tool")
async def post_tool(thread_id: str, run_id: str, tool_outputs: List[dict]):
    try:
        run = await openai.beta.threads.runs.submit_tool_outputs(
            run_id=run_id, thread_id=thread_id, tool_outputs=tool_outputs
        )
        return {
            "run_id": run.id,
            "thread_id": thread_id,
            "status": run.status,
            "required_action": run.required_action,
            "last_error": run.last_error,
        }
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create-assistant")
async def create_assistant(
    name: str = Form(...),
    instructions: str = Form(...),
    model: str = Form(...),
    temperature: float = Form(...),
    top_p: float = Form(...),
    files: List[UploadFile] = File(...),
):
    url = "https://api.openai.com/v1/assistants"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    payload = {
        "name": name,
        "instructions": instructions,
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "tools": [{"type": "code_interpreter"}, {"type": "file_search"}],
    }

    logging.debug(f"Request payload: {payload}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            assistant_data = response.json()
            assistant_id = assistant_data["id"]
            logging.debug(f"Assistant created with ID: {assistant_id}")

            # Upload files
            file_ids = []
            for file in files:
                file_data = await file.read()
                file_payload = {"file": (file.filename, file_data, file.content_type)}
                file_response = await client.post(
                    "https://api.openai.com/v1/files",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=file_payload,
                    data={"purpose": "assistants"},
                )
                if file_response.status_code == 200:
                    file_response_data = file_response.json()
                    file_ids.append(file_response_data["id"])
                else:
                    logging.error(
                        f"File upload failed: {file_response.status_code} - {file_response.text}"
                    )
                    raise HTTPException(
                        status_code=file_response.status_code, detail=file_response.text
                    )

            logging.debug(f"Uploaded file IDs: {file_ids}")

            # Create vector store with uploaded file IDs
            vector_store_payload = {
                "name": f"{name}_vector_store",
                "file_ids": file_ids,
            }
            vector_store_url = "https://api.openai.com/v1/vector_stores"
            vector_store_response = await client.post(
                vector_store_url, headers=headers, json=vector_store_payload
            )
            if vector_store_response.status_code == 200:
                vector_store_data = vector_store_response.json()
                vector_store_id = vector_store_data["id"]

                logging.debug(f"Vector store created with ID: {vector_store_id}")

                # Update the assistant with the vector store ID
                update_assistant_payload = {
                    "tool_resources": {
                        "file_search": {"vector_store_ids": [vector_store_id]}
                    }
                }
                update_response = await client.post(
                    f"https://api.openai.com/v1/assistants/{assistant_id}",
                    headers=headers,
                    json=update_assistant_payload,
                )
                if update_response.status_code != 200:
                    raise HTTPException(
                        status_code=update_response.status_code,
                        detail=update_response.text,
                    )

                assistant_data["vector_store"] = vector_store_data
                logging.debug(f"Vector store linked to assistant: {vector_store_data}")

                return {
                    "assistant_id": assistant_id,
                    "vector_store_id": vector_store_id,
                }
            else:
                logging.error(
                    f"Vector store creation failed: {vector_store_response.status_code} - {vector_store_response.text}"
                )
                raise HTTPException(
                    status_code=vector_store_response.status_code,
                    detail=vector_store_response.text,
                )
        else:
            logging.error(f"Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.post("/api/update-file-search")
async def update_file_search(
    assistant_id: str = Form(...), vector_store_id: str = Form(...)
):
    url = f"https://api.openai.com/v1/assistants/{assistant_id}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    payload = {
        "tool_resources": {"file_search": {"vector_store_ids": [vector_store_id]}}
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            logging.debug(
                f"File search updated for assistant ID: {assistant_id} with vector store ID: {vector_store_id}"
            )
            return {"status": "success"}
        else:
            logging.error(f"Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.post("/api/new")
async def create_new_thread(new_thread_request: NewThreadRequest = Body(...)):
    url = "https://api.openai.com/v1/threads"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Greet the user and tell it about yourself and ask it what it is looking for.",
            }
        ]
    }

    logging.debug(f"Create new thread payload: {payload}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            thread_data = response.json()
            thread_id = thread_data["id"]
            logging.debug(f"Thread created with ID: {thread_id}")

            run_payload = {
                "assistant_id": new_thread_request.assistant_id,
                "model": "gpt-4-turbo",  # Ensure you use a supported model
            }
            run_url = f"https://api.openai.com/v1/threads/{thread_id}/runs"
            run_response = await client.post(run_url, headers=headers, json=run_payload)
            if run_response.status_code == 200:
                run_data = run_response.json()
                logging.debug(f"Run created with ID: {run_data['id']}")
                return {"thread_id": thread_id, "run_id": run_data["id"]}
            else:
                logging.error(
                    f"Run creation failed: {run_response.status_code} - {run_response.text}"
                )
                raise HTTPException(
                    status_code=run_response.status_code, detail=run_response.text
                )
        else:
            logging.error(
                f"Thread creation failed: {response.status_code} - {response.text}"
            )
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str):
    url = f"https://api.openai.com/v1/threads/{thread_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            thread_data = response.json()
            logging.debug(f"Thread data: {thread_data}")
            return thread_data
        else:
            logging.error(
                f"Failed to retrieve thread: {response.status_code} - {response.text}"
            )
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.post("/api/threads/{thread_id}/messages")
async def create_message(thread_id: str, message: CreateMessage):
    url = f"https://api.openai.com/v1/threads/{thread_id}/messages"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    payload = {"role": "user", "content": message.content}

    logging.debug(f"Create message payload: {payload}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            response_data = response.json()
            logging.debug(f"Message created response data: {response_data}")

            # Fetch the updated messages to get the assistant's response
            response_url = f"https://api.openai.com/v1/threads/{thread_id}/messages"
            messages_response = await client.get(response_url, headers=headers)
            if messages_response.status_code == 200:
                messages_data = messages_response.json()
                logging.debug(f"Messages fetched response data: {messages_data}")

                if "data" in messages_data:
                    assistant_message = next(
                        (
                            msg
                            for msg in messages_data["data"]
                            if msg["role"] == "assistant"
                        ),
                        None,
                    )
                    if (
                        assistant_message
                        and assistant_message["content"]
                        and len(assistant_message["content"]) > 0
                        and "text" in assistant_message["content"][0]
                        and "value" in assistant_message["content"][0]["text"]
                    ):
                        return {
                            "status": "success",
                            "message": assistant_message["content"][0]["text"]["value"],
                        }
                    else:
                        logging.error("Assistant did not respond.")
                        raise HTTPException(
                            status_code=500, detail="Assistant did not respond."
                        )
                else:
                    logging.error("Key 'data' not found in response.")
                    raise HTTPException(
                        status_code=500, detail="Key 'data' not found in response."
                    )
            else:
                logging.error(
                    f"Failed to fetch messages: {messages_response.status_code} - {messages_response.text}"
                )
                raise HTTPException(
                    status_code=messages_response.status_code,
                    detail=messages_response.text,
                )
        else:
            logging.error(
                f"Message creation failed: {response.status_code} - {response.text}"
            )
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.post("/api/chat")
async def chat(chat_request: ChatRequest):
    thread_id = chat_request.thread_id
    user_message = chat_request.message

    # Send user message to the assistant
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create a new message in the thread
        message_payload = {"role": "user", "content": user_message}
        message_url = f"https://api.openai.com/v1/threads/{thread_id}/messages"
        message_response = await client.post(
            message_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
            },
            json=message_payload,
        )

        if message_response.status_code != 200:
            logging.error(
                f"Failed to send message: {message_response.status_code} - {message_response.text}"
            )
            raise HTTPException(
                status_code=message_response.status_code, detail=message_response.text
            )

        # Get assistant response
        response_url = f"https://api.openai.com/v1/threads/{thread_id}/messages"
        response = await client.get(
            response_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2",
            },
        )

        if response.status_code == 200:
            messages = response.json()["messages"]
            assistant_message = next(
                (msg for msg in messages if msg["role"] == "assistant"), None
            )
            if assistant_message:
                return {"message": assistant_message["content"]}
            else:
                raise HTTPException(
                    status_code=500, detail="Assistant did not respond."
                )
        else:
            logging.error(
                f"Failed to get assistant response: {response.status_code} - {response.text}"
            )
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/api/get-assistants")
async def get_assistants():
    url = "https://api.openai.com/v1/assistants"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            logging.debug("Retrieved assistants successfully.")
            return response.json()
        else:
            logging.error(
                f"Failed to retrieve assistants: {response.status_code} - {response.text}"
            )
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/api/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    url = f"https://api.openai.com/v1/assistants/{assistant_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            logging.debug(f"Retrieved assistant with ID: {assistant_id}")
            return response.json()
        else:
            logging.error(
                f"Failed to retrieve assistant: {response.status_code} - {response.text}"
            )
            raise HTTPException(status_code=response.status_code, detail=response.text)


import json
import httpx
import logging


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async with httpx.AsyncClient(
            timeout=300.0
        ) as client:  # Aumentar o timeout para 300 segundos
            async for message in websocket.iter_text():
                try:
                    message_data = json.loads(message)
                    assistant_id = message_data.get("assistant_id")
                    user_message = message_data.get("message")

                    # Enviar a solicitação para a API da OpenAI com streaming
                    async with client.stream(
                        "POST",
                        "https://api.openai.com/v1/threads/runs",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "OpenAI-Beta": "assistants=v2",
                            "Content-Type": "application/json",
                        },
                        json={
                            "assistant_id": assistant_id,
                            "thread": {
                                "messages": [{"role": "user", "content": user_message}]
                            },
                            "stream": True,
                        },
                    ) as response:
                        full_response_text = ""
                        async for line in response.aiter_lines():
                            try:
                                if line:
                                    logging.debug(f"Received line: {line}")
                                    if line.startswith("data:"):
                                        event = json.loads(line[5:].strip())
                                        if (
                                            event.get("object")
                                            == "thread.message.delta"
                                        ):
                                            # Se for uma parte da mensagem, adicione-a ao texto da resposta
                                            content = event.get("delta", {}).get(
                                                "content", []
                                            )
                                            for item in content:
                                                if item.get(
                                                    "type"
                                                ) == "text" and item.get(
                                                    "text", {}
                                                ).get("value"):
                                                    full_response_text += item["text"][
                                                        "value"
                                                    ]
                                            # Enviar a parte do texto para o corpo da mensagem de resposta do chatbot
                                            await websocket.send_text(
                                                full_response_text
                                            )
                                            full_response_text = (
                                                ""  # Reset after sending
                                            )
                            except json.JSONDecodeError as e:
                                logging.error(f"JSON decode error: {str(e)}")
                except Exception as e:
                    logging.error(
                        f"Error while communicating with OpenAI API: {str(e)}"
                    )
                    await websocket.send_text(f"Error: {str(e)}")

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as e:
        logging.error(f"Error in WebSocket: {str(e)}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
