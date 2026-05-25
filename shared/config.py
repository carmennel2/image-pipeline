"""Reads the worker's configuration from environment variables.

The CDK app sets these variables on the Lambda function, so nothing is
hard-coded.
"""
from __future__ import annotations

import os


def get(name: str) -> str:
    """Return a required environment variable, or raise if it is not set."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable {name!r} is not set")
    return value


def get_bool(name: str, default: bool = False) -> bool:
    """Return a boolean environment variable.

    "1", "true", and "yes" (any case) are True; an unset variable returns the default.
    """
    value = os.environ.get(name)
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes"}
