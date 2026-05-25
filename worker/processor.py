"""Image Processor: the core data-processing component.

Takes a source image and produces the standardised derivatives defined in
Section 2.1 of the design document. This module has no AWS dependencies, so
it can be unit-tested locally (see tests/test_processor.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

# Target sizes for the resized derivatives (longest edge, in pixels).
THUMBNAIL_SIZES: tuple[int, ...] = (256, 512, 1024)

# Text drawn as the watermark on the largest derivative.
WATERMARK_TEXT = "image-pipeline"


@dataclass
class Derivative:
    """One processed output image."""

    size: int      # the target longest-edge size this derivative was made for
    data: bytes    # the encoded WebP bytes
    width: int     # actual width of the derivative in pixels
    height: int    # actual height of the derivative in pixels


def process_image(source_bytes: bytes, watermark: bool = False) -> list[Derivative]:
    """Produce the WebP derivatives for one source image.

    Args:
        source_bytes: the raw bytes of the source image.
        watermark: if True, a watermark is applied to the largest derivative.

    Returns:
        One Derivative per entry in THUMBNAIL_SIZES, ordered smallest first.

    Raises:
        ValueError: if source_bytes is not a decodable image. The caller
            treats this as a permanent failure (see errors.py).
    """
    try:
        image = Image.open(BytesIO(source_bytes))
        # Image.open is lazy; load() forces a decode now so that a corrupt
        # or truncated file fails here rather than later.
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"source bytes are not a valid image: {exc}") from exc

    # Work in RGB so that every derivative encodes consistently as WebP.
    if image.mode != "RGB":
        image = image.convert("RGB")

    largest_size = max(THUMBNAIL_SIZES)
    derivatives: list[Derivative] = []

    for size in sorted(THUMBNAIL_SIZES):
        derivative_image = image.copy()
        # thumbnail() resizes in place, shrinks the image to fit within a
        # size-by-size box, and preserves the original aspect ratio.
        derivative_image.thumbnail((size, size))

        if watermark and size == largest_size:
            _apply_watermark(derivative_image)

        buffer = BytesIO()
        # No exif argument is passed, so Pillow writes no metadata chunk:
        # EXIF data from the source is not carried into the derivative.
        derivative_image.save(buffer, format="WEBP", quality=82, method=4)

        derivatives.append(
            Derivative(
                size=size,
                data=buffer.getvalue(),
                width=derivative_image.width,
                height=derivative_image.height,
            )
        )

    return derivatives


def _apply_watermark(image: Image.Image) -> None:
    """Draw a small text watermark in the bottom-right corner, in place."""
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    margin = 8
    x = image.width - text_width - margin
    y = image.height - text_height - margin

    # Draw the text twice, offset, for a simple readable outline.
    draw.text((x + 1, y + 1), WATERMARK_TEXT, fill=(0, 0, 0), font=font)
    draw.text((x, y), WATERMARK_TEXT, fill=(255, 255, 255), font=font)
