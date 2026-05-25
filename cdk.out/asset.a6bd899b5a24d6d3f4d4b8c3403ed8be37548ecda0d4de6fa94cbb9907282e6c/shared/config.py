"""Shared configuration, read from environment variables.

The infrastructure (the CDK app) sets these environment variables on the
Lambda function. Nothing in the code is hard-coded (design document
Section 10.5).
"""
from __future__ import annotations

import os


def get(name: str) -> str:
    """Return the value of a required environment variable.

    Raises:
        RuntimeError: if the variable is not set, so that a misconfiguration
            fails loudly and early rather than causing a confusing error
            later on.
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable {name!r} is not set")
    return value


def get_bool(name: str, default: bool = False) -> bool:
    """Return a boolean environment variable.

    The values "1", "true", and "yes" (case-insensitive) are read as True.
    If the variable is not set, `default` is returned.
    """
    value = os.environ.get(name)
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes"}
