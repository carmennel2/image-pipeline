"""Image Processor: the core data-processing component.

Takes a source image and produces the standardised derivatives defined in
Section 2.1 of the design document. This module has no AWS dependencies, so
it can be unit-tested locally (see tests/test_processor.py).
"""
from dataclasses import dataclass

# Target sizes for the resized derivatives (longest edge, in pixels).
THUMBNAIL_SIZES = (256, 512, 1024)


@dataclass
class Derivative:
    """One processed output image."""

    size: int      # the target longest-edge size this derivative was made for
    data: bytes    # the encoded WebP bytes
    width: int     # actual width of the derivative
    height: int    # actual height of the derivative


def process_image(source_bytes: bytes, watermark: bool = False) -> list[Derivative]:
    """Produce the WebP derivatives for one source image.

    Steps to implement:
      1. Decode `source_bytes` into an image (use Pillow: Image.open on a
         BytesIO wrapper of the bytes).
      2. For each size in THUMBNAIL_SIZES:
         - resize so the longest edge equals the size, preserving aspect
           ratio (Pillow's Image.thumbnail does exactly this in place);
         - encode the result as WebP into an in-memory buffer, without
           passing an exif argument, so no metadata chunk is written;
         - if `watermark` is True and this is the largest size, draw the
           watermark before encoding.
      3. Return a list of Derivative objects.

    Raise ValueError if `source_bytes` is not a valid image, so the caller
    can treat it as a permanent failure (see errors.py).
    """
    # TODO: implement using Pillow
    raise NotImplementedError
