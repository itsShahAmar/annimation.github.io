"""tests/test_video_creator.py — Focused tests for src/video_creator.py helpers."""

import sys
import unittest
from unittest.mock import MagicMock


# Stub heavy optional imports not needed for helper-level tests.
for _mod in (
    "edge_tts",
    "moviepy", "moviepy.editor",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "mutagen", "mutagen.mp3",
    "googleapiclient", "googleapiclient.discovery",
    "httpx",
):
    sys.modules.setdefault(_mod, MagicMock())


class TestFitBgAudioToDuration(unittest.TestCase):
    """Tests for src.video_creator._fit_bg_audio_to_duration()."""

    def setUp(self):
        import src.video_creator as vc
        self.vc = vc

    def test_returns_same_clip_when_duration_matches(self):
        clip = MagicMock()
        clip.duration = 20.0
        afx = MagicMock()

        result = self.vc._fit_bg_audio_to_duration(clip, 20.0, afx)

        self.assertIs(result, clip)
        clip.fx.assert_not_called()
        clip.subclip.assert_not_called()

    def test_loops_when_background_music_is_shorter(self):
        clip = MagicMock()
        clip.duration = 10.0
        looped = MagicMock()
        clip.fx.return_value = looped
        afx = MagicMock()
        afx.audio_loop = object()

        result = self.vc._fit_bg_audio_to_duration(clip, 20.0, afx)

        self.assertIs(result, looped)
        clip.fx.assert_called_once_with(afx.audio_loop, duration=20.0)
        clip.subclip.assert_not_called()

    def test_trims_when_background_music_is_longer(self):
        clip = MagicMock()
        clip.duration = 30.0
        trimmed = MagicMock()
        clip.subclip.return_value = trimmed
        afx = MagicMock()

        result = self.vc._fit_bg_audio_to_duration(clip, 20.0, afx)

        self.assertIs(result, trimmed)
        clip.subclip.assert_called_once_with(0, 20.0)
        clip.fx.assert_not_called()

    def test_uses_set_duration_for_invalid_source_duration(self):
        clip = MagicMock()
        clip.duration = 0.0
        duration_adjusted = MagicMock()
        clip.set_duration.return_value = duration_adjusted
        afx = MagicMock()

        result = self.vc._fit_bg_audio_to_duration(clip, 20.0, afx)

        self.assertIs(result, duration_adjusted)
        clip.set_duration.assert_called_once_with(20.0)
        clip.fx.assert_not_called()
        clip.subclip.assert_not_called()


class TestResolveTargetDuration(unittest.TestCase):
    """Tests for src.video_creator._resolve_target_duration()."""

    def setUp(self):
        import src.video_creator as vc
        self.vc = vc

    def test_uses_requested_audio_duration_when_positive(self):
        result = self.vc._resolve_target_duration(30.0, 55.0, None)
        self.assertEqual(result, 30.0)

    def test_uses_default_when_requested_duration_invalid(self):
        result = self.vc._resolve_target_duration(0.0, 55.0, None)
        self.assertEqual(result, 55.0)

    def test_prefers_measured_tts_duration_when_longer(self):
        result = self.vc._resolve_target_duration(30.0, 55.0, 62.5)
        self.assertEqual(result, 62.5)
