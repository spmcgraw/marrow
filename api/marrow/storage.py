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


class R2StorageAdapter(StorageAdapter):
    """Reads/writes attachments in a Cloudflare R2 bucket (S3-compatible API).

    Set STORAGE_BACKEND=r2 plus R2_ENDPOINT_URL, R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY, and R2_BUCKET to use this adapter.
    """

    def __init__(
        self,
        endpoint_url: str | None,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
    ) -> None:
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,  # None falls back to standard AWS S3 (useful in tests)
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",  # R2 requires "auto"; harmless against real AWS
        )

    def _key(self, attachment_id: str, filename: str) -> str:
        return f"{attachment_id}/{filename}"

    def read(self, attachment_id: str, filename: str) -> bytes:
        key = self._key(attachment_id, filename)
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def write(self, attachment_id: str, filename: str, data: bytes) -> None:
        key = self._key(attachment_id, filename)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)


def get_default_adapter() -> StorageAdapter:
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "r2":
        return R2StorageAdapter(
            endpoint_url=os.environ["R2_ENDPOINT_URL"],
            access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            bucket=os.environ["R2_BUCKET"],
        )
    storage_path = os.getenv("STORAGE_PATH", "/var/lib/marrow/attachments")
    return LocalFilesystemAdapter(storage_path)
