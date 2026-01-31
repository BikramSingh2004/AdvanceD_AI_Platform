"""LLM service using Ollama for local inference."""

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from app.config import get_settings
from app.services.transcription import format_timestamp
from app.services.vector_store import search_similar

settings = get_settings()


class OllamaClient:
    """Client for Ollama API."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate(
        self,
        prompt: str,
        system: str = None,
        stream: bool = False,
    ) -> str:
        """
        Generate a response from Ollama.

        Args:
            prompt: User prompt
            system: System prompt
            stream: Whether to stream the response

        Returns:
            Generated text
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if system:
                payload["system"] = system

            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_stream(
        self,
        prompt: str,
        system: str = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama.

        Args:
            prompt: User prompt
            system: System prompt

        Yields:
            Generated tokens
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
            }
            if system:
                payload["system"] = system

            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json

                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break

    async def check_health(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


# Global client instance
ollama_client = OllamaClient()


def build_rag_prompt(
    question: str,
    context_chunks: List[Dict[str, Any]],
    include_timestamps: bool = True,
) -> str:
    """
    Build a RAG prompt with retrieved context.

    Args:
        question: User's question
        context_chunks: Retrieved context chunks
        include_timestamps: Whether to include timestamp info

    Returns:
        Formatted prompt string
    """
    context_parts = []

    for i, chunk in enumerate(context_chunks, 1):
        chunk_text = f"[Source {i}]\n{chunk['content']}"

        if include_timestamps and "timestamp" in chunk:
            ts = chunk["timestamp"]
            start_fmt = format_timestamp(ts["start"])
            end_fmt = format_timestamp(ts["end"])
            chunk_text += f"\n(Timestamp: {start_fmt} - {end_fmt})"

        context_parts.append(chunk_text)

    context = "\n\n".join(context_parts)

    prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Answer based only on the provided context
- If referencing specific parts, mention the source number
- For audio/video content, include relevant timestamps in your answer using the format [MM:SS] or [HH:MM:SS]
- Be concise and accurate

ANSWER:"""

    return prompt


async def answer_question(
    document_id: str,
    question: str,
    include_timestamps: bool = True,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Answer a question about a document using RAG.

    Args:
        document_id: Document ID to query
        question: User's question
        include_timestamps: Include timestamp references
        top_k: Number of context chunks to retrieve

    Returns:
        Answer with sources and timestamps
    """
    # Retrieve relevant chunks
    chunks = await search_similar(question, document_id=document_id, top_k=top_k)

    if not chunks:
        return {
            "answer": "I couldn't find relevant information in the document to answer your question.",
            "sources": [],
            "timestamps": [],
        }

    # Build and send prompt
    prompt = build_rag_prompt(question, chunks, include_timestamps)
    system_prompt = """You are a helpful assistant that answers questions based on document content. 
Be accurate, concise, and always reference the source material when possible.
For audio/video content, include timestamps in [MM:SS] format when relevant."""

    answer = await ollama_client.generate(prompt, system=system_prompt)

    # Extract timestamps from sources
    timestamps = []
    for chunk in chunks:
        if "timestamp" in chunk:
            ts = chunk["timestamp"]
            timestamps.append(
                {
                    "start": ts["start"],
                    "end": ts["end"],
                    "text": (
                        chunk["content"][:100] + "..."
                        if len(chunk["content"]) > 100
                        else chunk["content"]
                    ),
                }
            )

    return {
        "answer": answer,
        "sources": chunks,
        "timestamps": timestamps,
    }


async def answer_question_stream(
    document_id: str,
    question: str,
    include_timestamps: bool = True,
    top_k: int = 5,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream an answer to a question about a document.

    Args:
        document_id: Document ID to query
        question: User's question
        include_timestamps: Include timestamp references
        top_k: Number of context chunks to retrieve

    Yields:
        Tokens and metadata
    """
    # Retrieve relevant chunks
    chunks = await search_similar(question, document_id=document_id, top_k=top_k)

    if not chunks:
        yield {
            "token": "I couldn't find relevant information in the document to answer your question.",
            "done": True,
            "sources": [],
            "timestamps": [],
        }
        return

    # Extract timestamps from sources
    timestamps = []
    for chunk in chunks:
        if "timestamp" in chunk:
            ts = chunk["timestamp"]
            timestamps.append(
                {
                    "start": ts["start"],
                    "end": ts["end"],
                    "text": (
                        chunk["content"][:100] + "..."
                        if len(chunk["content"]) > 100
                        else chunk["content"]
                    ),
                }
            )

    # Build and stream prompt
    prompt = build_rag_prompt(question, chunks, include_timestamps)
    system_prompt = """You are a helpful assistant that answers questions based on document content. 
Be accurate, concise, and always reference the source material when possible.
For audio/video content, include timestamps in [MM:SS] format when relevant."""

    async for token in ollama_client.generate_stream(prompt, system=system_prompt):
        yield {
            "token": token,
            "done": False,
            "sources": [],
            "timestamps": [],
        }

    # Final message with sources
    yield {
        "token": "",
        "done": True,
        "sources": chunks,
        "timestamps": timestamps,
    }


async def generate_summary(content: str, max_length: int = 500) -> str:
    """
    Generate a summary of document content.

    Args:
        content: Document text content
        max_length: Maximum content to summarize

    Returns:
        Summary text
    """
    # Truncate if too long
    if len(content) > 4000:
        content = content[:4000] + "..."

    prompt = f"""Please provide a concise summary of the following content in 2-3 paragraphs:

{content}

SUMMARY:"""

    system = "You are a helpful assistant that creates clear, concise summaries of documents."

    try:
        summary = await ollama_client.generate(prompt, system=system)
        return summary.strip()
    except Exception as e:
        return f"Summary generation failed: {str(e)}"


async def check_ollama_connection() -> Dict[str, Any]:
    """Check Ollama connection and available models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "connected": True,
                    "models": models,
                    "configured_model": settings.ollama_model,
                    "model_available": settings.ollama_model in models,
                }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
