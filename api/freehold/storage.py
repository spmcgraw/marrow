"""Storage adapter interface and local filesystem implementation."""

import os
from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    @abstractmethod
    def read(self, attachment_id: str, filename: str) -> bytes:
        """Return the raw bytes for an attachment."""
        ...

    @abstractmethod
    def write(self, attachment_id: str, filename: str, data: bytes) -> None:
        """Persist *data* for an attachment."""
        ...


class LocalFilesystemAdapter(StorageAdapter):
    """Reads/writes attachments in a local directory tree: <base>/<attachment_id>/<filename>."""

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    def read(self, attachment_id: str, filename: str) -> bytes:
        path = self.base_path / attachment_id / filename
        if not path.exists():
            raise FileNotFoundError(f"Attachment file not found: {path}")
        return path.read_bytes()

    def write(self, attachment_id: str, filename: str, data: bytes) -> None:
        path = self.base_path / attachment_id / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def get_default_adapter() -> StorageAdapter:
    storage_path = os.getenv("STORAGE_PATH", "/var/lib/freehold/attachments")
    return LocalFilesystemAdapter(storage_path)
