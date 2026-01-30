"""Tests for documents API routes."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os


class TestDocumentsAPI:
    """Test documents API endpoints."""

    def test_list_documents_empty(self, client, mock_mongodb):
        """Test listing documents when empty."""
        response = client.get("/api/documents/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0

    def test_list_documents(self, client, mock_mongodb, sample_document):
        """Test listing documents."""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[sample_document]
        )
        mock_mongodb.documents.find = MagicMock(return_value=mock_cursor)
        mock_mongodb.documents.count_documents = AsyncMock(return_value=1)
        
        response = client.get("/api/documents/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 1
        assert data["total"] == 1

    def test_list_documents_with_filter(self, client, mock_mongodb, sample_document):
        """Test listing documents with file type filter."""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[sample_document]
        )
        mock_mongodb.documents.find = MagicMock(return_value=mock_cursor)
        mock_mongodb.documents.count_documents = AsyncMock(return_value=1)
        
        response = client.get("/api/documents/?file_type=pdf")
        
        assert response.status_code == 200

    def test_get_document(self, client, mock_mongodb, sample_document):
        """Test getting a specific document."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        
        response = client.get(f"/api/documents/{sample_document['_id']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_document["_id"]
        assert data["filename"] == sample_document["filename"]

    def test_get_document_not_found(self, client, mock_mongodb):
        """Test getting non-existent document."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=None)
        
        response = client.get("/api/documents/non-existent")
        
        assert response.status_code == 404

    def test_get_document_content(self, client, mock_mongodb, sample_document):
        """Test getting document content."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        
        response = client.get(f"/api/documents/{sample_document['_id']}/content")
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "timestamps" in data

    def test_get_document_content_not_processed(self, client, mock_mongodb, sample_document):
        """Test getting content of unprocessed document."""
        sample_document["processed"] = False
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        
        response = client.get(f"/api/documents/{sample_document['_id']}/content")
        
        assert response.status_code == 400

    def test_delete_document(self, client, mock_mongodb, sample_document):
        """Test deleting a document."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        mock_mongodb.documents.delete_one = AsyncMock()
        mock_mongodb.chunks.delete_many = AsyncMock()
        mock_mongodb.chat_history.delete_many = AsyncMock()
        
        with patch("os.path.exists", return_value=True):
            with patch("os.remove"):
                with patch("app.api.routes.documents.remove_document", new_callable=AsyncMock):
                    response = client.delete(f"/api/documents/{sample_document['_id']}")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_delete_document_not_found(self, client, mock_mongodb):
        """Test deleting non-existent document."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=None)
        
        response = client.delete("/api/documents/non-existent")
        
        assert response.status_code == 404

    def test_get_timestamps(self, client, mock_mongodb, sample_audio_document):
        """Test getting document timestamps."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_audio_document)
        
        response = client.get(f"/api/documents/{sample_audio_document['_id']}/timestamps")
        
        assert response.status_code == 200
        data = response.json()
        assert "timestamps" in data
        assert len(data["timestamps"]) == 2

    def test_get_timestamps_pdf(self, client, mock_mongodb, sample_document):
        """Test getting timestamps for PDF (should fail)."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        
        response = client.get(f"/api/documents/{sample_document['_id']}/timestamps")
        
        assert response.status_code == 400
        assert "audio/video" in response.json()["detail"].lower()

    def test_get_timestamps_not_processed(self, client, mock_mongodb, sample_audio_document):
        """Test getting timestamps for unprocessed document."""
        sample_audio_document["processed"] = False
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_audio_document)
        
        response = client.get(f"/api/documents/{sample_audio_document['_id']}/timestamps")
        
        assert response.status_code == 400
