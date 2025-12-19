import unittest
import importlib
from unittest import skipIf

import numpy as np
from PIL import Image

from tests._test_path import SRC  # noqa: F401


def _can_import_passport_photo() -> bool:
    try:
        import passport_photo  # noqa: F401
        return True
    except Exception:
        return False


@skipIf(not _can_import_passport_photo(), "passport_photo.py dependencies (cv2/mediapipe) not available")
class TestPassportPhotoHelpers(unittest.TestCase):
    def setUp(self):
        import passport_photo
        self.pp = passport_photo

    def test_pil_bgr_roundtrip(self):
        img = Image.fromarray(np.array([[[10, 20, 30],[40,50,60]],[[70,80,90],[100,110,120]]], dtype=np.uint8), "RGB")
        bgr = self.pp._pil_to_bgr_np(img)
        back = self.pp._bgr_np_to_pil(bgr)
        arr1 = np.asarray(img)
        arr2 = np.asarray(back)
        self.assertEqual(arr1.shape, arr2.shape)
        self.assertTrue(np.allclose(arr1, arr2, atol=1))

    def test_resize_bgr_scale(self):
        bgr = np.zeros((10, 20, 3), dtype=np.uint8)
        out = self.pp._resize_bgr(bgr, scale=0.5)
        self.assertEqual(out.shape[0], 5)
        self.assertEqual(out.shape[1], 10)

    def test_crop_square_with_padding(self):
        # 4x4 image with distinct center pixel
        bgr = np.zeros((4, 4, 3), dtype=np.uint8)
        bgr[1, 1] = [0, 0, 255]  # red in BGR (blue=0, green=0, red=255)
        out = self.pp._crop_square_with_padding(bgr, center_xy=(0.0, 0.0), size=4, pad_color_bgr=(255,255,255))
        self.assertEqual(out.shape, (4, 4, 3))
        # Top-left should be padding white because crop goes out of bounds
        self.assertTrue((out[0, 0] == np.array([255,255,255])).all())
