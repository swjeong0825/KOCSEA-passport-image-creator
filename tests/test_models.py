import unittest
from dataclasses import FrozenInstanceError, replace

from tests._test_path import SRC  # noqa: F401  (ensures src on path)

from passportshop.core.models import ProcessingParams


class TestProcessingParams(unittest.TestCase):
    def test_defaults(self):
        p = ProcessingParams()
        self.assertEqual(p.size, 600)
        self.assertAlmostEqual(p.head_ratio, 0.62, places=4)
        self.assertTrue(p.remove_background)

    def test_frozen(self):
        p = ProcessingParams()
        with self.assertRaises(FrozenInstanceError):
            p.size = 700  # type: ignore[misc]

    def test_replace(self):
        p = ProcessingParams()
        p2 = replace(p, size=500, remove_background=False)
        self.assertEqual(p2.size, 500)
        self.assertFalse(p2.remove_background)
        # original unchanged
        self.assertEqual(p.size, 600)
