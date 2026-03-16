"""Central configuration for the Food Making Videos Factory pipeline."""

import os

# API Keys (loaded from GitHub Secrets / environment variables)
YOUTUBE_CLIENT_SECRET_JSON: str | None = os.getenv("YOUTUBE_CLIENT_SECRET")  # JSON string of OAuth2 client secret
YOUTUBE_TOKEN_JSON: str | None = os.getenv("YOUTUBE_TOKEN")  # JSON string of OAuth2 token
PEXELS_API_KEY: str | None = os.getenv("PEXELS_API_KEY")  # For stock footage (free tier)
NEWSAPI_KEY: str | None = os.getenv("NEWSAPI_KEY")  # NewsAPI.org key for trending headlines (optional)
OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")  # OpenRouter AI key for script generation
PIXABAY_API_KEY: str | None = os.getenv("PIXABAY_API_KEY")  # Pixabay API key for additional stock footage & music
UNSPLASH_ACCESS_KEY: str | None = os.getenv("UNSPLASH_ACCESS_KEY")  # Unsplash API key for food photography

# ---------------------------------------------------------------------------
# Additional stock footage API keys (all optional — pipeline works without them)
# ---------------------------------------------------------------------------
# Coverr — free stock footage, no API key required (uses public token)
COVERR_API_TOKEN: str = os.getenv("COVERR_API_TOKEN", "0H2YMH75AH")  # default public token
# Videvo — optional; register at videvo.net/api
VIDEVO_API_KEY: str | None = os.getenv("VIDEVO_API_KEY")
# Storyblocks (Videoblocks) — optional paid tier; register at storyblocks.com/api
STORYBLOCKS_PUBLIC_KEY: str | None = os.getenv("STORYBLOCKS_PUBLIC_KEY")
STORYBLOCKS_PRIVATE_KEY: str | None = os.getenv("STORYBLOCKS_PRIVATE_KEY")

# ---------------------------------------------------------------------------
# Stock footage source priority chain — tried in order until one succeeds.
#   "pexels"       — Pexels Videos API (requires PEXELS_API_KEY)
#   "pixabay"      — Pixabay Videos API (requires PIXABAY_API_KEY)
#   "coverr"       — Coverr free footage API (no key required)
#   "videvo"       — Videvo API (requires VIDEVO_API_KEY)
#   "unsplash"     — Unsplash image fallback with Ken Burns effect (requires UNSPLASH_ACCESS_KEY)
#   "pexels_image" — Pexels image fallback with Ken Burns effect (requires PEXELS_API_KEY)
#   "placeholder"  — Warm gradient placeholder (always succeeds)
# ---------------------------------------------------------------------------
VIDEO_SOURCE_PRIORITY: list = [
    "pexels", "pixabay", "coverr", "videvo", "unsplash", "pexels_image", "placeholder"
]

# Video settings
VIDEO_WIDTH: int = 1080
VIDEO_HEIGHT: int = 1920
VIDEO_FPS: int = 30
VIDEO_DURATION_TARGET: int = 55  # seconds target — optimal for food Shorts retention
FONT_SIZE: int = 60
FONT_COLOR: str = "white"
BG_MUSIC_VOLUME: float = 0.08
BG_MUSIC_PATH: str = "assets/bg_music.mp3"  # Optional static background music file

# ---------------------------------------------------------------------------
# Background music settings — scene-aware music selection and mixing
# ---------------------------------------------------------------------------
MUSIC_ENABLED: bool = True                   # Set False to disable background music entirely
MUSIC_VOLUME: float = BG_MUSIC_VOLUME        # Background music volume (0.0–1.0 relative to narration)
MUSIC_FADE_DURATION: float = 1.0             # Fade-in and fade-out duration in seconds
MUSIC_CACHE_DIR: str = "cache/music"         # Local cache directory for downloaded tracks

# Music source fallback chain — tried in order until one succeeds.
# Remove or reorder entries to customise behaviour.
#   "pixabay"            — Pixabay Music API (requires PIXABAY_API_KEY)
#   "jamendo"            — Jamendo API (requires JAMENDO_CLIENT_ID, free registration)
#   "free_music_archive" — Free Music Archive API (no API key required)
#   "ccmixter"           — ccMixter Creative Commons API (no API key required)
#   "freesound"          — Freesound API (requires FREESOUND_API_KEY, optional)
#   "silence"            — Locally-generated silent WAV (always succeeds)
MUSIC_SOURCE_PRIORITY: list = [
    "pixabay", "jamendo", "free_music_archive", "ccmixter", "freesound", "silence"
]

FREESOUND_API_KEY: str | None = os.getenv("FREESOUND_API_KEY")  # Optional — freesound.org API key
# Jamendo — free music API; register at devportal.jamendo.com for a client_id
JAMENDO_CLIENT_ID: str | None = os.getenv("JAMENDO_CLIENT_ID")  # Optional — jamendo.com free API

# ---------------------------------------------------------------------------
# Food content style settings
# ---------------------------------------------------------------------------
CONTENT_STYLE: str = "food making"               # content focus
ENGAGEMENT_LEVEL: str = "maximum"                # engagement intensity
FOOD_CATEGORIES: list = [
    "quick recipes",
    "cooking hacks",
    "meal prep",
    "food science",
    "kitchen tips",
    "restaurant-style at home",
    "healthy eating",
    "comfort food",
]
FOOD_PRESENTATION_STYLES: list = [
    "overhead flat lay",
    "close-up detail shots",
    "step-by-step preparation",
    "finished dish reveal",
    "ingredient showcase",
    "before and after",
]
HOOK_ZOOM: bool = True               # zoom effect on recipe reveals
FOOD_CAPTIONS: bool = True           # ingredient and step captions

# ---------------------------------------------------------------------------
# Subtitle / caption styling — bold, engaging word bursts for food content
# ---------------------------------------------------------------------------
SUBTITLE_FONT_SIZE: int = 92           # slightly larger for impact
SUBTITLE_FONT: str = "Liberation-Sans-Bold"  # fallback fonts tried in order by MoviePy
SUBTITLE_FONT_FALLBACKS: list = [      # tried in order if primary font is unavailable
    "Arial-Bold", "DejaVu-Sans-Bold", "FreeSans-Bold", "Liberation-Sans-Bold",
]
SUBTITLE_STROKE_WIDTH: int = 6         # thicker stroke = sharper legibility on any bg
SUBTITLE_BG_OPACITY: float = 0.82     # slightly more opaque pill for better contrast
SUBTITLE_HIGHLIGHT_COLOR: str = "#FF6B00"   # warm orange for food vibrancy
SUBTITLE_SECONDARY_COLOR: str = "#FFD700"   # golden yellow for warmth
SUBTITLE_ACCENT_COLOR: str = "#FF3366"      # red accent for urgency/CTAs
SUBTITLE_POSITION: float = 0.72        # vertical position (0 = top, 1 = bottom of frame)
SUBTITLE_MAX_WORDS: int = 4            # max words per caption burst
SUBTITLE_BG_CORNER_RADIUS: int = 28   # rounder pill for modern look
SUBTITLE_SHADOW_OFFSET: int = 3       # drop shadow offset in px
SUBTITLE_GLOW: bool = True             # neon glow behind pill background
SUBTITLE_GLOW_COLOR: str = "#FF6B00"  # glow colour (warm orange for food)
SUBTITLE_GLOW_RADIUS: int = 18        # glow blur radius in px
SUBTITLE_WORD_TIMING: bool = True      # scale each caption's duration by word count
SUBTITLE_ADAPTIVE_FONT: bool = True    # bigger font for short (1-2 word) power bursts
SUBTITLE_POP_SCALE: float = 1.25      # bigger pop for recipe reveals
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
VIDEO_COLOR_GRADE: bool = True         # vibrant, saturated colour grade for food appeal
VIDEO_CLIP_RANDOM_START: bool = True   # random clip start for visual variety per run

# ---------------------------------------------------------------------------
# TTS settings — female-only rotating voice pool, professional narration
# ---------------------------------------------------------------------------
TTS_VOICE: str = "en-US-JennyNeural"  # fallback voice if rotation is disabled
TTS_VOICE_ROTATE: bool = True          # True = pick a different voice each run
TTS_RATE: str = "+5%"                  # slightly faster pace for energy
TTS_VOLUME_NORMALIZE: bool = True      # normalize loudness with pydub

# Pexels fetch settings
PEXELS_PER_PAGE: int = 10  # more results = better footage variety

# Upload settings
YOUTUBE_CATEGORY_ID: str = "26"  # Howto & Style
PRIVACY_STATUS: str = "public"

# Scheduling
MAX_VIDEOS_PER_RUN: int = 1

# OpenRouter AI settings
OPENROUTER_MODEL: str = "openai/gpt-4o-mini"  # cost-effective model for script generation
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# ---------------------------------------------------------------------------
# Viral Optimization Engine — maximize reach and engagement
# ---------------------------------------------------------------------------
VIRAL_OPTIMIZATION_ENABLED: bool = True  # Enable the viral scoring & optimization pipeline
VIRAL_SCORE_THRESHOLD: float = 0.65      # Min score (0-1) to classify content as "high potential"
VIRAL_A_B_TITLES: bool = True            # Generate multiple title variants and score them
VIRAL_TITLE_VARIANTS: int = 3            # Number of A/B title variants to generate
VIRAL_HOOK_ROTATE: bool = True           # Rotate hook styles across runs for variety
VIRAL_ENGAGEMENT_BOOST: bool = True      # Inject micro-CTAs and engagement triggers into scripts
VIRAL_RETENTION_TARGET: float = 0.60    # Target viewer retention rate (60% = strong for Shorts)

# ---------------------------------------------------------------------------
# Coverr stock footage settings (free, no account required)
# ---------------------------------------------------------------------------
COVERR_PER_PAGE: int = 5  # results to fetch per Coverr query
