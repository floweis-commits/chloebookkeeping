"""
File storage abstraction layer.

Paths follow: {root}/{tenant_id}/{folder_path}/{filename}
Example:      ./storage/abc-123/2025/Tax Returns/return.pdf

Swap backend via STORAGE_BACKEND env var (local | s3).
All call sites use the same interface — only this file changes.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from backend.config import settings


class BaseFileStore(ABC):
    """Interface that all storage backends must implement."""

    @abstractmethod
    async def save(self, tenant_id: str, folder: str, filename: str, data: bytes) -> str:
        """Save file bytes → return the storage key/path."""
        ...

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read file bytes by storage key."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file by storage key."""
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        ...

    @abstractmethod
    async def mkdir(self, tenant_id: str, folder: str) -> str:
        """Ensure a folder exists on disk. Returns the folder path."""
        ...


class LocalFileStore(BaseFileStore):
    """Local filesystem implementation — ./storage/{tenant}/{folder}/{file}."""

    def __init__(self):
        self.root = Path(settings.storage_local_path)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, tenant_id: str, folder: str, filename: str, data: bytes) -> str:
        folder_clean = folder.strip("/")
        dest_dir = self.root / tenant_id / folder_clean if folder_clean else self.root / tenant_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / filename
        dest.write_bytes(data)
        return str(dest.relative_to(self.root))

    async def read(self, path: str) -> bytes:
        target = self.root / path
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_bytes()

    async def delete(self, path: str) -> None:
        target = self.root / path
        if target.exists():
            target.unlink()

    async def exists(self, path: str) -> bool:
        return (self.root / path).exists()

    async def mkdir(self, tenant_id: str, folder: str) -> str:
        folder_clean = folder.strip("/")
        dest = self.root / tenant_id / folder_clean
        dest.mkdir(parents=True, exist_ok=True)
        return str(dest.relative_to(self.root))


class S3FileStore(BaseFileStore):
    """S3 / Cloudflare R2 implementation — swap in when ready."""

    async def save(self, tenant_id: str, folder: str, filename: str, data: bytes) -> str:
        raise NotImplementedError("S3 backend not implemented yet")

    async def read(self, path: str) -> bytes:
        raise NotImplementedError("S3 backend not implemented yet")

    async def delete(self, path: str) -> None:
        raise NotImplementedError("S3 backend not implemented yet")

    async def exists(self, path: str) -> bool:
        raise NotImplementedError("S3 backend not implemented yet")

    async def mkdir(self, tenant_id: str, folder: str) -> str:
        raise NotImplementedError("S3 backend not implemented yet")


def _create_store() -> BaseFileStore:
    if settings.storage_backend == "local":
        return LocalFileStore()
    elif settings.storage_backend == "s3":
        return S3FileStore()
    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")


file_store: BaseFileStore = _create_store()
