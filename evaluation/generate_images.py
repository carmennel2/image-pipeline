"""Generate a directory of synthetic JPEG images for the scaling evaluation.

Each image is a 1024x768 picture with a random fill colour and a small
overlay text. This is enough to make every image unique on disk and
non-trivially compressible, so the resulting batch is realistic for
exercising the pipeline without the time and cost of sourcing real photos.

Usage:
    python evaluation/generate_images.py path/to/output_dir --count 10000
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw


WIDTH = 1024
HEIGHT = 768


def main() -> None:
    args = _parse_args()
    out_dir = Path(args.directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.count} images into {out_dir} ...")
    for i in range(1, args.count + 1):
        path = out_dir / f"s{i:05d}.jpg"
        _make_image(path, i)
        if i % 500 == 0:
            print(f"  generated {i} of {args.count}")
    print("Done.")


def _make_image(path: Path, index: int) -> None:
    """Write one 1024x768 JPEG with a random fill and an index label."""
    colour = (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    )
    image = Image.new("RGB", (WIDTH, HEIGHT), colour)
    draw = ImageDraw.Draw(image)
    draw.text((40, 40), f"synthetic image {index}", fill=(255, 255, 255))
    image.save(path, format="JPEG", quality=85)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic JPEG images for the scaling evaluation."
    )
    parser.add_argument("directory", help="the directory to write images into")
    parser.add_argument(
        "--count",
        type=int,
        default=10000,
        help="how many images to generate (default 10000)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(1)
