"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from . import __version__
from .aggregate import aggregate_project
from .io import load_config
from .pipeline import analyze_image
from .project import candidate_images, init_project
from .stats import run_statistics


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ricehullcolor", description="Rice hull colour phenotyping")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    command = sub.add_parser("init", help="create the standard experiment folder structure")
    command.add_argument("project")

    command = sub.add_parser("analyze", help="analyse one CAL/ROI image")
    command.add_argument("image")
    command.add_argument("--project", required=True)
    command.add_argument("--config")
    command.add_argument("--expected-count", type=int, help="optional QC expectation; actual detections are retained")

    command = sub.add_parser("batch", help="analyse every image in 03_ROI or, if empty, 02_CAL")
    command.add_argument("project")
    command.add_argument("--config")
    command.add_argument("--expected-count", type=int)
    command.add_argument("--continue-on-error", action="store_true")

    command = sub.add_parser("aggregate", help="create grain, image and material summaries")
    command.add_argument("project")
    command.add_argument("--xlsx")

    command = sub.add_parser("stats", help="run material-level indica/japonica association analysis")
    command.add_argument("input_csv")
    command.add_argument("--out", required=True)
    command.add_argument("--group-col", default="Group")
    command.add_argument("--date-col", default="Date")
    command.add_argument("--permutations", type=int, default=999)
    command.add_argument("--repeats", type=int, default=20)
    command.add_argument("--seed", type=int, default=20260914)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "init":
        paths = init_project(args.project)
        config_target = Path(args.project) / "hull_color_global_v1.yml"
        packaged = Path(__file__).parent / "resources" / "hull_color_global_v1.yml"
        shutil.copyfile(packaged, config_target)
        print(json.dumps({**{key: str(value) for key, value in paths.items()}, "config": str(config_target)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "analyze":
        result = analyze_image(args.image, args.project, args.config, args.expected_count)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "batch":
        load_config(args.config)  # fail before writing if the configuration is invalid
        images = candidate_images(args.project)
        if not images:
            raise FileNotFoundError("No TIFF/PNG/JPEG images found in the project's 03_ROI or 02_CAL folder")
        failures = []
        for index, image in enumerate(images, start=1):
            try:
                result = analyze_image(image, args.project, args.config, args.expected_count)
                print(f"[{index}/{len(images)}] {image.name}: {result['detected_count']} ROI")
            except Exception as exc:
                failures.append({"image": str(image), "error": str(exc)})
                print(f"[{index}/{len(images)}] ERROR {image.name}: {exc}")
                if not args.continue_on_error:
                    raise
        aggregate_project(args.project)
        if failures:
            failure_path = Path(args.project) / "06_LAB数据" / "batch_failures.json"
            failure_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
            return 2
        return 0
    if args.command == "aggregate":
        result = aggregate_project(args.project, args.xlsx)
        print(json.dumps({key: str(value) for key, value in result.items()}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "stats":
        result = run_statistics(args.input_csv, args.out, args.group_col, args.date_col, args.permutations, args.repeats, args.seed)
        print(json.dumps({key: str(value) for key, value in result.items()}, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

