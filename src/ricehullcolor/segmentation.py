"""Threshold-based rice hull segmentation with actual-count components."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass
class HullRegion:
    name: str
    mask: np.ndarray
    centroid_x: float
    centroid_y: float
    component_score: int


def block_any(mask: np.ndarray, factor: int) -> np.ndarray:
    if factor <= 1:
        return mask.copy()
    height, width = mask.shape
    pad_h = (-height) % factor
    pad_w = (-width) % factor
    padded = np.pad(mask, ((0, pad_h), (0, pad_w)), mode="constant")
    return padded.reshape(padded.shape[0] // factor, factor, padded.shape[1] // factor, factor).any(axis=(1, 3))


def central_mask(component_mask: np.ndarray, fraction: float) -> np.ndarray:
    """Keep the central fraction along the component's long image axis."""

    if not 0 < fraction <= 1:
        raise ValueError("central_fraction must be in (0, 1]")
    ys, xs = np.nonzero(component_mask)
    result = component_mask.copy()
    if not len(xs) or fraction == 1:
        return result
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    margin = (1.0 - fraction) / 2.0
    if y1 - y0 >= x1 - x0:
        low, high = y0 + margin * (y1 - y0), y1 - margin * (y1 - y0)
        yy = np.arange(result.shape[0])[:, None]
        result &= (yy >= low) & (yy <= high)
    else:
        low, high = x0 + margin * (x1 - x0), x1 - margin * (x1 - x0)
        xx = np.arange(result.shape[1])[None, :]
        result &= (xx >= low) & (xx <= high)
    return result


def segment_hulls(lab: np.ndarray, settings: dict) -> tuple[np.ndarray, list[HullRegion]]:
    """Segment hull tissue and return left-to-right central measurement masks."""

    lstar, astar, bstar = lab[..., 0], lab[..., 1], lab[..., 2]
    tissue = (
        (astar < float(settings["a_max"]))
        & (bstar > float(settings["b_min"]))
        & (lstar >= float(settings["l_min"]))
        & (lstar <= float(settings["l_max"]))
    )
    factor = int(settings.get("downsample", 2))
    small = block_any(tissue, factor)
    dilated = ndimage.binary_dilation(small, iterations=int(settings.get("dilate_iterations", 2)))
    labels, count = ndimage.label(dilated, structure=np.ones((3, 3), dtype=np.uint8))
    candidates = []
    minimum = max(1, int(settings.get("min_component_pixels", 24)) // (factor * factor))
    for label_id in range(1, count + 1):
        area = int(np.count_nonzero(small & (labels == label_id)))
        if area < minimum:
            continue
        ys, xs = np.nonzero(labels == label_id)
        candidates.append((area, label_id, float(xs.mean()), float(ys.mean())))

    candidates.sort(reverse=True)
    expected = settings.get("expected_count")
    if expected in (None, "", 0) and candidates:
        relative_minimum = candidates[0][0] * float(settings.get("relative_min_area", 0.10))
        candidates = [item for item in candidates if item[0] >= relative_minimum]
    limit = int(expected) if expected not in (None, "", 0) else int(settings.get("max_components", 10))
    candidates = candidates[:limit]
    candidates.sort(key=lambda item: (item[2], item[3]))

    regions: list[HullRegion] = []
    for area, label_id, cx, cy in candidates:
        small_component = labels == label_id
        expanded = np.repeat(np.repeat(small_component, factor, axis=0), factor, axis=1)
        full_component = tissue & expanded[: tissue.shape[0], : tissue.shape[1]]
        measured = central_mask(full_component, float(settings.get("central_fraction", 0.70)))
        if np.count_nonzero(measured) < int(settings.get("min_component_pixels", 24)):
            continue
        regions.append(HullRegion(f"S{len(regions) + 1:02d}", measured, cx * factor, cy * factor, area))
    return tissue, regions
