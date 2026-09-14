# Public release checklist

- [x] Replace every `OWNER` placeholder in `pyproject.toml` and `CITATION.cff`.
- [x] Use the public GitHub author identifier `Cryst4al`; a real name and ORCID can be added later.
- [ ] Confirm that no RAW/XMP/TIFF/JPEG experiment data or private material identifiers are tracked.
- [ ] Run `python -m unittest discover -s tests -v` on Python 3.10–3.12.
- [ ] Build the wheel and inspect its contents.
- [x] Create a public GitHub repository named `RiceHullColor`.
- [ ] Enable Issues and the GitHub Actions test workflow.
- [ ] Tag `v0.1.0` and create a GitHub Release with the wheel attached.
- [ ] Connect the repository to Zenodo before the next release if a DOI is required.
- [ ] Update `CITATION.cff` with the archived release DOI.
