"""Downloads the source image from the input S3 bucket."""
from __future__ import annotations

import boto3

# One client per execution environment, reused across warm invocations.
_s3 = boto3.client("s3")


def download_image(bucket: str, key: str) -> bytes:
    """Return the raw bytes of the image at `key` in `bucket`.

    Any S3 error is left to propagate so the error handler can classify it.
    """
    response = _s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
