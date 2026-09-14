import unittest

import numpy as np

from ricehullcolor.color import grayscale_bt601, lab_d50_to_srgb8, srgb_to_lab_d50


class ColorTests(unittest.TestCase):
    def test_white_and_black(self):
        lab = srgb_to_lab_d50(np.array([[255, 255, 255], [0, 0, 0]], dtype=np.uint8))
        self.assertAlmostEqual(float(lab[0, 0]), 100.0, places=3)
        self.assertAlmostEqual(float(lab[0, 1]), 0.0, places=2)
        self.assertAlmostEqual(float(lab[0, 2]), 0.0, places=2)
        self.assertAlmostEqual(float(lab[1, 0]), 0.0, places=6)

    def test_lab_round_trip(self):
        source = np.array([[180, 190, 80], [120, 100, 60]], dtype=np.uint8)
        recovered = lab_d50_to_srgb8(srgb_to_lab_d50(source))
        self.assertTrue(np.all(np.abs(recovered.astype(int) - source.astype(int)) <= 1))

    def test_gray_formula(self):
        self.assertAlmostEqual(float(grayscale_bt601(np.array([255, 0, 0]))), 76.245)


if __name__ == "__main__":
    unittest.main()

