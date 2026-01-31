"""Tests for PDF processing service."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestPdfProcessor:
    """Test PDF processing functions."""

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        from app.services.pdf_processor import chunk_text

        text = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)

        assert len(chunks) > 0
        assert all(isinstance(c, tuple) for c in chunks)
        assert all(len(c) == 2 for c in chunks)

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        from app.services.pdf_processor import chunk_text

        chunks = chunk_text("", chunk_size=100, chunk_overlap=10)

        assert chunks == []

    def test_chunk_text_single_paragraph(self):
        """Test chunking single paragraph."""
        from app.services.pdf_processor import chunk_text

        text = "This is a single paragraph of text."
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=10)

        assert len(chunks) == 1
        assert chunks[0][0] == text
        assert chunks[0][1] == 0

    def test_chunk_text_long_paragraph(self):
        """Test chunking very long paragraph."""
        from app.services.pdf_processor import chunk_text

        # Create a long paragraph
        text = "This is a sentence. " * 50
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)

        assert len(chunks) > 1
        # Check indices are sequential
        for i, (_, idx) in enumerate(chunks):
            assert idx == i

    def test_split_into_sentences(self):
        """Test sentence splitting."""
        from app.services.pdf_processor import split_into_sentences

        text = "This is sentence one. This is sentence two! Is this sentence three?"
        sentences = split_into_sentences(text)

        assert len(sentences) == 3
        assert sentences[0] == "This is sentence one."
        assert sentences[1] == "This is sentence two!"
        assert sentences[2] == "Is this sentence three?"

    def test_split_into_sentences_empty(self):
        """Test splitting empty text."""
        from app.services.pdf_processor import split_into_sentences

        sentences = split_into_sentences("")

        assert sentences == []

    @pytest.mark.asyncio
    async def test_process_pdf_mock(self):
        """Test PDF processing with mocked file."""
        from app.services.pdf_processor import process_pdf

        with patch("app.services.pdf_processor._extract_pdf_text") as mock_extract:
            mock_extract.return_value = "[Page 1]\nTest content"

            result = await process_pdf("test.pdf")

            assert result == "[Page 1]\nTest content"
            mock_extract.assert_called_once_with("test.pdf")

    def test_extract_pdf_text_sync(self):
        """Test synchronous PDF extraction with mock."""
        from app.services.pdf_processor import _extract_pdf_text

        with patch("fitz.open") as mock_fitz:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Page content"
            mock_doc.__iter__ = lambda self: iter([mock_page])
            mock_doc.__enter__ = lambda self: self
            mock_doc.__exit__ = MagicMock(return_value=False)
            mock_fitz.return_value = mock_doc

            result = _extract_pdf_text("test.pdf")

            assert "Page content" in result
            assert "[Page 1]" in result

    @pytest.mark.asyncio
    async def test_extract_pdf_with_metadata(self):
        """Test PDF extraction with metadata."""
        from app.services.pdf_processor import extract_pdf_with_metadata

        with patch(
            "app.services.pdf_processor._extract_pdf_with_metadata_sync"
        ) as mock_extract:
            mock_extract.return_value = {
                "text": "Content",
                "metadata": {"title": "Test", "page_count": 1},
                "pages": [{"page_number": 1, "text": "Content"}],
            }

            result = await extract_pdf_with_metadata("test.pdf")

            assert result["text"] == "Content"
            assert result["metadata"]["title"] == "Test"
            assert len(result["pages"]) == 1
