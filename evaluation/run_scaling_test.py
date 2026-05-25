"""Run the scaling evaluation: submit a batch and record progress over time.

This script counts the images in the batch directory, records a baseline of
the metadata table, runs the submitter to send the batch, and then samples
how many images have been processed (the count of metadata records) until
the whole batch is complete.

Counting completed records is an exact, monotonically increasing measurement,
unlike the work queue's own approximate counters, so it produces a clean
curve. Each sample records:
  - completed: images processed so far in this run
  - backlog:   images still to be processed (total minus completed)

The samples are written to a timestamped CSV in this folder, ready to be
plotted as the scaling graph for the evaluation (design document Section 14.3).

Usage:
  python evaluation/run_scaling_test.py <image-directory> \
      --input-bucket <input-bucket-name> --queue-url <work-queue-url>
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
POLL_SECONDS = 4
# Stop waiting if no image completes for this long after the batch is submitted.
STALL_TIMEOUT_SECONDS = 150


def _find_table(dynamodb) -> str:
    """Return the name of the metadata table created by the stack."""
    for name in dynamodb.list_tables()["TableNames"]:
        if "ImagePipelineStack" in name and "MetadataTable" in name:
            return name
    raise SystemExit("Could not find the metadata table.")


def _count_items(dynamodb, table: str) -> int:
    """Return the total number of items in the table."""
    total = 0
    kwargs: dict = {"TableName": table, "Select": "COUNT"}
    while True:
        response = dynamodb.scan(**kwargs)
        total += response["Count"]
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            return total
        kwargs["ExclusiveStartKey"] = start_key


def main() -> None:
    """Run a monitored scaling test and write the samples to a CSV."""
    import boto3

    args = _parse_args()
    directory = Path(args.directory)
    total = sum(
        1
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if total == 0:
        raise SystemExit(f"No images found in {directory}")

    dynamodb = boto3.client("dynamodb")
    table = _find_table(dynamodb)
    baseline = _count_items(dynamodb, table)
    print(f"Batch size: {total} images. Metadata table baseline: {baseline} items.\n")

    out_dir = Path(__file__).resolve().parent
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    csv_path = out_dir / f"run_{stamp}.csv"

    stop = threading.Event()
    start = time.monotonic()

    def monitor() -> None:
        with csv_path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["elapsed_seconds", "timestamp", "completed", "backlog"])
            last_completed = 0
            last_progress_at = time.monotonic()
            while True:
                completed = max(0, min(_count_items(dynamodb, table) - baseline, total))
                backlog = total - completed
                elapsed = round(time.monotonic() - start, 1)
                writer.writerow(
                    [elapsed, datetime.now(timezone.utc).isoformat(), completed, backlog]
                )
                handle.flush()
                print(f"  t={elapsed:>7}s   completed={completed:>5}   backlog={backlog:>5}")
                if completed > last_completed:
                    last_completed = completed
                    last_progress_at = time.monotonic()
                if stop.is_set():
                    if completed >= total:
                        break
                    if time.monotonic() - last_progress_at > STALL_TIMEOUT_SECONDS:
                        print("  no further progress; stopping.")
                        break
                time.sleep(POLL_SECONDS)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

    print("Submitting the batch (the progress monitor is now running) ...\n")
    subprocess.run(
        [
            sys.executable,
            "submitter/submit.py",
            args.directory,
            "--input-bucket",
            args.input_bucket,
            "--queue-url",
            args.queue_url,
        ],
        check=True,
    )
    print("\nBatch submitted. Recording until every image is processed ...\n")
    stop.set()
    thread.join()

    total_time = round(time.monotonic() - start, 1)
    print(f"\nRun complete in {total_time} seconds.")
    print(f"Samples written to: {csv_path}")


def _parse_args() -> argparse.Namespace:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the scaling evaluation.")
    parser.add_argument("directory", help="the directory of source images to submit")
    parser.add_argument(
        "--input-bucket", required=True, help="name of the input S3 bucket"
    )
    parser.add_argument(
        "--queue-url", required=True, help="URL of the SQS work queue"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
