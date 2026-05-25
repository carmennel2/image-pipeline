"""Records one item per processed image in DynamoDB."""
from __future__ import annotations

import boto3

# One resource per execution environment, reused across warm invocations.
_dynamodb = boto3.resource("dynamodb")


def write_record(table: str, record: dict) -> None:
    """Write the metadata `record` for one image to `table`.

    Uses put_item, which overwrites by key, so reprocessing an image
    replaces its record rather than duplicating it. The record must contain
    the partition key "imageId".
    """
    _dynamodb.Table(table).put_item(Item=record)
