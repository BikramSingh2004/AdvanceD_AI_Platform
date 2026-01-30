"""Pytest configuration and fixtures."""
import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database.mongodb import mongodb
from app.config import Settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Get test settings."""
    return Settings(
        mongodb_url="mongodb://localhost:27017",
        mongodb_db_name="test_document_qa",
        upload_dir="test_uploads",
        debug=True,
    )


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB for testing."""
    mock_db = MagicMock()
    mock_db.documents = MagicMock()
    mock_db.chunks = MagicMock()
    mock_db.chat_history = MagicMock()
    
    # Configure async methods
    mock_db.documents.find_one = AsyncMock()
    mock_db.documents.insert_one = AsyncMock()
    mock_db.documents.update_one = AsyncMock()
    mock_db.documents.delete_one = AsyncMock()
    mock_db.documents.find = MagicMock(return_value=MagicMock(
        skip=MagicMock(return_value=MagicMock(
            limit=MagicMock(return_value=MagicMock(
                sort=MagicMock(return_value=MagicMock(
                    to_list=AsyncMock(return_value=[])
                ))
            ))
        ))
    ))
    mock_db.documents.count_documents = AsyncMock(return_value=0)
    mock_db.documents.create_index = AsyncMock()
    
    mock_db.chunks.delete_many = AsyncMock()
    mock_db.chunks.create_index = AsyncMock()
    
    mock_db.chat_history.find_one = AsyncMock()
    mock_db.chat_history.update_one = AsyncMock()
    mock_db.chat_history.delete_one = AsyncMock()
    mock_db.chat_history.delete_many = AsyncMock()
    mock_db.chat_history.create_index = AsyncMock()
    
    return mock_db


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    with patch("app.services.vector_store._faiss_index") as mock_index, \
         patch("app.services.vector_store._document_store", {}), \
         patch("app.services.vector_store._chunk_to_doc", {}), \
         patch("app.services.vector_store._current_idx", 0):
        mock_index.ntotal = 0
        yield mock_index


@pytest.fixture
def mock_ollama():
    """Mock Ollama client for testing."""
    with patch("app.services.llm.ollama_client") as mock:
        mock.generate = AsyncMock(return_value="This is a test response.")
        mock.generate_stream = AsyncMock()
        mock.check_health = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_whisper():
    """Mock Whisper model for testing."""
    with patch("app.services.transcription.get_whisper_model") as mock:
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value={
            "text": "This is test transcription.",
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "This is test"},
                {"start": 5.0, "end": 10.0, "text": "transcription."},
            ],
            "language": "en",
        })
        mock.return_value = mock_model
        yield mock


@pytest.fixture
def client(mock_mongodb) -> Generator:
    """Create test client with mocked database."""
    with patch("app.database.mongodb.get_database", return_value=mock_mongodb):
        with patch("app.api.routes.upload.get_database", return_value=mock_mongodb):
            with patch("app.api.routes.documents.get_database", return_value=mock_mongodb):
                with patch("app.api.routes.chat.get_database", return_value=mock_mongodb):
                    with TestClient(app) as test_client:
                        yield test_client


@pytest.fixture
async def async_client(mock_mongodb) -> AsyncGenerator:
    """Create async test client."""
    with patch("app.database.mongodb.get_database", return_value=mock_mongodb):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing."""
    # Minimal valid PDF
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test content) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""


@pytest.fixture
def sample_document() -> dict:
    """Sample document for testing."""
    from datetime import datetime
    return {
        "_id": "test-doc-123",
        "filename": "test.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
        "file_path": "uploads/test-doc-123.pdf",
        "content": "This is test content from the document.",
        "summary": "Test document summary.",
        "timestamps": [],
        "chunk_count": 5,
        "created_at": datetime.utcnow(),
        "processed": True,
        "processing_error": None,
    }


@pytest.fixture
def sample_audio_document() -> dict:
    """Sample audio document for testing."""
    from datetime import datetime
    return {
        "_id": "test-audio-123",
        "filename": "test.mp3",
        "file_type": "audio",
        "file_size": 10240,
        "mime_type": "audio/mpeg",
        "file_path": "uploads/test-audio-123.mp3",
        "content": "This is transcribed audio content.",
        "summary": "Audio transcription summary.",
        "timestamps": [
            {"start": 0.0, "end": 5.0, "text": "Hello world"},
            {"start": 5.0, "end": 10.0, "text": "This is a test"},
        ],
        "chunk_count": 2,
        "created_at": datetime.utcnow(),
        "processed": True,
        "processing_error": None,
    }
