"""End-to-end measurement of one color-corrected rice hull image."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import __version__
from .color import grayscale_bt601, lab_d50_to_srgb8, srgb_to_lab_d50
from .io import load_config, read_rgb, sha256_file, to_uint8_preview
from .project import locate_project_folders, parse_image_identity
from .roi import convex_hull, imagej_roi_count, write_imagej_roi_zip
from .segmentation import HullRegion, segment_hulls

FIELDS = [
    "Material",
    "Date",
    "Image",
    "ROI",
    "PixelCount",
    "L_mean",
    "a_mean",
    "b_mean",
    "L_median",
    "a_median",
    "b_median",
    "L_sd",
    "a_sd",
    "b_sd",
    "R",
    "G",
    "B",
    "RGB",
    "Gray",
    "SourceROIImage",
    "ColorSpace",
    "Method",
]


def _config_digest(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stats(values: np.ndarray) -> tuple[float, float, float]:
    return float(values.mean()), float(np.median(values)), float(values.std(ddof=1)) if values.size > 1 else 0.0


def _region_polygon(region: HullRegion) -> np.ndarray:
    boundary = region.mask & ~ndimage.binary_erosion(region.mask)
    ys, xs = np.nonzero(boundary)
    if len(xs) < 3:
        ys, xs = np.nonzero(region.mask)
    return convex_hull(np.column_stack((xs, ys)))


def _row(identity, path: Path, lab: np.ndarray, region: HullRegion, method: str) -> dict[str, Any]:
    pixels = lab[region.mask]
    lmean, lmedian, lsd = _stats(pixels[:, 0])
    amean, amedian, asd = _stats(pixels[:, 1])
    bmean, bmedian, bsd = _stats(pixels[:, 2])
    rgb = lab_d50_to_srgb8(np.array([lmean, amean, bmean]))
    gray = float(grayscale_bt601(rgb))
    return {
        "Material": identity.material,
        "Date": identity.date,
        "Image": identity.image,
        "ROI": region.name,
        "PixelCount": int(len(pixels)),
        "L_mean": round(lmean, 4),
        "a_mean": round(amean, 4),
        "b_mean": round(bmean, 4),
        "L_median": round(lmedian, 4),
        "a_median": round(amedian, 4),
        "b_median": round(bmedian, 4),
        "L_sd": round(lsd, 4),
        "a_sd": round(asd, 4),
        "b_sd": round(bsd, 4),
        "R": int(rgb[0]),
        "G": int(rgb[1]),
        "B": int(rgb[2]),
        "RGB": f"({rgb[0]},{rgb[1]},{rgb[2]})",
        "Gray": round(gray, 2),
        "SourceROIImage": path.name,
        "ColorSpace": "CIELAB D50 from embedded/declared sRGB",
        "Method": method,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_qc(path: Path, rgb: np.ndarray, polygons: list[np.ndarray], names: list[str], quality: int, max_pixels: int, icc: bytes | None) -> None:
    image = Image.fromarray(to_uint8_preview(rgb), mode="RGB")
    scale = min(1.0, max_pixels / max(image.size))
    if scale < 1:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    for polygon, name in zip(polygons, names):
        xy = [(int(x * scale), int(y * scale)) for x, y in polygon]
        draw.line(xy + [xy[0]], fill=(230, 50, 50), width=max(2, round(3 * scale)))
        anchor = min(xy, key=lambda point: (point[0], point[1]))
        draw.rectangle((anchor[0], anchor[1], anchor[0] + 32, anchor[1] + 15), fill=(255, 255, 255))
        draw.text((anchor[0] + 2, anchor[1] + 1), name, fill=(180, 0, 0))
    save_kwargs: dict[str, Any] = {"quality": quality, "subsampling": 0}
    if icc:
        save_kwargs["icc_profile"] = icc
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, **save_kwargs)


def analyze_image(
    image_path: str | Path,
    project: str | Path,
    config_path: str | Path | None = None,
    expected_count: int | None = None,
) -> dict[str, Any]:
    """Analyse one CAL/ROI image and write CSV, ROI.zip, QC and manifest."""

    source = Path(image_path).resolve()
    folders = locate_project_folders(project)
    config = load_config(config_path)
    settings = dict(config["segmentation"])
    if expected_count is not None:
        settings["expected_count"] = int(expected_count)
    image_data = read_rgb(source)
    identity = parse_image_identity(source)
    lab = srgb_to_lab_d50(image_data.rgb)
    _, regions = segment_hulls(lab, settings)
    if not regions:
        raise RuntimeError(f"No hull regions detected in {source.name}; inspect thresholds and image crop")

    method = (
        f"actual-count components; central {int(float(settings.get('central_fraction', .7)) * 100)}% "
        f"green-tissue mask; a*<{settings['a_max']}, b*>{settings['b_min']}, "
        f"{settings['l_min']}<=L*<={settings['l_max']}"
    )
    rows = [_row(identity, source, lab, region, method) for region in regions]
    polygons = [_region_polygon(region) for region in regions]
    names = [region.name for region in regions]
    csv_path = folders["lab"] / f"{identity.key}_LAB.csv"
    roi_path = folders["roi_zip"] / f"{identity.key}_ROI.zip"
    qc_path = folders["qc"] / f"{identity.key}_QC.jpg"
    manifest_path = folders["lab"] / f"{identity.key}_manifest.json"
    _write_csv(csv_path, rows)
    write_imagej_roi_zip(roi_path, polygons, names)
    _write_qc(
        qc_path,
        image_data.rgb,
        polygons,
        names,
        int(config.get("qc", {}).get("jpeg_quality", 95)),
        int(config.get("qc", {}).get("max_preview_pixels", 3000)),
        image_data.icc_profile,
    )
    if imagej_roi_count(roi_path) != len(rows):
        raise RuntimeError(f"ROI ZIP verification failed for {roi_path}")

    warnings = []
    if image_data.rgb.dtype == np.uint8:
        warnings.append("8-bit input: formal analysis should use a 16-bit sRGB TIFF")
    if source.suffix.lower() in {".jpg", ".jpeg"}:
        warnings.append("JPEG input: lossy files are not recommended for formal colour analysis")
    if not image_data.icc_profile:
        warnings.append("No embedded ICC profile detected; values were interpreted as sRGB")
    if expected_count is not None and len(rows) != expected_count:
        warnings.append(f"Detected {len(rows)} regions, expected {expected_count}; inspect the QC overlay")
    manifest = {
        "software": "RiceHullColor",
        "version": __version__,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "input": str(source),
        "input_sha256": sha256_file(source),
        "input_dtype": str(image_data.rgb.dtype),
        "input_shape": list(image_data.rgb.shape),
        "image_backend": image_data.source_backend,
        "icc_embedded": bool(image_data.icc_profile),
        "config": config,
        "config_sha256": _config_digest(config),
        "detected_count": len(rows),
        "expected_count": expected_count,
        "warnings": warnings,
        "outputs": {"csv": str(csv_path), "roi_zip": str(roi_path), "qc": str(qc_path)},
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    manifest["manifest"] = str(manifest_path)
    return manifest

