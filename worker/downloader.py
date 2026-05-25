"""Image Downloader: fetches the source image from the input S3 bucket."""
from __future__ import annotations

import boto3

# Created once per execution environment and reused across warm invocations.
_s3 = boto3.client("s3")


def download_image(bucket: str, key: str) -> bytes:
    """Download the source image identified by `key` from `bucket`.

    Args:
        bucket: the name of the input S3 bucket.
        key: the object key of the source image.

    Returns:
        The raw bytes of the source image.

    Any error raised by S3 is allowed to propagate so that the error
    handler (errors.py) can classify it.
    """
    response = _s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
