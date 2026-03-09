"""
tts.py — Text-to-speech generation for the Funny Animation Shorts Factory.

Converts narration script text to an MP3 audio file and returns the file
path together with the audio duration in seconds.  Completely free — no
API keys required.

Primary engine: edge-tts (Microsoft Edge neural voices — natural, high quality)
Fallback engine: gTTS (Google's free TTS — works offline)

Comedy optimisation features:
- Comedy-optimised voice selection: prefers expressive, energetic voices
- Text sanitisation to strip any markup before synthesis
- Post-generation loudness normalization via pydub
- Rotating voice selection: a different neural voice is chosen each run
  using a time-based seed so the channel sounds varied and fresh.
- Slightly faster TTS rate (+5%) for comedy energy and pacing
"""

import asyncio
import logging
import random
import re
import tempfile
import time
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Comedy-optimised voice pool — energetic, expressive neural voices that
# deliver comedy scripts with the right energy.  Ordered by energy level
# (most expressive first) within each gender group.
# ---------------------------------------------------------------------------
_VOICE_POOL: list[dict] = [
    # --- High-energy / expressive female voices (great for comedy delivery) ---
    {"name": "en-US-SaraNeural",         "gender": "female", "style": "cheerful",  "energy": "high"},
    {"name": "en-US-AriaNeural",         "gender": "female", "style": "chat",      "energy": "high"},
    {"name": "en-US-JennyNeural",        "gender": "female", "style": "newscast",  "energy": "high"},
    {"name": "en-US-MichelleNeural",     "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-US-CoraNeural",         "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-US-ElizabethNeural",    "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-GB-SoniaNeural",        "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-GB-LibbyNeural",        "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-AU-NatashaNeural",      "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-CA-ClaraNeural",        "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-IN-NeerjaNeural",       "gender": "female", "style": "natural",   "energy": "medium"},
    {"name": "en-IE-EmilyNeural",        "gender": "female", "style": "natural",   "energy": "medium"},
    # --- High-energy / expressive male voices (great for comedy delivery) ---
    {"name": "en-US-TonyNeural",         "gender": "male",   "style": "natural",   "energy": "high"},
    {"name": "en-US-DavisNeural",        "gender": "male",   "style": "chat",      "energy": "high"},
    {"name": "en-US-JasonNeural",        "gender": "male",   "style": "natural",   "energy": "high"},
    {"name": "en-US-GuyNeural",          "gender": "male",   "style": "newscast",  "energy": "medium"},
    {"name": "en-US-ChristopherNeural",  "gender": "male",   "style": "newscast",  "energy": "medium"},
    {"name": "en-US-EricNeural",         "gender": "male",   "style": "natural",   "energy": "medium"},
    {"name": "en-US-BrandonNeural",      "gender": "male",   "style": "natural",   "energy": "medium"},
    {"name": "en-GB-RyanNeural",         "gender": "male",   "style": "natural",   "energy": "medium"},
    {"name": "en-GB-ThomasNeural",       "gender": "male",   "style": "natural",   "energy": "medium"},
    {"name": "en-AU-WilliamNeural",      "gender": "male",   "style": "natural",   "energy": "medium"},
    {"name": "en-CA-LiamNeural",         "gender": "male",   "style": "natural",   "energy": "medium"},
    {"name": "en-IN-PrabhatNeural",      "gender": "male",   "style": "natural",   "energy": "medium"},
]

# High-energy voices get priority weighting in comedy selection
_HIGH_ENERGY_VOICES = [v["name"] for v in _VOICE_POOL if v.get("energy") == "high"]
_ALL_VOICES = [v["name"] for v in _VOICE_POOL]


def pick_voice() -> str:
    """Return a comedy-optimised voice name from ``_VOICE_POOL``.

    Comedy selection strategy:
    - Uses a time-based hour index to rotate through voices each run
    - High-energy / expressive voices (marked ``energy: high``) are preferred
      and selected 70% of the time; the rest of the pool fills the remaining 30%
    - Alternates naturally between male and female voices

    Returns:
        The ``en-*-*Neural`` voice name string accepted by edge-tts.
    """
    if not getattr(config, "TTS_VOICE_ROTATE", True):
        return config.TTS_VOICE

    hour_index = int(time.time() // 3600)
    # 70% chance: pick from high-energy voices for better comedy delivery
    rng = random.Random(hour_index)  # noqa: S311
    if _HIGH_ENERGY_VOICES and rng.random() < 0.70:
        voice_name = _HIGH_ENERGY_VOICES[hour_index % len(_HIGH_ENERGY_VOICES)]
    else:
        voice_name = _ALL_VOICES[hour_index % len(_ALL_VOICES)]

    voice_entry = next((v for v in _VOICE_POOL if v["name"] == voice_name), _VOICE_POOL[0])
    logger.info(
        "Comedy voice selected: %s (%s, %s, energy=%s)",
        voice_entry["name"], voice_entry["gender"], voice_entry["style"], voice_entry.get("energy", "medium"),
    )
    return voice_entry["name"]



def _clean_text_for_tts(text: str) -> str:
    """Sanitise *text* so it is safe and natural for TTS engines.

    Strips any residual markup, normalises whitespace, and removes characters
    that TTS engines may try to spell out (e.g. ``<``, ``>``, ``&``).
    Also cleans up emoji characters that don't vocalise well.
    """
    # Remove any XML/HTML-like tags that may have leaked in
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Remove HTML entities
    cleaned = re.sub(r"&[a-zA-Z]+;", " ", cleaned)
    cleaned = re.sub(r"&#x?[0-9a-fA-F]+;", " ", cleaned)
    # Remove stray angle brackets; convert literal ampersands to "and"
    cleaned = cleaned.replace("<", " ").replace(">", " ").replace("&", " and ")
    # Remove emoji characters (they can cause TTS issues)
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", " ", cleaned)
    # Collapse multiple spaces into one
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _get_audio_duration(audio_path: Path) -> float:
    """Return the duration (in seconds) of an audio file.

    Tries ``mutagen`` first, then ``pydub`` as a fallback.
    Returns 0.0 if neither library is available.
    """
    try:
        from mutagen.mp3 import MP3  # type: ignore[import]

        audio = MP3(str(audio_path))
        duration: float = audio.info.length
        logger.debug("Audio duration via mutagen: %.2f s", duration)
        return duration
    except Exception:  # noqa: BLE001
        pass

    try:
        from pydub import AudioSegment  # type: ignore[import]

        segment = AudioSegment.from_file(str(audio_path))
        duration = len(segment) / 1000.0
        logger.debug("Audio duration via pydub: %.2f s", duration)
        return duration
    except Exception:  # noqa: BLE001
        pass

    logger.warning("Could not determine audio duration; defaulting to 0.0 s")
    return 0.0


def _normalize_audio(audio_path: Path) -> None:
    """Normalize the loudness of an MP3 file in-place using pydub.

    Brings the peak amplitude to 0 dBFS so the narration always plays
    at a consistent, clear volume regardless of the TTS engine output level.
    """
    try:
        from pydub import AudioSegment  # type: ignore[import]
        from pydub.effects import normalize  # type: ignore[import]

        segment = AudioSegment.from_file(str(audio_path))
        normalized = normalize(segment)
        normalized.export(str(audio_path), format="mp3", bitrate=config.AUDIO_BITRATE)
        logger.debug("Audio normalization applied to '%s'", audio_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Audio normalization skipped: %s", exc)


async def _generate_edge_tts(text: str, output_path: str, voice: str, rate: str) -> None:
    """Async helper that calls edge-tts to synthesise *text* and save to *output_path*.

    Passes plain text to edge-tts (SSML is **not** used because edge-tts v7+
    internally escapes all XML tags, which causes the TTS engine to read the
    markup aloud instead of interpreting it).  The neural voice already
    handles sentence boundaries and comma pauses naturally from punctuation.
    """
    import edge_tts  # type: ignore[import]

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def generate_speech(script_text: str) -> tuple[Path, float]:
    """Generate TTS audio for *script_text* using a comedy-optimised voice.

    Tries Microsoft Edge's free neural TTS (edge-tts) first for natural,
    high-quality audio.  Falls back to Google's gTTS if edge-tts is
    unavailable or fails.

    Args:
        script_text: The narration text to convert to speech.

    Returns:
        A tuple of ``(audio_path, duration_seconds)`` where *audio_path* is a
        :class:`pathlib.Path` pointing to the generated MP3 file.

    Raises:
        RuntimeError: If all TTS engines fail.
    """
    tmp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    audio_path = Path(tmp_file.name)
    tmp_file.close()

    logger.info("Generating comedy TTS for %d characters of script text…", len(script_text))

    clean_text = _clean_text_for_tts(script_text)
    logger.debug("Cleaned TTS text (%d chars): %s…", len(clean_text), clean_text[:80])

    # --- Primary: edge-tts (free Microsoft neural voice) ---
    try:
        import edge_tts  # type: ignore[import]  # noqa: F401 — check availability before asyncio.run

        voice = pick_voice()
        asyncio.run(
            _generate_edge_tts(
                clean_text,
                str(audio_path),
                voice,
                config.TTS_RATE,
            )
        )
        logger.info("Comedy TTS generated via edge-tts (voice: %s)", voice)
    except Exception as edge_exc:  # noqa: BLE001
        logger.warning("edge-tts failed (%s); falling back to gTTS", edge_exc)

        # --- Fallback: gTTS ---
        try:
            from gtts import gTTS  # type: ignore[import]
        except ImportError as exc:
            audio_path.unlink(missing_ok=True)
            raise RuntimeError(
                "Neither edge-tts nor gTTS is installed — "
                "run: pip install edge-tts gTTS"
            ) from exc

        try:
            tts = gTTS(
                text=clean_text,
                lang=config.TTS_LANGUAGE,
                slow=False,
            )
            tts.save(str(audio_path))
            logger.info("Comedy TTS generated via gTTS (lang: %s)", config.TTS_LANGUAGE)
        except Exception as gtts_exc:
            audio_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Both TTS engines failed — edge-tts: {edge_exc}; gTTS: {gtts_exc}"
            ) from gtts_exc

    if getattr(config, "TTS_VOLUME_NORMALIZE", True):
        _normalize_audio(audio_path)

    duration = _get_audio_duration(audio_path)
    logger.info("Comedy TTS audio saved to '%s' (%.2f s)", audio_path, duration)
    return audio_path, duration
