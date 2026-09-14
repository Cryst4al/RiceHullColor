"""Aggregate per-ROI results into image, material-date and material tables."""

from __future__ import annotations

from copy import copy
from pathlib import Path

import numpy as np
import pandas as pd

from .color import grayscale_bt601, lab_d50_to_srgb8
from .project import locate_project_folders

LAB_COLUMNS = ["L_mean", "a_mean", "b_mean"]


def _display_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    lab = out[LAB_COLUMNS].to_numpy(dtype=float)
    rgb = lab_d50_to_srgb8(lab)
    out["R"] = rgb[:, 0]
    out["G"] = rgb[:, 1]
    out["B"] = rgb[:, 2]
    out["RGB"] = [f"({r},{g},{b})" for r, g, b in rgb]
    out["Gray"] = np.round(grayscale_bt601(rgb), 2)
    return out


def _weighted_summary(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for values, group in frame.groupby(keys, dropna=False, sort=True):
        if not isinstance(values, tuple):
            values = (values,)
        weights = group["PixelCount"].to_numpy(dtype=float)
        row = dict(zip(keys, values))
        row["ROICount"] = len(group)
        row["PixelCount"] = int(weights.sum())
        for column in LAB_COLUMNS:
            row[column] = np.average(group[column].to_numpy(dtype=float), weights=weights)
        rows.append(row)
    return _display_columns(pd.DataFrame(rows))


def aggregate_project(project: str | Path, xlsx: str | Path | None = None) -> dict[str, Path | int]:
    folders = locate_project_folders(project)
    files = sorted(
        p
        for p in folders["lab"].glob("*_LAB.csv")
        if not p.name.upper().startswith("HULL_LAB")
    )
    if not files:
        raise FileNotFoundError(f"No per-image *_LAB.csv files found in {folders['lab']}")
    grains = pd.concat((pd.read_csv(path, encoding="utf-8-sig") for path in files), ignore_index=True)
    for column in ["PixelCount", *LAB_COLUMNS]:
        grains[column] = pd.to_numeric(grains[column], errors="raise")

    image = _weighted_summary(grains, ["Material", "Date", "Image", "SourceROIImage"])
    material_date = image.groupby(["Material", "Date"], as_index=False).agg(
        ImageCount=("Image", "size"),
        ROICount=("ROICount", "sum"),
        PixelCount=("PixelCount", "sum"),
        L_mean=("L_mean", "mean"),
        a_mean=("a_mean", "mean"),
        b_mean=("b_mean", "mean"),
    )
    material_date = _display_columns(material_date)
    material = material_date.groupby("Material", as_index=False).agg(
        DateCount=("Date", "nunique"),
        ImageCount=("ImageCount", "sum"),
        ROICount=("ROICount", "sum"),
        PixelCount=("PixelCount", "sum"),
        L_mean=("L_mean", "mean"),
        a_mean=("a_mean", "mean"),
        b_mean=("b_mean", "mean"),
    )
    material = _display_columns(material)

    outputs = {
        "grain_csv": folders["lab"] / "HULL_LAB_RGB_GRAIN_ALL.csv",
        "image_csv": folders["lab"] / "HULL_LAB_RGB_IMAGE_SUMMARY.csv",
        "material_date_csv": folders["lab"] / "HULL_LAB_RGB_MATERIAL_DATE_SUMMARY.csv",
        "material_csv": folders["lab"] / "HULL_LAB_RGB_MATERIAL_SUMMARY.csv",
    }
    for table, key in ((grains, "grain_csv"), (image, "image_csv"), (material_date, "material_date_csv"), (material, "material_csv")):
        table.to_csv(outputs[key], index=False, encoding="utf-8-sig")

    xlsx_path = Path(xlsx) if xlsx else folders["results"] / "RiceHullColor_summary.xlsx"
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    method = pd.DataFrame(
        {
            "Item": ["Statistical unit", "Image summary", "Material summary", "RGB conversion", "Gray formula"],
            "Value": [
                "Material mean",
                "Pixel-weighted mean of detected hull ROIs",
                "Equal-weight mean of image means",
                "Mean CIELAB D50 converted to sRGB and rounded to 8-bit",
                "BT.601: 0.299R + 0.587G + 0.114B",
            ],
        }
    )
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        material.to_excel(writer, sheet_name="材料汇总", index=False)
        material_date.to_excel(writer, sheet_name="材料日期汇总", index=False)
        image.to_excel(writer, sheet_name="图像汇总", index=False)
        grains.to_excel(writer, sheet_name="逐粒明细", index=False)
        method.to_excel(writer, sheet_name="方法说明", index=False)
        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cell in worksheet[1]:
                font = copy(cell.font)
                font.bold = True
                cell.font = font
            for column in worksheet.columns:
                width = min(40, max(10, max(len(str(cell.value or "")) for cell in column) + 2))
                worksheet.column_dimensions[column[0].column_letter].width = width
    outputs["xlsx"] = xlsx_path
    outputs["grain_rows"] = len(grains)
    outputs["image_rows"] = len(image)
    outputs["material_rows"] = len(material)
    return outputs
