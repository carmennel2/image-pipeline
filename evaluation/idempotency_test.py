"""Demonstrate that processing the same image twice leaves the system consistent.

The pipeline guarantees at-least-once delivery, so the worker can be asked to
process the same image more than once. The design (Section 8.3) handles this
by writing every derivative to a deterministic S3 key and every metadata
record to DynamoDB by image identifier, so a second run overwrites the first
in place rather than creating duplicates.

This script demonstrates that behaviour end to end:

  1. Upload one image to the input bucket.
  2. Send one SQS message and wait for the record to appear in DynamoDB.
     Record the derivative keys, the byte size of each derivative, and the
     completedAt timestamp.
  3. Send a second SQS message with the same imageId, and wait until the
     completedAt timestamp changes, which is the proof that a second
     processing has actually happened.
  4. Assert that DynamoDB still contains exactly one record for the imageId,
     and that S3 still contains exactly three derivative objects under the
     same keys.

Usage:
    python evaluation/idempotency_test.py path/to/image.jpg \\
        --input-bucket <InputBucketName> \\
        --output-bucket <OutputBucketName> \\
        --queue-url <WorkQueueUrl> \\
        --table <MetadataTableName>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3

POLL_INTERVAL_SECONDS = 3
TIMEOUT_SECONDS = 180


def main() -> None:
    args = _parse_args()
    image_path = Path(args.image)
    if not image_path.is_file():
        print(f"not a file: {image_path}", file=sys.stderr)
        sys.exit(1)

    image_id = args.image_id or f"img-idem-{uuid.uuid4().hex[:8]}"
    input_key = f"input/{image_id}{image_path.suffix.lower()}"
    job_id = f"job-idempotency-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"

    s3 = boto3.client("s3")
    sqs = boto3.client("sqs")
    table = boto3.resource("dynamodb").Table(args.table)

    print(f"Image id for this test: {image_id}")
    print(f"Uploading {image_path} to s3://{args.input_bucket}/{input_key} ...")
    s3.upload_file(str(image_path), args.input_bucket, input_key)

    print("Sending first SQS message ...")
    _send_message(sqs, args.queue_url, image_id, input_key, job_id)

    print("Waiting for first processing to complete ...")
    first_record = _wait_for_record(table, image_id)
    first_completed_at = first_record["completedAt"]
    first_keys = first_record["derivativeKeys"]
    print(f"  first completedAt: {first_completed_at}")
    print(f"  derivative keys:   {list(first_keys)}")

    print("Sending second SQS message with the same imageId ...")
    _send_message(sqs, args.queue_url, image_id, input_key, job_id)

    print("Waiting for second processing to overwrite the record ...")
    second_record = _wait_for_completed_at_change(table, image_id, first_completed_at)
    second_completed_at = second_record["completedAt"]
    second_keys = second_record["derivativeKeys"]
    print(f"  second completedAt: {second_completed_at}")

    print("Counting DynamoDB records for the imageId ...")
    ddb_count = _count_records(table, image_id)
    print(f"  records in DynamoDB: {ddb_count}")

    print("Counting S3 derivative objects under the imageId prefix ...")
    s3_keys = _list_derivative_keys(s3, args.output_bucket, image_id)
    print(f"  objects in S3:       {len(s3_keys)}")
    for key in s3_keys:
        print(f"    - {key}")

    print()
    print("Result:")
    same_keys = list(first_keys) == list(second_keys)
    timestamp_advanced = second_completed_at > first_completed_at
    ok = ddb_count == 1 and len(s3_keys) == 3 and same_keys and timestamp_advanced
    print(f"  DynamoDB records:           {ddb_count} (expected 1)")
    print(f"  S3 derivative objects:      {len(s3_keys)} (expected 3)")
    print(f"  derivative keys unchanged:  {same_keys}")
    print(f"  completedAt advanced:       {timestamp_advanced}")
    print(f"  idempotent:                 {ok}")

    if not ok:
        sys.exit(1)


def _send_message(sqs, queue_url: str, image_id: str, input_key: str, job_id: str) -> None:
    body = {
        "imageId": image_id,
        "inputKey": input_key,
        "jobId": job_id,
        "submittedAt": datetime.now(timezone.utc).isoformat(),
    }
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))


def _wait_for_record(table, image_id: str) -> dict:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = table.get_item(Key={"imageId": image_id})
        item = response.get("Item")
        if item is not None:
            return item
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"no record appeared for {image_id} within {TIMEOUT_SECONDS} s")


def _wait_for_completed_at_change(table, image_id: str, previous: str) -> dict:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = table.get_item(Key={"imageId": image_id})
        item = response.get("Item")
        if item is not None and item["completedAt"] != previous:
            return item
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(
        f"completedAt did not change for {image_id} within {TIMEOUT_SECONDS} s"
    )


def _count_records(table, image_id: str) -> int:
    """Count records for the imageId. With an exact-key get_item this is 0 or 1."""
    response = table.get_item(Key={"imageId": image_id})
    return 1 if response.get("Item") is not None else 0


def _list_derivative_keys(s3, output_bucket: str, image_id: str) -> list[str]:
    prefix = f"derivatives/{image_id}/"
    paginator = s3.get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=output_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return sorted(keys)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demonstrate idempotency by processing the same image twice."
    )
    parser.add_argument("image", help="path to one source image to process")
    parser.add_argument("--input-bucket", required=True)
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--queue-url", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument(
        "--image-id",
        help="override the image id (default: a generated one starting img-idem-)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
