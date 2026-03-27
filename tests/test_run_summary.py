"""tests/test_run_summary.py — Unit tests for src/run_summary.py"""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path


class TestStartRun(unittest.TestCase):
    def setUp(self):
        from src.run_summary import start_run
        self.start = start_run

    def test_returns_run_summary(self):
        from src.run_summary import RunSummary
        s = self.start()
        self.assertIsInstance(s, RunSummary)

    def test_status_in_progress(self):
        s = self.start()
        self.assertEqual(s.status, "in_progress")

    def test_start_time_set(self):
        s = self.start()
        self.assertGreater(s.start_time, 0)

    def test_run_id_non_empty(self):
        s = self.start()
        self.assertTrue(s.run_id)


class TestFinishRun(unittest.TestCase):
    def setUp(self):
        from src.run_summary import start_run, finish_run
        self.start = start_run
        self.finish = finish_run

    def test_status_updated(self):
        s = self.start()
        result = self.finish(s, status="success", topic="pasta", title="Pasta Video")
        self.assertEqual(result.status, "success")

    def test_elapsed_seconds_computed(self):
        s = self.start()
        time.sleep(0.05)
        result = self.finish(s, status="success")
        self.assertGreater(result.elapsed_seconds, 0)

    def test_fields_populated(self):
        s = self.start()
        result = self.finish(
            s, status="success", topic="pasta", title="Pasta",
            style_pack="golden_hour", cta_strategy="soft", cta_variant="A",
            trend_score=0.75, virality_score=80.0, qa_confidence=0.95,
            qa_passed=True, template_used="enhanced_ai", music_source="pixabay",
            video_path="/tmp/video.mp4", upload_url="https://yt.be/abc",
            upload_id="abc123",
        )
        self.assertEqual(result.topic, "pasta")
        self.assertEqual(result.title, "Pasta")
        self.assertEqual(result.style_pack, "golden_hour")
        self.assertAlmostEqual(result.trend_score, 0.75)
        self.assertEqual(result.upload_id, "abc123")

    def test_dry_run_status(self):
        s = self.start()
        result = self.finish(s, status="dry_run")
        self.assertEqual(result.status, "dry_run")


class TestRunSummaryHelpers(unittest.TestCase):
    def setUp(self):
        from src.run_summary import start_run
        self.s = start_run()

    def test_add_error_appends(self):
        self.s.add_error("Something went wrong")
        self.assertIn("Something went wrong", self.s.errors)

    def test_add_warning_appends(self):
        self.s.add_warning("Minor issue")
        self.assertIn("Minor issue", self.s.warnings)

    def test_record_stage_updates_timings(self):
        self.s.record_stage("tts", 2.5)
        self.assertAlmostEqual(self.s.stage_timings["tts"], 2.5)

    def test_to_dict_is_serializable(self):
        self.s.record_stage("tts", 1.0)
        d = self.s.to_dict()
        # Should be JSON serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["status"], "in_progress")


class TestFormatRunReport(unittest.TestCase):
    def setUp(self):
        from src.run_summary import start_run, finish_run, format_run_report
        self.start = start_run
        self.finish = finish_run
        self.format = format_run_report

    def test_success_report_has_checkmark(self):
        s = self.start()
        s = self.finish(s, status="success", topic="pasta", title="Title")
        report = self.format(s)
        self.assertIn("✅", report)
        self.assertIn("SUCCESS", report)

    def test_failed_report_has_cross(self):
        s = self.start()
        s.add_error("Critical failure")
        s = self.finish(s, status="failed")
        report = self.format(s)
        self.assertIn("❌", report)

    def test_dry_run_report_has_lightning(self):
        s = self.start()
        s = self.finish(s, status="dry_run")
        report = self.format(s)
        self.assertIn("⚡", report)


class TestSaveAuditLog(unittest.TestCase):
    def setUp(self):
        from src.run_summary import start_run, finish_run, save_audit_log
        self.start = start_run
        self.finish = finish_run
        self.save = save_audit_log

    def test_audit_log_written(self):
        s = self.start()
        s = self.finish(s, status="success", topic="pasta")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.save(s, output_dir=tmpdir)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["topic"], "pasta")
            self.assertEqual(data["status"], "success")

    def test_audit_log_filename_contains_run_id(self):
        s = self.start()
        s = self.finish(s, status="success")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.save(s, output_dir=tmpdir)
            self.assertIn(s.run_id, path.name)


class TestStageTimer(unittest.TestCase):
    def setUp(self):
        from src.run_summary import start_run, stage_timer
        self.start = start_run
        self.timer = stage_timer

    def test_stage_timer_records_elapsed(self):
        s = self.start()
        with self.timer(s, "my_stage"):
            time.sleep(0.05)
        self.assertIn("my_stage", s.stage_timings)
        self.assertGreater(s.stage_timings["my_stage"], 0)


if __name__ == "__main__":
    unittest.main()
