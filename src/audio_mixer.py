"""
audio_mixer.py — Audio mixing utilities for the Food Making Videos Factory.

Provides helpers to layer narration (TTS audio) over background music with
configurable volume levels, fade-in/fade-out effects, and duration
synchronisation.  Uses pydub for audio manipulation.
"""

import logging
import math
import tempfile
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def mix_narration_with_music(
    narration_path: Path,
    music_path: Path,
    output_path: Path | None = None,
    music_volume: float = 0.08,
    fade_duration: float = 1.0,
) -> Path:
    """Overlay background music under TTS narration and export the mixed audio.

    The music track is looped or trimmed to exactly match the narration
    duration, then mixed at ``music_volume`` relative amplitude underneath
    the full-scale narration.  Fade-in and fade-out are applied to the
    music to avoid abrupt starts and stops.

    Args:
        narration_path: Path to the TTS narration MP3 file.
        music_path:     Path to the background music MP3 file.
        output_path:    Destination path for the mixed audio.  A temporary
                        file is created when ``None``.
        music_volume:   Background music volume as a fraction of full scale
                        (0.0 = silent, 1.0 = same level as narration).
        fade_duration:  Music fade-in and fade-out duration in seconds.

    Returns:
        Path to the mixed MP3 audio file.

    Raises:
        RuntimeError: If pydub is not installed.
    """
    try:
        from pydub import AudioSegment  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError("pydub is required for audio mixing") from exc

    narration = AudioSegment.from_file(str(narration_path))
    music = AudioSegment.from_file(str(music_path))

    narration_ms = len(narration)
    fade_ms = int(fade_duration * 1000)

    # Loop the music track until it covers the full narration duration
    if len(music) < narration_ms:
        loops_needed = (narration_ms // len(music)) + 2
        music = music * loops_needed
    music = music[:narration_ms]

    # Apply fade-in / fade-out so music doesn't cut in or out abruptly.
    # Fade-out is capped at 2× the fade-in duration but never exceeds 25%
    # of narration length so it finishes well before the video ends.
    if fade_ms > 0:
        music = music.fade_in(fade_ms).fade_out(min(fade_ms * 2, narration_ms // 4))

    # Convert linear volume ratio to dB gain and apply to music track
    clamped_vol = max(1e-6, min(float(music_volume), 1.0))
    volume_db = 20.0 * math.log10(clamped_vol)
    music = music + volume_db  # pydub + operator adjusts gain in dBFS

    # Overlay music under narration (narration stays at full level)
    mixed = narration.overlay(music)

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = Path(tmp.name)
        tmp.close()

    mixed.export(str(output_path), format="mp3", bitrate="320k")
    logger.info("Mixed narration + music written to: %s", output_path)
    return output_path


def get_music_volume() -> float:
    """Return the configured background music volume (0.0–1.0).

    Reads ``MUSIC_VOLUME`` from config, falling back to ``BG_MUSIC_VOLUME``
    for backward compatibility.
    """
    return float(
        getattr(config, "MUSIC_VOLUME", getattr(config, "BG_MUSIC_VOLUME", 0.08))
    )


def get_fade_duration() -> float:
    """Return the configured music fade-in/fade-out duration in seconds."""
    return float(getattr(config, "MUSIC_FADE_DURATION", 1.0))
