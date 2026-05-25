"""Writes the derivative images to the output S3 bucket."""
from __future__ import annotations

from collections.abc import Iterable

import boto3

from .processor import Derivative

# One client per execution environment, reused across warm invocations.
_s3 = boto3.client("s3")


def output_key(image_id: str, size: int) -> str:
    """Return the S3 key for a derivative.

    The key depends only on the image id and size, so reprocessing an image
    overwrites the same objects. This is what makes the worker idempotent.
    """
    return f"derivatives/{image_id}/{size}.webp"


def upload_derivatives(
    bucket: str, image_id: str, derivatives: Iterable[Derivative]
) -> list[str]:
    """Upload each derivative and return the list of keys written."""
    keys: list[str] = []
    for derivative in derivatives:
        key = output_key(image_id, derivative.size)
        _s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=derivative.data,
            ContentType="image/webp",
        )
        keys.append(key)
    return keys
