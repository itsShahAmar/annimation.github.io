"""Central configuration for the Funny Animation Shorts Factory pipeline."""

import os

# API Keys (loaded from GitHub Secrets / environment variables)
# NOTE: No paid API keys required!  Script generation uses free templates
# and TTS uses Microsoft's free edge-tts neural voices.
YOUTUBE_CLIENT_SECRET_JSON: str | None = os.getenv("YOUTUBE_CLIENT_SECRET")  # JSON string of OAuth2 client secret
YOUTUBE_TOKEN_JSON: str | None = os.getenv("YOUTUBE_TOKEN")  # JSON string of OAuth2 token
PEXELS_API_KEY: str | None = os.getenv("PEXELS_API_KEY")  # For stock footage (free tier)
NEWSAPI_KEY: str | None = os.getenv("NEWSAPI_KEY")  # NewsAPI.org key for trending headlines (optional)

# Video settings
VIDEO_WIDTH: int = 1080
VIDEO_HEIGHT: int = 1920
VIDEO_FPS: int = 30
VIDEO_DURATION_TARGET: int = 55  # seconds target — slightly longer for comedy timing
FONT_SIZE: int = 60
FONT_COLOR: str = "white"
BG_MUSIC_VOLUME: float = 0.08
BG_MUSIC_PATH: str = "assets/bg_music.mp3"  # Relative path to background music file (leave empty to disable)

# ---------------------------------------------------------------------------
# Animation / Comedy style settings
# ---------------------------------------------------------------------------
ANIMATION_STYLE: str = "2D cartoon"                # default animation style
COMEDY_LEVEL: str = "maximum"                       # comedy intensity
ANIMATION_GENRES: list = [
    "slapstick",
    "parody",
    "absurd humor",
    "situational comedy",
    "dark comedy lite",
    "wholesome funny",
    "roast comedy",
    "plot twist comedy",
]
CHARACTER_STYLES: list = [
    "stick figures with attitude",
    "chibi anime characters",
    "pixel art sprites",
    "rubber hose cartoon",
    "south park style",
    "minimalist blob characters",
]
COMEDY_SOUND_EFFECTS: bool = True
PUNCHLINE_ZOOM: bool = True          # zoom effect on punchlines
MEME_CAPTIONS: bool = True           # meme-style captions

# ---------------------------------------------------------------------------
# Subtitle / caption styling — bold, meme-style animated word bursts
# ---------------------------------------------------------------------------
SUBTITLE_FONT_SIZE: int = 92           # slightly larger for impact
SUBTITLE_FONT: str = "Liberation-Sans-Bold"  # fallback fonts tried in order by MoviePy
SUBTITLE_FONT_FALLBACKS: list = [      # tried in order if primary font is unavailable
    "Arial-Bold", "DejaVu-Sans-Bold", "FreeSans-Bold", "Liberation-Sans-Bold",
]
SUBTITLE_STROKE_WIDTH: int = 6         # thicker stroke = sharper legibility on any bg
SUBTITLE_BG_OPACITY: float = 0.82     # slightly more opaque pill for better contrast
SUBTITLE_HIGHLIGHT_COLOR: str = "#FF4500"   # orange-red for comedy punch
SUBTITLE_SECONDARY_COLOR: str = "#FFD700"   # gold for laughs
SUBTITLE_ACCENT_COLOR: str = "#00FF7F"      # spring green accent
SUBTITLE_POSITION: float = 0.72        # vertical position (0 = top, 1 = bottom of frame)
SUBTITLE_MAX_WORDS: int = 4            # max words per caption burst
SUBTITLE_BG_CORNER_RADIUS: int = 28   # rounder pill for modern look
SUBTITLE_SHADOW_OFFSET: int = 3       # drop shadow offset in px
SUBTITLE_GLOW: bool = True             # neon glow behind pill background
SUBTITLE_GLOW_COLOR: str = "#FFD700"  # glow colour (gold for laughs)
SUBTITLE_GLOW_RADIUS: int = 18        # glow blur radius in px
SUBTITLE_WORD_TIMING: bool = True      # scale each caption's duration by word count
SUBTITLE_ADAPTIVE_FONT: bool = True    # bigger font for short (1-2 word) power bursts
SUBTITLE_POP_SCALE: float = 1.25      # bigger pop for comedy emphasis
SUBTITLE_ALL_CAPS: bool = True         # render captions in uppercase for impact
SUBTITLE_DELAY: float = 0.25          # seconds to delay captions so they trail speech (sync fix)
SUBTITLE_END_BUFFER: float = 0.4      # seconds of padding at the end; prevents captions outrunning speech

# ---------------------------------------------------------------------------
# Video encoding quality — high-bitrate for crisp 1080 × 1920 Shorts
# ---------------------------------------------------------------------------
VIDEO_PRESET: str = "slow"
VIDEO_BITRATE: str = "16000k"          # raised from 12000k for sharper quality
AUDIO_BITRATE: str = "320k"            # raised from 256k for cleaner audio
VIDEO_TRANSITION_DURATION: float = 0.35
VIDEO_VIGNETTE: bool = True            # cinematic dark-edge vignette overlay
VIDEO_COLOR_GRADE: bool = True         # vibrant, saturated colour grade for animation feel
VIDEO_CLIP_RANDOM_START: bool = True   # random clip start for visual variety per run

# ---------------------------------------------------------------------------
# TTS settings — rotating voice pool, comedy-optimised energetic voices
# ---------------------------------------------------------------------------
TTS_VOICE: str = "en-US-JennyNeural"  # fallback voice if rotation is disabled
TTS_VOICE_ROTATE: bool = True          # True = pick a different voice each run
TTS_RATE: str = "+5%"                  # slightly faster pace for comedy energy
TTS_LANGUAGE: str = "en"              # fallback for gTTS
TTS_VOLUME_NORMALIZE: bool = True      # normalize loudness with pydub

# Pexels fetch settings
PEXELS_PER_PAGE: int = 10  # more results = better footage variety

# Upload settings
YOUTUBE_CATEGORY_ID: str = "22"  # People & Blogs
PRIVACY_STATUS: str = "public"

# Scheduling
MAX_VIDEOS_PER_RUN: int = 1
