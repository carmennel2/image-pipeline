"""Unit tests for the Image Processor.

The processor has no AWS dependencies, so these tests run locally.
See design document Section 14.2.
"""


def test_produces_three_derivatives() -> None:
    """Processing an image should return one derivative per target size."""
    # TODO: build or load a small test image, call process_image,
    #       and assert that it returns three derivatives.
    raise NotImplementedError


def test_derivatives_are_webp() -> None:
    """Each derivative should be encoded as WebP."""
    # TODO: assert the format of each derivative.
    raise NotImplementedError


def test_exif_is_removed() -> None:
    """A derivative should carry no EXIF metadata."""
    # TODO: process an image that has EXIF data and assert it is gone.
    raise NotImplementedError
