"""Command-line submitter.

Uploads a directory of source images to the input S3 bucket and places one
SQS message on the work queue per image. See design document Section 5.3.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3

# File extensions the submitter treats as images.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

# SQS accepts at most ten messages in a single send_message_batch request.
SQS_BATCH_LIMIT = 10


def main() -> None:
    """Entry point for the submitter."""
    args = _parse_args()
    images = _find_images(Path(args.directory))
    if not images:
        print(f"No image files found in {args.directory}", file=sys.stderr)
        sys.exit(1)

    job_id = args.job_id or f"job-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    s3 = boto3.client("s3")
    sqs = boto3.client("sqs")

    print(f"Submitting {len(images)} image(s) under job {job_id}")
    batch: list[dict] = []
    submitted = 0
    for path in images:
        image_id = f"img-{uuid.uuid4().hex[:12]}"
        input_key = f"input/{image_id}{path.suffix.lower()}"

        # Upload the source image, then queue a message that points to it.
        s3.upload_file(str(path), args.input_bucket, input_key)
        batch.append(_message_entry(image_id, input_key, job_id))
        submitted += 1

        if len(batch) == SQS_BATCH_LIMIT:
            _send_batch(sqs, args.queue_url, batch)
            batch.clear()
        if submitted % 100 == 0:
            print(f"  submitted {submitted} of {len(images)}")

    if batch:
        _send_batch(sqs, args.queue_url, batch)

    print(f"Done. Submitted {submitted} image(s) under job {job_id}.")


def _message_entry(image_id: str, input_key: str, job_id: str) -> dict:
    """Build one SQS batch entry describing an image to process."""
    body = {
        "imageId": image_id,
        "inputKey": input_key,
        "jobId": job_id,
        "submittedAt": datetime.now(timezone.utc).isoformat(),
    }
    return {"Id": image_id, "MessageBody": json.dumps(body)}


def _send_batch(sqs, queue_url: str, entries: list[dict]) -> None:
    """Send a batch of up to ten messages to the work queue."""
    response = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)
    failed = response.get("Failed", [])
    if failed:
        raise RuntimeError(f"failed to enqueue {len(failed)} message(s): {failed}")


def _find_images(directory: Path) -> list[Path]:
    """Return the sorted image files directly inside `directory`."""
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        sys.exit(1)
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def _parse_args() -> argparse.Namespace:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Upload a directory of images and queue them for processing."
    )
    parser.add_argument("directory", help="the directory of source images to submit")
    parser.add_argument(
        "--input-bucket", required=True, help="name of the input S3 bucket"
    )
    parser.add_argument(
        "--queue-url", required=True, help="URL of the SQS work queue"
    )
    parser.add_argument(
        "--job-id", help="optional job identifier; one is generated if omitted"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
