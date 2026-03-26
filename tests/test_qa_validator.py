"""tests/test_qa_validator.py — Unit tests for src/qa_validator.py"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


def _make_script_data(**overrides):
    base = {
        "title": "The Secret to Perfect Pasta Carbonara",
        "script": " ".join(["word"] * 80),   # 80-word script
        "caption_script": "caption text",
        "hook": "Stop scrolling",
        "scenes": ["boiling water", "pasta plating", "sauce close-up"],
        "tags": ["pasta", "recipe", "cooking", "food", "easy", "quick"],
        "description": "A great pasta recipe.",
    }
    base.update(overrides)
    return base


class TestValidateScript(unittest.TestCase):
    def setUp(self):
        from src.qa_validator import validate_script
        self.validate = validate_script

    def test_valid_script_passes(self):
        data = _make_script_data()
        report = self.validate(data)
        self.assertTrue(report.passed)
        self.assertGreater(report.confidence_score, 0.8)

    def test_empty_title_fails(self):
        data = _make_script_data(title="")
        report = self.validate(data)
        self.assertFalse(report.passed)

    def test_forbidden_script_term_fails(self):
        data = _make_script_data(script="This recipe is explicit content " + " ".join(["word"] * 60))
        report = self.validate(data)
        self.assertFalse(report.passed)

    def test_too_short_script_fails(self):
        data = _make_script_data(script="Short.")
        report = self.validate(data)
        self.assertFalse(report.passed)

    def test_no_tags_fails(self):
        data = _make_script_data(tags=[])
        report = self.validate(data)
        self.assertFalse(report.passed)

    def test_long_title_fails(self):
        data = _make_script_data(title="T" * 150)
        report = self.validate(data)
        self.assertFalse(report.passed)


class TestValidateMetadata(unittest.TestCase):
    def setUp(self):
        from src.qa_validator import validate_metadata
        self.validate = validate_metadata

    def test_valid_metadata_passes(self):
        report = self.validate(
            title="Great Pasta Recipe",
            description="A short description.",
            tags=["pasta", "recipe", "cooking", "food", "easy"],
        )
        self.assertTrue(report.passed)

    def test_too_long_description_fails(self):
        report = self.validate(
            title="Title",
            description="D" * 6000,
            tags=["food", "recipe", "easy", "quick", "tasty"],
        )
        self.assertFalse(report.passed)


class TestValidateVideoOutput(unittest.TestCase):
    def setUp(self):
        from src.qa_validator import validate_video_output
        self.validate = validate_video_output

    def test_none_video_path_fails(self):
        report = self.validate(
            video_path=None,
            script_data=_make_script_data(),
            audio_duration=30.0,
        )
        self.assertFalse(report.passed)

    def test_nonexistent_video_file_fails(self):
        report = self.validate(
            video_path=Path("/tmp/nonexistent_video_file_12345.mp4"),
            script_data=_make_script_data(),
            audio_duration=30.0,
        )
        self.assertFalse(report.passed)

    def test_existing_video_file_passes_file_check(self):
        # Create a temp file with enough content
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content " * 1000)
            tmp_path = Path(f.name)
        try:
            report = self.validate(
                video_path=tmp_path,
                script_data=_make_script_data(),
                audio_duration=30.0,
            )
            # File integrity check should pass
            file_check = next(c for c in report.checks if c.name == "file_integrity")
            self.assertTrue(file_check.passed)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_duration_too_short_fails(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"content " * 2000)
            tmp_path = Path(f.name)
        try:
            report = self.validate(
                video_path=tmp_path,
                script_data=_make_script_data(),
                audio_duration=5.0,   # Too short
            )
            dur_check = next(c for c in report.checks if c.name == "duration_bounds")
            self.assertFalse(dur_check.passed)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_duration_too_long_soft_fails(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"content " * 2000)
            tmp_path = Path(f.name)
        try:
            report = self.validate(
                video_path=tmp_path,
                script_data=_make_script_data(),
                audio_duration=90.0,  # Over max
            )
            dur_check = next(c for c in report.checks if c.name == "duration_bounds")
            self.assertFalse(dur_check.passed)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_hard_fail_raises_on_failure(self):
        from src.qa_validator import QAValidationError
        with self.assertRaises(QAValidationError):
            self.validate(
                video_path=None,
                script_data=_make_script_data(),
                audio_duration=30.0,
                hard_fail=True,
            )

    def test_report_format_is_string(self):
        report = self.validate(
            video_path=None,
            script_data=_make_script_data(),
            audio_duration=30.0,
        )
        formatted = report.format_report()
        self.assertIsInstance(formatted, str)
        self.assertIn("QA Validation Report", formatted)


class TestQAReportFormatting(unittest.TestCase):
    def setUp(self):
        from src.qa_validator import QAReport, CheckResult
        self.Report = QAReport
        self.CheckResult = CheckResult

    def test_passed_report_shows_pass(self):
        r = self.Report(
            checks=[self.CheckResult("test", True, 1.0, "OK")],
            confidence_score=1.0,
            passed=True,
        )
        text = r.format_report()
        self.assertIn("PASSED", text)

    def test_failed_report_shows_fail(self):
        r = self.Report(
            checks=[self.CheckResult("test", False, 0.0, "Fail", "Fix it")],
            confidence_score=0.0,
            passed=False,
            issues=["test: Fail"],
            suggestions=["Fix it"],
        )
        text = r.format_report()
        self.assertIn("FAILED", text)
        self.assertIn("Fix it", text)


if __name__ == "__main__":
    unittest.main()
