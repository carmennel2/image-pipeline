"""Output Uploader: writes the derivative images to the output S3 bucket."""
from __future__ import annotations

from collections.abc import Iterable

import boto3

from .processor import Derivative

# Created once per execution environment and reused across warm invocations.
_s3 = boto3.client("s3")


def output_key(image_id: str, size: int) -> str:
    """Return the deterministic S3 object key for a derivative.

    The key is a pure function of `image_id` and `size`. Reprocessing the
    same image therefore writes to the same keys, which is what makes the
    worker idempotent (design document Section 8.3).
    """
    return f"derivatives/{image_id}/{size}.webp"


def upload_derivatives(
    bucket: str, image_id: str, derivatives: Iterable[Derivative]
) -> list[str]:
    """Upload each derivative to `bucket` at its deterministic key.

    An existing object at the same key is overwritten, which is safe
    because a repeated run produces byte-identical content.

    Returns:
        The list of object keys written.
    """
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
