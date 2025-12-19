import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image

from tests._test_path import SRC  # noqa: F401

from passportshop.core.models import ProcessingParams
from passportshop.validation import validator as v


@dataclass
class LM:
    x: float
    y: float


def _find(report, rule_id: str):
    for r in report.results:
        if r.rule_id == rule_id:
            return r
    raise AssertionError(f"Rule not found: {rule_id}")


class TestValidator(unittest.TestCase):
    def test_validator_rules_present_and_expected_pass_fail_mix(self):
        # A mid-gray image => lighting should pass, background whiteness should fail.
        arr = np.full((600, 600, 3), 160, dtype=np.uint8)
        img = Image.fromarray(arr, "RGB")
        params = ProcessingParams()

        def stub_landmarks(_img):
            nose = LM(300, 250)
            forehead = LM(300, 100)
            chin = LM(300, 430)
            return (nose, forehead, chin)

        with patch.object(v, "_detect_face_landmarks", new=stub_landmarks):
            report = v.validate_passport_photo(img, params)

        self.assertEqual(len(report.results), 5)
        self.assertFalse(report.passed)  # background expected to fail

        self.assertTrue(_find(report, "Size").passed)
        self.assertTrue(_find(report, "Head ratio").passed)
        self.assertTrue(_find(report, "Centering").passed)

        self.assertFalse(_find(report, "Background whiteness").passed)
        # self.assertTrue(_find(report, "Lighting").passed)

    def test_white_image_background_pass_lighting_fail(self):
        # Pure white => background passes, lighting likely fails due to bright clipping
        arr = np.full((600, 600, 3), 255, dtype=np.uint8)
        img = Image.fromarray(arr, "RGB")
        params = ProcessingParams()

        def stub_landmarks(_img):
            nose = LM(300, 250)
            forehead = LM(300, 100)
            chin = LM(300, 430)
            return (nose, forehead, chin)

        with patch.object(v, "_detect_face_landmarks", new=stub_landmarks):
            report = v.validate_passport_photo(img, params)

        self.assertTrue(_find(report, "Background whiteness").passed)
        self.assertFalse(_find(report, "Lighting").passed)

    def test_format_report_text(self):
        arr = np.full((600, 600, 3), 160, dtype=np.uint8)
        img = Image.fromarray(arr, "RGB")
        params = ProcessingParams()

        with patch.object(v, "_detect_face_landmarks", new=lambda _img: (LM(300,250), LM(300,100), LM(300,430))):
            report = v.validate_passport_photo(img, params)

        txt = v.format_report_text(report)
        self.assertIn("PassportShop Validation Report", txt)
        self.assertIn("Overall:", txt)
        self.assertIn("Size:", txt)
