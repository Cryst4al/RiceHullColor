"""Colour conversions used by the phenotyping pipeline.

Input RGB values are interpreted as IEC 61966-2-1 sRGB (D65). CIELAB values
are calculated after Bradford adaptation to the D50 reference white, matching
the established Photoshop/ImageJ workflow used by this project.
"""

from __future__ import annotations

import numpy as np

D50 = np.array([0.96422, 1.0, 0.82521], dtype=np.float64)
EPSILON = 216.0 / 24389.0
KAPPA = 24389.0 / 27.0


def _normalise_rgb(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb)
    if arr.ndim < 1 or arr.shape[-1] < 3:
        raise ValueError("RGB input must have a final dimension of at least 3")
    arr = arr[..., :3]
    if np.issubdtype(arr.dtype, np.integer):
        maximum = float(np.iinfo(arr.dtype).max)
    else:
        maximum = 1.0 if not arr.size or np.nanmax(arr) <= 1.0 else 255.0
    return np.clip(arr.astype(np.float64) / maximum, 0.0, 1.0)


def srgb_to_lab_d50(rgb: np.ndarray) -> np.ndarray:
    """Convert an sRGB array to CIELAB D50.

    Returns an array with the same leading dimensions and final channels
    ``L*, a*, b*``.
    """

    x = _normalise_rgb(rgb)
    linear = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    rgb_to_xyz_d65 = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz_d65 = linear @ rgb_to_xyz_d65.T
    bradford_d65_to_d50 = np.array(
        [
            [1.0478112, 0.0228866, -0.0501270],
            [0.0295424, 0.9904844, -0.0170491],
            [-0.0092345, 0.0150436, 0.7521316],
        ]
    )
    xyz = (xyz_d65 @ bradford_d65_to_d50.T) / D50
    f = np.where(xyz > EPSILON, np.cbrt(xyz), (KAPPA * xyz + 16.0) / 116.0)
    return np.stack(
        (116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])),
        axis=-1,
    )


def lab_d50_to_srgb(lab: np.ndarray) -> np.ndarray:
    """Convert CIELAB D50 to floating-point sRGB values in [0, 1]."""

    arr = np.asarray(lab, dtype=np.float64)
    if arr.shape[-1] != 3:
        raise ValueError("Lab input must have exactly three channels")
    lstar, astar, bstar = np.moveaxis(arr, -1, 0)
    fy = (lstar + 16.0) / 116.0
    fx = fy + astar / 500.0
    fz = fy - bstar / 200.0

    def inverse_f(value: np.ndarray) -> np.ndarray:
        cube = value**3
        return np.where(cube > EPSILON, cube, (116.0 * value - 16.0) / KAPPA)

    xyz_d50 = np.stack((D50[0] * inverse_f(fx), inverse_f(fy), D50[2] * inverse_f(fz)), axis=-1)
    bradford_d50_to_d65 = np.array(
        [
            [0.9555766, -0.0230393, 0.0631636],
            [-0.0282895, 1.0099416, 0.0210077],
            [0.0122982, -0.0204830, 1.3299098],
        ]
    )
    xyz_d65 = xyz_d50 @ bradford_d50_to_d65.T
    xyz_to_rgb = np.array(
        [
            [3.2404542, -1.5371385, -0.4985314],
            [-0.9692660, 1.8760108, 0.0415560],
            [0.0556434, -0.2040259, 1.0572252],
        ]
    )
    linear = xyz_d65 @ xyz_to_rgb.T
    encoded = np.where(
        linear <= 0.0031308,
        12.92 * linear,
        1.055 * np.maximum(linear, 0.0) ** (1.0 / 2.4) - 0.055,
    )
    return np.clip(encoded, 0.0, 1.0)


def lab_d50_to_srgb8(lab: np.ndarray) -> np.ndarray:
    """Convert CIELAB D50 to rounded 8-bit sRGB values."""

    return np.rint(lab_d50_to_srgb(lab) * 255.0).astype(np.uint8)


def grayscale_bt601(rgb8: np.ndarray) -> np.ndarray:
    """Return BT.601 luma-like grayscale from 8-bit sRGB values."""

    arr = np.asarray(rgb8, dtype=np.float64)
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]

