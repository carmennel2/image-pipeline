"""Shared configuration, read from environment variables.

The infrastructure (the CDK app) sets these environment variables on the
Lambda function. Nothing here is hard-coded (design document Section 10.5).
"""
import os


def get(name: str) -> str:
    """Return the value of a required environment variable, or raise if missing."""
    # TODO: read os.environ[name]; raise a clear error if it is not set
    raise NotImplementedError


# Variables to expose once `get` is implemented, for example:
# INPUT_BUCKET = get("INPUT_BUCKET")
# OUTPUT_BUCKET = get("OUTPUT_BUCKET")
# METADATA_TABLE = get("METADATA_TABLE")
