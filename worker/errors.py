"""Error classification for the worker.

Distinguishes transient failures (retry) from permanent failures (send to
the dead-letter queue). See design document Section 8.4.
"""


class PermanentError(Exception):
    """A failure that will never succeed on retry, for example a corrupt image."""


class TransientError(Exception):
    """A failure that may succeed on retry, for example a brief network error."""


def classify(exception: Exception) -> Exception:
    """Return a PermanentError or TransientError for a caught exception.

    Steps to implement:
      - A ValueError from the processor (an invalid image) is permanent.
      - A network or timeout error from S3 or DynamoDB is transient.
      - When in doubt, treat it as transient so the message is retried.
    """
    # TODO: implement
    raise NotImplementedError
