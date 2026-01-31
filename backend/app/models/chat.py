"""Chat-related Pydantic models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: List[dict] = Field(default_factory=list, description="Source references")


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    document_id: str = Field(..., description="ID of the document to query")
    message: str = Field(..., description="User's question or message")
    include_timestamps: bool = Field(
        default=True, description="Include timestamp references for media"
    )


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    message: str = Field(..., description="Assistant's response")
    sources: List[dict] = Field(default_factory=list, description="Source chunks used")
    timestamps: List[dict] = Field(
        default_factory=list, description="Relevant timestamps"
    )


class ChatHistory(BaseModel):
    """Chat history for a document."""

    document_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StreamToken(BaseModel):
    """A single token in a streaming response."""

    token: str
    done: bool = False
    sources: List[dict] = Field(default_factory=list)
    timestamps: List[dict] = Field(default_factory=list)
