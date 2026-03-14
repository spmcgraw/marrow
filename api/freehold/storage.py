"""Storage adapter interface and local filesystem implementation."""

import os
from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    @abstractmethod
    def read(self, attachment_id: str, filename: str) -> bytes:
        """Return the raw bytes for an attachment."""
        ...


class LocalFilesystemAdapter(StorageAdapter):
    """Reads attachments from a local directory tree: <base>/<attachment_id>/<filename>."""

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    def read(self, attachment_id: str, filename: str) -> bytes:
        path = self.base_path / attachment_id / filename
        if not path.exists():
            raise FileNotFoundError(f"Attachment file not found: {path}")
        return path.read_bytes()


def get_default_adapter() -> StorageAdapter:
    storage_path = os.getenv("STORAGE_PATH", "/var/lib/freehold/attachments")
    return LocalFilesystemAdapter(storage_path)
