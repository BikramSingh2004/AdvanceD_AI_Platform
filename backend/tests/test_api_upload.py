"""Tests for upload API routes."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestUploadAPI:
    """Test upload API endpoints."""

    def test_upload_pdf(self, client, mock_mongodb, sample_pdf_content):
        """Test PDF file upload."""
        mock_mongodb.documents.insert_one = AsyncMock()

        with patch("app.api.routes.upload.process_document_background"):
            response = client.post(
                "/api/upload/",
                files={
                    "file": ("test.pdf", BytesIO(sample_pdf_content), "application/pdf")
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["file_type"] == "pdf"
        assert data["processed"] is False

    def test_upload_audio(self, client, mock_mongodb):
        """Test audio file upload."""
        mock_mongodb.documents.insert_one = AsyncMock()

        audio_content = b"fake audio content"

        with patch("app.api.routes.upload.process_document_background"):
            response = client.post(
                "/api/upload/",
                files={"file": ("test.mp3", BytesIO(audio_content), "audio/mpeg")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.mp3"
        assert data["file_type"] == "audio"

    def test_upload_video(self, client, mock_mongodb):
        """Test video file upload."""
        mock_mongodb.documents.insert_one = AsyncMock()

        video_content = b"fake video content"

        with patch("app.api.routes.upload.process_document_background"):
            response = client.post(
                "/api/upload/",
                files={"file": ("test.mp4", BytesIO(video_content), "video/mp4")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.mp4"
        assert data["file_type"] == "video"

    def test_upload_unsupported_type(self, client, mock_mongodb):
        """Test upload with unsupported file type."""
        response = client.post(
            "/api/upload/",
            files={
                "file": ("test.exe", BytesIO(b"content"), "application/octet-stream")
            },
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_upload_status(self, client, mock_mongodb, sample_document):
        """Test getting upload status."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)

        response = client.get(f"/api/upload/status/{sample_document['_id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_document["_id"]
        assert data["processed"] is True

    def test_upload_status_not_found(self, client, mock_mongodb):
        """Test upload status for non-existent document."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=None)

        response = client.get("/api/upload/status/non-existent")

        assert response.status_code == 404

    def test_get_file_type_pdf(self):
        """Test file type detection for PDF."""
        from app.api.routes.upload import get_file_type
        from app.models import FileType

        result = get_file_type("document.pdf")

        assert result == FileType.PDF

    def test_get_file_type_audio(self):
        """Test file type detection for audio."""
        from app.api.routes.upload import get_file_type
        from app.models import FileType

        assert get_file_type("audio.mp3") == FileType.AUDIO
        assert get_file_type("audio.wav") == FileType.AUDIO
        assert get_file_type("audio.m4a") == FileType.AUDIO

    def test_get_file_type_video(self):
        """Test file type detection for video."""
        from app.api.routes.upload import get_file_type
        from app.models import FileType

        assert get_file_type("video.mp4") == FileType.VIDEO
        assert get_file_type("video.webm") == FileType.VIDEO

    def test_get_file_type_unsupported(self):
        """Test file type detection for unsupported types."""
        from app.api.routes.upload import get_file_type
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            get_file_type("file.txt")

        assert exc_info.value.status_code == 400

    def test_get_mime_type(self):
        """Test MIME type detection."""
        from app.api.routes.upload import get_mime_type

        assert get_mime_type("doc.pdf") == "application/pdf"
        assert get_mime_type("audio.mp3") == "audio/mpeg"
        assert get_mime_type("audio.wav") == "audio/wav"
        assert get_mime_type("video.mp4") == "video/mp4"
        assert get_mime_type("video.webm") == "video/webm"
        assert get_mime_type("unknown.xyz") == "application/octet-stream"
