"""Synthetic geometry tests; no private footage or optional dependencies."""
import importlib.util
import math
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'skills/volleyball-video-analysis/scripts/floor_map.py'
SPEC = importlib.util.spec_from_file_location('floor_map', PATH)
floor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(floor)


def camera(x, y):
    d = 1 + .013*x + .019*y
    return [(110*x + 15*y + 4000)/d, (8*x + 70*y + 2000)/d]


def fixture():
    controls = [{'image': camera(x, y), 'court': [x, y]}
                for x, y in [(0, 0), (18, 0), (18, 9), (0, 9), (6, 0), (12, 9)]]
    return {'controls': controls,
            'holdouts': [{'image': camera(6, 3), 'court': [6, 3]},
                         {'image': camera(12, 6), 'court': [12, 6]}],
            'points': [{'id': 'feet', 'kind': 'floor', 'image': camera(8, 7)}]}


class FloorMapTests(unittest.TestCase):
    def test_projective_camera_and_large_pixel_offset(self):
        result = floor.reconstruct(fixture())
        self.assertLess(result['holdout_max_m'], 1e-7)
        self.assertLess(math.dist(result['points'][0]['court'], [8, 7]), 1e-7)

    def test_holdout_exposes_wrong_calibration(self):
        data = fixture()
        data['holdouts'][0]['court'] = [9, 3]
        result = floor.reconstruct(data)
        self.assertAlmostEqual(result['holdout_max_m'], 3)

    def test_collinear_controls_rejected(self):
        data = fixture()
        data['controls'] = [{'image': [i*100, 5], 'court': [i, 0]} for i in range(4)]
        with self.assertRaisesRegex(ValueError, 'singular'):
            floor.reconstruct(data)

    def test_missing_or_reused_holdout_rejected(self):
        data = fixture()
        data['holdouts'] = []
        with self.assertRaises(ValueError):
            floor.reconstruct(data)
        data['holdouts'] = [data['controls'][0]]
        with self.assertRaisesRegex(ValueError, 'duplicates'):
            floor.reconstruct(data)

    def test_nonfinite_and_bool_coordinates_rejected(self):
        for value in [math.nan, math.inf, True]:
            data = fixture()
            data['points'][0]['image'][0] = value
            with self.assertRaises(ValueError):
                floor.reconstruct(data)

    def test_airborne_points_and_duplicate_ids_rejected(self):
        data = fixture()
        data['points'][0]['kind'] = 'ball'
        with self.assertRaisesRegex(ValueError, 'grounded'):
            floor.reconstruct(data)
        data = fixture()
        data['points'] *= 2
        with self.assertRaisesRegex(ValueError, 'unique'):
            floor.reconstruct(data)

    def test_projection_near_infinity_rejected(self):
        model = {'image_center': [0, 0], 'image_scale': 1,
                 'court_center': [0, 0], 'court_scale': 1,
                 'coefficients': [1, 0, 0, 0, 1, 0, -1, 0]}
        with self.assertRaisesRegex(ValueError, 'infinity'):
            floor.project(model, [1, 0])


if __name__ == '__main__':
    unittest.main()
