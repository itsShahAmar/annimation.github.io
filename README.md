# 🍳 Food Making Videos Factory

> Fully automated pipeline that creates **engaging food-making YouTube Shorts**.
> Uses AI-powered professional scripts (OpenRouter), female neural TTS voices,
> multi-source food stock footage with cinematic grading.
> **Designed for English-speaking audiences.**

[![Tests](https://github.com/itsShahAmar/annimation.github.io/actions/workflows/tests.yml/badge.svg)](https://github.com/itsShahAmar/annimation.github.io/actions/workflows/tests.yml)
[![Pipeline](https://github.com/itsShahAmar/annimation.github.io/actions/workflows/automation.yml/badge.svg)](https://github.com/itsShahAmar/annimation.github.io/actions/workflows/automation.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🍽️ What It Does

The **Food Making Videos Factory** automatically:

1. 🔥 **Finds Viral Food Topics** — Scans Google Trends + YouTube Trends + food niche pools and applies a food-awareness scoring heuristic to pick the most engaging recipe/cooking premise
2. 🤖 **AI Script Writing** — Professional scripts via [OpenRouter AI](https://openrouter.ai) (GPT-4o-mini) with viral hooks, step-by-step food narration, and strategic CTAs at 25%, 50%, 75%, and 95% of the script. Falls back to high-quality templates when the API key is not set.
3. 🎙️ **Female Professional Narration** — 12 female Microsoft Edge Neural TTS voices rotating each run for variety (Sara, Aria, Jenny, Michelle, Cora, Elizabeth, Sonia, Libby, Natasha, Clara, Neerja, Emily)
4. 🎬 **Food Video Assembly** — Stock footage from Pexels (primary), Pixabay (secondary), and Unsplash (image fallback) with warm food colour grading and bold captions
5. 🚀 **Uploads & Goes Viral** — Direct to your YouTube channel via the official API (category: Howto & Style)

All 100% automated — runs every 6 hours via GitHub Actions.

---

## 🚀 Quick Start

### Prerequisites

- A **YouTube channel** with a Google Cloud project and OAuth2 client secret
- A **Pexels API key** (free at [pexels.com/api](https://www.pexels.com/api/))
- An **OpenRouter API key** (for AI script generation — get yours at [openrouter.ai](https://openrouter.ai/keys))
- A **GitHub account** to fork this repo and set Secrets
- _(Optional)_ A **Pixabay API key** (free at [pixabay.com/api/docs](https://pixabay.com/api/docs/)) for additional stock footage
- _(Optional)_ An **Unsplash Access Key** (free at [unsplash.com/developers](https://unsplash.com/developers)) for food photography fallback
- _(Optional)_ A **NewsAPI key** for trending headline topics

### Step 1 — Fork the Repository

Click **Fork** at the top of this page, then clone your fork:

```bash
git clone https://github.com/<your-username>/annimation.github.io
cd annimation.github.io
pip install -r requirements.txt
```

### Step 2 — Create a Google Cloud OAuth2 Client Secret

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable the **YouTube Data API v3**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. Choose **Desktop app**, download the JSON file

### Step 3 — Authorise Your YouTube Channel

Run the one-time authorisation flow locally:

```bash
python -c "
import json, os
from google_auth_oauthlib.flow import InstalledAppFlow

secret = json.loads(open('client_secret.json').read())
flow = InstalledAppFlow.from_client_config(
    secret,
    scopes=['https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube']
)
creds = flow.run_local_server(port=0)
print(creds.to_json())
"
```

Copy the JSON output — you'll need it for `YOUTUBE_TOKEN` secret.

### Step 4 — Set GitHub Secrets

Go to **Settings → Secrets → Actions** in your fork and add:

| Secret | Value | Source |
|--------|-------|--------|
| `YOUTUBE_CLIENT_SECRET` | JSON content of your OAuth2 client file | Step 2 above |
| `YOUTUBE_TOKEN` | JSON token from the auth flow | Step 3 above |
| `PEXELS_API_KEY` | Your Pexels API key | [pexels.com/api](https://www.pexels.com/api/) |
| `OPENROUTER_API_KEY` | Your OpenRouter API key | [openrouter.ai/keys](https://openrouter.ai/keys) |
| `PIXABAY_API_KEY` | _(Optional)_ Your Pixabay key | [pixabay.com/api/docs](https://pixabay.com/api/docs/) |
| `UNSPLASH_ACCESS_KEY` | _(Optional)_ Your Unsplash key | [unsplash.com/developers](https://unsplash.com/developers) |
| `NEWSAPI_KEY` | _(Optional)_ Your NewsAPI key | [newsapi.org](https://newsapi.org/) |
| `FREESOUND_API_KEY` | _(Optional)_ Your Freesound key | [freesound.org/apiv2/apply](https://freesound.org/apiv2/apply/) |

### Step 5 — Enable GitHub Actions

Go to **Actions** tab in your fork and click **"I understand my workflows, go ahead and enable them"**.

The pipeline will automatically run every 6 hours and upload a new food video to your channel.

---

## 🎵 Free Music Sources & Fallbacks

Background music is sourced automatically using a **multi-source fallback chain** — no single point of failure. Each source is tried in order until one succeeds:

| Priority | Source | API Key | Notes |
|----------|--------|---------|-------|
| 1️⃣ Primary | [Pixabay Music](https://pixabay.com/api/docs/) | `PIXABAY_API_KEY` _(optional)_ | High-quality royalty-free tracks |
| 2️⃣ Secondary | [Free Music Archive](https://freemusicarchive.org) | None required | Creative Commons licensed music |
| 3️⃣ Optional | [Freesound](https://freesound.org/apiv2/apply/) | `FREESOUND_API_KEY` _(optional)_ | Large community sound library |
| 4️⃣ Fallback | Silence Generator | None required | Always succeeds — guarantees an audio track |

**How it works:**
- If `PIXABAY_API_KEY` is set, Pixabay Music is tried first (highest quality).
- Free Music Archive is always tried next — no API key needed.
- If `FREESOUND_API_KEY` is set, Freesound is tried as an additional source.
- If all network sources fail, a silent audio track is generated locally so the pipeline never fails due to missing music.

> **No music secrets?** The pipeline still works. Free Music Archive requires no key, and the silence generator ensures the pipeline always has an audio track.

---

## 🧠 AI Script Generation (OpenRouter)

Scripts are generated using [OpenRouter AI](https://openrouter.ai) which gives you access to GPT-4o-mini, Claude, Llama, and more via a single API.

### How to Get Your OpenRouter API Key

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
3. Click **"Create Key"** and copy the key
4. Add it as `OPENROUTER_API_KEY` in GitHub Secrets

### What the AI Generates

Each AI-generated script includes:
- **Viral hook** (first 3-5 seconds): curiosity gap or shocking food fact
- **Professional food narration**: step-by-step technique with personality
- **Strategic CTAs**: like (25%), subscribe (50%), comment (75%), share (end)
- **15-25 SEO-optimised tags**: mix of broad and niche food keywords
- **SEO-friendly description**: with main keyword in first line + timestamps

> **No API key?** The pipeline falls back to high-quality template-based scripts automatically — no configuration needed.

---

## 🎙️ Female Voice Rotation

12 professional female neural voices rotate across runs for channel variety:

| Voice | Accent | Style |
|-------|--------|-------|
| Sara Neural | US English | Cheerful, energetic |
| Aria Neural | US English | Friendly, conversational |
| Jenny Neural | US English | Professional, clear |
| Michelle Neural | US English | Natural, warm |
| Cora Neural | US English | Engaging, friendly |
| Elizabeth Neural | US English | Clear, authoritative |
| Sonia Neural | British English | Professional |
| Libby Neural | British English | Friendly |
| Natasha Neural | Australian English | Energetic |
| Clara Neural | Canadian English | Warm |
| Neerja Neural | Indian English | Professional |
| Emily Neural | Irish English | Charming |

All voices use +5% speed rate for energetic food content delivery.

---

## 📊 Viral Optimization Features

Every video is automatically optimised for maximum engagement:

### Hook Strategy
- First 1-3 seconds must grab attention (curiosity gap or shocking food fact)
- Pattern interrupts to prevent scroll-past
- Emotional trigger in the opening

### CTA Placement
- **25% mark**: Like CTA
- **50% mark**: Subscribe CTA  
- **75% mark**: Comment CTA
- **Near end**: Share CTA

### Tags Strategy (15-30 tags)
- Broad tags: `cooking`, `recipes`, `food`
- Niche tags: topic-specific ingredients and techniques
- Trending hashtags: `#FoodHacks`, `#CookingTips`, `#RecipeIdeas`

## 🗂️ Project Structure

```
annimation.github.io/
├── config.py                    # Central configuration (API keys, all settings)
├── requirements.txt             # Python dependencies
├── src/
│   ├── pipeline.py              # Main orchestrator — 9-stage production pipeline
│   ├── trending.py              # Food topic discovery (Google Trends, YouTube, NewsAPI)
│   ├── trend_scorer.py          # 🆕 Weighted trend scoring, deduplication & novelty filter
│   ├── scriptwriter.py          # OpenRouter AI + template script generation
│   ├── enhanced_scriptwriter.py # Step-by-step enriched scripts with beat markers
│   ├── cta_engine.py            # 🆕 CTA strategy matrix, hooks & subscribe prompts
│   ├── style_packs.py           # 🆕 Cinematic food style packs (lighting, color grade)
│   ├── qa_validator.py          # 🆕 QA validation gates (duration, terms, file integrity)
│   ├── run_summary.py           # 🆕 Structured run summaries and audit logs
│   ├── tts.py                   # Female-only Edge TTS with voice rotation
│   ├── video_creator.py         # Multi-source food video assembly (cinematic)
│   ├── virality_optimizer.py    # Virality scoring and improvement suggestions
│   ├── viral_tags_generator.py  # Multi-tier tagging (30–50 tags)
│   ├── music_selector.py        # Scene-aware background music selection
│   ├── audio_mixer.py           # Audio mixing and normalization
│   ├── footage_alternatives.py  # Multi-source stock footage fallbacks
│   ├── music_alternatives.py    # Free music source alternatives
│   ├── realistic_steps_generator.py  # Realistic cooking step generation
│   └── uploader.py              # YouTube OAuth upload
├── tests/
│   ├── test_trend_scorer.py     # 🆕 Trend scoring and selection tests
│   ├── test_cta_engine.py       # 🆕 CTA strategy and hook injection tests
│   ├── test_style_packs.py      # 🆕 Style pack selection and scene enrichment tests
│   ├── test_qa_validator.py     # 🆕 QA validation gate tests
│   ├── test_run_summary.py      # 🆕 Run summary and audit log tests
│   ├── test_scriptwriter.py     # Script generation tests
│   ├── test_enhanced_scriptwriter.py
│   ├── test_pipeline.py
│   ├── test_virality_optimizer.py
│   ├── test_viral_tags_generator.py
│   ├── test_music_selector.py
│   ├── test_audio_mixer.py
│   ├── test_video_creator.py
│   ├── test_music_alternatives.py
│   ├── test_config.py
│   └── test_uploader.py
├── artifacts/                   # 🆕 Auto-generated run artifacts (audit logs, digests)
│   ├── audit_YYYYMMDDTHHMMSSZ.json   # Per-run audit log
│   ├── trend_digest_YYYYMMDDTHHMMSS.json  # Daily trend digest
│   └── topic_history.json       # Novelty tracking history
└── .github/workflows/
    ├── automation.yml           # Pipeline: runs every 8 hours + manual dry-run trigger
    └── tests.yml                # CI: runs on every push/PR
```

---

## 🏗️ Architecture

The pipeline runs in **9 ordered stages**, each in a separate module for clear
separation of concerns and independent testability:

```
[0] Credentials validation   — fail fast before heavy work
[1] Trend ingestion          — fetch + score + deduplicate + novelty filter
[2] Style pack selection     — choose cinematic visual profile for the topic
[3] Script generation        — AI (OpenRouter) or template fallback
[4] CTA injection            — insert hooks and subscribe prompts
[4.5] Scene enrichment       — add style cues to footage search queries
[5] TTS narration            — female neural voice, normalised audio
[5.5] Music selection        — scene-aware free background music
[6] Video render             — cinematic 1080×1920 Shorts video
[7] QA validation            — duration, terms, file, tags, word count
[8] Virality analysis        — scoring and improvement suggestions
[9] YouTube upload           — with full metadata package
```

Each stage is timed and recorded in the run summary.

---

## 🆕 Content Engine Upgrades

### Trend Intelligence (`src/trend_scorer.py`)
- **Weighted scoring** across recency, velocity, food-niche relevance, and engagement.
- **Deduplication** using exact and near-duplicate (Jaccard similarity ≥ 0.75) checks.
- **Novelty filtering** — topics used within the last 3 days are penalised 50%.
- **Machine-readable daily digest** saved to `artifacts/trend_digest_*.json`.
- **Topic history tracking** in `artifacts/topic_history.json` to avoid repetition.

### CTA Engine (`src/cta_engine.py`)
- **5 CTA strategies**: `soft`, `urgency`, `community`, `value`, `challenge`.
- **Auto-selection** based on engagement cues (trending, educational, community).
- **A/B variant generation** — try different hooks and CTAs across runs.
- **3-point injection**: CTAs inserted at ~25%, ~50–75%, and ~95% of the script.
- **Subscribe prompts** at natural narrative boundaries (non-spammy).
- **Ending card wording** templates for maximum last-second conversion.

### Cinematic Style Packs (`src/style_packs.py`)
Five pre-built style profiles for food shorts:

| Pack | Best For | Pacing | Color Grade |
|------|----------|--------|-------------|
| `golden_hour` | Comfort food, biryani, pasta | Medium | Warm amber, 1.3× saturation |
| `macro_studio` | Cheese pulls, desserts, burgers | Fast | Vivid contrast, 1.6× saturation |
| `street_energy` | Tacos, kebabs, street food | Fast | Fiery warm, open-flame look |
| `fresh_and_clean` | Salads, smoothies, bowls | Medium | Bright, 1.4× saturation, cool |
| `dark_luxury` | Steak, fine dining, risotto | Slow | Moody contrast, deep shadows |

### QA Validation Gates (`src/qa_validator.py`)
Automated checks before every upload:
- ✅ Duration bounds (15–60 seconds)
- ✅ File integrity (exists, correct size range)
- ✅ Forbidden term scanning (script + title)
- ✅ Title length (≤ 100 chars)
- ✅ Tag count and total character validation
- ✅ Script word count (30–300 words)
- ✅ Scene count appropriateness for duration
- ✅ Confidence score aggregation — configurable minimum to proceed

### Run Summaries & Audit Logs (`src/run_summary.py`)
- Structured per-stage timing (`stage_timings` dict).
- Per-run JSON audit log saved to `artifacts/` and uploaded as workflow artifact.
- Fields: topic, title, style pack, CTA strategy, A/B variant, trend score,
  virality score, QA confidence, template used, music source, output path, upload URL.

---

## ⚙️ Configuration

All settings live in `config.py` — never commit secrets.

### New config flags added in this upgrade

```python
# Trend Intelligence
TREND_SCORER_ENABLED = True           # Use weighted scoring (vs. legacy heuristic)
TREND_HISTORY_PATH = "artifacts/topic_history.json"
TREND_DIGEST_ENABLED = True           # Save daily trend digest JSON
TREND_TOP_K = 5                       # Random selection pool size from top-scored topics

# CTA Engine
CTA_ENGINE_ENABLED = True
CTA_STRATEGY = "auto"                 # "auto" | "soft" | "urgency" | "community" | "value" | "challenge"
CTA_AB_VARIANT = "A"                  # "A" or "B"
CTA_PLATFORM = "youtube_shorts"

# Style Packs
STYLE_PACK_ENABLED = True
STYLE_PACK_NAME = "auto"              # "auto" or a pack name like "macro_studio"
STYLE_PACK_ENRICH_SCENES = True

# QA Gates
QA_ENABLED = True
QA_HARD_FAIL = False                  # True = abort pipeline on QA failure
QA_MIN_CONFIDENCE = 0.50              # Minimum confidence score to proceed
QA_MIN_DURATION = 15.0                # seconds
QA_MAX_DURATION = 60.0                # seconds

# Observability
RUN_SUMMARY_ENABLED = True
AUDIT_LOG_ENABLED = True
AUDIT_LOG_DIR = "artifacts"

# Dry-run mode
DRY_RUN = False                       # Set DRY_RUN=true env var to skip upload
```

### Existing key settings

```python
YOUTUBE_CATEGORY_ID = "26"            # Howto & Style
VIDEO_DURATION_TARGET = 55            # seconds (optimal for Shorts retention)
TTS_VOICE_ROTATE = True               # rotate female voices each run
TTS_RATE = "+5%"                      # slightly faster for energy
OPENROUTER_MODEL = "openai/gpt-4o-mini"  # cost-effective AI model
VIRALITY_MIN_SCORE = 0.0              # 0.0 = always proceed regardless of score
ENHANCED_SCRIPT_ENABLED = True        # step-by-step script generation
VIRAL_TAGS_ENABLED = True             # 30–50 multi-tier tags
```

---

## 🚀 Local Setup and Run

### Prerequisites

```bash
# System
sudo apt-get install -y ffmpeg imagemagick fonts-liberation

# Python 3.11+
pip install -r requirements.txt
```

### Environment Variables

Copy these into your shell or a `.env` file (never commit):

```bash
export YOUTUBE_CLIENT_SECRET='...'   # YouTube OAuth2 client secret (JSON)
export YOUTUBE_TOKEN='...'           # YouTube OAuth2 token (JSON)
export OPENROUTER_API_KEY='...'      # OpenRouter AI key (required for AI scripts)
export PEXELS_API_KEY='...'          # Pexels stock footage (required)
# Optional:
export PIXABAY_API_KEY='...'         # Pixabay music + footage
export UNSPLASH_ACCESS_KEY='...'     # Unsplash photography fallback
export NEWSAPI_KEY='...'             # NewsAPI trending headlines
export FREESOUND_API_KEY='...'       # Freesound music fallback
export YOUTUBE_DATA_API_KEY='...'    # YouTube CC video footage search
```

### Run the Pipeline

```bash
# Full run (creates and uploads to YouTube)
python -m src.pipeline

# Dry run (skips YouTube upload — great for testing locally)
DRY_RUN=true python -m src.pipeline

# Fast render in CI mode
VIDEO_FAST_RENDER=true python -m src.pipeline

# Specific style pack and CTA strategy
STYLE_PACK_NAME=macro_studio CTA_STRATEGY=urgency python -m src.pipeline
```

### Run Tests

```bash
# Full test suite (285 tests as of this upgrade)
python -m pytest tests/ -v

# New module tests only
python -m pytest tests/test_trend_scorer.py tests/test_cta_engine.py \
    tests/test_style_packs.py tests/test_qa_validator.py \
    tests/test_run_summary.py -v

# Quick check
python -m pytest tests/ -q
```

---

## 🔄 CI/CD

### `tests.yml` — runs on every push and PR to `main`
- Installs minimal dependencies (pytest, requests)
- Runs full test suite (no API keys needed — all external calls are mocked)

### `automation.yml` — runs every 8 hours
- Installs system deps (ffmpeg, ImageMagick) and Python dependencies
- Runs full pipeline with all secrets from GitHub Secrets
- Uploads `artifacts/` (audit logs + trend digests) as workflow artifacts
- Supports **manual dry-run trigger** via `workflow_dispatch` → `dry_run: true`

### Triggering a Manual Dry Run
1. Go to **Actions → Food Making Videos Factory**
2. Click **Run workflow**
3. Set `dry_run` = `true`
4. Click **Run workflow**

Artifacts (audit log + trend digest) will be uploaded even if the pipeline fails.

---

## 🔧 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `QA validation failed: Title is empty` | Script generation returned no title | Check OpenRouter key; template fallback will kick in next run |
| `QA: Duration 8.0s is below minimum 15s` | TTS script too short | Increase script word count; check `_MIN_WORDS` in scriptwriter |
| `Virality score 0%` | Missing tags or empty script | Ensure `VIRAL_TAGS_ENABLED=True` and script generation succeeded |
| `No background music available` | All music sources failed | Add `PIXABAY_API_KEY` secret or check network; silence fallback is used |
| `Enhanced scriptwriter failed` | OpenRouter quota/key issue | Set `OPENROUTER_API_KEY`; falls back to template scriptwriter |
| `Trend digest save failed` | `artifacts/` not writable | CI creates the directory before pipeline run |
| ImageMagick `@*` error | Security policy blocks file reads | Run the ImageMagick policy fix step |

---

## 🔐 Secrets Setup (GitHub)

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Required | Description |
|--------|----------|-------------|
| `YOUTUBE_CLIENT_SECRET` | ✅ | YouTube OAuth2 client secret JSON |
| `YOUTUBE_TOKEN` | ✅ | YouTube OAuth2 token JSON |
| `PEXELS_API_KEY` | ✅ | Pexels stock footage API key |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter AI for script generation |
| `PIXABAY_API_KEY` | ⚪ Optional | Pixabay music + footage |
| `UNSPLASH_ACCESS_KEY` | ⚪ Optional | Unsplash food photography fallback |
| `NEWSAPI_KEY` | ⚪ Optional | NewsAPI trending headlines |
| `FREESOUND_API_KEY` | ⚪ Optional | Freesound music fallback |
| `YOUTUBE_DATA_API_KEY` | ⚪ Optional | YouTube CC video search for footage |

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `edge-tts` | Microsoft neural TTS (female voices) |
| `moviepy` | Video assembly and editing |
| `requests` | Stock media API calls (Pexels, Pixabay, Unsplash) |
| `httpx` | OpenRouter AI API calls |
| `pydub` | Audio normalization |
| `google-api-python-client` | YouTube upload |

---

## 🪧 Migration Notes (v1 → v2)

All existing config flags remain valid and unchanged. New flags default to safe
production-ready values that improve output quality without breaking existing
behaviour:

- `TREND_SCORER_ENABLED = True` — replaces simple food-score heuristic with
  weighted multi-dimension scoring. The output (topic string) is identical.
- `CTA_ENGINE_ENABLED = True` — injects CTAs into the narration script. The
  video structure is unchanged; CTA phrases are woven into the script text.
- `STYLE_PACK_ENABLED = True` — enriches scene search queries with cinematic
  cues. No breaking change to video_creator API.
- `QA_ENABLED = True`, `QA_HARD_FAIL = False` — validation runs but will not
  abort the pipeline unless you explicitly set `QA_HARD_FAIL = True`.
- `AUDIT_LOG_ENABLED = True` — writes JSON files to `artifacts/` which is
  git-ignored by default. Add `artifacts/` to `.gitignore` if not already.
- `DRY_RUN = False` — same default behaviour as before. Set `DRY_RUN=true` to
  run without uploading.

To opt out of any new module, set the corresponding `_ENABLED` flag to `False`
in `config.py` or pass it as an environment variable.

---

## 📜 License

MIT — see [LICENSE](LICENSE).
