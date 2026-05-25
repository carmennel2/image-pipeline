"""Metadata Writer: records one item per processed image in DynamoDB."""
from __future__ import annotations

import boto3

# Created once per execution environment and reused across warm invocations.
_dynamodb = boto3.resource("dynamodb")


def write_record(table: str, record: dict) -> None:
    """Write the metadata record for one image to the DynamoDB `table`.

    The record is written with put_item, which overwrites any existing item
    that has the same key. The record's key attribute is the image
    identifier, so a repeated run replaces rather than duplicates the record
    (design document Section 8.3).

    Args:
        table: the name of the DynamoDB table.
        record: the metadata item to write. It must contain the partition
            key attribute "imageId".
    """
    _dynamodb.Table(table).put_item(Item=record)
