import tempfile
import unittest
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

from ricehullcolor.aggregate import aggregate_project
from ricehullcolor.pipeline import analyze_image
from ricehullcolor.project import init_project, parse_image_identity
from ricehullcolor.roi import imagej_roi_count


def synthetic_hulls(path: Path, offset: int = 0) -> None:
    image = Image.new("RGB", (720, 260), "white")
    draw = ImageDraw.Draw(image)
    for index in range(3):
        x = 90 + index * 210 + offset
        draw.ellipse((x, 55, x + 65, 215), fill=(180, 190, 80))
    image.save(path)


class PipelineTests(unittest.TestCase):
    def test_filename(self):
        item = parse_image_identity("TEST-R1-P01-HULL-20260813-I03_ROI.tif")
        self.assertEqual(item.material, "TEST-R1-P01")
        self.assertEqual(item.date, "20260813")
        self.assertEqual(item.image, "I03")

    def test_analysis_and_aggregation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folders = init_project(root)
            image1 = folders["roi_image"] / "TEST-HULL-20260813-I01_ROI.png"
            image2 = folders["roi_image"] / "TEST-HULL-20260813-I02_ROI.png"
            synthetic_hulls(image1)
            synthetic_hulls(image2, 4)
            result1 = analyze_image(image1, root)
            result2 = analyze_image(image2, root)
            self.assertEqual(result1["detected_count"], 3)
            self.assertEqual(result2["detected_count"], 3)
            self.assertEqual(imagej_roi_count(root / "05_ROI选区" / "TEST-HULL-20260813-I01_ROI.zip"), 3)
            summary = aggregate_project(root)
            self.assertEqual(summary["grain_rows"], 6)
            self.assertEqual(summary["image_rows"], 2)
            self.assertEqual(summary["material_rows"], 1)
            grains = pd.read_csv(summary["grain_csv"], encoding="utf-8-sig")
            self.assertTrue({"L_mean", "a_mean", "b_mean", "R", "G", "B", "Gray"}.issubset(grains.columns))


if __name__ == "__main__":
    unittest.main()
