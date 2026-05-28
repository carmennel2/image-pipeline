"""Image processor: resizes a source image into the standard WebP derivatives.

Has no AWS dependencies, so it can be unit-tested locally.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

# Longest-edge sizes (in pixels) for the three derivatives.
THUMBNAIL_SIZES: tuple[int, ...] = (256, 512, 1024)
WATERMARK_TEXT = "image-pipeline"


@dataclass
class Derivative:
    """One processed output image."""

    size: int      # longest-edge size this derivative was made for
    data: bytes    # encoded WebP bytes
    width: int
    height: int


def process_image(source_bytes: bytes, watermark: bool = False) -> list[Derivative]:
    """Resize one source image into WebP derivatives, smallest first.

    Raises ValueError if the bytes are not a decodable image, which the
    caller treats as a permanent failure.
    """
    try:
        opened = Image.open(BytesIO(source_bytes))
        opened.load()  # force the decode now so a corrupt file fails here
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"source bytes are not a valid image: {exc}") from exc

    # WebP encoding expects RGB; convert returns a plain Image, not an ImageFile.
    image: Image.Image = opened if opened.mode == "RGB" else opened.convert("RGB")

    largest_size = max(THUMBNAIL_SIZES)
    derivatives: list[Derivative] = []

    for size in sorted(THUMBNAIL_SIZES):
        derivative_image = image.copy()
        derivative_image.thumbnail((size, size))  # resizes in place, keeps aspect ratio

        if watermark and size == largest_size:
            _apply_watermark(derivative_image)

        buffer = BytesIO()
        # Saving without an exif argument drops the source metadata.
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
    """Draw a small text watermark in the bottom-right corner."""
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    margin = 8
    x = image.width - text_width - margin
    y = image.height - text_height - margin

    # Drawn twice, offset, to give the text a readable outline.
    draw.text((x + 1, y + 1), WATERMARK_TEXT, fill=(0, 0, 0), font=font)
    draw.text((x, y), WATERMARK_TEXT, fill=(255, 255, 255), font=font)
