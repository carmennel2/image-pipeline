"""Image Downloader: fetches the source image from the input S3 bucket."""


def download_image(bucket: str, key: str) -> bytes:
    """Download the source image identified by `key` from `bucket`.

    Returns the raw image bytes. Use the boto3 S3 client. Let any S3 error
    propagate so the error handler can classify it.
    """
    # TODO: implement using boto3
    raise NotImplementedError
