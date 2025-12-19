import unittest
from pathlib import Path

from tests._test_path import SRC  # noqa: F401

from passportshop.app.temp_paths import TempPaths


class TestTempPaths(unittest.TestCase):
    def test_default_creates_dir_and_preview_path(self):
        tp = TempPaths.default(app_name="passportshop_test_unittest")
        self.assertTrue(tp.base_dir.exists())
        self.assertTrue(tp.base_dir.is_dir())
        self.assertEqual(tp.preview_image.name, "preview.jpg")

    def test_cleanup_removes_preview_file(self):
        tp = TempPaths.default(app_name="passportshop_test_unittest")
        tp.base_dir.mkdir(parents=True, exist_ok=True)
        tp.preview_image.write_bytes(b"test")
        self.assertTrue(tp.preview_image.exists())

        tp.cleanup()
        self.assertFalse(tp.preview_image.exists())

        # Safe to call again
        tp.cleanup()
