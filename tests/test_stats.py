import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from ricehullcolor.stats import run_statistics


class StatisticsTests(unittest.TestCase):
    def test_material_level_outputs(self):
        rng = np.random.default_rng(42)
        rows = []
        for index in range(24):
            japonica = index >= 12
            rows.append(
                {
                    "Material": f"M{index + 1:02d}",
                    "Date": "20260813" if index % 2 == 0 else "20260816",
                    "Group": "Japonica" if japonica else "Indica",
                    "Lstar": 52 if japonica else 58 + rng.normal(0, 0.6),
                    "astar": -11.5 if japonica else -10 + rng.normal(0, 0.2),
                    "bstar": 35.5 if japonica else 36.7 + rng.normal(0, 0.3),
                    "Gray": 120 if japonica else 134 + rng.normal(0, 1),
                }
            )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            csv_path = root / "data.csv"
            pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")
            result = run_statistics(csv_path, root / "stats", permutations=19, repeats=2)
            self.assertEqual(result["rows"], 24)
            self.assertTrue((root / "stats" / "RiceHullColor_statistics.xlsx").exists())
            self.assertTrue((root / "stats" / "01_Lab_gray_boxplots.png").exists())
            univariate = pd.read_csv(root / "stats" / "univariate_date_adjusted.csv")
            self.assertEqual(set(univariate["Trait"]), {"Lstar", "astar", "bstar", "Gray"})


if __name__ == "__main__":
    unittest.main()

