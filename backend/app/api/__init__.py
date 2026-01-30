"""API module."""
from app.api.routes import upload_router, documents_router, chat_router

__all__ = ["upload_router", "documents_router", "chat_router"]
