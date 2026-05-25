"""Output Uploader: writes the derivative images to the output S3 bucket."""


def output_key(image_id: str, size: int) -> str:
    """Return the deterministic S3 object key for a derivative.

    The key MUST be a pure function of `image_id` and `size`. This is what
    makes reprocessing idempotent (design document Section 8.3).
    """
    # TODO: implement, for example f"derivatives/{image_id}/{size}.webp"
    raise NotImplementedError


def upload_derivatives(bucket: str, image_id: str, derivatives) -> list[str]:
    """Upload each derivative to `bucket` at its deterministic key.

    Returns the list of object keys written. Overwriting an existing object
    is safe because the content is identical on a repeated run.
    """
    # TODO: implement using boto3
    raise NotImplementedError
