"""Worker entry point: processes the image referenced by an SQS message."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from shared import config

from . import downloader, errors, metadata, uploader
from .processor import process_image

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context: object) -> None:
    """Lambda entry point, invoked by the SQS event source mapping.

    Returning normally lets Lambda delete the message; raising an exception
    leaves it on the queue to be retried.
    """
    settings = _load_settings()
    for record in event["Records"]:
        _process_record(record, settings)


def _process_record(record: dict, settings: dict) -> None:
    """Download, process, and store the outputs for one image."""
    message = json.loads(record["body"])
    image_id = message["imageId"]
    input_key = message["inputKey"]
    job_id = message.get("jobId", "unknown")

    log = logging.LoggerAdapter(logger, {"imageId": image_id, "jobId": job_id})
    started = time.monotonic()
    log.info("processing started for %s", input_key)

    try:
        source = downloader.download_image(settings["input_bucket"], input_key)
        derivatives = process_image(source, watermark=settings["watermark"])
        output_keys = uploader.upload_derivatives(
            settings["output_bucket"], image_id, derivatives
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        metadata.write_record(
            settings["metadata_table"],
            {
                "imageId": image_id,
                "jobId": job_id,
                "inputKey": input_key,
                "derivativeKeys": output_keys,
                "derivativeSizes": [d.size for d in derivatives],
                "derivativeBytes": [len(d.data) for d in derivatives],
                "processingMs": elapsed_ms,
                "completedAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        log.info("processing completed in %s ms", elapsed_ms)
    except Exception as exc:  # noqa: BLE001
        # Classify the failure and re-raise, so the message is not deleted
        # and SQS can redeliver it or move it to the dead-letter queue.
        classified = errors.classify(exc)
        log.error("processing failed: %s: %s", type(classified).__name__, classified)
        raise classified from exc


def _load_settings() -> dict:
    """Read the worker's configuration from environment variables."""
    return {
        "input_bucket": config.get("INPUT_BUCKET"),
        "output_bucket": config.get("OUTPUT_BUCKET"),
        "metadata_table": config.get("METADATA_TABLE"),
        "watermark": config.get_bool("WATERMARK", default=False),
    }
