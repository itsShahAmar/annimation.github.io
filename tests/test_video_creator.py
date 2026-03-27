"""tests/test_video_creator.py — Focused tests for src/video_creator.py helpers."""

import sys
import unittest
from pathlib import Path
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


class TestFitBaseVideoDuration(unittest.TestCase):
    """Tests for src.video_creator._fit_base_video_duration()."""

    def setUp(self):
        import src.video_creator as vc
        self.vc = vc

    def test_freezes_when_base_is_shorter_than_target(self):
        base = MagicMock()
        base.duration = 8.0
        frozen = MagicMock()
        base.fx.return_value = frozen
        vfx = MagicMock()
        vfx.freeze = object()

        result = self.vc._fit_base_video_duration(base, 10.0, vfx)

        self.assertIs(result, frozen)
        base.fx.assert_called_once_with(vfx.freeze, t=7.95, freeze_duration=2.0)
        base.subclip.assert_not_called()

    def test_trims_when_base_is_longer_than_target(self):
        base = MagicMock()
        base.duration = 12.0
        trimmed = MagicMock()
        base.subclip.return_value = trimmed
        vfx = MagicMock()

        result = self.vc._fit_base_video_duration(base, 10.0, vfx)

        self.assertIs(result, trimmed)
        base.subclip.assert_called_once_with(0, 10.0)
        base.fx.assert_not_called()

    def test_returns_same_base_when_duration_matches_target(self):
        base = MagicMock()
        base.duration = 10.0
        vfx = MagicMock()

        result = self.vc._fit_base_video_duration(base, 10.0, vfx)

        self.assertIs(result, base)
        base.fx.assert_not_called()
        base.subclip.assert_not_called()


class TestProbeVideoDuration(unittest.TestCase):
    """Tests for src.video_creator._probe_video_duration()."""

    def setUp(self):
        import src.video_creator as vc
        self.vc = vc

    def test_returns_float_when_ffprobe_succeeds(self):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.stdout = "5.10\n"
        with patch("subprocess.run", return_value=mock_result):
            result = self.vc._probe_video_duration(Path("/tmp/fake.mp4"))
        self.assertAlmostEqual(result, 5.10)

    def test_returns_none_when_ffprobe_output_is_na(self):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.stdout = "N/A\n"
        with patch("subprocess.run", return_value=mock_result):
            result = self.vc._probe_video_duration(Path("/tmp/fake.mp4"))
        self.assertIsNone(result)

    def test_returns_none_when_ffprobe_output_is_empty(self):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = self.vc._probe_video_duration(Path("/tmp/fake.mp4"))
        self.assertIsNone(result)

    def test_returns_none_when_ffprobe_raises(self):
        from unittest.mock import patch
        with patch("subprocess.run", side_effect=FileNotFoundError("ffprobe not found")):
            result = self.vc._probe_video_duration(Path("/tmp/fake.mp4"))
        self.assertIsNone(result)


class TestLoadSafeVideoClip(unittest.TestCase):
    """Tests for src.video_creator._load_safe_video_clip()."""

    def setUp(self):
        import src.video_creator as vc
        self.vc = vc

    def _make_clip(self, duration: float) -> MagicMock:
        clip = MagicMock()
        clip.duration = duration
        trimmed = MagicMock()
        trimmed.duration = duration - self.vc._CLIP_TAIL_TRIM_S
        clip.subclip.return_value = trimmed
        return clip

    def test_trims_tail_when_ffprobe_matches_moviepy_duration(self):
        """When ffprobe agrees with MoviePy, a _CLIP_TAIL_TRIM_S tail is removed."""
        from unittest.mock import patch
        clip = self._make_clip(5.10)
        VideoFileClip = MagicMock(return_value=clip)

        with patch.object(self.vc, "_probe_video_duration", return_value=5.10):
            result = self.vc._load_safe_video_clip(VideoFileClip, Path("/tmp/fake.mp4"))

        clip.subclip.assert_called_once_with(0, 5.10 - self.vc._CLIP_TAIL_TRIM_S)

    def test_uses_ffprobe_duration_when_lower_than_moviepy(self):
        """When ffprobe reports a shorter duration, that is used as the safe end."""
        from unittest.mock import patch
        clip = self._make_clip(5.10)
        VideoFileClip = MagicMock(return_value=clip)

        with patch.object(self.vc, "_probe_video_duration", return_value=5.07):
            result = self.vc._load_safe_video_clip(VideoFileClip, Path("/tmp/fake.mp4"))

        clip.subclip.assert_called_once_with(0, 5.07 - self.vc._CLIP_TAIL_TRIM_S)

    def test_falls_back_to_moviepy_duration_when_ffprobe_unavailable(self):
        """When ffprobe is unavailable, the MoviePy duration minus the tail buffer is used."""
        from unittest.mock import patch
        clip = self._make_clip(5.10)
        VideoFileClip = MagicMock(return_value=clip)

        with patch.object(self.vc, "_probe_video_duration", return_value=None):
            result = self.vc._load_safe_video_clip(VideoFileClip, Path("/tmp/fake.mp4"))

        clip.subclip.assert_called_once_with(0, 5.10 - self.vc._CLIP_TAIL_TRIM_S)

    def test_does_not_trim_when_safe_end_exceeds_duration(self):
        """No subclip call when the clip is too short to trim."""
        from unittest.mock import patch
        clip = MagicMock()
        clip.duration = 0.05  # shorter than _CLIP_TAIL_TRIM_S (0.1)
        VideoFileClip = MagicMock(return_value=clip)

        with patch.object(self.vc, "_probe_video_duration", return_value=None):
            result = self.vc._load_safe_video_clip(VideoFileClip, Path("/tmp/fake.mp4"))

        clip.subclip.assert_not_called()
        self.assertIs(result, clip)

