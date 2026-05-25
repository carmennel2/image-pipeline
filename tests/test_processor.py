"""Unit tests for the Image Processor.

The processor has no AWS dependencies, so these tests run locally with no
cloud setup. See design document Section 14.2.
"""
from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from worker.processor import THUMBNAIL_SIZES, Derivative, process_image


def _make_image(width: int, height: int, with_exif: bool = False) -> bytes:
    """Build an in-memory JPEG for testing, optionally carrying EXIF data."""
    image = Image.new("RGB", (width, height), color=(120, 90, 200))
    buffer = BytesIO()
    if with_exif:
        exif = image.getexif()
        exif[0x0110] = "TestCamera"  # the EXIF "Model" tag
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_produces_one_derivative_per_size() -> None:
    """Processing an image returns one derivative per target size."""
    derivatives = process_image(_make_image(2000, 1500))
    assert len(derivatives) == len(THUMBNAIL_SIZES)
    assert all(isinstance(d, Derivative) for d in derivatives)


def test_derivatives_are_webp() -> None:
    """Each derivative is encoded as WebP."""
    for derivative in process_image(_make_image(2000, 1500)):
        assert Image.open(BytesIO(derivative.data)).format == "WEBP"


def test_longest_edge_matches_target() -> None:
    """Each derivative is resized so its longest edge does not exceed the target."""
    for derivative in process_image(_make_image(2000, 1500)):
        assert max(derivative.width, derivative.height) <= derivative.size


def test_aspect_ratio_is_preserved() -> None:
    """Resizing preserves the original aspect ratio."""
    for derivative in process_image(_make_image(2000, 1000)):
        assert derivative.width == derivative.height * 2


def test_exif_is_removed() -> None:
    """A derivative carries no EXIF metadata, even when the source had some."""
    source = _make_image(1600, 1200, with_exif=True)
    assert Image.open(BytesIO(source)).getexif()  # the source genuinely has EXIF
    for derivative in process_image(source):
        assert not Image.open(BytesIO(derivative.data)).getexif()


def test_invalid_image_raises_value_error() -> None:
    """Bytes that are not a valid image raise ValueError (a permanent failure)."""
    with pytest.raises(ValueError):
        process_image(b"this is definitely not an image")
