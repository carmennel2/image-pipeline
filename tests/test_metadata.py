"""Unit tests for the metadata writer.

Uses moto to mock DynamoDB so the tests are deterministic and need no AWS credentials.
"""
from __future__ import annotations

from collections.abc import Iterator

import boto3
import pytest
from moto import mock_aws

from worker import metadata


@pytest.fixture
def table(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Create a mocked DynamoDB table and rebind the metadata module to it."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="metadata",
            KeySchema=[{"AttributeName": "imageId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "imageId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        ).wait_until_exists()
        metadata._dynamodb = ddb
        yield "metadata"


def test_write_record_creates_item(table: str) -> None:
    """A new record is written and is retrievable by its imageId."""
    metadata.write_record(table, {"imageId": "img-1", "jobId": "job-1"})

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    item = ddb.Table(table).get_item(Key={"imageId": "img-1"})["Item"]
    assert item["jobId"] == "job-1"


def test_repeat_write_overwrites_the_existing_item(table: str) -> None:
    """A second put_item with the same key replaces the record, not duplicates it."""
    metadata.write_record(table, {"imageId": "img-1", "jobId": "first"})
    metadata.write_record(table, {"imageId": "img-1", "jobId": "second"})

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    item = ddb.Table(table).get_item(Key={"imageId": "img-1"})["Item"]
    assert item["jobId"] == "second"


def test_scan_shows_one_record_per_image_id(table: str) -> None:
    """Writing the same imageId twice still leaves one item; different ids stay separate."""
    metadata.write_record(table, {"imageId": "img-1"})
    metadata.write_record(table, {"imageId": "img-1"})  # same key, second time
    metadata.write_record(table, {"imageId": "img-2"})

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    items = ddb.Table(table).scan()["Items"]
    assert {i["imageId"] for i in items} == {"img-1", "img-2"}
    assert len(items) == 2
