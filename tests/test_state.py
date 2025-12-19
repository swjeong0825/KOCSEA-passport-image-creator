import unittest

from tests._test_path import SRC  # noqa: F401

from passportshop.app.state import AppState
from passportshop.core.models import ProcessingParams


class TestAppState(unittest.TestCase):
    def test_reset_clears_fields_and_restores_defaults(self):
        s = AppState()
        s.input_path = "/tmp/x.jpg"
        s.original_pil = object()  # sentinel; PIL not needed
        s.processed_pil = object()
        s.processed_temp_path = "/tmp/preview.jpg"
        s.validation_report = object()  # type: ignore[assignment]
        s.params = ProcessingParams(size=500, head_ratio=0.6, remove_background=False)

        s.reset()

        self.assertIsNone(s.input_path)
        self.assertIsNone(s.original_pil)
        self.assertIsNone(s.processed_pil)
        self.assertIsNone(s.processed_temp_path)
        self.assertIsNone(s.validation_report)
        self.assertEqual(s.params, ProcessingParams())
