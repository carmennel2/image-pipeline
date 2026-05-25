"""Command-line submitter: uploads a directory of images and queues them.

Uploading and enqueuing run concurrently so a large batch lands on the queue
quickly, which is what creates the workload spike for the scaling evaluation.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import boto3

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
SQS_BATCH_LIMIT = 10  # most messages SQS accepts in one send_message_batch call
CONCURRENCY = 24      # concurrent workers for uploading and enqueuing


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

    print("Uploading images to S3 ...")
    items = _upload_all(s3, args.input_bucket, images)

    print("Enqueuing messages on the work queue ...")
    _enqueue_all(sqs, args.queue_url, items, job_id)

    print(f"Done. Submitted {len(items)} image(s) under job {job_id}.")


def _upload_all(s3, bucket: str, images: list[Path]) -> list[tuple[str, str]]:
    """Upload every image to S3 concurrently and return (image_id, key) pairs."""

    def upload(path: Path) -> tuple[str, str]:
        image_id = f"img-{uuid.uuid4().hex[:12]}"
        input_key = f"input/{image_id}{path.suffix.lower()}"
        s3.upload_file(str(path), bucket, input_key)
        return image_id, input_key

    items: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for done, item in enumerate(pool.map(upload, images), start=1):
            items.append(item)
            if done % 200 == 0:
                print(f"  uploaded {done} of {len(images)}")
    return items


def _enqueue_all(
    sqs, queue_url: str, items: list[tuple[str, str]], job_id: str
) -> None:
    """Send one SQS message per image, in concurrent batches of ten."""
    batches = [
        items[i : i + SQS_BATCH_LIMIT]
        for i in range(0, len(items), SQS_BATCH_LIMIT)
    ]

    def send(batch: list[tuple[str, str]]) -> None:
        entries = [
            _message_entry(image_id, input_key, job_id)
            for image_id, input_key in batch
        ]
        response = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)
        if response.get("Failed"):
            raise RuntimeError(f"failed to enqueue: {response['Failed']}")

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        list(pool.map(send, batches))


def _message_entry(image_id: str, input_key: str, job_id: str) -> dict:
    """Build one SQS batch entry describing an image to process."""
    body = {
        "imageId": image_id,
        "inputKey": input_key,
        "jobId": job_id,
        "submittedAt": datetime.now(timezone.utc).isoformat(),
    }
    return {"Id": image_id, "MessageBody": json.dumps(body)}


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
