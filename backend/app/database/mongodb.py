"""MongoDB database connection and utilities."""

from typing import Optional

from app.config import get_settings
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

settings = get_settings()


class MongoDB:
    """MongoDB connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


mongodb = MongoDB()


async def connect_to_mongodb():
    """Connect to MongoDB database."""
    mongodb.client = AsyncIOMotorClient(settings.mongodb_url)
    mongodb.db = mongodb.client[settings.mongodb_db_name]

    # Create indexes for better query performance
    await mongodb.db.documents.create_index("filename")
    await mongodb.db.documents.create_index("file_type")
    await mongodb.db.documents.create_index("created_at")
    await mongodb.db.chunks.create_index("document_id")
    await mongodb.db.chat_history.create_index("document_id")

    print(f"Connected to MongoDB: {settings.mongodb_db_name}")


async def close_mongodb_connection():
    """Close MongoDB connection."""
    if mongodb.client:
        mongodb.client.close()
        print("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    if mongodb.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongodb first.")
    return mongodb.db
