"""Shared in-memory image normalization for hashing and embedding."""

from __future__ import annotations

from PIL import Image, ImageOps


def prepare_rgb_image(image: Image.Image) -> Image.Image:
    oriented = ImageOps.exif_transpose(image)
    has_alpha = oriented.mode in {"RGBA", "LA"} or (
        oriented.mode == "P" and "transparency" in oriented.info
    )
    if not has_alpha:
        return oriented.convert("RGB")
    rgba = oriented.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, rgba).convert("RGB")
