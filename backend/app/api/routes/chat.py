"""Chat API routes with WebSocket support for streaming."""

import json
from datetime import datetime

from app.database import get_database
from app.models import ChatMessage, ChatRequest, ChatResponse
from app.services.llm import (answer_question, answer_question_stream,
                              check_ollama_connection)
from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Send a chat message and get a response.

    This is the non-streaming endpoint for simple Q&A.
    """
    # Verify document exists and is processed
    document = await db.documents.find_one({"_id": request.document_id})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.get("processed", False):
        raise HTTPException(status_code=400, detail="Document not yet processed")

    # Check Ollama connection
    ollama_status = await check_ollama_connection()
    if not ollama_status.get("connected", False):
        raise HTTPException(
            status_code=503,
            detail="Ollama service not available. Please ensure Ollama is running.",
        )

    # Get answer
    result = await answer_question(
        document_id=request.document_id,
        question=request.message,
        include_timestamps=request.include_timestamps,
    )

    # Save to chat history
    user_message = ChatMessage(
        role="user",
        content=request.message,
        timestamp=datetime.utcnow(),
        sources=[],
    )

    assistant_message = ChatMessage(
        role="assistant",
        content=result["answer"],
        timestamp=datetime.utcnow(),
        sources=result["sources"],
    )

    await db.chat_history.update_one(
        {"document_id": request.document_id},
        {
            "$push": {
                "messages": {
                    "$each": [
                        user_message.model_dump(),
                        assistant_message.model_dump(),
                    ]
                }
            },
            "$set": {"updated_at": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
        upsert=True,
    )

    return ChatResponse(
        message=result["answer"],
        sources=result["sources"],
        timestamps=result["timestamps"],
    )


@router.websocket("/stream/{document_id}")
async def chat_stream(
    websocket: WebSocket,
    document_id: str,
):
    """
    WebSocket endpoint for streaming chat responses.

    Protocol:
    1. Client connects and sends JSON: {"message": "question", "include_timestamps": true}
    2. Server streams JSON responses: {"token": "...", "done": false}
    3. Final message includes sources: {"token": "", "done": true, "sources": [...], "timestamps": [...]}
    """
    await websocket.accept()

    # Get database
    from app.database import get_database

    db = get_database()

    # Verify document exists
    document = await db.documents.find_one({"_id": document_id})

    if not document:
        await websocket.send_json({"error": "Document not found"})
        await websocket.close()
        return

    if not document.get("processed", False):
        await websocket.send_json({"error": "Document not yet processed"})
        await websocket.close()
        return

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request = json.loads(data)

            message = request.get("message", "")
            include_timestamps = request.get("include_timestamps", True)

            if not message:
                await websocket.send_json({"error": "Message is required"})
                continue

            # Check Ollama connection
            ollama_status = await check_ollama_connection()
            if not ollama_status.get("connected", False):
                await websocket.send_json(
                    {
                        "error": "Ollama service not available. Please ensure Ollama is running."
                    }
                )
                continue

            # Stream response
            full_response = ""
            sources = []
            timestamps = []

            async for chunk in answer_question_stream(
                document_id=document_id,
                question=message,
                include_timestamps=include_timestamps,
            ):
                full_response += chunk["token"]

                if chunk["done"]:
                    sources = chunk.get("sources", [])
                    timestamps = chunk.get("timestamps", [])

                await websocket.send_json(chunk)

            # Save to chat history
            user_message = ChatMessage(
                role="user",
                content=message,
                timestamp=datetime.utcnow(),
                sources=[],
            )

            assistant_message = ChatMessage(
                role="assistant",
                content=full_response,
                timestamp=datetime.utcnow(),
                sources=sources,
            )

            await db.chat_history.update_one(
                {"document_id": document_id},
                {
                    "$push": {
                        "messages": {
                            "$each": [
                                user_message.model_dump(),
                                assistant_message.model_dump(),
                            ]
                        }
                    },
                    "$set": {"updated_at": datetime.utcnow()},
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass


@router.get("/history/{document_id}")
async def get_chat_history(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get chat history for a document."""
    history = await db.chat_history.find_one({"document_id": document_id})

    if not history:
        return {"document_id": document_id, "messages": []}

    return {
        "document_id": document_id,
        "messages": history.get("messages", []),
    }


@router.delete("/history/{document_id}")
async def clear_chat_history(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Clear chat history for a document."""
    await db.chat_history.delete_one({"document_id": document_id})
    return {"message": "Chat history cleared"}


@router.get("/status")
async def get_chat_status():
    """Check chat service status including Ollama connection."""
    ollama_status = await check_ollama_connection()

    return {
        "status": "healthy" if ollama_status.get("connected") else "degraded",
        "ollama": ollama_status,
    }
