"""Error classification for the worker.

Distinguishes transient failures (which should be retried) from permanent
failures (which should end up in the dead-letter queue). See design
document Section 8.4.
"""
from __future__ import annotations


class PermanentError(Exception):
    """A failure that will never succeed on retry, for example a corrupt image."""


class TransientError(Exception):
    """A failure that may succeed on retry, for example a brief network error."""


# Exception types treated as permanent. The Image Processor raises ValueError
# when the source bytes are not a valid image.
_PERMANENT_TYPES: tuple[type[Exception], ...] = (ValueError,)


def classify(exception: Exception) -> Exception:
    """Return a PermanentError or TransientError for a caught exception.

    A permanent failure cannot succeed however many times it is retried.
    Anything else, for example a network or timeout error talking to S3 or
    DynamoDB, is treated as transient so that the message is retried.

    Args:
        exception: the exception caught while processing an image.

    Returns:
        A PermanentError or TransientError describing the failure.
    """
    if isinstance(exception, (PermanentError, TransientError)):
        return exception
    if isinstance(exception, _PERMANENT_TYPES):
        return PermanentError(str(exception))
    return TransientError(str(exception))
