"""API routes module."""

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.upload import router as upload_router

__all__ = ["upload_router", "documents_router", "chat_router"]
