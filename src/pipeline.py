"""
pipeline.py — Main orchestrator for the Funny Animation Shorts Factory pipeline.

Runs all steps in sequence:
  1. Fetch the best trending topic (comedy-scored)
  2. Generate a comedy animation script
  3. Convert the script to speech (TTS)
  4. Create the animation-style video
  5. Generate a comedy thumbnail
  6. Upload to YouTube

Usage::

    python -m src.pipeline
"""

import logging
import time
from pathlib import Path

import config

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _cleanup(*paths: Path | None) -> None:
    """Delete temporary files, ignoring errors."""
    for p in paths:
        if p is not None:
            try:
                p.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass


def run_pipeline() -> None:
    """Execute the full Funny Animation Shorts Factory creation and upload pipeline."""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("🎬 Funny Animation Shorts Factory — pipeline starting")
    logger.info("=" * 60)

    audio_path: Path | None = None
    video_path: Path | None = None
    thumb_path: Path | None = None

    try:
        # ------------------------------------------------------------------
        # Step 0: Validate YouTube credentials (fail fast before heavy work)
        # ------------------------------------------------------------------
        logger.info("[0/6] 🔑 Validating YouTube credentials…")
        from src.uploader import validate_credentials  # noqa: PLC0415

        validate_credentials()
        logger.info("      Credentials OK")

        # ------------------------------------------------------------------
        # Step 1: Find best comedy topic
        # ------------------------------------------------------------------
        logger.info("[1/6] 🎭 Finding comedy gold — fetching trending topics…")
        from src.trending import get_best_topic  # noqa: PLC0415

        topic = get_best_topic()
        logger.info("      Comedy topic selected: '%s'", topic)

        # ------------------------------------------------------------------
        # Step 2: Generate comedy animation script
        # ------------------------------------------------------------------
        logger.info("[2/6] ✍️  Writing jokes — generating comedy script for: '%s'…", topic)
        from src.scriptwriter import generate_script  # noqa: PLC0415

        script_data = generate_script(topic)
        title = script_data["title"]
        script_text = script_data["script"]
        caption_text = script_data["caption_script"]
        hook_text = script_data["hook"]
        scenes = script_data["scenes"]
        tags = script_data["tags"]
        description = script_data["description"]
        logger.info("      Comedy title: '%s'", title)

        # ------------------------------------------------------------------
        # Step 3: Text-to-speech (expressive voice acting)
        # ------------------------------------------------------------------
        logger.info("[3/6] 🎙️  Voice acting — generating expressive TTS audio…")
        from src.tts import generate_speech  # noqa: PLC0415

        audio_path, audio_duration = generate_speech(script_text)
        logger.info("      Audio duration: %.2f s", audio_duration)

        # ------------------------------------------------------------------
        # Step 4: Create animation-style video
        # ------------------------------------------------------------------
        logger.info("[4/6] 🎬 Animating it — creating cartoon-style video…")
        from src.video_creator import create_video  # noqa: PLC0415

        video_path = create_video(audio_path, script_text, scenes, audio_duration,
                                  hook_text=hook_text)
        logger.info("      Video path: '%s'", video_path)

        # ------------------------------------------------------------------
        # Step 5: Generate comedy thumbnail
        # ------------------------------------------------------------------
        logger.info("[5/6] 🖼️  Eye-candy thumbnail — generating comedy animation thumbnail…")
        from src.thumbnail import create_thumbnail  # noqa: PLC0415

        thumb_path = create_thumbnail(title, topic)
        logger.info("      Thumbnail path: '%s'", thumb_path)

        # ------------------------------------------------------------------
        # Step 6: Upload to YouTube
        # ------------------------------------------------------------------
        logger.info("[6/6] 🚀 Upload and go viral — uploading to YouTube…")
        from src.uploader import upload_video  # noqa: PLC0415

        video_id, video_url = upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            thumbnail_path=thumb_path,
        )
        logger.info("      Upload complete: %s", video_url)

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("🎉 Funny Animation Shorts Factory — pipeline completed in %.1f seconds", elapsed)
        logger.info("  Topic      : %s", topic)
        logger.info("  Title      : %s", title)
        logger.info("  Video ID   : %s", video_id)
        logger.info("  URL        : %s", video_url)
        logger.info("=" * 60)

    except Exception as exc:  # noqa: BLE001
        elapsed = time.time() - start_time
        logger.error("💥 Pipeline failed after %.1f seconds: %s", elapsed, exc, exc_info=True)
    finally:
        _cleanup(audio_path, video_path, thumb_path)
        logger.info("🧹 Temporary files cleaned up")


if __name__ == "__main__":
    run_pipeline()
