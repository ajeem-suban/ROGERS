import os
import hashlib
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/tiff"}

class UploadResponse(BaseModel):
    filename: str
    file_id: str
    size_bytes: int
    content_type: str
    status: str

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """Receives and securely stores a document for processing."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file format: {file.content_type}. Allowed: {ALLOWED_MIME_TYPES}"
        )

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    safe_filename = f"{file_hash}_{file.filename}"
    target_path = UPLOAD_DIR / safe_filename

    with open(target_path, "wb") as f:
        f.write(content)

    return UploadResponse(
        filename=file.filename or "unknown",
        file_id=file_hash,
        size_bytes=len(content),
        content_type=file.content_type or "application/octet-stream",
        status="uploaded"
    )
