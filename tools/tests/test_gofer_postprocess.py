"""Check evidence selection in each independent GOFER postprocessor.

Small synthetic rasters exercise rejection paths and a known exact comparison;
these are software checks, not substitutes for historical validation evidence.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]
CASES = ('caldor_2021', 'czu_lightning_complex_2020', 'glass_2020', 'kincade_2019')
TRANSFORM = from_origin(500000, 4200000, 30, 30)
CRS = rasterio.crs.CRS.from_epsg(32610)


def load_case(name):
    scripts = ROOT / 'cases/Validation/landscape_scale' / name / 'scripts'
    # Import the helper owned by this case, not a suite-wide or sibling helper.
    previous = sys.modules.pop('report_language', None)
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(name + '_postprocess', scripts / 'postprocess.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert Path(sys.modules['report_language'].__file__).parent == scripts
        return module
    finally:
        sys.path.pop(0)
        sys.modules.pop('report_language', None)
        if previous is not None:
            sys.modules['report_language'] = previous


MODULES = {name: load_case(name) for name in CASES}


def raster(path, values, *, count=1, transform=TRANSFORM, crs=CRS, nodata=-9999):
    values = np.asarray(values, dtype='float32')
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', driver='GTiff', height=values.shape[0],
                       width=values.shape[1], count=count, dtype='float32',
                       transform=transform, crs=crs, nodata=nodata) as dst:
        for band in range(1, count + 1):
            dst.write(values, band)


class GoferEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_latest_unique_member_one(self):
        older = self.root / 'time_of_arrival_0000001_0000100.tif'
        latest = self.root / 'time_of_arrival_0000001_0000200.tif'
        latest.touch()
        older.touch()
        for name, module in MODULES.items():
            with self.subTest(case=name):
                self.assertEqual(module.latest_toa(self.root), latest)
                self.assertIsNone(module.latest_toa(self.root / 'absent'))

    def test_rejects_other_member_malformed_name_and_duplicate_time(self):
        base = self.root / 'time_of_arrival_0000001_0000200.tif'
        base.touch()
        for extra in ('time_of_arrival_0000002_0000300.tif',
                      'time_of_arrival_unknown.tif', 'time_of_arrival_1_200.tif'):
            path = self.root / extra
            path.touch()
            for name, module in MODULES.items():
                with self.subTest(case=name, extra=extra):
                    with self.assertRaises(ValueError):
                        module.latest_toa(self.root)
            path.unlink()

    def test_landscape_mask_preserves_nodata(self):
        raster(self.root / 'landscape.tif', [[101, -9999], [102, 103]], count=8)
        for name, module in MODULES.items():
            with self.subTest(case=name):
                mask, rule = module.domain_mask((2, 2), self.root, TRANSFORM, CRS)
                np.testing.assert_array_equal(mask, [[True, False], [True, True]])
                self.assertEqual(rule, 'valid landscape cells')

    def test_accepts_only_reproduced_model_coordinate_rounding(self):
        # Actual archived Kincade grid: single-precision centers serialized F12.2.
        source = from_origin(498709.598755626, 4305580.90800621, 30, 30)
        serialized = from_origin(498709.59, 4305581.0, 30, 30)
        raster(self.root / 'landscape.tif', np.full((1667, 2), 101),
               count=8, transform=source)
        for name, module in MODULES.items():
            with self.subTest(case=name):
                self.assertEqual(module.serialized_model_grid(source, 1667), serialized)
                mask, _ = module.domain_mask((1667, 2), self.root, serialized, CRS)
                self.assertTrue(mask.all())
                # Even a small arbitrary shift must not pass a broad tolerance.
                shifted = from_origin(498709.64, 4305581.0, 30, 30)
                with self.assertRaises(ValueError):
                    module.domain_mask((1667, 2), self.root, shifted, CRS)

    def test_missing_misaligned_and_invalid_landscape_rejected(self):
        for name, module in MODULES.items():
            with self.subTest(case=name, condition='missing'):
                with self.assertRaises(ValueError):
                    module.domain_mask((2, 2), self.root, TRANSFORM, CRS)
        for options in ({'transform': from_origin(500030, 4200000, 30, 30)},
                        {'crs': 'EPSG:32611'}, {'count': 1}):
            raster(self.root / 'landscape.tif', [[101, 101], [101, 101]],
                   **({'count': 8} | options))
            for name, module in MODULES.items():
                with self.subTest(case=name, condition=options):
                    with self.assertRaises(ValueError):
                        module.domain_mask((2, 2), self.root, TRANSFORM, CRS)
        raster(self.root / 'landscape.tif', [[-9999, -9999]], count=8)
        for name, module in MODULES.items():
            for shape in ((2, 2), (1, 2)):
                with self.subTest(case=name, shape=shape):
                    with self.assertRaises(ValueError):
                        module.domain_mask(shape, self.root, TRANSFORM, CRS)

    def comparison(self):
        raster(self.root / 'landscape.tif', [[101, -9999], [101, 101]], count=8)
        raster(self.root / 'time_of_arrival_0000001_0014400.tif',
               [[3600, -9999], [10800, 14400]])
        raster(self.root / 'observed.tif', [[1, np.nan], [3, 4]], nodata=np.nan)
        run = {'run_id': 'baseline', 'label': 'Synthetic check',
               'configuration': 'baseline', 'directory': self.root}
        source = {'weather': {'offset_from_event_start_h': 0},
                  'simulation': {'planned_stop_h': 4}}
        paths = {'inputs': self.root, 'observation': self.root / 'observed.tif'}
        return run, source, paths

    def test_exact_comparison_and_missing_evidence_status(self):
        run, source, paths = self.comparison()
        for name, module in MODULES.items():
            with self.subTest(case=name):
                result, arrays = module.evaluate_run(run, source, paths)
                self.assertEqual(result['status'], 'CHARACTERIZED')
                self.assertEqual(result['arrival_time_error']['rmse_h'], 0)
                self.assertEqual(result['arrival_time_error']['co_burned_cells'], 3)
                self.assertEqual(result['overlap'][-1]['jaccard'], 1)
                self.assertIsNotNone(arrays)
        (self.root / 'landscape.tif').unlink()
        for name, module in MODULES.items():
            with self.subTest(case=name, condition='missing landscape'):
                result, arrays = module.evaluate_run(run, source, paths)
                self.assertEqual(result['status'], 'NOT EVALUABLE')
                self.assertIsNone(arrays)

    def test_empty_observation_is_not_evaluable(self):
        run, source, paths = self.comparison()
        raster(paths['observation'], [[np.nan, np.nan], [np.nan, np.nan]], nodata=np.nan)
        for name, module in MODULES.items():
            with self.subTest(case=name):
                result, arrays = module.evaluate_run(run, source, paths)
                self.assertEqual(result['status'], 'NOT EVALUABLE')
                self.assertIsNone(arrays)

    def test_ambiguous_result_is_not_evaluable(self):
        run, source, paths = self.comparison()
        (self.root / 'time_of_arrival_1_14400.tif').touch()
        for name, module in MODULES.items():
            with self.subTest(case=name):
                result, arrays = module.evaluate_run(run, source, paths)
                self.assertEqual(result['status'], 'NOT EVALUABLE')
                self.assertIsNone(arrays)


if __name__ == '__main__':
    unittest.main()
