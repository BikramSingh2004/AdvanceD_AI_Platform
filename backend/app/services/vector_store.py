"""Vector store service using FAISS and sentence-transformers."""
import asyncio
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from app.config import get_settings
from app.models import TimestampSegment, DocumentChunk
from app.services.pdf_processor import chunk_text

settings = get_settings()

# Global instances
_embedding_model = None
_faiss_index = None
_document_store: Dict[str, List[DocumentChunk]] = {}  # document_id -> chunks
_chunk_to_doc: Dict[int, Tuple[str, int]] = {}  # faiss_idx -> (doc_id, chunk_idx)
_current_idx = 0

INDEX_PATH = "vector_store/faiss.index"
STORE_PATH = "vector_store/store.pkl"


def get_embedding_model():
    """Get or load the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


async def initialize_vector_store():
    """Initialize the vector store on startup."""
    global _faiss_index, _document_store, _chunk_to_doc, _current_idx
    
    import faiss
    
    # Create directory
    os.makedirs("vector_store", exist_ok=True)
    
    # Load existing index if available
    if os.path.exists(INDEX_PATH) and os.path.exists(STORE_PATH):
        try:
            _faiss_index = faiss.read_index(INDEX_PATH)
            with open(STORE_PATH, 'rb') as f:
                data = pickle.load(f)
                _document_store = data.get('document_store', {})
                _chunk_to_doc = data.get('chunk_to_doc', {})
                _current_idx = data.get('current_idx', 0)
            print(f"Loaded existing vector store with {_faiss_index.ntotal} vectors")
        except Exception as e:
            print(f"Error loading vector store: {e}. Creating new one.")
            _create_new_index()
    else:
        _create_new_index()


def _create_new_index():
    """Create a new FAISS index."""
    global _faiss_index, _document_store, _chunk_to_doc, _current_idx
    import faiss
    
    # Get embedding dimension
    model = get_embedding_model()
    dimension = model.get_sentence_embedding_dimension()
    
    # Create FAISS index (using L2 distance)
    _faiss_index = faiss.IndexFlatL2(dimension)
    _document_store = {}
    _chunk_to_doc = {}
    _current_idx = 0
    print(f"Created new vector store with dimension {dimension}")


async def save_vector_store():
    """Save vector store to disk."""
    import faiss
    
    os.makedirs("vector_store", exist_ok=True)
    
    if _faiss_index is not None:
        faiss.write_index(_faiss_index, INDEX_PATH)
        with open(STORE_PATH, 'wb') as f:
            pickle.dump({
                'document_store': _document_store,
                'chunk_to_doc': _chunk_to_doc,
                'current_idx': _current_idx,
            }, f)


async def index_document(
    document_id: str,
    content: str,
    timestamps: List[TimestampSegment] = None,
) -> int:
    """
    Index a document's content in the vector store.
    
    Args:
        document_id: Document ID
        content: Document text content
        timestamps: Optional timestamps for audio/video
        
    Returns:
        Number of chunks indexed
    """
    global _current_idx
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _index_document_sync, document_id, content, timestamps
    )


def _index_document_sync(
    document_id: str,
    content: str,
    timestamps: List[TimestampSegment] = None,
) -> int:
    """Synchronous document indexing."""
    global _current_idx, _faiss_index, _document_store, _chunk_to_doc
    
    import faiss
    
    # Initialize if needed
    if _faiss_index is None:
        _create_new_index()
    
    # Remove existing chunks for this document
    _remove_document_sync(document_id)
    
    # Create chunks
    if timestamps:
        # For audio/video, use timestamp segments as chunks
        chunks = []
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
        # For text/PDF, chunk the content
        text_chunks = chunk_text(content)
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
    
    # Add to FAISS index
    start_idx = _current_idx
    _faiss_index.add(embeddings.astype(np.float32))
    
    # Update mappings
    for i, chunk in enumerate(chunks):
        faiss_idx = start_idx + i
        _chunk_to_doc[faiss_idx] = (document_id, chunk.chunk_index)
    
    _current_idx += len(chunks)
    _document_store[document_id] = chunks
    
    # Save to disk
    _save_sync()
    
    return len(chunks)


def _save_sync():
    """Synchronous save."""
    import faiss
    
    os.makedirs("vector_store", exist_ok=True)
    
    if _faiss_index is not None:
        faiss.write_index(_faiss_index, INDEX_PATH)
        with open(STORE_PATH, 'wb') as f:
            pickle.dump({
                'document_store': _document_store,
                'chunk_to_doc': _chunk_to_doc,
                'current_idx': _current_idx,
            }, f)


async def search_similar(
    query: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search for similar chunks in the vector store.
    
    Args:
        query: Search query
        document_id: Optional document ID to filter results
        top_k: Number of results to return
        
    Returns:
        List of matching chunks with scores
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _search_sync, query, document_id, top_k
    )


def _search_sync(
    query: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Synchronous search."""
    global _faiss_index, _document_store, _chunk_to_doc
    
    if _faiss_index is None or _faiss_index.ntotal == 0:
        return []
    
    # Generate query embedding
    model = get_embedding_model()
    query_embedding = model.encode([query], convert_to_numpy=True)
    
    # Search in FAISS
    search_k = top_k * 3 if document_id else top_k  # Search more if filtering
    distances, indices = _faiss_index.search(query_embedding.astype(np.float32), search_k)
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:  # No more results
            break
            
        doc_id, chunk_idx = _chunk_to_doc.get(idx, (None, None))
        if doc_id is None:
            continue
            
        # Filter by document ID if specified
        if document_id and doc_id != document_id:
            continue
        
        chunks = _document_store.get(doc_id, [])
        chunk = next((c for c in chunks if c.chunk_index == chunk_idx), None)
        
        if chunk:
            result = {
                "document_id": doc_id,
                "chunk_index": chunk_idx,
                "content": chunk.content,
                "score": float(1 / (1 + dist)),  # Convert distance to similarity score
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
    """Remove a document from the vector store."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _remove_document_sync, document_id)


def _remove_document_sync(document_id: str):
    """Synchronous document removal."""
    global _document_store, _chunk_to_doc
    
    # Note: FAISS doesn't support true deletion with IndexFlatL2
    # We just remove from our mappings; the vectors remain but won't be returned
    # For production, use IndexIDMap or rebuild index periodically
    
    if document_id in _document_store:
        # Remove chunk mappings
        indices_to_remove = [
            idx for idx, (doc_id, _) in _chunk_to_doc.items()
            if doc_id == document_id
        ]
        for idx in indices_to_remove:
            del _chunk_to_doc[idx]
        
        del _document_store[document_id]
        _save_sync()


async def get_document_chunks(document_id: str) -> List[DocumentChunk]:
    """Get all chunks for a document."""
    return _document_store.get(document_id, [])
