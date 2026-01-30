"""Tests for Pydantic models."""
import pytest
from datetime import datetime


class TestDocumentModels:
    """Test document-related models."""

    def test_file_type_enum(self):
        """Test FileType enum values."""
        from app.models import FileType
        
        assert FileType.PDF.value == "pdf"
        assert FileType.AUDIO.value == "audio"
        assert FileType.VIDEO.value == "video"

    def test_timestamp_segment(self):
        """Test TimestampSegment model."""
        from app.models import TimestampSegment
        
        ts = TimestampSegment(start=0.0, end=5.0, text="Hello world")
        
        assert ts.start == 0.0
        assert ts.end == 5.0
        assert ts.text == "Hello world"

    def test_document_chunk(self):
        """Test DocumentChunk model."""
        from app.models import DocumentChunk, TimestampSegment
        
        chunk = DocumentChunk(
            document_id="doc-123",
            content="Test content",
            chunk_index=0,
            metadata={"page": 1},
        )
        
        assert chunk.document_id == "doc-123"
        assert chunk.content == "Test content"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {"page": 1}
        assert chunk.timestamp is None

    def test_document_chunk_with_timestamp(self):
        """Test DocumentChunk with timestamp."""
        from app.models import DocumentChunk, TimestampSegment
        
        ts = TimestampSegment(start=0.0, end=5.0, text="Test")
        chunk = DocumentChunk(
            document_id="doc-123",
            content="Test content",
            chunk_index=0,
            timestamp=ts,
        )
        
        assert chunk.timestamp is not None
        assert chunk.timestamp.start == 0.0

    def test_document_response(self):
        """Test DocumentResponse model."""
        from app.models import DocumentResponse, FileType
        
        response = DocumentResponse(
            id="doc-123",
            filename="test.pdf",
            file_type=FileType.PDF,
            file_size=1024,
            summary="Test summary",
            processed=True,
            created_at=datetime.utcnow(),
            chunk_count=5,
        )
        
        assert response.id == "doc-123"
        assert response.file_type == FileType.PDF
        assert response.processed is True

    def test_document_list_response(self):
        """Test DocumentListResponse model."""
        from app.models import DocumentListResponse, DocumentResponse, FileType
        
        docs = [
            DocumentResponse(
                id="doc-1",
                filename="test1.pdf",
                file_type=FileType.PDF,
                file_size=1024,
                processed=True,
                created_at=datetime.utcnow(),
            ),
        ]
        
        response = DocumentListResponse(documents=docs, total=1)
        
        assert len(response.documents) == 1
        assert response.total == 1


class TestChatModels:
    """Test chat-related models."""

    def test_chat_message(self):
        """Test ChatMessage model."""
        from app.models import ChatMessage
        
        msg = ChatMessage(
            role="user",
            content="Hello, how are you?",
        )
        
        assert msg.role == "user"
        assert msg.content == "Hello, how are you?"
        assert msg.sources == []

    def test_chat_request(self):
        """Test ChatRequest model."""
        from app.models import ChatRequest
        
        request = ChatRequest(
            document_id="doc-123",
            message="What is this about?",
            include_timestamps=True,
        )
        
        assert request.document_id == "doc-123"
        assert request.message == "What is this about?"
        assert request.include_timestamps is True

    def test_chat_response(self):
        """Test ChatResponse model."""
        from app.models import ChatResponse
        
        response = ChatResponse(
            message="This document is about testing.",
            sources=[{"content": "Test content", "score": 0.9}],
            timestamps=[{"start": 0.0, "end": 5.0, "text": "Hello"}],
        )
        
        assert response.message == "This document is about testing."
        assert len(response.sources) == 1
        assert len(response.timestamps) == 1

    def test_stream_token(self):
        """Test StreamToken model."""
        from app.models import StreamToken
        
        token = StreamToken(
            token="Hello",
            done=False,
        )
        
        assert token.token == "Hello"
        assert token.done is False
        assert token.sources == []
        assert token.timestamps == []
