"""Minimal ImageJ polygon ROI ZIP interoperability."""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path

import numpy as np


def convex_hull(points_xy: np.ndarray) -> np.ndarray:
    """Return the monotonic-chain convex hull of integer x/y points."""

    unique = sorted({(int(x), int(y)) for x, y in np.asarray(points_xy)})
    if len(unique) <= 2:
        return np.asarray(unique, dtype=np.int32)

    def cross(origin, a, b):
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

    lower: list[tuple[int, int]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[int, int]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return np.asarray(lower[:-1] + upper[:-1], dtype=np.int32)


def imagej_polygon_bytes(points_xy: np.ndarray) -> bytes:
    """Encode a polygon in the ImageJ ROI binary format (version 227)."""

    points = np.asarray(points_xy, dtype=np.int32)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError("An ImageJ polygon ROI requires at least three x/y points")
    left, top = int(points[:, 0].min()), int(points[:, 1].min())
    right, bottom = int(points[:, 0].max()) + 1, int(points[:, 1].max()) + 1
    relative_x = points[:, 0] - left
    relative_y = points[:, 1] - top
    if max(right - left, bottom - top) > 65535:
        raise ValueError("ROI bounding box exceeds the ImageJ 16-bit coordinate range")

    header = bytearray(64)
    header[0:4] = b"Iout"
    struct.pack_into(">H", header, 4, 227)
    header[6] = 0  # polygon
    struct.pack_into(">hhhhH", header, 8, top, left, bottom, right, len(points))
    coordinates = b"".join(struct.pack(">H", int(v)) for v in relative_x)
    coordinates += b"".join(struct.pack(">H", int(v)) for v in relative_y)
    return bytes(header) + coordinates


def write_imagej_roi_zip(path: str | Path, polygons: list[np.ndarray], names: list[str]) -> None:
    if len(polygons) != len(names):
        raise ValueError("Polygon and name counts differ")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for polygon, name in zip(polygons, names):
            archive.writestr(f"{name}.roi", imagej_polygon_bytes(polygon))


def imagej_roi_count(path: str | Path) -> int:
    with zipfile.ZipFile(path) as archive:
        return sum(name.lower().endswith(".roi") for name in archive.namelist())

