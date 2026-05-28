"""Unit tests for the output uploader.

Uses moto to mock S3 so the tests are deterministic and need no AWS credentials.
"""
from __future__ import annotations

from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from worker import uploader
from worker.processor import Derivative


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Create a mocked S3 bucket and rebind the uploader's cached client to it."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-output")
        uploader._s3 = client
        yield "test-output"


def _three_derivatives() -> list[Derivative]:
    return [
        Derivative(size=256, data=b"webp-256-bytes", width=256, height=192),
        Derivative(size=512, data=b"webp-512-bytes", width=512, height=384),
        Derivative(size=1024, data=b"webp-1024-bytes", width=1024, height=768),
    ]


def test_uploads_one_object_per_derivative(bucket: str) -> None:
    """Uploading three derivatives writes three S3 objects under the imageId prefix."""
    keys = uploader.upload_derivatives(bucket, "img-abc", _three_derivatives())
    s3 = boto3.client("s3", region_name="us-east-1")
    listed = s3.list_objects_v2(Bucket=bucket, Prefix="derivatives/img-abc/")
    assert listed["KeyCount"] == 3
    assert set(keys) == {obj["Key"] for obj in listed["Contents"]}


def test_keys_follow_the_deterministic_pattern(bucket: str) -> None:
    """Object keys are derivatives/<imageId>/<size>.webp, in size order."""
    keys = uploader.upload_derivatives(bucket, "img-abc", _three_derivatives())
    assert keys == [
        "derivatives/img-abc/256.webp",
        "derivatives/img-abc/512.webp",
        "derivatives/img-abc/1024.webp",
    ]


def test_repeat_upload_overwrites_in_place(bucket: str) -> None:
    """A second run with the same imageId overwrites without creating duplicates."""
    uploader.upload_derivatives(bucket, "img-abc", _three_derivatives())
    second = [
        Derivative(size=256, data=b"new-256", width=256, height=192),
        Derivative(size=512, data=b"new-512", width=512, height=384),
        Derivative(size=1024, data=b"new-1024", width=1024, height=768),
    ]
    uploader.upload_derivatives(bucket, "img-abc", second)

    s3 = boto3.client("s3", region_name="us-east-1")
    listed = s3.list_objects_v2(Bucket=bucket, Prefix="derivatives/img-abc/")
    assert listed["KeyCount"] == 3  # still three, not six

    body = s3.get_object(Bucket=bucket, Key="derivatives/img-abc/256.webp")["Body"].read()
    assert body == b"new-256"


def test_content_type_is_webp(bucket: str) -> None:
    """Each uploaded object has its Content-Type set to image/webp."""
    uploader.upload_derivatives(bucket, "img-abc", _three_derivatives())
    s3 = boto3.client("s3", region_name="us-east-1")
    head = s3.head_object(Bucket=bucket, Key="derivatives/img-abc/256.webp")
    assert head["ContentType"] == "image/webp"


def test_output_key_function_is_deterministic() -> None:
    """The pure key function returns the same path for the same inputs."""
    assert uploader.output_key("img-abc", 512) == "derivatives/img-abc/512.webp"
    assert uploader.output_key("img-abc", 512) == uploader.output_key("img-abc", 512)
