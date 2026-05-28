"""Unit tests for the input downloader.

Uses moto to mock S3 so the tests are deterministic and need no AWS credentials.
"""
from __future__ import annotations

from collections.abc import Iterator

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from worker import downloader


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Create a mocked S3 bucket with one stored object and rebind the downloader."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-input")
        client.put_object(
            Bucket="test-input", Key="input/img-1.jpg", Body=b"fake-jpeg-bytes"
        )
        downloader._s3 = client
        yield "test-input"


def test_download_returns_object_bytes(bucket: str) -> None:
    """Downloading an existing key returns the stored bytes."""
    assert downloader.download_image(bucket, "input/img-1.jpg") == b"fake-jpeg-bytes"


def test_missing_key_raises_client_error(bucket: str) -> None:
    """Downloading a key that does not exist surfaces the S3 error."""
    with pytest.raises(ClientError):
        downloader.download_image(bucket, "input/missing.jpg")
