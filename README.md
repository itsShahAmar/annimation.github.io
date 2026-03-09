# 🎬 Funny Animation Shorts Factory

> Fully automated pipeline that creates **hilarious animated comedy YouTube Shorts**.
> Uses AI-powered comedy scripts, cartoon-style visuals, expressive voice acting, and
> meme-worthy thumbnails. **100% free, no paid APIs.**

[![Tests](https://github.com/ShahAmar-Official/annimation.github.io/actions/workflows/tests.yml/badge.svg)](https://github.com/ShahAmar-Official/annimation.github.io/actions/workflows/tests.yml)
[![Pipeline](https://github.com/ShahAmar-Official/annimation.github.io/actions/workflows/automation.yml/badge.svg)](https://github.com/ShahAmar-Official/annimation.github.io/actions/workflows/automation.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🤣 What It Does

The **Funny Animation Shorts Factory** automatically:

1. 🎭 **Finds Comedy Gold** — Scans trending topics + applies comedy scoring to pick the funniest premise
2. ✍️ **Writes Jokes** — AI comedy script engine with 30+ hook templates, 6 body patterns (dialogue, chaos narrator, tutorial gone wrong, inner monologue, news anchor, time travel)
3. 🎙️ **Voice Acting** — Expressive neural TTS voices (Microsoft Edge, free) optimised for comedy delivery
4. 🎬 **Animates It** — Cartoon-style video assembly with vibrant color grading and meme-style captions
5. 🖼️ **Eye-Candy Thumbnail** — Neon gradient, starburst burst shapes, WOW/LOL/OMG overlays
6. 🚀 **Uploads & Goes Viral** — Direct to your YouTube channel via the official API

All 100% automated — runs every 6 hours via GitHub Actions. **Zero cost.**

---

## 🚀 Quick Start

### Prerequisites

- A **YouTube channel** with a Google Cloud project and OAuth2 client secret
- A **Pexels API key** (free at [pexels.com/api](https://www.pexels.com/api/))
- A **GitHub account** to fork this repo and set Secrets
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

SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.force-ssl']

flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
creds = flow.run_local_server(port=0)
print(json.dumps({
    'access_token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri
}, indent=2))
"
```

Copy the printed JSON — this is your `YOUTUBE_TOKEN`.

### Step 4 — Add GitHub Secrets

In your fork: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|-------------|-------|
| `YOUTUBE_CLIENT_SECRET` | Contents of your OAuth2 JSON file |
| `YOUTUBE_TOKEN` | Token JSON from Step 3 |
| `PEXELS_API_KEY` | Your Pexels API key |
| `NEWSAPI_KEY` | *(Optional)* Your NewsAPI key |

### Step 5 — Enable GitHub Actions

Go to **Actions** tab → enable workflows. The pipeline runs every 6 hours automatically, or trigger it manually via **workflow_dispatch**.

---

## 😂 Comedy Script Features

### 30+ Hook Templates

The scriptwriter opens every video with an absurd, meme-culture hook designed to stop the scroll in the first 3 seconds:

- `"What if {topic} was actually run by a council of angry cats?"`
- `"POV: You explained {topic} to your grandma and she started a business."`
- `"Nobody: ... Absolutely Nobody: ... {topic}: chaos ensues."`
- `"{topic} but it is explained by two neurons fighting in your brain."`
- `"Me trying to understand {topic} at 3 AM be like..."`
- And 25+ more Gen-Z, meme-culture, relatable comedy hooks

### 6 Comedy Body Patterns

| Pattern | Description |
|---------|-------------|
| 🗣️ Character Dialogue | Two funny animated characters debating/reacting |
| 📢 Narrator + Chaos | Calm narrator voice while animated chaos unfolds |
| 📋 Tutorial Gone Wrong | How-to that hilariously goes off the rails |
| 🧠 Inner Monologue | Character's thoughts vs reality |
| 📺 News Anchor | Fake news broadcast with ridiculous takes |
| ⏰ Time Travel | Future/past perspective comedy |

### Animation-Style Scenes

Scene descriptions are designed for cartoon visuals:

- *"Chibi character rage-typing on a tiny laptop while papers fly everywhere"*
- *"Two stick figures in a heated debate with thought bubbles full of chaos"*
- *"Character doing the surprised Pikachu face as explosions happen behind"*
- *"Rubber hose cartoon brain running in circles with tiny gears flying off"*

---

## 🎨 Animation Styles Supported

The pipeline is designed around these visual styles (via Pexels query optimisation):

| Style | Description |
|-------|-------------|
| **2D Cartoon** | Classic flat animation with bold outlines |
| **Chibi Anime** | Small, cute characters with oversized expressions |
| **Pixel Art** | 8-bit/16-bit retro game sprites |
| **Rubber Hose** | Classic 1930s-style squiggly limbs |
| **Stick Figures** | Minimalist with maximum attitude |
| **Minimalist Blob** | Simple shapes with huge personality |

---

## ⚙️ Configuration

All settings are in `config.py`. Key comedy-specific options:

```python
VIDEO_DURATION_TARGET = 55       # Slightly longer for comedy timing
ANIMATION_STYLE = "2D cartoon"
COMEDY_LEVEL = "maximum"
COMEDY_SOUND_EFFECTS = True
PUNCHLINE_ZOOM = True            # Zoom on punchlines
MEME_CAPTIONS = True             # Meme-style captions

# Subtitle colours (comedy palette)
SUBTITLE_HIGHLIGHT_COLOR = "#FF4500"   # orange-red punch
SUBTITLE_SECONDARY_COLOR = "#FFD700"   # gold laughs
SUBTITLE_ACCENT_COLOR = "#00FF7F"      # spring green
SUBTITLE_ALL_CAPS = True
SUBTITLE_POP_SCALE = 1.25             # bigger pop for emphasis
SUBTITLE_FONT_SIZE = 92
```

---

## 🗂️ Project Structure

```
annimation.github.io/
├── config.py               # Central configuration
├── requirements.txt        # Python dependencies
├── index.html              # Landing page / setup wizard
├── src/
│   ├── pipeline.py         # Main orchestrator
│   ├── scriptwriter.py     # Comedy script generator (30+ hooks!)
│   ├── trending.py         # Comedy-scored trending topics
│   ├── tts.py              # Expressive TTS voice acting
│   ├── video_creator.py    # Animation-style video assembly
│   ├── thumbnail.py        # Comedy animation thumbnails
│   └── uploader.py         # YouTube Data API v3 uploader
├── tests/
│   ├── test_scriptwriter.py
│   └── test_uploader.py
└── .github/workflows/
    ├── automation.yml      # Cron pipeline (every 6 hours)
    ├── tests.yml           # Test runner
    └── pages.yml           # GitHub Pages deployment
```

---

## 🧪 Running Tests

```bash
pip install pytest requests
python -m pytest tests/ -v
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We welcome:

- New comedy hook templates
- New body pattern styles
- Animation style improvements
- Better thumbnail designs
- Bug fixes

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## ⚠️ Disclaimer

- This project uses the **YouTube Data API v3** — ensure your content complies with [YouTube's Terms of Service](https://www.youtube.com/t/terms).
- Stock footage is sourced from [Pexels](https://www.pexels.com/license/) under their free license.
- Comedy scripts are template-generated and do not target, mock, or harm any individual.
- The pipeline is designed for wholesome, universally appealing comedy content.