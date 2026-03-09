"""
thumbnail.py — Generate eye-catching comedy animation thumbnails for the
Funny Animation Shorts Factory.

Creates vibrant neon gradient backgrounds with bold comic-style title text,
emoji accents, burst shapes, and WOW/LOL/OMG overlays — designed to stop
the scroll and signal instant comedy content.
"""

import logging
import math
import random
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# Thumbnail dimensions (YouTube standard)
THUMB_W = 1280
THUMB_H = 720

# ---------------------------------------------------------------------------
# Comedy colour palettes — vibrant neon gradients
# ---------------------------------------------------------------------------
_GRADIENT_PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((255, 200, 0), (255, 80, 0)),       # yellow-to-orange (energy!)
    ((255, 0, 150), (120, 0, 255)),      # pink-to-purple (viral vibes)
    ((0, 230, 200), (0, 100, 255)),      # cyan-to-blue (fresh and fun)
    ((80, 255, 0), (0, 200, 100)),       # lime-to-green (wholesome chaos)
    ((255, 100, 0), (255, 0, 100)),      # orange-to-red (spicy comedy)
    ((0, 255, 200), (255, 200, 0)),      # mint-to-gold (premium funny)
]

_ACCENT_COLORS: list[tuple[int, int, int]] = [
    (255, 255, 0),   # bright yellow
    (255, 0, 200),   # hot pink
    (0, 255, 100),   # neon green
    (255, 150, 0),   # vivid orange
    (100, 200, 255), # sky blue
]

_TEXT_COLOR = (255, 255, 255)    # white
_STROKE_COLOR = (0, 0, 0)        # black for outline

# ---------------------------------------------------------------------------
# Comedy emoji bank — maps topic keywords to reaction emojis
# ---------------------------------------------------------------------------
_COMEDY_TOPIC_EMOJIS: list[tuple[list[str], str]] = [
    (["cat", "cats", "kitten", "pet"], "😹"),
    (["dog", "puppy", "woof"], "🐶"),
    (["food", "eat", "cook", "pizza", "snack"], "😋"),
    (["brain", "think", "mind", "smart"], "🧠"),
    (["wifi", "internet", "tech", "phone", "app"], "📱"),
    (["school", "homework", "teacher", "study"], "📚"),
    (["monday", "alarm", "morning", "wake", "sleep"], "😴"),
    (["work", "boss", "office", "meeting", "job"], "💼"),
    (["game", "gamer", "video game", "play"], "🎮"),
    (["money", "finance", "invest", "budget"], "💸"),
    (["travel", "vacation", "trip", "adventure"], "✈️"),
    (["ai", "robot", "automation", "machine"], "🤖"),
    (["music", "song", "dance", "beat"], "🎵"),
    (["sport", "gym", "workout", "fitness"], "💪"),
]

_DEFAULT_COMEDY_EMOJIS = ["😂", "💀", "🤣", "😭", "🔥", "💥", "😱", "🎉"]

# ---------------------------------------------------------------------------
# Accent text overlays — big comedy reaction words
# ---------------------------------------------------------------------------
_ACCENT_TEXTS: list[str] = ["LOL", "WOW", "OMG", "lmao", "bruh", "fr??", "HELP"]


def _make_gradient(w: int, h: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Create a vertical linear gradient image."""
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(top[0] + t * (bottom[0] - top[0]))
        g = int(top[1] + t * (bottom[1] - top[1]))
        b = int(top[2] + t * (bottom[2] - top[2]))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Attempt to load a TrueType font; fall back to the default bitmap font."""
    font_candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    logger.warning("No TrueType font found; using default bitmap font")
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
    """Break *text* into lines that fit within *max_width* pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_text_with_stroke(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
                            font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
                            fill: tuple[int, ...], stroke_fill: tuple[int, ...],
                            stroke_width: int) -> None:
    """Draw text with a thick outline/stroke for readability."""
    try:
        draw.text(xy, text, font=font, fill=fill,
                  stroke_width=stroke_width, stroke_fill=stroke_fill)
    except TypeError:
        x, y = xy
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx * dx + dy * dy <= stroke_width * stroke_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
        draw.text(xy, text, font=font, fill=fill)


def _draw_burst(draw: ImageDraw.ImageDraw, cx: int, cy: int, r_outer: int,
                r_inner: int, points: int, fill: tuple[int, ...]) -> None:
    """Draw a cartoon-style starburst / explosion shape.

    Args:
        draw: ImageDraw context.
        cx, cy: Center coordinates.
        r_outer: Outer radius (spike tips).
        r_inner: Inner radius (spike bases).
        points: Number of spike points.
        fill: Fill colour.
    """
    coords: list[tuple[float, float]] = []
    for i in range(points * 2):
        angle = math.pi * i / points - math.pi / 2
        r = r_outer if i % 2 == 0 else r_inner
        coords.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(coords, fill=fill)


def _topic_emoji(topic: str) -> str:
    """Return a comedy-appropriate emoji for the topic."""
    topic_lower = topic.lower()
    for keywords, emoji in _COMEDY_TOPIC_EMOJIS:
        if any(kw in topic_lower for kw in keywords):
            return emoji
    # Fall back to a random comedy reaction emoji seeded on the topic
    seed = sum(ord(c) for c in topic)
    return _DEFAULT_COMEDY_EMOJIS[seed % len(_DEFAULT_COMEDY_EMOJIS)]


def create_thumbnail(title: str, topic: str) -> Path:
    """Generate a 1280 × 720 JPEG comedy animation thumbnail for the given video *title*.

    Design language:
    - Vibrant neon gradient background
    - Cartoon-style starburst behind the title text
    - Bold white title with thick black stroke
    - Large comedy emoji accent
    - WOW/LOL/OMG accent overlay in the corner
    - Bright accent bar at the bottom with subscribe CTA

    Args:
        title: The video title to display prominently.
        topic: The trending topic (used for emoji and palette selection).

    Returns:
        Path to the saved JPEG thumbnail file.
    """
    # Seed randomness on the topic so thumbnails are consistent per topic
    rng = random.Random(sum(ord(c) for c in topic))

    # Pick gradient palette
    palette = rng.choice(_GRADIENT_PALETTES)
    accent_color = rng.choice(_ACCENT_COLORS)

    img = _make_gradient(THUMB_W, THUMB_H, palette[0], palette[1])
    draw = ImageDraw.Draw(img)

    # Draw cartoon starburst explosion behind the text area
    burst_cx = THUMB_W // 2
    burst_cy = THUMB_H // 2 - 40
    _draw_burst(draw, burst_cx, burst_cy, r_outer=380, r_inner=300, points=12,
                fill=(*accent_color, 180))  # type: ignore[arg-type]

    # Second smaller burst for depth
    _draw_burst(draw, burst_cx - 80, burst_cy + 30, r_outer=260, r_inner=210, points=8,
                fill=(255, 255, 255, 60))  # type: ignore[arg-type]

    # Subtle glow overlay for depth
    glow = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        [(THUMB_W // 2 - 450, 30), (THUMB_W // 2 + 450, THUMB_H - 80)],
        fill=(255, 255, 255, 40),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=50))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, glow)
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Large comedy emoji — top left
    emoji = _topic_emoji(topic)
    emoji_font = _load_font(160)
    try:
        draw.text((40, 20), emoji, font=emoji_font, fill=_TEXT_COLOR)
    except Exception:  # noqa: BLE001
        pass

    # Accent text (LOL / WOW / OMG) — top right, rotated feel via bold font
    accent_word = rng.choice(_ACCENT_TEXTS)
    accent_font = _load_font(80)
    try:
        # Position in top right corner
        bbox = draw.textbbox((0, 0), accent_word, font=accent_font)
        aw = bbox[2] - bbox[0]
        _draw_text_with_stroke(
            draw, (THUMB_W - aw - 40, 20), accent_word,
            font=accent_font,
            fill=(255, 255, 0),
            stroke_fill=(0, 0, 0),
            stroke_width=5,
        )
    except Exception:  # noqa: BLE001
        pass

    # Title text — bold, white, large, centred
    title_upper = title.upper()
    title_font = _load_font(100)
    max_text_w = THUMB_W - 120
    lines = _wrap_text(title_upper, title_font, max_text_w)
    line_height = 120
    total_text_h = len(lines) * line_height
    start_y = max(170, (THUMB_H - total_text_h) // 2 - 10)

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        _draw_text_with_stroke(
            draw, (60, y), line,
            font=title_font,
            fill=_TEXT_COLOR,
            stroke_fill=_STROKE_COLOR,
            stroke_width=6,
        )

    # Bottom accent bar — bright colour with subscribe CTA
    bar_y = THUMB_H - 80
    draw.rounded_rectangle(
        [(20, bar_y), (THUMB_W - 20, THUMB_H - 10)],
        radius=18,
        fill=(0, 0, 0, 180),  # type: ignore[arg-type]
    )

    watermark_font = _load_font(42)
    _draw_text_with_stroke(
        draw, (50, bar_y + 14), "▶ SUBSCRIBE — NEW FUNNY ANIMATION EVERY DAY!",
        font=watermark_font,
        fill=(255, 255, 0),
        stroke_fill=(0, 0, 0),
        stroke_width=2,
    )

    # Save
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    thumb_path = Path(tmp.name)
    tmp.close()
    img.save(thumb_path, "JPEG", quality=95, subsampling=0)
    logger.info("Comedy animation thumbnail saved to '%s'", thumb_path)
    return thumb_path
