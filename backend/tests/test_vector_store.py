"""Tests for vector store service."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


class TestVectorStore:
    """Test vector store functions."""

    def test_get_embedding_model(self):
        """Test embedding model loading."""
        with patch("sentence_transformers.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model

            # Reset the global model
            import app.services.vector_store as vs
            from app.services.vector_store import get_embedding_model

            vs._embedding_model = None

            model = get_embedding_model()

            assert model is mock_model
            mock_st.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_vector_store_new(self):
        """Test initializing new vector store."""
        with patch("faiss.IndexFlatL2") as mock_index_class:
            with patch("os.path.exists", return_value=False):
                with patch("os.makedirs"):
                    with patch(
                        "app.services.vector_store.get_embedding_model"
                    ) as mock_model:
                        mock_model.return_value.get_sentence_embedding_dimension.return_value = (
                            384
                        )

                        import app.services.vector_store as vs
                        from app.services.vector_store import initialize_vector_store

                        # Reset state
                        vs._faiss_index = None
                        vs._document_store = {}
                        vs._chunk_to_doc = {}
                        vs._current_idx = 0

                        await initialize_vector_store()

                        mock_index_class.assert_called_with(384)

    @pytest.mark.asyncio
    async def test_index_document(self):
        """Test document indexing."""
        from app.services.vector_store import index_document

        with patch("app.services.vector_store._index_document_sync") as mock_sync:
            mock_sync.return_value = 5

            result = await index_document("doc-123", "Test content")

            assert result == 5
            mock_sync.assert_called_once()

    def test_index_document_sync_text(self):
        """Test synchronous document indexing for text."""
        import app.services.vector_store as vs

        # Setup mocks
        mock_index = MagicMock()
        mock_index.ntotal = 0

        with patch.object(vs, "_faiss_index", mock_index):
            with patch.object(vs, "_document_store", {}):
                with patch.object(vs, "_chunk_to_doc", {}):
                    with patch.object(vs, "_current_idx", 0):
                        with patch(
                            "app.services.vector_store.get_embedding_model"
                        ) as mock_model:
                            mock_model.return_value.encode.return_value = np.zeros(
                                (3, 384), dtype=np.float32
                            )

                            with patch(
                                "app.services.vector_store.chunk_text"
                            ) as mock_chunk:
                                mock_chunk.return_value = [
                                    ("Chunk 1", 0),
                                    ("Chunk 2", 1),
                                    ("Chunk 3", 2),
                                ]

                                with patch("app.services.vector_store._save_sync"):
                                    with patch(
                                        "app.services.vector_store._remove_document_sync"
                                    ):
                                        result = vs._index_document_sync(
                                            "doc-123", "Test content", None
                                        )

                                        assert result == 3

    @pytest.mark.asyncio
    async def test_search_similar(self):
        """Test similarity search."""
        from app.services.vector_store import search_similar

        with patch("app.services.vector_store._search_sync") as mock_sync:
            mock_sync.return_value = [
                {"document_id": "doc-123", "content": "Test", "score": 0.9},
            ]

            results = await search_similar("query", document_id="doc-123", top_k=5)

            assert len(results) == 1
            assert results[0]["score"] == 0.9

    def test_search_sync_empty_index(self):
        """Test search with empty index."""
        import app.services.vector_store as vs

        with patch.object(vs, "_faiss_index", None):
            results = vs._search_sync("query", None, 5)

            assert results == []

    @pytest.mark.asyncio
    async def test_remove_document(self):
        """Test document removal."""
        from app.services.vector_store import remove_document

        with patch("app.services.vector_store._remove_document_sync") as mock_sync:
            await remove_document("doc-123")

            mock_sync.assert_called_once_with("doc-123")

    @pytest.mark.asyncio
    async def test_get_document_chunks(self):
        """Test getting document chunks."""
        import app.services.vector_store as vs
        from app.models import DocumentChunk

        chunks = [
            DocumentChunk(document_id="doc-123", content="Test", chunk_index=0),
        ]

        with patch.object(vs, "_document_store", {"doc-123": chunks}):
            from app.services.vector_store import get_document_chunks

            result = await get_document_chunks("doc-123")

            assert len(result) == 1
            assert result[0].content == "Test"

    @pytest.mark.asyncio
    async def test_get_document_chunks_not_found(self):
        """Test getting chunks for non-existent document."""
        import app.services.vector_store as vs

        with patch.object(vs, "_document_store", {}):
            from app.services.vector_store import get_document_chunks

            result = await get_document_chunks("non-existent")

            assert result == []
