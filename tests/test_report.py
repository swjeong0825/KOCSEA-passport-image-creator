import unittest
from dataclasses import FrozenInstanceError

from tests._test_path import SRC  # noqa: F401

from passportshop.validation.report import RuleResult, ValidationReport


class TestValidationReport(unittest.TestCase):
    def test_report_is_frozen(self):
        rr = RuleResult(rule_id="Size", passed=True, message="ok", metrics={"a": 1})
        rep = ValidationReport(passed=True, results=[rr])

        self.assertTrue(rep.passed)
        self.assertEqual(rep.results[0].rule_id, "Size")

        with self.assertRaises(FrozenInstanceError):
            rep.passed = False  # type: ignore[misc]

        with self.assertRaises(FrozenInstanceError):
            rr.message = "changed"  # type: ignore[misc]
