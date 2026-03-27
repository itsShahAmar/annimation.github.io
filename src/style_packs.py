"""
style_packs.py — Cinematic food style packs for the Food Making Videos Factory.

Defines reusable visual and narrative style profiles that drive:
- Stock footage search queries (macro textures, plating, sizzle, steam cues)
- Color grade presets (warm golden hour, cool fresh, dramatic dark)
- Lighting descriptors used in script prompts
- Transition and pacing guides
- Caption colour themes per style

Key exports
-----------
- :func:`get_style_pack`        — retrieve a style pack by name
- :func:`select_style_for_topic` — auto-select best style for a topic
- :func:`build_scene_queries`   — enrich raw scene descriptions with style cues
- :func:`get_color_grade_params` — return color-grade config dict
- :data:`STYLE_PACKS`           — registry of all available packs

Usage::

    from src.style_packs import select_style_for_topic, build_scene_queries
    style = select_style_for_topic("creamy pasta carbonara")
    queries = build_scene_queries(["close-up pasta", "plating"], style)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ColorGrade:
    """Color grading parameters for a style pack."""
    name: str
    warmth: float           # -1.0 (cool) to +1.0 (warm)
    saturation: float       # 0.5 (muted) to 1.8 (vivid)
    contrast: float         # 0.5 (flat) to 1.8 (punchy)
    brightness: float       # -0.3 (dark) to +0.3 (bright)
    highlight_color: str    # hex — caption/overlay accent
    secondary_color: str    # hex — secondary accent


@dataclass
class StylePack:
    """A complete cinematic style profile for a food short.

    Attributes:
        name:               Short identifier (slug).
        display_name:       Human-readable name.
        description:        One-line description.
        target_foods:       Food types best suited for this style.
        visual_cues:        List of visual direction keywords added to
                            footage search queries.
        lighting_preset:    Lighting descriptor used in script prompts.
        plating_aesthetic:  Plating style description for prompt enrichment.
        texture_cues:       Texture/detail words for close-up searches.
        steam_sizzle_cues:  Action words for dynamic food shots.
        color_grade:        :class:`ColorGrade` config.
        transition_style:   Preferred transition type (``"crossfade"``, etc.).
        pacing:             ``"fast"`` / ``"medium"`` / ``"slow"``
        caption_theme:      Caption color theme identifier.
        prompt_modifiers:   Extra adjectives injected into AI script prompts.
    """
    name: str
    display_name: str
    description: str
    target_foods: list[str]
    visual_cues: list[str]
    lighting_preset: str
    plating_aesthetic: str
    texture_cues: list[str]
    steam_sizzle_cues: list[str]
    color_grade: ColorGrade
    transition_style: str = "crossfade"
    pacing: str = "medium"
    caption_theme: str = "warm_orange"
    prompt_modifiers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Style pack registry
# ---------------------------------------------------------------------------

STYLE_PACKS: dict[str, StylePack] = {

    "golden_hour": StylePack(
        name="golden_hour",
        display_name="Golden Hour",
        description="Warm, inviting golden tones. Perfect for comfort food and baked goods.",
        target_foods=["bread", "pasta", "baked", "soup", "stew", "casserole", "roast",
                      "comfort", "family", "homemade", "biryani", "curry"],
        visual_cues=["golden hour lighting", "warm kitchen", "rustic wooden table",
                     "natural light", "soft bokeh", "golden tones", "cozy atmosphere"],
        lighting_preset="warm natural window light, soft shadows, golden-amber haze",
        plating_aesthetic="rustic farmhouse — wooden boards, linen napkins, scattered herbs",
        texture_cues=["crispy golden crust", "caramelised surface", "glistening glaze",
                      "flaky layers", "bubbly cheese"],
        steam_sizzle_cues=["steam rising", "fresh from oven", "sizzling butter",
                           "golden bubbles", "crackling crust"],
        color_grade=ColorGrade(
            name="golden_hour",
            warmth=0.6,
            saturation=1.3,
            contrast=1.1,
            brightness=0.05,
            highlight_color="#FF8C00",
            secondary_color="#FFD700",
        ),
        transition_style="crossfade",
        pacing="medium",
        caption_theme="warm_orange",
        prompt_modifiers=["warm", "comforting", "golden", "irresistible", "home-style"],
    ),

    "macro_studio": StylePack(
        name="macro_studio",
        display_name="Macro Studio",
        description="Hyper-realistic close-up shots. Textures, bubbles, drips in extreme detail.",
        target_foods=["chocolate", "dessert", "ice cream", "sauce", "drizzle", "syrup",
                      "burger", "pizza", "cheese pull", "steak", "sushi"],
        visual_cues=["extreme macro shot", "food photography", "studio lighting",
                     "shallow depth of field", "ultra-detailed texture", "product photography"],
        lighting_preset="ring light or diffused LED panel, clean white or dark background",
        plating_aesthetic="minimalist studio — black or white slate, single garnish, precision drizzle",
        texture_cues=["gooey cheese pull", "crispy crunch", "smooth ganache", "bubbling caramel",
                      "glossy sheen", "perfect cross-section", "melting butter"],
        steam_sizzle_cues=["steam burst", "cheese stretch", "chocolate drip", "sizzling fat",
                           "caramel pull", "sauce pour", "ice cream melt"],
        color_grade=ColorGrade(
            name="macro_studio",
            warmth=0.2,
            saturation=1.6,
            contrast=1.4,
            brightness=0.0,
            highlight_color="#FF3366",
            secondary_color="#FF6B00",
        ),
        transition_style="cut",
        pacing="fast",
        caption_theme="hot_pink",
        prompt_modifiers=["ultra-realistic", "cinematic", "mouth-watering", "visually stunning",
                          "hyper-detailed", "close-up"],
    ),

    "street_energy": StylePack(
        name="street_energy",
        display_name="Street Energy",
        description="High-energy street food vibes. Fast cuts, vibrant colours, action shots.",
        target_foods=["taco", "street food", "kebab", "grill", "chaat", "noodle", "skewer",
                      "wrap", "sandwich", "food truck", "market", "hawker", "tikka"],
        visual_cues=["street food market", "food stall", "outdoor cooking", "charcoal grill",
                     "busy kitchen", "food vendor", "neon lights", "crowd", "energy"],
        lighting_preset="natural outdoor daylight or dramatic fire/flame ambient glow",
        plating_aesthetic="street style — paper wrap, metal tray, banana leaf, news print",
        texture_cues=["char marks", "flame-licked edges", "dripping sauce", "crispy skin",
                      "crunchy garnish", "juicy cross-section"],
        steam_sizzle_cues=["open flame sizzle", "smoke billowing", "fat dripping on coals",
                           "sauce spatter", "wok toss", "charcoal glow"],
        color_grade=ColorGrade(
            name="street_energy",
            warmth=0.4,
            saturation=1.5,
            contrast=1.3,
            brightness=0.0,
            highlight_color="#FF4500",
            secondary_color="#FFD700",
        ),
        transition_style="cut",
        pacing="fast",
        caption_theme="fiery_red",
        prompt_modifiers=["vibrant", "bold", "authentic", "irresistible", "street-style",
                          "high-energy", "fast-paced"],
    ),

    "fresh_and_clean": StylePack(
        name="fresh_and_clean",
        display_name="Fresh & Clean",
        description="Bright, airy, health-forward aesthetic. Perfect for salads, bowls, smoothies.",
        target_foods=["salad", "smoothie", "bowl", "healthy", "vegan", "fresh", "juice",
                      "fruit", "vegetable", "grain bowl", "avocado", "overnight oats"],
        visual_cues=["bright natural light", "white marble surface", "fresh ingredients",
                     "airy kitchen", "minimalist", "pastel tones", "overhead flat lay"],
        lighting_preset="bright soft daylight through white curtains, minimal shadows",
        plating_aesthetic="minimalist wellness — white bowl on marble, fresh herb garnish, lemon wedge",
        texture_cues=["dewy fresh vegetables", "vibrant colours", "glistening dressing",
                      "creamy smooth texture", "crisp lettuce", "colourful toppings"],
        steam_sizzle_cues=["fresh herb sprinkle", "dressing pour", "avocado slice reveal",
                           "berry drop", "ice clinking", "blender whirl"],
        color_grade=ColorGrade(
            name="fresh_and_clean",
            warmth=-0.1,
            saturation=1.4,
            contrast=1.0,
            brightness=0.15,
            highlight_color="#00CC88",
            secondary_color="#FFD700",
        ),
        transition_style="crossfade",
        pacing="medium",
        caption_theme="fresh_green",
        prompt_modifiers=["fresh", "vibrant", "healthy", "clean", "bright", "nourishing",
                          "colourful"],
    ),

    "dark_luxury": StylePack(
        name="dark_luxury",
        display_name="Dark Luxury",
        description="Moody, dramatic plating. Fine dining inspired with deep shadows and rich textures.",
        target_foods=["steak", "fine dining", "chocolate dessert", "truffle", "lobster",
                      "wine", "risotto", "seared", "reduction sauce", "plated dessert"],
        visual_cues=["dark background", "moody lighting", "fine dining plating",
                     "dramatic shadows", "luxury restaurant", "candlelight effect",
                     "dark marble surface"],
        lighting_preset="single-source side lighting, deep shadows, candlelit warmth",
        plating_aesthetic="fine dining — dark plate, micro-herb garnish, sauce swoosh, precision dots",
        texture_cues=["glossy reduction", "perfect sear marks", "caramelised crust",
                      "silky smooth sauce", "crispy microgreens", "truffle shavings"],
        steam_sizzle_cues=["gentle steam curl", "sauce pour in slow motion", "flame sear",
                           "butter basting", "reduction simmer", "garnish placement"],
        color_grade=ColorGrade(
            name="dark_luxury",
            warmth=0.3,
            saturation=1.2,
            contrast=1.6,
            brightness=-0.15,
            highlight_color="#C9A84C",
            secondary_color="#FF6B00",
        ),
        transition_style="crossfade",
        pacing="slow",
        caption_theme="gold",
        prompt_modifiers=["luxurious", "refined", "indulgent", "restaurant-worthy",
                          "cinematic", "dramatic", "world-class"],
    ),
}

# Default fallback style
_DEFAULT_STYLE = "golden_hour"

# ---------------------------------------------------------------------------
# Style keyword matching map for auto-selection
# ---------------------------------------------------------------------------
_STYLE_KEYWORD_MAP: dict[str, list[str]] = {
    "macro_studio": [
        "chocolate", "dessert", "cheese pull", "pizza", "burger", "steak", "sushi",
        "ice cream", "sauce", "drizzle", "syrup", "close-up", "texture",
    ],
    "street_energy": [
        "street food", "taco", "kebab", "grill", "chaat", "noodle", "skewer",
        "wrap", "sandwich", "tikka", "kabab", "pakora", "market", "hawker", "vendor",
        "spicy", "crispy fried",
    ],
    "fresh_and_clean": [
        "salad", "smoothie", "bowl", "healthy", "vegan", "fresh", "juice",
        "fruit", "vegetable", "grain bowl", "avocado", "oats", "light", "clean eating",
    ],
    "dark_luxury": [
        "fine dining", "truffle", "lobster", "wine", "risotto", "seared", "reduction",
        "plated dessert", "luxury", "michelin", "fancy",
    ],
    "golden_hour": [
        "pasta", "bread", "baked", "soup", "stew", "casserole", "roast", "comfort",
        "homemade", "biryani", "curry", "family", "pancake", "warm", "golden",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_style_pack(name: str) -> StylePack:
    """Retrieve a style pack by *name*.

    Args:
        name: Style pack identifier (e.g. ``"golden_hour"``).

    Returns:
        The matching :class:`StylePack`, or the default if not found.
    """
    return STYLE_PACKS.get(name, STYLE_PACKS[_DEFAULT_STYLE])


def select_style_for_topic(topic: str) -> StylePack:
    """Auto-select the best :class:`StylePack` for a given *topic*.

    Scans the topic string for keywords associated with each style and
    returns the best match.  Falls back to ``"golden_hour"`` if no match.

    Args:
        topic: The food topic string.

    Returns:
        The best-matching :class:`StylePack`.
    """
    lower = topic.lower()
    best_style = _DEFAULT_STYLE
    best_hits = 0

    for style_name, keywords in _STYLE_KEYWORD_MAP.items():
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > best_hits:
            best_hits = hits
            best_style = style_name

    return STYLE_PACKS[best_style]


def build_scene_queries(
    raw_scenes: list[str],
    style: StylePack,
    add_visual_cues: bool = True,
    add_texture_cues: bool = True,
) -> list[str]:
    """Enrich raw scene description strings with style-specific visual cues.

    For each scene, appends a subset of the style's visual and texture cues
    so that stock footage searches return more on-brand results.

    Args:
        raw_scenes:       Original scene description strings.
        style:            The :class:`StylePack` to apply.
        add_visual_cues:  If True, append a random visual cue.
        add_texture_cues: If True, append a random texture cue.

    Returns:
        List of enriched scene query strings.
    """
    enriched: list[str] = []
    for scene in raw_scenes:
        parts = [scene]
        if add_visual_cues and style.visual_cues:
            parts.append(random.choice(style.visual_cues))
        if add_texture_cues and style.texture_cues:
            parts.append(random.choice(style.texture_cues))
        enriched.append(", ".join(parts))
    return enriched


def get_color_grade_params(style: StylePack) -> dict[str, Any]:
    """Return color grade configuration as a plain dict for video_creator.

    Args:
        style: The :class:`StylePack` whose color grade to extract.

    Returns:
        Dict with keys matching config variable names for color grading.
    """
    cg = style.color_grade
    return {
        "warmth": cg.warmth,
        "saturation": cg.saturation,
        "contrast": cg.contrast,
        "brightness": cg.brightness,
        "highlight_color": cg.highlight_color,
        "secondary_color": cg.secondary_color,
        "style_name": style.name,
    }


def get_prompt_modifier_string(style: StylePack) -> str:
    """Return a comma-separated string of prompt modifiers for the style.

    Args:
        style: The :class:`StylePack` to extract modifiers from.

    Returns:
        Comma-separated modifier string (e.g. ``"warm, comforting, golden"``).
    """
    return ", ".join(style.prompt_modifiers)


def list_available_styles() -> list[dict[str, str]]:
    """Return a summary list of all registered style packs.

    Returns:
        List of dicts with ``name``, ``display_name``, ``description``.
    """
    return [
        {
            "name": sp.name,
            "display_name": sp.display_name,
            "description": sp.description,
            "pacing": sp.pacing,
            "caption_theme": sp.caption_theme,
        }
        for sp in STYLE_PACKS.values()
    ]
