"""Shared test setup.

The worker modules construct boto3 clients at import time, which requires a
region. Setting it here, before any test modules are imported, lets the
storage-component tests import the worker package cleanly even when no AWS
credentials are configured.
"""
from __future__ import annotations

import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
