"""Image and configuration input/output helpers."""

from __future__ import annotations

import hashlib
import importlib.resources
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image


@dataclass
class ImageData:
    rgb: np.ndarray
    icc_profile: bytes | None
    source_backend: str
    source_mode: str


def read_rgb(path: str | Path) -> ImageData:
    """Read an RGB image without silently accepting grayscale data.

    ``tifffile`` is preferred for 16-bit TIFF. Pillow is the fallback and is
    sufficient for PNG/JPEG and many TIFF files.
    """

    source = Path(path)
    icc = None
    if source.suffix.lower() in {".tif", ".tiff"}:
        try:
            import tifffile  # type: ignore

            with tifffile.TiffFile(source) as tif:
                rgb = tif.asarray()
                tag = tif.pages[0].tags.get(34675)
                icc = bytes(tag.value) if tag is not None else None
            if rgb.ndim == 3 and rgb.shape[-1] >= 3:
                return ImageData(rgb[..., :3], icc, "tifffile", str(rgb.dtype))
        except (ImportError, OSError, ValueError):
            pass

    with Image.open(source) as image:
        icc = image.info.get("icc_profile")
        mode = image.mode
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        rgb = np.asarray(image)[..., :3]
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected an RGB image, got shape {rgb.shape} from {source}")
    return ImageData(rgb, icc, "Pillow", mode)


def load_config(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        resource = importlib.resources.files("ricehullcolor").joinpath("resources/hull_color_global_v1.yml")
        with resource.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
    else:
        with Path(path).open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
    if not isinstance(config, dict) or "segmentation" not in config:
        raise ValueError("Configuration must contain a segmentation section")
    return config


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def to_uint8_preview(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb)
    if arr.dtype == np.uint8:
        return arr
    if np.issubdtype(arr.dtype, np.integer):
        maximum = float(np.iinfo(arr.dtype).max)
        return np.rint(np.clip(arr.astype(np.float64) / maximum, 0, 1) * 255).astype(np.uint8)
    maximum = 1.0 if np.nanmax(arr) <= 1 else 255.0
    return np.rint(np.clip(arr / maximum, 0, 1) * 255).astype(np.uint8)
