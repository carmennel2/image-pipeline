"""Lambda entry point and orchestration for the worker.

Receives an SQS event and coordinates the other components to process the
image it refers to. See Section 5.1 of the design document.
"""
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
    """AWS Lambda entry point, invoked by the SQS event source mapping.

    The event source mapping uses a batch size of one, so `event` carries a
    single SQS record. The image referenced by the message is downloaded,
    processed, and its outputs are stored. Returning normally signals Lambda
    to delete the message; raising an exception leaves the message on the
    queue to be retried (design document Section 8).
    """
    settings = _load_settings()
    for record in event["Records"]:
        _process_record(record, settings)


def _process_record(record: dict, settings: dict) -> None:
    """Process a single SQS record end to end."""
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
    except Exception as exc:  # noqa: BLE001 - classified on the next line
        classified = errors.classify(exc)
        log.error("processing failed: %s: %s", type(classified).__name__, classified)
        # Re-raise so that Lambda does not delete the message. SQS makes the
        # message visible again after the visibility timeout, and the redrive
        # policy moves it to the dead-letter queue if it keeps failing
        # (design document Section 8.4).
        raise classified from exc


def _load_settings() -> dict:
    """Read the worker's configuration from environment variables."""
    return {
        "input_bucket": config.get("INPUT_BUCKET"),
        "output_bucket": config.get("OUTPUT_BUCKET"),
        "metadata_table": config.get("METADATA_TABLE"),
        "watermark": config.get_bool("WATERMARK", default=False),
    }
