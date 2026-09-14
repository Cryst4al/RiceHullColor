# RiceHullColor

RiceHullColor is a reproducible image-analysis toolkit for rice hull color phenotyping. It converts globally color-corrected `CAL.tif` images—or cropped, otherwise unmodified `ROI.tif` images—into hull-level, image-level, and material-level CIELAB D50, sRGB, and grayscale measurements. It also produces Fiji/ImageJ-compatible ROI files, quality-control overlays, Excel workbooks, and auditable run manifests.

> The quantitative pipeline starts from a 16-bit sRGB TIFF. RAW white balance, lens correction, and 16-bit sRGB export are performed in Adobe Camera Raw before analysis. RiceHullColor never modifies the original RAW sensor data. JPEG input is supported for demonstration only and is not recommended for formal color analysis.

## Key features

- Reports the actual number of detected hulls instead of forcing every image to contain exactly ten objects.
- Preserves the validated settings: a tissue mask of `a* < -5`, `b* > 5`, and `15 <= L* <= 90`, followed by measurement of the central 70% of each connected component.
- Converts sRGB D65 to CIELAB D50 using Bradford chromatic adaptation.
- Converts mean CIELAB D50 values back to 8-bit sRGB for reporting.
- Calculates grayscale using BT.601: `0.299R + 0.587G + 0.114B`.
- Exports per-hull CSV files, image and material summaries, Excel workbooks, Fiji/ImageJ `ROI.zip` files, QC overlays, and JSON audit manifests.
- Stores thresholds, minimum component area, maximum object count, and central measurement fraction in a versioned YAML configuration.
- Provides both a command-line interface and a lightweight Windows desktop interface.
- Includes material-level association statistics, PCA, PERMANOVA, and repeated cross-validated logistic regression.

## Installation

### Windows guided installation

Open PowerShell in the source directory and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows.ps1
```

After installation, double-click `run_gui.cmd` to open the desktop interface.

### Manual installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux or macOS
source .venv/bin/activate

python -m pip install -e .
```

For complete 16-bit Photoshop TIFF support, install the TIFF extras:

```bash
python -m pip install -e ".[tiff]"
```

## Quick start

Create the standard experiment structure:

```bash
ricehullcolor init D:\experiment\HULL
```

Place color-corrected master images in `02_CAL颜色校正图`, or cropped analysis images in `03_ROI分析图`. The recommended filename format is:

```text
DEMO001-R1-P03-HULL-20260813-I01_ROI.tif
```

Analyze one image:

```bash
ricehullcolor analyze "03_ROI分析图/DEMO001-R1-P03-HULL-20260813-I01_ROI.tif" \
  --project . --config configs/hull_color_global_v1.yml
```

Analyze a project and create a unified Excel workbook:

```bash
ricehullcolor batch . --config configs/hull_color_global_v1.yml
ricehullcolor aggregate . --xlsx results/RiceHullColor_summary.xlsx
```

Open the desktop interface:

```bash
ricehullcolor-gui
```

## Project structure

```text
HULL/
├─ 00_RAW原始备份/          # untouched RAW backup
├─ 01_RAW工作副本/          # RAW working copies and XMP sidecars
├─ 02_CAL颜色校正图/         # 16-bit sRGB color-corrected master TIFFs
├─ 03_ROI分析图/             # cropped analysis TIFFs
├─ 04_QC预览图/              # numbered ROI overlays
├─ 05_ROI选区/               # Fiji/ImageJ ROI.zip files
├─ 06_LAB数据/               # CSV measurements and audit manifests
└─ results/                  # Excel workbooks and statistical outputs
```

Per-hull output includes pixel count; mean, median, and standard deviation of L*, a*, and b*; converted RGB; grayscale; source filename; color space; and measurement method.

Image summaries are pixel-weighted across valid hull ROIs. Material summaries first calculate an image mean and then average image means with equal weight, preventing images with larger masks from dominating the material phenotype.

## Association analysis

Prepare a material-level CSV containing `Material`, `Date`, `Group`, `Lstar`, `astar`, `bstar`, and optionally `Gray`. `Group` should contain `Indica` and `Japonica`:

```bash
ricehullcolor stats data.csv --out results/statistics
```

The statistical workflow reports:

- date-adjusted linear models;
- Benjamini–Hochberg false-discovery-rate correction;
- Hedges' g standardized effect sizes;
- date-restricted PERMANOVA with partial R²;
- PCA scores and publication-ready plots;
- repeated stratified cross-validation of L2-regularized logistic regression;
- AUC, balanced accuracy, sensitivity, and specificity.

The material is the statistical unit. Multiple hulls and images from the same material are technical subsamples and must not be treated as independent biological samples.

## Scientific interpretation

- RiceHullColor quantifies phenotypic associations under controlled imaging and global color correction; it does not establish genetic causality.
- Grayscale and L* both primarily measure lightness and are usually highly correlated. They should not be interpreted as independent evidence.
- When dates are combined, retain the imaging date and adjust for batch effects or run sensitivity analyses.
- If material identity and imaging date are completely confounded, material effects cannot be separated from date effects.
- Every automated segmentation result must be checked using the QC overlay. Merged hulls, strong reflections, shadows, disease lesions, or abnormal backgrounds require manual review in Fiji/ImageJ.

## Documentation

- [Algorithm and statistical methods—Chinese](docs/METHODS_ZH.md)
- [Adobe Camera Raw and Photoshop protocol—Chinese](docs/PHOTOSHOP_ACR_ZH.md)
- [Release notes](docs/RELEASE_NOTES_0.1.0.md)

## Data privacy

The repository `.gitignore` excludes RAW files, XMP sidecars, experiment-stage image folders, and generated results. Do not commit photographs containing labels, personal information, or unpublished experimental data.

The repository and release package contain synthetic schema examples only. No experimental photographs, real material identifiers, or unpublished measurements are included.

## Validation

- Six automated tests cover color conversion, grayscale calculation, actual-count segmentation, ImageJ ROI export, Excel aggregation, and statistical output.
- GitHub Actions validates the package on Python 3.10, 3.11, and 3.12.
- An anonymized regression check on a historical 16-bit TIFF reproduced the ROI count, pixel counts, and CIELAB summary statistics from the original workflow.

## Citation and license

RiceHullColor is released under the Apache License 2.0. The current public author identifier is the GitHub account `Cryst4al`. A full author name and ORCID can be added to `CITATION.cff` for formal academic citation.

For a persistent scholarly DOI, connect the GitHub repository to Zenodo before publishing a future release.

