"""Tests for chat API routes."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestChatAPI:
    """Test chat API endpoints."""

    def test_chat_message(self, client, mock_mongodb, sample_document):
        """Test sending a chat message."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        mock_mongodb.chat_history.update_one = AsyncMock()
        
        with patch("app.api.routes.chat.check_ollama_connection") as mock_check:
            mock_check.return_value = {"connected": True}
            
            with patch("app.api.routes.chat.answer_question") as mock_answer:
                mock_answer.return_value = {
                    "answer": "This is a test answer.",
                    "sources": [{"content": "Test", "score": 0.9}],
                    "timestamps": [],
                }
                
                response = client.post(
                    "/api/chat/",
                    json={
                        "document_id": sample_document["_id"],
                        "message": "What is this about?",
                        "include_timestamps": True,
                    },
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "This is a test answer."
        assert len(data["sources"]) == 1

    def test_chat_document_not_found(self, client, mock_mongodb):
        """Test chat with non-existent document."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=None)
        
        response = client.post(
            "/api/chat/",
            json={
                "document_id": "non-existent",
                "message": "Test?",
            },
        )
        
        assert response.status_code == 404

    def test_chat_document_not_processed(self, client, mock_mongodb, sample_document):
        """Test chat with unprocessed document."""
        sample_document["processed"] = False
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        
        response = client.post(
            "/api/chat/",
            json={
                "document_id": sample_document["_id"],
                "message": "Test?",
            },
        )
        
        assert response.status_code == 400

    def test_chat_ollama_unavailable(self, client, mock_mongodb, sample_document):
        """Test chat when Ollama is unavailable."""
        mock_mongodb.documents.find_one = AsyncMock(return_value=sample_document)
        
        with patch("app.api.routes.chat.check_ollama_connection") as mock_check:
            mock_check.return_value = {"connected": False}
            
            response = client.post(
                "/api/chat/",
                json={
                    "document_id": sample_document["_id"],
                    "message": "Test?",
                },
            )
        
        assert response.status_code == 503

    def test_get_chat_history(self, client, mock_mongodb):
        """Test getting chat history."""
        mock_mongodb.chat_history.find_one = AsyncMock(return_value={
            "document_id": "doc-123",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
        })
        
        response = client.get("/api/chat/history/doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2

    def test_get_chat_history_empty(self, client, mock_mongodb):
        """Test getting chat history when empty."""
        mock_mongodb.chat_history.find_one = AsyncMock(return_value=None)
        
        response = client.get("/api/chat/history/doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []

    def test_clear_chat_history(self, client, mock_mongodb):
        """Test clearing chat history."""
        mock_mongodb.chat_history.delete_one = AsyncMock()
        
        response = client.delete("/api/chat/history/doc-123")
        
        assert response.status_code == 200
        assert "cleared" in response.json()["message"].lower()

    def test_get_chat_status(self, client, mock_mongodb):
        """Test getting chat service status."""
        with patch("app.api.routes.chat.check_ollama_connection") as mock_check:
            mock_check.return_value = {"connected": True, "models": ["llama3.2"]}
            
            response = client.get("/api/chat/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["ollama"]["connected"] is True

    def test_get_chat_status_degraded(self, client, mock_mongodb):
        """Test chat status when Ollama is down."""
        with patch("app.api.routes.chat.check_ollama_connection") as mock_check:
            mock_check.return_value = {"connected": False}
            
            response = client.get("/api/chat/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
