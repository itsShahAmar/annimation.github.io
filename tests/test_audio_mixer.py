"""
tests/test_audio_mixer.py — Unit tests for src/audio_mixer.py

Tests audio mixing helpers with fully mocked pydub calls so no real audio
files or processing are required.

Run with: python -m pytest tests/ -v
"""

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Stub heavy optional imports not needed for audio_mixer tests
for _mod in (
    "edge_tts",
    "moviepy", "moviepy.editor",
    "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "mutagen", "mutagen.mp3",
    "googleapiclient", "googleapiclient.discovery",
    "httpx",
):
    sys.modules.setdefault(_mod, MagicMock())


class TestGetMusicVolume(unittest.TestCase):
    """Tests for audio_mixer.get_music_volume()."""

    def setUp(self):
        import src.audio_mixer as am
        self.am = am

    def test_returns_configured_music_volume(self):
        with patch.object(self.am.config, "MUSIC_VOLUME", 0.15):
            self.assertAlmostEqual(self.am.get_music_volume(), 0.15)

    def test_returns_bg_music_volume_when_music_volume_matches(self):
        """BG_MUSIC_VOLUME is the fallback; changing it affects the result."""
        with patch.object(self.am.config, "MUSIC_VOLUME", 0.12), \
             patch.object(self.am.config, "BG_MUSIC_VOLUME", 0.12):
            vol = self.am.get_music_volume()
        self.assertAlmostEqual(vol, 0.12)

    def test_returns_float(self):
        vol = self.am.get_music_volume()
        self.assertIsInstance(vol, float)

    def test_volume_is_positive(self):
        vol = self.am.get_music_volume()
        self.assertGreater(vol, 0.0)

    def test_volume_does_not_exceed_one(self):
        with patch.object(self.am.config, "BG_MUSIC_VOLUME", 0.5):
            vol = self.am.get_music_volume()
        self.assertLessEqual(vol, 1.0)


class TestGetFadeDuration(unittest.TestCase):
    """Tests for audio_mixer.get_fade_duration()."""

    def setUp(self):
        import src.audio_mixer as am
        self.am = am

    def test_returns_configured_fade_duration(self):
        with patch.object(self.am.config, "MUSIC_FADE_DURATION", 2.5):
            self.assertAlmostEqual(self.am.get_fade_duration(), 2.5)

    def test_returns_float(self):
        duration = self.am.get_fade_duration()
        self.assertIsInstance(duration, float)

    def test_returns_positive_value(self):
        duration = self.am.get_fade_duration()
        self.assertGreater(duration, 0)


class TestMixNarrationWithMusic(unittest.TestCase):
    """Tests for audio_mixer.mix_narration_with_music()."""

    def setUp(self):
        import src.audio_mixer as am
        self.am = am

    def _make_audio_segment_mock(self, duration_ms: int) -> MagicMock:
        """Return a MagicMock that behaves like a pydub AudioSegment."""
        seg = MagicMock()
        seg.__len__ = MagicMock(return_value=duration_ms)
        seg.__mul__ = MagicMock(return_value=seg)
        seg.__getitem__ = MagicMock(return_value=seg)
        seg.__add__ = MagicMock(return_value=seg)
        seg.fade_in = MagicMock(return_value=seg)
        seg.fade_out = MagicMock(return_value=seg)
        seg.overlay = MagicMock(return_value=seg)
        seg.export = MagicMock()
        return seg

    def test_returns_output_path_when_provided(self):
        narration = self._make_audio_segment_mock(30_000)
        music = self._make_audio_segment_mock(60_000)
        mixed = self._make_audio_segment_mock(30_000)
        narration.overlay.return_value = mixed

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file = MagicMock(side_effect=[narration, music])

        with patch.dict(sys.modules, {"pydub": mock_pydub}):
            result = self.am.mix_narration_with_music(
                Path("/tmp/narration.mp3"),
                Path("/tmp/music.mp3"),
                output_path=Path("/tmp/output.mp3"),
                music_volume=0.1,
                fade_duration=1.0,
            )

        self.assertEqual(result, Path("/tmp/output.mp3"))
        mixed.export.assert_called_once_with(
            "/tmp/output.mp3", format="mp3", bitrate="320k"
        )

    def test_creates_temp_file_when_output_path_is_none(self):
        narration = self._make_audio_segment_mock(30_000)
        music = self._make_audio_segment_mock(60_000)
        mixed = self._make_audio_segment_mock(30_000)
        narration.overlay.return_value = mixed

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file = MagicMock(side_effect=[narration, music])

        with patch.dict(sys.modules, {"pydub": mock_pydub}):
            result = self.am.mix_narration_with_music(
                Path("/tmp/narration.mp3"),
                Path("/tmp/music.mp3"),
                output_path=None,
                music_volume=0.1,
                fade_duration=1.0,
            )

        self.assertIsInstance(result, Path)
        mixed.export.assert_called_once()

    def test_music_shorter_than_narration_is_looped(self):
        """Music that is shorter than narration must be looped."""
        narration = self._make_audio_segment_mock(60_000)  # 60 s
        music = self._make_audio_segment_mock(10_000)       # 10 s — needs looping

        looped_music = self._make_audio_segment_mock(70_000)
        music.__mul__ = MagicMock(return_value=looped_music)
        looped_music.__getitem__ = MagicMock(return_value=looped_music)
        looped_music.__add__ = MagicMock(return_value=looped_music)
        looped_music.fade_in = MagicMock(return_value=looped_music)
        looped_music.fade_out = MagicMock(return_value=looped_music)
        looped_music.overlay = MagicMock(return_value=looped_music)
        looped_music.export = MagicMock()
        narration.overlay.return_value = looped_music

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file = MagicMock(side_effect=[narration, music])

        with patch.dict(sys.modules, {"pydub": mock_pydub}):
            self.am.mix_narration_with_music(
                Path("/tmp/narration.mp3"),
                Path("/tmp/music.mp3"),
                output_path=Path("/tmp/out.mp3"),
                music_volume=0.1,
                fade_duration=1.0,
            )

        # Music was shorter, so __mul__ (looping) should have been called
        music.__mul__.assert_called_once()

    def test_fade_applied_to_music(self):
        """Fade-in and fade-out are applied to background music."""
        narration = self._make_audio_segment_mock(30_000)
        music = self._make_audio_segment_mock(60_000)
        mixed = self._make_audio_segment_mock(30_000)
        narration.overlay.return_value = mixed

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file = MagicMock(side_effect=[narration, music])

        with patch.dict(sys.modules, {"pydub": mock_pydub}):
            self.am.mix_narration_with_music(
                Path("/tmp/narration.mp3"),
                Path("/tmp/music.mp3"),
                output_path=Path("/tmp/out.mp3"),
                music_volume=0.1,
                fade_duration=1.0,
            )

        music.fade_in.assert_called_once_with(1000)

    def test_volume_applied_as_db_gain(self):
        """Volume ratio is converted to dB and applied via the + operator."""
        narration = self._make_audio_segment_mock(30_000)
        music = self._make_audio_segment_mock(60_000)
        mixed = self._make_audio_segment_mock(30_000)
        narration.overlay.return_value = mixed

        mock_pydub = MagicMock()
        mock_pydub.AudioSegment.from_file = MagicMock(side_effect=[narration, music])

        music_volume = 0.1
        expected_db = 20.0 * math.log10(music_volume)

        with patch.dict(sys.modules, {"pydub": mock_pydub}):
            self.am.mix_narration_with_music(
                Path("/tmp/narration.mp3"),
                Path("/tmp/music.mp3"),
                output_path=Path("/tmp/out.mp3"),
                music_volume=music_volume,
                fade_duration=1.0,
            )

        # Verify that music.__add__ was called with the expected dB value
        add_call_args = music.__add__.call_args
        self.assertIsNotNone(add_call_args)
        applied_db = add_call_args[0][0]
        self.assertAlmostEqual(applied_db, expected_db, places=5)

    def test_raises_runtime_error_without_pydub(self):
        """If pydub is not importable, RuntimeError is raised."""
        with patch.dict(sys.modules, {"pydub": None}):
            with self.assertRaises((RuntimeError, ImportError)):
                self.am.mix_narration_with_music(
                    Path("/tmp/n.mp3"), Path("/tmp/m.mp3")
                )


if __name__ == "__main__":
    unittest.main()
