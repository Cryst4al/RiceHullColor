# RiceHullColor v0.1.0

The first reproducible public MVP packages the established rice hull color workflow as a Python command-line application and a lightweight Windows desktop interface.

## Included features

- Standard experiment folder initialization.
- Reading of 16-bit sRGB TIFF files and common preview-image formats.
- sRGB D65 to CIELAB D50 conversion.
- Actual-count connected-component detection and central-70% tissue measurement.
- Per-hull CIELAB, converted sRGB, and BT.601 grayscale values.
- Fiji/ImageJ `ROI.zip`, QC overlays, and JSON audit manifests.
- Image-level, material-date, and material-level summaries with Excel export.
- Date-adjusted univariate models, BH-FDR, Hedges' g, PERMANOVA partial R², PCA, and repeated cross-validated logistic regression.
- Adobe Camera Raw and statistical-method documentation.
- Windows installation script and GitHub Actions testing.

## Validation

- All six automated tests pass.
- In an anonymized regression check using a historical 16-bit TIFF, all ten ROI counts, pixel counts, and CIELAB mean, median, and standard-deviation values matched the original workflow.
- The public package contains no validation image, experimental result, or other unpublished data.

## Known limitations

- RAW white balance, lens correction, and 16-bit sRGB CAL export still require Adobe Camera Raw or equivalent validated software.
- Automatic ROI detection depends on the background and imaging conditions; every result must be checked using its QC overlay.
- Merged hulls and complex backgrounds may require manual correction in Fiji/ImageJ.
- The current release does not create camera DCP profiles or automatically calibrate colors from certified chart reference values.
- Phenotypic association does not establish genetic causality.

