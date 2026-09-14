"""Project layout and filename conventions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FOLDERS = {
    "raw_backup": "00_RAW原始备份",
    "raw_work": "01_RAW工作副本",
    "cal": "02_CAL颜色校正图",
    "roi_image": "03_ROI分析图",
    "qc": "04_QC预览图",
    "roi_zip": "05_ROI选区",
    "lab": "06_LAB数据",
    "results": "results",
}


@dataclass(frozen=True)
class ImageIdentity:
    key: str
    material: str
    date: str
    image: str


def init_project(root: str | Path) -> dict[str, Path]:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    paths = {name: base / folder for name, folder in FOLDERS.items()}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def locate_project_folders(root: str | Path) -> dict[str, Path]:
    base = Path(root)
    paths = {name: base / folder for name, folder in FOLDERS.items()}
    for key in ("qc", "roi_zip", "lab", "results"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def parse_image_identity(path: str | Path) -> ImageIdentity:
    stem = Path(path).stem
    key = re.sub(r"_(RAW|CAL|ROI|QC)$", "", stem, flags=re.IGNORECASE)
    match = re.match(r"^(?P<material>.+)-HULL-(?P<date>\d{8})-(?P<image>I\d+)$", key, re.IGNORECASE)
    if match:
        return ImageIdentity(key, match.group("material"), match.group("date"), match.group("image").upper())
    return ImageIdentity(key, key, "", "")


def candidate_images(root: str | Path) -> list[Path]:
    folders = locate_project_folders(root)
    source = folders["roi_image"]
    files = sorted(p for p in source.iterdir() if p.suffix.lower() in {".tif", ".tiff", ".png", ".jpg", ".jpeg"}) if source.exists() else []
    if files:
        return files
    source = folders["cal"]
    return sorted(p for p in source.iterdir() if p.suffix.lower() in {".tif", ".tiff", ".png", ".jpg", ".jpeg"}) if source.exists() else []

