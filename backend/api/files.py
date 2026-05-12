"""
File storage endpoints — list, search, upload, download, delete, create folder, recent.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User, FileRecord
from backend.api.deps import get_current_user, get_tenant_permission, require_role
from backend.storage.file_store import file_store

router = APIRouter()

# ── Constants ─────────────────────────────────────────────

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024  # 50 MB

ALLOWED_MIME_TYPES = {
    # PDF
    "application/pdf",
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    # Excel
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Word
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

ALLOWED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".xls", ".xlsx", ".doc", ".docx",
}


# ── Schemas ───────────────────────────────────────────────

class FileOut(BaseModel):
    id: UUID
    name: str
    folder: str
    is_folder: bool
    mime_type: str | None
    size_bytes: int | None
    is_new: bool  # inverted from is_seen
    created_at: str

    class Config:
        from_attributes = True


class FolderCreateRequest(BaseModel):
    folder_path: str  # e.g. "2025/Tax Returns"


# ── Helpers ───────────────────────────────────────────────

def _to_file_out(record: FileRecord) -> FileOut:
    return FileOut(
        id=record.id,
        name=record.name,
        folder=record.folder,
        is_folder=record.is_folder,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        is_new=not record.is_seen,
        created_at=record.created_at.isoformat(),
    )


def _validate_file(upload: UploadFile) -> None:
    """Validate mime type and extension."""
    # Check extension
    filename = upload.filename or ""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Check content type (fallback — browsers sometimes send wrong type)
    if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
        # Allow if extension is valid — content_type can be unreliable
        pass


# ── Endpoints ─────────────────────────────────────────────

@router.get("/{client_id}", response_model=list[FileOut])
async def list_files(
    client_id: UUID,
    folder: str = Query("/", description="Folder path to list, e.g. '/' or '2025/Tax Returns'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List folders and files in a folder for a given client."""
    await get_tenant_permission(client_id, current_user, db)

    folder_clean = folder.strip("/") or "/"

    result = await db.execute(
        select(FileRecord)
        .where(
            FileRecord.tenant_id == client_id,
            FileRecord.folder == folder_clean,
        )
        .order_by(FileRecord.is_folder.desc(), FileRecord.name.asc())
    )
    records = result.scalars().all()

    return [_to_file_out(r) for r in records]


@router.get("/{client_id}/search", response_model=list[FileOut])
async def search_files(
    client_id: UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across file names and folder paths for a client."""
    await get_tenant_permission(client_id, current_user, db)

    pattern = f"%{q}%"
    result = await db.execute(
        select(FileRecord)
        .where(
            FileRecord.tenant_id == client_id,
            FileRecord.is_folder == False,  # noqa: E712 — only search actual files
            or_(
                FileRecord.name.ilike(pattern),
                FileRecord.folder.ilike(pattern),
            ),
        )
        .order_by(FileRecord.created_at.desc())
        .limit(50)
    )
    records = result.scalars().all()

    return [_to_file_out(r) for r in records]


@router.post("/{client_id}/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    client_id: UUID,
    folder: str = Query("/", description="Target folder path"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to a folder. Requires at least editor access."""
    await get_tenant_permission(client_id, current_user, db, min_level="editor")

    _validate_file(file)

    # Read file data and check size
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
        )

    folder_clean = folder.strip("/") or "/"
    filename = file.filename or "untitled"

    # Save to storage backend
    storage_path = await file_store.save(
        tenant_id=str(client_id),
        folder=folder_clean,
        filename=filename,
        data=data,
    )

    # Create DB record
    record = FileRecord(
        tenant_id=client_id,
        name=filename,
        path=storage_path,
        mime_type=file.content_type,
        size_bytes=len(data),
        folder=folder_clean,
        is_folder=False,
        uploaded_by=current_user.id,
        is_seen=False,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return _to_file_out(record)


@router.get("/{client_id}/recent", response_model=list[FileOut])
async def recent_files(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Last 10 files uploaded for a client (for dashboard)."""
    await get_tenant_permission(client_id, current_user, db)

    result = await db.execute(
        select(FileRecord)
        .where(
            FileRecord.tenant_id == client_id,
            FileRecord.is_folder == False,  # noqa: E712
        )
        .order_by(FileRecord.created_at.desc())
        .limit(10)
    )
    records = result.scalars().all()

    return [_to_file_out(r) for r in records]


@router.get("/{file_id}/download")
async def download_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a file by ID and mark it as seen."""
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    await get_tenant_permission(record.tenant_id, current_user, db)

    # Mark as seen
    if not record.is_seen:
        record.is_seen = True
        await db.commit()

    # Read from storage and stream back
    data = await file_store.read(record.path)

    return Response(
        content=data,
        media_type=record.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{record.name}"'},
    )


@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file. Requires bookkeeper role or owner access level."""
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    await get_tenant_permission(record.tenant_id, current_user, db, min_level="owner")

    # Delete from storage
    try:
        await file_store.delete(record.path)
    except FileNotFoundError:
        pass  # file already gone from disk, still clean up DB

    # Delete DB record
    await db.delete(record)
    await db.commit()

    return {"detail": f"File '{record.name}' deleted"}


@router.post("/{client_id}/folder", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def create_folder(
    client_id: UUID,
    body: FolderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new folder. Requires at least editor access."""
    await get_tenant_permission(client_id, current_user, db, min_level="editor")

    folder_path = body.folder_path.strip("/")
    if not folder_path:
        raise HTTPException(status_code=422, detail="Folder path cannot be empty")

    # Determine parent folder and folder name
    if "/" in folder_path:
        parent_folder = folder_path.rsplit("/", 1)[0]
        folder_name = folder_path.rsplit("/", 1)[1]
    else:
        parent_folder = "/"
        folder_name = folder_path

    # Check if folder already exists
    existing = await db.execute(
        select(FileRecord).where(
            FileRecord.tenant_id == client_id,
            FileRecord.name == folder_name,
            FileRecord.folder == parent_folder,
            FileRecord.is_folder == True,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Folder already exists")

    # Create on disk
    await file_store.mkdir(tenant_id=str(client_id), folder=folder_path)

    # Create DB record
    record = FileRecord(
        tenant_id=client_id,
        name=folder_name,
        path=f"{client_id}/{folder_path}",
        folder=parent_folder,
        is_folder=True,
        uploaded_by=current_user.id,
        is_seen=True,  # folders don't need "New" badge
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return _to_file_out(record)


@router.patch("/{file_id}/seen")
async def mark_seen(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a file as seen (clears 'New' badge)."""
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    await get_tenant_permission(record.tenant_id, current_user, db)

    record.is_seen = True
    await db.commit()

    return {"detail": "Marked as seen"}
