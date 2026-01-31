"""Document management API routes."""

import os
from typing import Optional

from app.database import get_database
from app.models import DocumentListResponse, DocumentResponse, FileType
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    file_type: Optional[FileType] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all uploaded documents with optional filtering."""
    query = {}
    if file_type:
        query["file_type"] = file_type.value

    cursor = db.documents.find(query).skip(skip).limit(limit).sort("created_at", -1)
    documents = await cursor.to_list(length=limit)
    total = await db.documents.count_documents(query)

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc["_id"],
                filename=doc["filename"],
                file_type=FileType(doc["file_type"]),
                file_size=doc["file_size"],
                summary=doc.get("summary"),
                processed=doc["processed"],
                created_at=doc["created_at"],
                chunk_count=doc.get("chunk_count", 0),
            )
            for doc in documents
        ],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get details of a specific document."""
    document = await db.documents.find_one({"_id": document_id})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document["_id"],
        filename=document["filename"],
        file_type=FileType(document["file_type"]),
        file_size=document["file_size"],
        summary=document.get("summary"),
        processed=document["processed"],
        created_at=document["created_at"],
        chunk_count=document.get("chunk_count", 0),
    )


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get the extracted text content of a document."""
    document = await db.documents.find_one({"_id": document_id})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document["processed"]:
        raise HTTPException(status_code=400, detail="Document not yet processed")

    return {
        "id": document["_id"],
        "content": document.get("content", ""),
        "timestamps": document.get("timestamps", []),
    }


import os

# here
from fastapi import Request
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_206_PARTIAL_CONTENT


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    document = await db.documents.find_one({"_id": document_id})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = document["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    # ✅ RANGE REQUEST (this enables seeking)
    if range_header:
        start_str, end_str = range_header.replace("bytes=", "").split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)

        def iter_file():
            with open(file_path, "rb") as f:
                f.seek(start)
                yield f.read(end - start + 1)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": document["mime_type"],
        }

        return StreamingResponse(
            iter_file(),
            status_code=HTTP_206_PARTIAL_CONTENT,
            headers=headers,
        )

    # ✅ NORMAL FULL FILE (first load)
    return StreamingResponse(
        open(file_path, "rb"),
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Type": document["mime_type"],
        },
    )


# @router.get("/{document_id}/file")
# async def get_document_file(
#     document_id: str,
#     db: AsyncIOMotorDatabase = Depends(get_database),
# ):
#     """Download the original file."""
#     document = await db.documents.find_one({"_id": document_id})
#
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
#
#     file_path = document["file_path"]
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found on disk")
#
#     return FileResponse(
#         path=file_path,
#         filename=document["filename"],
#         media_type=document["mime_type"],
#     )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a document and its associated data."""
    document = await db.documents.find_one({"_id": document_id})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    file_path = document["file_path"]
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    await db.documents.delete_one({"_id": document_id})
    await db.chunks.delete_many({"document_id": document_id})
    await db.chat_history.delete_many({"document_id": document_id})

    # Remove from vector store
    from app.services.vector_store import remove_document

    await remove_document(document_id)

    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/timestamps")
async def get_document_timestamps(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get timestamps for audio/video documents."""
    document = await db.documents.find_one({"_id": document_id})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document["file_type"] not in [FileType.AUDIO.value, FileType.VIDEO.value]:
        raise HTTPException(
            status_code=400, detail="Timestamps only available for audio/video files"
        )

    if not document["processed"]:
        raise HTTPException(status_code=400, detail="Document not yet processed")

    return {
        "id": document["_id"],
        "timestamps": document.get("timestamps", []),
    }
