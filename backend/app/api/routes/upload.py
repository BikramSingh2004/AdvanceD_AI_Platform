"""File upload API routes."""

import os
import uuid
from datetime import datetime

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.database import get_database
from app.models import DocumentResponse, FileType

settings = get_settings()
router = APIRouter(prefix="/upload", tags=["upload"])


def get_file_type(filename: str) -> FileType:
    """Determine file type from extension."""
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return FileType.PDF
    elif ext in ["mp3", "wav", "m4a", "ogg"]:
        return FileType.AUDIO
    elif ext in ["mp4", "webm", "mkv", "avi"]:
        return FileType.VIDEO
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    ext = filename.lower().split(".")[-1]
    mime_types = {
        "pdf": "application/pdf",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "avi": "video/x-msvideo",
    }
    return mime_types.get(ext, "application/octet-stream")


async def process_document_background(
    document_id: str, file_path: str, file_type: FileType
):
    """Background task to process uploaded document."""
    from app.database import get_database
    from app.services.pdf_processor import process_pdf
    from app.services.transcription import transcribe_media
    from app.services.vector_store import index_document

    db = get_database()

    try:
        content = ""
        timestamps = []

        if file_type == FileType.PDF:
            content = await process_pdf(file_path)
        elif file_type in [FileType.AUDIO, FileType.VIDEO]:
            result = await transcribe_media(file_path)
            content = result["text"]
            timestamps = result["timestamps"]

        # Index document in vector store
        chunk_count = await index_document(document_id, content, timestamps)

        # Generate summary
        from app.services.llm import generate_summary

        summary = await generate_summary(content[:4000])  # Limit content for summary

        # Update document in database
        await db.documents.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "content": content,
                    "summary": summary,
                    "timestamps": [
                        t.model_dump() if hasattr(t, "model_dump") else t
                        for t in timestamps
                    ],
                    "chunk_count": chunk_count,
                    "processed": True,
                    "processing_error": None,
                }
            },
        )
        print(f"Document {document_id} processed successfully")

    except Exception as e:
        print(f"Error processing document {document_id}: {str(e)}")
        await db.documents.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "processed": False,
                    "processing_error": str(e),
                }
            },
        )


@router.post("/", response_model=DocumentResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Upload a PDF, audio, or video file for processing.

    The file will be saved and processed in the background.
    Processing includes:
    - PDF: Text extraction
    - Audio/Video: Transcription with timestamps
    - All: Vector embedding and indexing
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = file.filename.lower().split(".")[-1]
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed types: {settings.allowed_extensions}",
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size / 1024 / 1024}MB",
        )

    # Generate unique ID and file path
    document_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    safe_filename = f"{document_id}.{file_ext}"
    file_path = os.path.join(settings.upload_dir, safe_filename)

    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Determine file type
    file_type = get_file_type(file.filename)
    mime_type = get_mime_type(file.filename)

    # Create document record
    document = {
        "_id": document_id,
        "filename": file.filename,
        "file_type": file_type.value,
        "file_size": file_size,
        "mime_type": mime_type,
        "file_path": file_path,
        "content": None,
        "summary": None,
        "timestamps": [],
        "chunk_count": 0,
        "created_at": datetime.utcnow(),
        "processed": False,
        "processing_error": None,
    }

    await db.documents.insert_one(document)

    # Start background processing
    background_tasks.add_task(
        process_document_background, document_id, file_path, file_type
    )

    return DocumentResponse(
        id=document_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        summary=None,
        processed=False,
        created_at=document["created_at"],
        chunk_count=0,
    )


@router.get("/status/{document_id}", response_model=DocumentResponse)
async def get_upload_status(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get the processing status of an uploaded document."""
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
