"""Vector store service using FAISS and sentence-transformers."""

import asyncio
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.config import get_settings
from app.models import DocumentChunk, TimestampSegment
from app.services.pdf_processor import chunk_text

settings = get_settings()

# Module-level globals (initialized here)
_embedding_model = None  # type: ignore
_faiss_index = None  # type: ignore
_document_store: Dict[str, List[DocumentChunk]] = {}
_chunk_to_doc: Dict[int, Tuple[str, int]] = {}
_current_idx = 0

INDEX_PATH = "vector_store/faiss.index"
STORE_PATH = "vector_store/store.pkl"


def get_embedding_model():
    """Get or lazily load the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


async def initialize_vector_store():
    """
    Initialize the vector store on startup. Loads an existing FAISS index
    and document store if available, otherwise creates a new empty index.
    """
    global _faiss_index, _document_store, _chunk_to_doc, _current_idx

    import faiss  # local import to keep startup lighter if not used

    os.makedirs("vector_store", exist_ok=True)

    if os.path.exists(INDEX_PATH) and os.path.exists(STORE_PATH):
        try:
            _faiss_index = faiss.read_index(INDEX_PATH)
            with open(STORE_PATH, "rb") as f:
                data = pickle.load(f)
                _document_store = data.get("document_store", {})
                _chunk_to_doc = data.get("chunk_to_doc", {})
                _current_idx = data.get("current_idx", 0)
            print(f"Loaded existing vector store with {_faiss_index.ntotal} vectors")
        except Exception as e:
            print(f"Error loading vector store: {e}. Creating new one.")
            _create_new_index()
    else:
        _create_new_index()


def _create_new_index():
    """Create a new FAISS index and reset in-memory stores."""
    global _faiss_index, _document_store, _chunk_to_doc, _current_idx

    import faiss

    model = get_embedding_model()
    dimension = model.get_sentence_embedding_dimension()

    # Use a simple flat L2 index for clarity (production may use IVF/IDMap)
    _faiss_index = faiss.IndexFlatL2(dimension)
    _document_store = {}
    _chunk_to_doc = {}
    _current_idx = 0
    print(f"Created new vector store with dimension {dimension}")


async def save_vector_store():
    """Persist FAISS index and document mappings to disk."""
    import faiss

    os.makedirs("vector_store", exist_ok=True)

    if _faiss_index is not None:
        faiss.write_index(_faiss_index, INDEX_PATH)
        with open(STORE_PATH, "wb") as f:
            pickle.dump(
                {
                    "document_store": _document_store,
                    "chunk_to_doc": _chunk_to_doc,
                    "current_idx": _current_idx,
                },
                f,
            )


async def index_document(
    document_id: str,
    content: str,
    timestamps: Optional[List[TimestampSegment]] = None,
) -> int:
    """
    Index a document's content in the vector store asynchronously.

    Returns the number of chunks indexed.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _index_document_sync, document_id, content, timestamps
    )


def _index_document_sync(
    document_id: str,
    content: str,
    timestamps: Optional[List[TimestampSegment]] = None,
) -> int:
    """Synchronous document indexing implementation."""
    global _current_idx

    import faiss

    # Ensure index exists
    if _faiss_index is None:
        _create_new_index()

    # Remove any existing chunks for this document
    _remove_document_sync(document_id)

    # Build chunks
    if timestamps:
        chunks: List[DocumentChunk] = []
        for i, ts in enumerate(timestamps):
            chunk = DocumentChunk(
                document_id=document_id,
                content=ts.text,
                chunk_index=i,
                timestamp=ts,
                metadata={"start": ts.start, "end": ts.end},
            )
            chunks.append(chunk)
    else:
        text_chunks = chunk_text(content)
        # chunk_text is expected to return iterable of (text, index)
        chunks = [
            DocumentChunk(
                document_id=document_id,
                content=text,
                chunk_index=idx,
                metadata={},
            )
            for text, idx in text_chunks
        ]

    if not chunks:
        return 0

    # Generate embeddings
    model = get_embedding_model()
    texts = [c.content for c in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True)

    # Ensure correct shape and dtype for FAISS
    arr = np.asarray(embeddings, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    # Add vectors to FAISS index
    start_idx = _current_idx
    _faiss_index.add(arr)

    # Update mappings for each new vector
    for i, chunk in enumerate(chunks):
        faiss_idx = start_idx + i
        _chunk_to_doc[faiss_idx] = (document_id, chunk.chunk_index)

    _current_idx += len(chunks)
    _document_store[document_id] = chunks

    # Persist synchronously
    _save_sync()

    return len(chunks)


def _save_sync():
    """Synchronous save helper used by indexing/removal."""
    import faiss

    os.makedirs("vector_store", exist_ok=True)

    if _faiss_index is not None:
        faiss.write_index(_faiss_index, INDEX_PATH)
        with open(STORE_PATH, "wb") as f:
            pickle.dump(
                {
                    "document_store": _document_store,
                    "chunk_to_doc": _chunk_to_doc,
                    "current_idx": _current_idx,
                },
                f,
            )


async def search_similar(
    query: str, document_id: Optional[str] = None, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Asynchronously search for similar chunks."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_sync, query, document_id, top_k)


def _search_sync(
    query: str, document_id: Optional[str] = None, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Synchronous search implementation."""
    if _faiss_index is None or _faiss_index.ntotal == 0:
        return []

    # Build query embedding
    model = get_embedding_model()
    query_embedding = model.encode([query], convert_to_numpy=True)
    q_arr = np.asarray(query_embedding, dtype=np.float32)
    if q_arr.ndim == 1:
        q_arr = q_arr.reshape(1, -1)

    # If filtering by document, search a larger k then filter results
    search_k = top_k * 3 if document_id else top_k
    distances, indices = _faiss_index.search(q_arr, search_k)

    results: List[Dict[str, Any]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            break

        doc_id, chunk_idx = _chunk_to_doc.get(idx, (None, None))
        if doc_id is None:
            continue

        if document_id and doc_id != document_id:
            continue

        chunks = _document_store.get(doc_id, [])
        chunk = next((c for c in chunks if c.chunk_index == chunk_idx), None)
        if chunk:
            result: Dict[str, Any] = {
                "document_id": doc_id,
                "chunk_index": chunk_idx,
                "content": chunk.content,
                "score": float(1 / (1 + dist)),
                "metadata": chunk.metadata,
            }
            if chunk.timestamp:
                result["timestamp"] = {
                    "start": chunk.timestamp.start,
                    "end": chunk.timestamp.end,
                }
            results.append(result)

        if len(results) >= top_k:
            break

    return results


async def remove_document(document_id: str):
    """Asynchronously remove a document's chunks from the index store."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _remove_document_sync, document_id)


def _remove_document_sync(document_id: str):
    """Synchronous removal - updates mappings and persists the store."""
    # Note: IndexFlatL2 does not support deletions; we remove mappings only.
    if document_id in _document_store:
        indices_to_remove = [
            idx for idx, (doc_id, _) in _chunk_to_doc.items() if doc_id == document_id
        ]
        for idx in indices_to_remove:
            if idx in _chunk_to_doc:
                del _chunk_to_doc[idx]

        # Remove document's chunks mapping
        if document_id in _document_store:
            del _document_store[document_id]

        _save_sync()


async def get_document_chunks(document_id: str) -> List[DocumentChunk]:
    """Return all stored chunks for a document (in-memory)."""
    return _document_store.get(document_id, [])
