"""PDF processing service using PyMuPDF."""

import asyncio
from typing import List, Tuple

import fitz  # PyMuPDF

from app.config import get_settings

settings = get_settings()


async def process_pdf(file_path: str) -> str:
    """
    Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text content
    """
    # Run in executor to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_pdf_text, file_path)


def _extract_pdf_text(file_path: str) -> str:
    """Synchronous PDF text extraction."""
    text_content = []

    with fitz.open(file_path) as doc:
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                text_content.append(f"[Page {page_num + 1}]\n{text}")

    return "\n\n".join(text_content)


def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Tuple[str, int]]:
    """
    Split text into chunks with overlap.

    Args:
        text: Text to split
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks

    Returns:
        List of (chunk_text, chunk_index) tuples
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    if not text:
        return []

    # Split by paragraphs first
    paragraphs = text.split("\n\n")

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph would exceed chunk size
        if len(current_chunk) + len(para) + 2 > chunk_size:
            if current_chunk:
                chunks.append((current_chunk.strip(), chunk_index))
                chunk_index += 1

                # Keep overlap from previous chunk
                words = current_chunk.split()
                overlap_words = (
                    words[-chunk_overlap:] if len(words) > chunk_overlap else words
                )
                current_chunk = " ".join(overlap_words) + "\n\n" + para
            else:
                # Paragraph itself is too long, split by sentences
                sentences = split_into_sentences(para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 > chunk_size:
                        if current_chunk:
                            chunks.append((current_chunk.strip(), chunk_index))
                            chunk_index += 1
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    # Add remaining chunk
    if current_chunk.strip():
        chunks.append((current_chunk.strip(), chunk_index))

    return chunks


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    import re

    # Simple sentence splitting
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


async def extract_pdf_with_metadata(file_path: str) -> dict:
    """
    Extract text and metadata from PDF.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dictionary with text, metadata, and page info
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_pdf_with_metadata_sync, file_path)


def _extract_pdf_with_metadata_sync(file_path: str) -> dict:
    """Synchronous extraction with metadata."""
    result = {
        "text": "",
        "metadata": {},
        "pages": [],
    }

    with fitz.open(file_path) as doc:
        # Extract metadata
        result["metadata"] = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "keywords": doc.metadata.get("keywords", ""),
            "page_count": len(doc),
        }

        # Extract text page by page
        all_text = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            page_info = {
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
            }
            result["pages"].append(page_info)
            if text.strip():
                all_text.append(f"[Page {page_num + 1}]\n{text}")

        result["text"] = "\n\n".join(all_text)

    return result
