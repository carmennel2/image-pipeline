"""Classifies worker failures as transient (retry) or permanent (dead-letter)."""
from __future__ import annotations


class PermanentError(Exception):
    """A failure that will never succeed on retry, such as a corrupt image."""


class TransientError(Exception):
    """A failure that may succeed on retry, such as a brief network error."""


# A ValueError from the processor means the image itself is invalid.
_PERMANENT_TYPES: tuple[type[Exception], ...] = (ValueError,)


def classify(exception: Exception) -> Exception:
    """Wrap an exception as a PermanentError or TransientError.

    Anything not known to be permanent is treated as transient, so the
    message is retried rather than discarded.
    """
    if isinstance(exception, (PermanentError, TransientError)):
        return exception
    if isinstance(exception, _PERMANENT_TYPES):
        return PermanentError(str(exception))
    return TransientError(str(exception))
