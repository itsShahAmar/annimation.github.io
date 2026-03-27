"""
cta_engine.py — Conversion-focused CTA and hook engine for the Food Making Videos Factory.

Provides:
- Hook framework for the first 1–2 seconds optimised for viewer retention.
- CTA strategy matrix (soft / urgency / community) selected by context.
- Subscribe prompt insertion at natural narrative points (non-spammy).
- A/B variant generation for testing different approaches.
- Ending card logic and caption-level conversion wording templates.

Key exports
-----------
- :func:`generate_hook`          — first-second retention hook
- :func:`select_cta_strategy`    — pick CTA type based on context
- :func:`inject_cta_into_script` — insert CTAs at strategic positions
- :func:`generate_ab_variants`   — produce A/B pairs for testing
- :func:`get_ending_card_text`   — ending card wording
- :class:`CTAStrategy`           — enum of available CTA types
- :class:`CTAContext`            — context object used for strategy selection

Usage::

    from src.cta_engine import inject_cta_into_script, CTAContext
    ctx = CTAContext(topic="pasta carbonara", style="urgency", platform="youtube_shorts")
    script = inject_cta_into_script(script_text, ctx)
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------

class CTAStrategy(str, Enum):
    """Available CTA strategy types."""
    SOFT = "soft"               # gentle subscribe nudge, low pressure
    URGENCY = "urgency"         # FOMO-driven, time-sensitive framing
    COMMUNITY = "community"     # belonging / tribe framing
    VALUE = "value"             # promise of more value if they subscribe
    CHALLENGE = "challenge"     # dare the viewer to try it


@dataclass
class CTAContext:
    """Context used to select and personalise CTAs.

    Attributes:
        topic:          The food topic of the current short.
        style:          Requested CTA style (or ``"auto"`` for auto-select).
        platform:       Target platform (``"youtube_shorts"``, etc.).
        ab_variant:     ``"A"`` or ``"B"`` for A/B testing.
        engagement_cue: Optional engagement signal (e.g. ``"high_retention"``).
    """
    topic: str
    style: str = "auto"
    platform: str = "youtube_shorts"
    ab_variant: str = "A"
    engagement_cue: str = ""


@dataclass
class InjectedScript:
    """Script text with CTA injection metadata."""
    text: str
    hook: str
    cta_positions: list[tuple[int, str]] = field(default_factory=list)
    ending_card: str = ""
    strategy_used: CTAStrategy = CTAStrategy.SOFT
    ab_variant: str = "A"


# ---------------------------------------------------------------------------
# Hook templates — opening lines optimised for the first 1–2 seconds
# ---------------------------------------------------------------------------

_HOOK_TEMPLATES_A: list[str] = [
    "Stop scrolling — this {topic} is about to change the way you cook forever.",
    "You have been making {topic} wrong your entire life — here is the fix.",
    "This is the {topic} secret that restaurants do not want you to know.",
    "Wait until you see what one simple trick does to {topic}.",
    "Nobody talks about this when it comes to {topic} — but they should.",
    "Three seconds and you will never forget this {topic} technique.",
    "The moment I tried this {topic} method I never looked back.",
    "This {topic} is so good it should be illegal to keep it this easy.",
    "Everything you thought you knew about {topic} is about to change.",
    "I am obsessed with this {topic} and after this video you will be too.",
]

_HOOK_TEMPLATES_B: list[str] = [
    "POV: you just discovered the best {topic} recipe on the internet.",
    "Hear me out — this {topic} hits different and I need you to try it.",
    "If you only make one thing this week, make this {topic}.",
    "The {topic} recipe that made my whole family go completely silent.",
    "I tested every {topic} method so you do not have to — this one wins.",
    "This {topic} took me five minutes and everyone thought I ordered it.",
    "Real talk — this is the {topic} you have been looking for.",
    "My most requested {topic} recipe and I am finally sharing it.",
    "Warning: this {topic} is dangerously addictive.",
    "Finally — a {topic} recipe that actually works every single time.",
]

# ---------------------------------------------------------------------------
# CTA templates — three placement types: early (25%), mid (50–75%), end (95%)
# ---------------------------------------------------------------------------

_CTA_SOFT: dict[str, list[str]] = {
    "early": [
        "Hit follow so you never miss a recipe like this.",
        "Subscribe — I drop recipes like this every week.",
        "Tap follow if you love discovering recipes this good.",
    ],
    "mid": [
        "If this is looking good, give it a like — it really helps.",
        "Let me know in the comments if you are going to try this.",
        "Save this video so you have it when you are ready to cook.",
    ],
    "end": [
        "Subscribe for more recipes that actually impress people.",
        "Follow for a new recipe every single day.",
        "If you enjoyed this, subscribe — there is a lot more coming.",
    ],
}

_CTA_URGENCY: dict[str, list[str]] = {
    "early": [
        "Subscribe NOW before this method gets mainstream and everywhere.",
        "Follow fast — this {topic} trend is blowing up and you need to be ahead of it.",
        "Do not miss the next one — hit subscribe right now.",
    ],
    "mid": [
        "This technique is going viral — save it before it disappears from your feed.",
        "Like this if you want to see the full version before everyone else does.",
        "Comment 'recipe' and I will send you the exact ingredients list today.",
    ],
    "end": [
        "Subscribe now — the next video is even better and dropping soon.",
        "Hit follow before you forget — you will thank yourself later.",
        "This recipe is already going viral — subscribe so you never miss the next one.",
    ],
}

_CTA_COMMUNITY: dict[str, list[str]] = {
    "early": [
        "Join the family — we share recipes that actually taste this good every day.",
        "This community is obsessed with {topic} and I think you belong here.",
        "We are building a community of real food lovers — hit subscribe to join us.",
    ],
    "mid": [
        "Tag someone who needs to try this {topic} right now.",
        "Drop a fire emoji if this is going straight to your dinner table.",
        "Comment your favourite way to eat {topic} — I read every single one.",
    ],
    "end": [
        "Subscribe and join a community that eats this well every single week.",
        "The community is growing — hit follow and let us cook together.",
        "Welcome to the family — subscribe and I will see you in the next one.",
    ],
}

_CTA_VALUE: dict[str, list[str]] = {
    "early": [
        "Subscribe — every video teaches you a technique that makes you a better cook.",
        "Follow for daily tips that actually make a difference in the kitchen.",
        "Hit subscribe — the next video reveals the trick behind perfect {topic} every time.",
    ],
    "mid": [
        "I have a full breakdown of this technique on my channel — subscribe so you do not miss it.",
        "Save this — the variation at the end is even better than the original.",
        "Like this if you want the full recipe with measurements in the caption.",
    ],
    "end": [
        "Subscribe for more techniques that level up every meal you make.",
        "Follow for pro kitchen secrets that restaurants charge you for.",
        "Hit subscribe — next video teaches you three more upgrades to this dish.",
    ],
}

_CTA_CHALLENGE: dict[str, list[str]] = {
    "early": [
        "I dare you to try this {topic} and tell me it is not the best you have ever had.",
        "Challenge: make this {topic} tonight and report back in the comments.",
        "Bet you cannot eat just one bite of this {topic}.",
    ],
    "mid": [
        "Send this to the person who claims they cannot cook — problem solved.",
        "Try this and let me know in the comments if you pulled it off.",
        "I challenge you to find a faster way to make {topic} this good.",
    ],
    "end": [
        "Subscribe and take the weekly cooking challenge with the community.",
        "Follow and challenge yourself to make one new recipe every week.",
        "Subscribe — next week is an even harder challenge and you will want to be there.",
    ],
}

_CTA_BY_STRATEGY: dict[CTAStrategy, dict[str, list[str]]] = {
    CTAStrategy.SOFT: _CTA_SOFT,
    CTAStrategy.URGENCY: _CTA_URGENCY,
    CTAStrategy.COMMUNITY: _CTA_COMMUNITY,
    CTAStrategy.VALUE: _CTA_VALUE,
    CTAStrategy.CHALLENGE: _CTA_CHALLENGE,
}

# ---------------------------------------------------------------------------
# Ending card templates
# ---------------------------------------------------------------------------

_ENDING_CARDS: list[str] = [
    "Subscribe and follow for a new recipe every single day. 🍳",
    "Hit subscribe — your next favourite recipe is already waiting for you. 🔥",
    "Follow for daily food content that makes people say WOW. ✨",
    "Subscribe now and let us cook something incredible together every week. 👨‍🍳",
    "If this made you hungry, subscribe — there is so much more where this came from. 🤤",
    "New recipe dropping tomorrow — subscribe so you never miss it. ⏰",
    "The community is cooking every day — come join us. Subscribe now. ❤️",
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_hook(topic: str, ab_variant: str = "A") -> str:
    """Generate a retention-optimised first-second hook for *topic*.

    Args:
        topic:      The food topic.
        ab_variant: ``"A"`` or ``"B"`` — selects from different template pools.

    Returns:
        Formatted hook string with *topic* substituted in.
    """
    pool = _HOOK_TEMPLATES_A if ab_variant.upper() == "A" else _HOOK_TEMPLATES_B
    template = random.choice(pool)
    return template.format(topic=topic)


def select_cta_strategy(ctx: CTAContext) -> CTAStrategy:
    """Select the best CTA strategy for *ctx*.

    If ``ctx.style`` is ``"auto"``, picks based on ``engagement_cue``:
    - ``"high_retention"`` → COMMUNITY
    - ``"trending"``       → URGENCY
    - ``"educational"``    → VALUE
    - default              → SOFT (50%) or random choice

    Args:
        ctx: :class:`CTAContext` with topic, style, and cues.

    Returns:
        A :class:`CTAStrategy` enum value.
    """
    if ctx.style != "auto":
        try:
            return CTAStrategy(ctx.style)
        except ValueError:
            pass

    cue = ctx.engagement_cue.lower()
    if "retention" in cue or "community" in cue:
        return CTAStrategy.COMMUNITY
    if "trending" in cue or "viral" in cue or "urgency" in cue:
        return CTAStrategy.URGENCY
    if "educational" in cue or "tip" in cue or "technique" in cue:
        return CTAStrategy.VALUE
    if "challenge" in cue:
        return CTAStrategy.CHALLENGE

    # Default: 50% soft, 50% random
    if random.random() < 0.5:
        return CTAStrategy.SOFT
    return random.choice(list(CTAStrategy))


def _pick_cta(strategy: CTAStrategy, placement: str, topic: str) -> str:
    """Pick and format a CTA string for the given strategy and placement."""
    templates = _CTA_BY_STRATEGY[strategy].get(placement, _CTA_SOFT["mid"])
    template = random.choice(templates)
    return template.format(topic=topic)


def inject_cta_into_script(
    script_text: str,
    ctx: CTAContext,
) -> InjectedScript:
    """Insert CTA phrases at strategic positions in *script_text*.

    Injects at approximately 25%, 50–75%, and 95% of the script, choosing
    natural sentence boundaries to avoid interrupting narration flow.

    Args:
        script_text: The narration script text.
        ctx:         :class:`CTAContext` for strategy selection.

    Returns:
        :class:`InjectedScript` with modified text and metadata.
    """
    strategy = select_cta_strategy(ctx)
    sentences = re.split(r"(?<=[.!?])\s+", script_text.strip())
    n = len(sentences)

    if n < 3:
        # Too short to inject — just append end CTA
        end_cta = _pick_cta(strategy, "end", ctx.topic)
        full = script_text.strip() + " " + end_cta
        return InjectedScript(
            text=full,
            hook=generate_hook(ctx.topic, ctx.ab_variant),
            cta_positions=[(len(script_text), end_cta)],
            ending_card=get_ending_card_text(),
            strategy_used=strategy,
            ab_variant=ctx.ab_variant,
        )

    # Calculate injection points
    early_idx = max(1, n // 4)
    mid_idx = n // 2
    end_idx = max(n - 1, n - 1)

    early_cta = _pick_cta(strategy, "early", ctx.topic)
    mid_cta = _pick_cta(strategy, "mid", ctx.topic)
    end_cta = _pick_cta(strategy, "end", ctx.topic)

    # Build modified sentences list with CTAs inserted
    modified: list[str] = []
    cta_positions: list[tuple[int, str]] = []

    for i, sentence in enumerate(sentences):
        modified.append(sentence)
        if i == early_idx:
            modified.append(early_cta)
            cta_positions.append((i, early_cta))
        elif i == mid_idx:
            modified.append(mid_cta)
            cta_positions.append((i, mid_cta))
        elif i == end_idx:
            modified.append(end_cta)
            cta_positions.append((i, end_cta))

    final_text = " ".join(modified)
    hook = generate_hook(ctx.topic, ctx.ab_variant)

    return InjectedScript(
        text=final_text,
        hook=hook,
        cta_positions=cta_positions,
        ending_card=get_ending_card_text(),
        strategy_used=strategy,
        ab_variant=ctx.ab_variant,
    )


def generate_ab_variants(
    script_text: str,
    topic: str,
    platform: str = "youtube_shorts",
) -> tuple[InjectedScript, InjectedScript]:
    """Generate two A/B variant scripts with different hooks and CTA approaches.

    Args:
        script_text: Base narration script.
        topic:       Food topic.
        platform:    Target platform.

    Returns:
        ``(variant_a, variant_b)`` — two :class:`InjectedScript` objects.
    """
    ctx_a = CTAContext(topic=topic, style="auto", platform=platform, ab_variant="A")
    ctx_b = CTAContext(topic=topic, style="auto", platform=platform, ab_variant="B",
                       engagement_cue="trending")
    return inject_cta_into_script(script_text, ctx_a), inject_cta_into_script(script_text, ctx_b)


def get_ending_card_text() -> str:
    """Return a randomly selected ending card subscribe prompt.

    Returns:
        A short, energetic ending card string.
    """
    return random.choice(_ENDING_CARDS)


def get_subscribe_prompt_for_caption(variant: str = "A") -> str:
    """Return a short subscribe prompt suitable for caption overlay.

    Args:
        variant: ``"A"`` or ``"B"`` for different wording styles.

    Returns:
        Short caption-level subscribe string (<=6 words).
    """
    prompts_a = [
        "SUBSCRIBE for daily recipes! 🔥",
        "FOLLOW for more food magic! ✨",
        "TAP SUBSCRIBE — don't miss this! 📲",
    ]
    prompts_b = [
        "👆 FOLLOW for more! 🍳",
        "NEW RECIPE DAILY — SUBSCRIBE! ⏰",
        "JOIN THE FOOD FAM! ❤️",
    ]
    pool = prompts_a if variant.upper() == "A" else prompts_b
    return random.choice(pool)
