"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOllamaClient:
    """Test Ollama client."""

    @pytest.mark.asyncio
    async def test_generate(self):
        """Test generate method."""
        from app.services.llm import OllamaClient

        client = OllamaClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Test response"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client.generate("Test prompt")

            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_system(self):
        """Test generate with system prompt."""
        from app.services.llm import OllamaClient

        client = OllamaClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "Test response"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client.generate("Test prompt", system="You are helpful")

            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test health check success."""
        from app.services.llm import OllamaClient

        client = OllamaClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await client.check_health()

            assert result is True

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check failure."""
        from app.services.llm import OllamaClient

        client = OllamaClient()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client

            result = await client.check_health()

            assert result is False


class TestRAGFunctions:
    """Test RAG-related functions."""

    def test_build_rag_prompt(self):
        """Test RAG prompt building."""
        from app.services.llm import build_rag_prompt

        chunks = [
            {"content": "First chunk content", "score": 0.9},
            {"content": "Second chunk content", "score": 0.8},
        ]

        prompt = build_rag_prompt("What is this about?", chunks)

        assert "First chunk content" in prompt
        assert "Second chunk content" in prompt
        assert "What is this about?" in prompt
        assert "[Source 1]" in prompt
        assert "[Source 2]" in prompt

    def test_build_rag_prompt_with_timestamps(self):
        """Test RAG prompt with timestamps."""
        from app.services.llm import build_rag_prompt

        chunks = [
            {
                "content": "Test content",
                "timestamp": {"start": 60, "end": 65},
            },
        ]

        prompt = build_rag_prompt("Question?", chunks, include_timestamps=True)

        assert "01:00" in prompt or "1:00" in prompt

    @pytest.mark.asyncio
    async def test_answer_question(self):
        """Test question answering."""
        from app.services.llm import answer_question

        with patch("app.services.llm.search_similar") as mock_search:
            mock_search.return_value = [
                {"content": "Relevant content", "document_id": "doc-123", "score": 0.9},
            ]

            with patch("app.services.llm.ollama_client") as mock_client:
                mock_client.generate = AsyncMock(return_value="Test answer")

                result = await answer_question("doc-123", "What is this?")

                assert result["answer"] == "Test answer"
                assert len(result["sources"]) == 1

    @pytest.mark.asyncio
    async def test_answer_question_no_chunks(self):
        """Test question answering with no relevant chunks."""
        from app.services.llm import answer_question

        with patch("app.services.llm.search_similar") as mock_search:
            mock_search.return_value = []

            result = await answer_question("doc-123", "What is this?")

            assert "couldn't find" in result["answer"].lower()
            assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_generate_summary(self):
        """Test summary generation."""
        from app.services.llm import generate_summary

        with patch("app.services.llm.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value="This is a summary.")

            result = await generate_summary("Long document content...")

            assert result == "This is a summary."

    @pytest.mark.asyncio
    async def test_generate_summary_truncation(self):
        """Test summary with long content truncation."""
        from app.services.llm import generate_summary

        long_content = "x" * 5000

        with patch("app.services.llm.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value="Summary")

            await generate_summary(long_content)

            # Check that generate was called with truncated content
            call_args = mock_client.generate.call_args
            assert len(call_args[0][0]) < len(long_content) + 500

    @pytest.mark.asyncio
    async def test_check_ollama_connection(self):
        """Test Ollama connection check."""
        from app.services.llm import check_ollama_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": [{"name": "llama3.2"}]}
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await check_ollama_connection()

            assert result["connected"] is True
            assert "llama3.2" in result["models"]
