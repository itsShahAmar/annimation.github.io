"""
music_selector.py — Scene-aware background music selection for the Food Making Videos Factory.

Classifies scenes by type (intro / middle / punchline) and downloads royalty-free
background music from free sources:

  1. Freesound API  — requires ``FREESOUND_API_KEY`` (free registration at freesound.org/apiv2/apply/).
  2. Silence fallback — returns ``None`` so the pipeline continues without music.

Downloaded tracks are cached locally under ``MUSIC_CACHE_DIR`` to avoid redundant
API calls across pipeline runs.
"""

import hashlib
import logging
from pathlib import Path

import requests

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scene-type → music mood search queries
# ---------------------------------------------------------------------------
_SCENE_MOOD_MAP: dict[str, list[str]] = {
    "intro": [
        "uplifting cooking background music",
        "cheerful kitchen background music",
        "happy food background",
    ],
    "middle": [
        "energetic cooking background music",
        "upbeat kitchen background music",
        "lively food preparation music",
    ],
    "punchline": [
        "triumphant reveal background music",
        "satisfying achievement music",
        "happy celebration food music",
    ],
}

_FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/text/"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def classify_scene_type(scene_index: int, total_scenes: int) -> str:
    """Return the type of a scene based on its position in the video.

    Args:
        scene_index:   Zero-based index of the scene.
        total_scenes:  Total number of scenes in the video.

    Returns:
        ``'intro'`` for the first scene, ``'punchline'`` for the last,
        and ``'middle'`` for all others.  Returns ``'middle'`` when
        ``total_scenes`` is 1 or less.
    """
    if total_scenes <= 1:
        return "middle"
    if scene_index == 0:
        return "intro"
    if scene_index >= total_scenes - 1:
        return "punchline"
    return "middle"


def get_mood_for_scene(scene_type: str) -> str:
    """Return a music search query string for the given scene type.

    Rotates among available mood phrases hourly for variety.

    Args:
        scene_type: One of ``'intro'``, ``'middle'``, or ``'punchline'``.
                    Falls back to ``'middle'`` if unrecognised.

    Returns:
        A descriptive music search query string.
    """
    import time

    moods = _SCENE_MOOD_MAP.get(scene_type, _SCENE_MOOD_MAP["middle"])
    idx = int(time.time() // 3600) % len(moods)
    return moods[idx]


def get_music_for_scenes(scenes: list[str], topic: str) -> Path | None:
    """Select and download background music suitable for the given video scenes.

    Determines the dominant scene type from the scene list and searches
    Freesound for a matching royalty-free track.  Previously downloaded
    tracks are served from the local cache to minimise API usage.

    Args:
        scenes: List of scene description strings from script generation.
        topic:  The food topic being covered (used to refine the search).

    Returns:
        Path to the downloaded MP3 file, or ``None`` if music is
        unavailable (no API key, API error, or music disabled in config).
    """
    if not getattr(config, "MUSIC_ENABLED", True):
        logger.info("Background music disabled via MUSIC_ENABLED config")
        return None

    cache_dir = Path(getattr(config, "MUSIC_CACHE_DIR", "cache/music"))
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not create music cache directory '%s': %s", cache_dir, exc)
        return None

    # Pick a scene type representative of the overall video content
    total = len(scenes)
    primary_scene_type = "intro" if total <= 2 else "middle"
    mood_query = get_mood_for_scene(primary_scene_type)
    # Blend the food topic into the search for more relevant results
    search_query = f"{mood_query} {topic}".strip() if topic else mood_query

    # Check local cache before hitting the API
    cache_key = hashlib.md5(search_query.encode()).hexdigest()[:12]
    cached = list(cache_dir.glob(f"{cache_key}_*.mp3"))
    if cached:
        logger.info("Using cached background music: %s", cached[0])
        return cached[0]

    # Try Freesound as the primary free music source
    music_path = _download_from_freesound(search_query, cache_dir, cache_key)
    if music_path:
        return music_path

    logger.warning("No background music sourced — video will use TTS narration only")
    return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _download_from_freesound(query: str, cache_dir: Path, cache_key: str) -> Path | None:
    """Search Freesound for background music and download the best match.

    Requires ``FREESOUND_API_KEY`` to be set in the environment.
    Downloads the high-quality MP3 preview of the top-rated result.

    Args:
        query:     Search query string.
        cache_dir: Directory to save the downloaded file.
        cache_key: Short hash used as part of the cached filename.

    Returns:
        Path to the downloaded MP3, or ``None`` on any failure.
    """
    api_key = getattr(config, "FREESOUND_API_KEY", None)
    if not api_key:
        logger.debug("FREESOUND_API_KEY not configured — skipping Freesound music search")
        return None

    try:
        resp = requests.get(
            _FREESOUND_SEARCH_URL,
            params={
                "query": query,
                "filter": "duration:[30 TO 180] type:mp3",
                "fields": "id,name,previews,duration,license",
                "sort": "rating_desc",
                "page_size": 5,
                "token": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

        if not results:
            logger.debug("Freesound returned no results for query '%s'", query)
            return None

        # Pick the first result that exposes a downloadable preview URL
        for result in results:
            previews = result.get("previews", {})
            preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
            if not preview_url:
                continue

            sound_id = result.get("id", "unknown")
            out_path = cache_dir / f"{cache_key}_{sound_id}.mp3"

            try:
                with requests.get(preview_url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(out_path, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=8192):
                            fh.write(chunk)
                logger.info(
                    "Downloaded background music '%s' (id=%s) → %s",
                    result.get("name", sound_id), sound_id, out_path,
                )
                return out_path
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to download Freesound preview for id=%s: %s", sound_id, exc
                )

    except Exception as exc:  # noqa: BLE001
        logger.warning("Freesound search failed for query '%s': %s", query, exc)

    return None
