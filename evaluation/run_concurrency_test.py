"""Measure how processing time scales with the number of concurrent workers.

The same batch of images is processed three times, with the SQS event source
mapping's MaximumConcurrency setting capped at 2, then 5, then 10. The total
processing time for each run is recorded so that the linear-scaling claim
in the design (Section 7.5, NFR5) can be verified by measurement.

Using the event source mapping's MaximumConcurrency rather than the
function's reservedConcurrentExecutions avoids the "minimum unreserved"
account quota rule, which on a small student account blocks any reservation
that would push the unreserved pool below ten.

The script writes a single CSV summarising the three runs and produces a
matching PNG bar chart.

Usage:
    python evaluation/run_concurrency_test.py path/to/image_dir \\
        --input-bucket <InputBucketName> \\
        --queue-url <WorkQueueUrl>
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

CONCURRENCY_LEVELS = (2, 5, 10)
POLL_SECONDS = 4
# Give up if no image completes for this long after the batch is submitted.
STALL_TIMEOUT_SECONDS = 300


def main() -> None:
    args = _parse_args()
    image_dir = Path(args.directory)
    if not image_dir.is_dir():
        raise SystemExit(f"Not a directory: {image_dir}")

    images = sorted(p for p in image_dir.iterdir() if p.is_file())
    batch_size = len(images)
    if batch_size == 0:
        raise SystemExit(f"No images found in {image_dir}")
    print(f"Batch size: {batch_size} images")

    lambda_client = boto3.client("lambda")
    dynamodb = boto3.client("dynamodb")
    function_name = _find_function(lambda_client)
    table_name = _find_table(dynamodb)
    mapping_uuid = _find_sqs_mapping(lambda_client, function_name)
    print(f"Worker function:       {function_name}")
    print(f"Metadata table:        {table_name}")
    print(f"Event source mapping:  {mapping_uuid}")

    results: list[dict] = []
    try:
        for concurrency in CONCURRENCY_LEVELS:
            print(f"\n--- Running at concurrency {concurrency} ---")
            _set_mapping_concurrency(lambda_client, mapping_uuid, concurrency)
            _wait_for_mapping_enabled(lambda_client, mapping_uuid)

            baseline = _count_items(dynamodb, table_name)
            target = baseline + batch_size

            start = time.monotonic()
            _run_submitter(args, image_dir)
            elapsed = _wait_until_target(dynamodb, table_name, target)
            wall_clock = time.monotonic() - start

            throughput = batch_size / wall_clock
            print(
                f"  done in {wall_clock:.1f} s ({throughput:.2f} img/s, "
                f"processing-only wait {elapsed:.1f} s)"
            )
            results.append(
                {
                    "concurrency": concurrency,
                    "batch_size": batch_size,
                    "wall_clock_seconds": round(wall_clock, 2),
                    "throughput_images_per_second": round(throughput, 2),
                }
            )
    finally:
        # Always remove the per-mapping cap so the function returns to using
        # the full account quota for its concurrency.
        print("\nRemoving the MaximumConcurrency cap on the event source mapping ...")
        _clear_mapping_concurrency(lambda_client, mapping_uuid)

    _write_summary(results)


def _find_function(lambda_client) -> str:
    paginator = lambda_client.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page["Functions"]:
            if "ImagePipelineStack" in fn["FunctionName"] and "Worker" in fn["FunctionName"]:
                return fn["FunctionName"]
    raise SystemExit("Could not find the worker Lambda function.")


def _find_table(dynamodb) -> str:
    for name in dynamodb.list_tables()["TableNames"]:
        if "ImagePipelineStack" in name and "MetadataTable" in name:
            return name
    raise SystemExit("Could not find the metadata table.")


def _find_sqs_mapping(lambda_client, function_name: str) -> str:
    """Return the UUID of the SQS event source mapping attached to the worker."""
    response = lambda_client.list_event_source_mappings(FunctionName=function_name)
    for mapping in response.get("EventSourceMappings", []):
        if mapping.get("EventSourceArn", "").startswith("arn:aws:sqs:"):
            return mapping["UUID"]
    raise SystemExit("Could not find an SQS event source mapping for the worker.")


def _set_mapping_concurrency(lambda_client, uuid: str, value: int) -> None:
    """Cap concurrency for the SQS event source mapping."""
    lambda_client.update_event_source_mapping(
        UUID=uuid, ScalingConfig={"MaximumConcurrency": value}
    )


def _clear_mapping_concurrency(lambda_client, uuid: str) -> None:
    """Remove the MaximumConcurrency cap by writing an empty ScalingConfig."""
    try:
        lambda_client.update_event_source_mapping(UUID=uuid, ScalingConfig={})
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise


def _wait_for_mapping_enabled(lambda_client, uuid: str) -> None:
    """Poll the mapping until State is Enabled, so the new cap is live."""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        mapping = lambda_client.get_event_source_mapping(UUID=uuid)
        if mapping["State"] == "Enabled":
            return
        time.sleep(2)
    print("  warning: mapping did not return to Enabled within 60 s, continuing anyway")


def _run_submitter(args: argparse.Namespace, image_dir: Path) -> None:
    print(f"  submitting {image_dir} ...")
    job_id = f"job-conc-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    completed = subprocess.run(
        [
            sys.executable,
            "submitter/submit.py",
            str(image_dir),
            "--input-bucket",
            args.input_bucket,
            "--queue-url",
            args.queue_url,
            "--job-id",
            job_id,
        ],
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit("submitter failed")


def _count_items(dynamodb, table_name: str) -> int:
    """Count items in the table using a paginated scan with Select=COUNT."""
    total = 0
    paginator = dynamodb.get_paginator("scan")
    for page in paginator.paginate(TableName=table_name, Select="COUNT"):
        total += page["Count"]
    return total


def _wait_until_target(dynamodb, table_name: str, target: int) -> float:
    """Poll the table until item count reaches target and return the elapsed seconds."""
    start = time.monotonic()
    last_count = -1
    last_progress = start
    while True:
        count = _count_items(dynamodb, table_name)
        if count != last_count:
            last_count = count
            last_progress = time.monotonic()
            print(f"    completed {count} of {target}")
        if count >= target:
            return time.monotonic() - start
        if time.monotonic() - last_progress > STALL_TIMEOUT_SECONDS:
            raise SystemExit(
                f"stalled: no progress for {STALL_TIMEOUT_SECONDS} s; aborting"
            )
        time.sleep(POLL_SECONDS)


def _write_summary(results: list[dict]) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = Path("evaluation")
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"concurrency_{timestamp}.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "concurrency",
                "batch_size",
                "wall_clock_seconds",
                "throughput_images_per_second",
            ],
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"\nWrote {csv_path}")

    png_path = csv_path.with_suffix(".png")
    try:
        _plot(results, png_path)
        print(f"Wrote {png_path}")
    except ImportError:
        print("matplotlib not installed; skipping chart")


def _plot(results: list[dict], png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    concurrencies = [r["concurrency"] for r in results]
    times = [r["wall_clock_seconds"] for r in results]
    throughputs = [r["throughput_images_per_second"] for r in results]

    fig, ax_left = plt.subplots(figsize=(8, 5))
    bars = ax_left.bar(
        [str(c) for c in concurrencies],
        times,
        color="#1A5C86",
        alpha=0.85,
        label="wall-clock time",
    )
    ax_left.set_xlabel("Concurrent workers")
    ax_left.set_ylabel("Wall-clock time (seconds)")
    ax_left.set_title("Processing time and throughput against concurrency")
    for bar, t in zip(bars, times):
        ax_left.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{t:.0f} s",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax_right = ax_left.twinx()
    ax_right.plot(
        [str(c) for c in concurrencies],
        throughputs,
        color="#E8821E",
        marker="o",
        linewidth=2.5,
        label="throughput",
    )
    ax_right.set_ylabel("Throughput (images per second)")

    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure processing time at different worker concurrencies."
    )
    parser.add_argument("directory", help="directory of images to submit each run")
    parser.add_argument("--input-bucket", required=True)
    parser.add_argument("--queue-url", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
