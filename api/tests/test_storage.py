"""Tests for storage adapters (local filesystem and R2/S3-compatible)."""

import boto3
import pytest

from marrow.storage import LocalFilesystemAdapter, R2StorageAdapter

# moto v4+ uses mock_aws; fall back to mock_s3 for older installs
try:
    from moto import mock_aws as _mock
except ImportError:
    from moto import mock_s3 as _mock


# ---------------------------------------------------------------------------
# LocalFilesystemAdapter
# ---------------------------------------------------------------------------


def test_local_write_and_read(tmp_path):
    adapter = LocalFilesystemAdapter(tmp_path)
    adapter.write("attach-1", "file.txt", b"hello world")
    assert adapter.read("attach-1", "file.txt") == b"hello world"


def test_local_creates_subdirectory(tmp_path):
    adapter = LocalFilesystemAdapter(tmp_path)
    adapter.write("attach-nested", "deep/path.bin", b"data")
    assert (tmp_path / "attach-nested" / "deep" / "path.bin").read_bytes() == b"data"


def test_local_file_not_found(tmp_path):
    adapter = LocalFilesystemAdapter(tmp_path)
    with pytest.raises(FileNotFoundError):
        adapter.read("nonexistent", "file.txt")


# ---------------------------------------------------------------------------
# R2StorageAdapter (moto-mocked S3)
# ---------------------------------------------------------------------------


def _make_r2_adapter(bucket: str = "test-bucket") -> R2StorageAdapter:
    """Return an R2StorageAdapter whose boto3 client uses standard AWS endpoints.

    moto intercepts calls to the standard AWS S3 endpoint (s3.amazonaws.com).
    Custom endpoint_url values (e.g. real R2 URLs) bypass moto and hit the
    network, so tests must omit endpoint_url and let moto intercept.
    The production adapter still accepts endpoint_url; this helper is test-only.
    """
    boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    ).create_bucket(Bucket=bucket)

    return R2StorageAdapter(
        endpoint_url=None,  # let moto intercept via standard AWS endpoint
        access_key_id="test",
        secret_access_key="test",
        bucket=bucket,
    )


@_mock
def test_r2_write_and_read():
    adapter = _make_r2_adapter()
    adapter.write("attach-2", "photo.png", b"image bytes")
    assert adapter.read("attach-2", "photo.png") == b"image bytes"


@_mock
def test_r2_multiple_attachments():
    adapter = _make_r2_adapter()
    adapter.write("attach-a", "doc.pdf", b"pdf bytes")
    adapter.write("attach-b", "doc.pdf", b"other pdf bytes")

    assert adapter.read("attach-a", "doc.pdf") == b"pdf bytes"
    assert adapter.read("attach-b", "doc.pdf") == b"other pdf bytes"
