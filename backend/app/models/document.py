"""Document-related Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported file types."""

    PDF = "pdf"
    AUDIO = "audio"
    VIDEO = "video"


class TimestampSegment(BaseModel):
    """Timestamp segment for audio/video transcription."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")


class DocumentChunk(BaseModel):
    """A chunk of document text for vector search."""

    id: Optional[str] = None
    document_id: str
    content: str
    chunk_index: int
    metadata: dict = Field(default_factory=dict)
    timestamp: Optional[TimestampSegment] = None


class DocumentBase(BaseModel):
    """Base document model."""

    filename: str
    file_type: FileType
    file_size: int
    mime_type: str


class DocumentCreate(DocumentBase):
    """Model for creating a document."""

    pass


class Document(DocumentBase):
    """Full document model with all fields."""

    id: str = Field(..., alias="_id")
    file_path: str
    content: Optional[str] = None
    summary: Optional[str] = None
    timestamps: List[TimestampSegment] = Field(default_factory=list)
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
    processing_error: Optional[str] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class DocumentResponse(BaseModel):
    """API response for document operations."""

    id: str
    filename: str
    file_type: FileType
    file_size: int
    summary: Optional[str] = None
    processed: bool
    created_at: datetime
    chunk_count: int = 0

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: List[DocumentResponse]
    total: int
