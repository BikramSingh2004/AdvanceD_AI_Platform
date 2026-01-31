"""API module."""

from app.api.routes import chat_router, documents_router, upload_router

__all__ = ["upload_router", "documents_router", "chat_router"]
