"""
viral_optimizer.py — Viral Optimization Engine for the Food Making Videos Factory.

Analyzes, scores, and enhances video scripts for maximum viral potential on
YouTube Shorts. Uses evidence-based engagement patterns drawn from high-performing
food content: hook strength analysis, emotional trigger detection, A/B title
scoring, CTA placement verification, and retention rate prediction.

Usage::

    from src.viral_optimizer import optimize_script_data, ViralScore

    score, enhanced = optimize_script_data(script_data, topic)
    print(f"Viral score: {score.overall:.2f} — {score.label}")
"""

import hashlib
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Viral score dataclass
# ---------------------------------------------------------------------------

@dataclass
class ViralScore:
    """Composite viral-potential score for a food video script.

    All sub-scores are normalised to the range 0.0 – 1.0.
    ``overall`` is a weighted average of the sub-scores.
    ``label`` is a human-readable tier classification.
    ``suggestions`` lists actionable improvements detected.
    """

    hook_strength: float = 0.0        # How compelling is the opening hook
    emotional_impact: float = 0.0     # Emotional triggers present in the script
    cta_placement: float = 0.0        # Strategic placement of CTAs
    topic_trendiness: float = 0.0     # How trending / search-hungry the topic is
    title_clickthrough: float = 0.0   # Expected click-through rate from title
    overall: float = 0.0              # Weighted composite score
    label: str = "standard"           # viral / high_potential / standard / below_average
    retention_estimate: float = 0.0   # Predicted viewer-retention rate (0–1)
    suggestions: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hook strength signals — phrases that create curiosity gaps / pattern interrupts
# ---------------------------------------------------------------------------
_STRONG_HOOK_SIGNALS: list[str] = [
    "you have been making", "you've been making",
    "nobody told me", "chefs have been hiding",
    "secret ingredient", "forget everything",
    "this changes everything", "you will never",
    "the reason your", "this one trick",
    "wait until you see", "the truth about",
    "i tested", "what if i told you",
    "viral", "the real way", "the only method",
    "this is why", "finally explained",
]

_EMOTIONAL_TRIGGER_WORDS: list[str] = [
    "shocking", "incredible", "unbelievable", "secret", "hidden",
    "transform", "never", "always", "perfect", "best ever",
    "blow your mind", "changed", "mistake", "wrong", "fix",
    "restaurant", "five-star", "professional", "chef", "gourmet",
    "family", "guests", "culinary school", "comfort", "simple",
]

_CTA_MARKERS: list[str] = [
    "like", "subscribe", "follow", "comment", "share", "save",
    "tag", "tap", "hit", "drop", "let me know",
]

# Trending food keyword patterns that score well in search
_TRENDING_FOOD_KEYWORDS: list[str] = [
    "air fryer", "viral", "hack", "secret", "one pan",
    "five minute", "5 minute", "one ingredient", "restaurant quality",
    "quick", "easy", "budget", "cheap", "five ingredients",
    "no bake", "meal prep", "weight loss", "healthy", "crispy",
    "fluffy", "creamy", "perfect", "best", "ultimate",
    "tiktok", "trending", "hack", "tips", "mistakes",
    "biryani", "karahi", "tikka", "butter chicken", "pakora",
    "samosa", "naan", "paratha", "daal", "haleem",
]

# Power words that boost click-through rate in titles
_TITLE_POWER_WORDS: list[str] = [
    "secret", "viral", "hack", "trick", "method", "revealed",
    "finally", "nobody", "ever", "perfect", "ultimate", "best",
    "wrong", "mistake", "fix", "easy", "quick", "simple",
    "restaurant", "chef", "professional", "gourmet", "incredible",
    "changed", "transform", "genius", "insane", "mind-blowing",
]

# Question-based title patterns drive high CTR
_TITLE_QUESTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bwhy\b", re.I),
    re.compile(r"\bhow to\b", re.I),
    re.compile(r"\bwhat if\b", re.I),
    re.compile(r"\bwhat is\b", re.I),
    re.compile(r"\?\s*$"),
]

# ---------------------------------------------------------------------------
# A/B title variant generator
# ---------------------------------------------------------------------------

_TITLE_VARIANT_TEMPLATES: list[str] = [
    # Curiosity-gap angle
    "The {topic} Secret That Changes Everything \U0001f92f",
    "Why Everyone Is Making {topic} Wrong \U0001f525",
    "This Is The Only {topic} Method That Actually Works \U0001f4af",
    # Number-based angle
    "3 Mistakes Ruining Your {topic} (And The Fix) \u26a0\ufe0f",
    "The 1 Ingredient That Makes {topic} Perfect Every Time \u2728",
    "5-Minute {topic} That Tastes Like A Restaurant Made It \u2764\ufe0f",
    # Emotional angle
    "The {topic} Recipe Your Family Will Request Every Week \U0001f60d",
    "Stop Wasting Money On {topic} — Make This At Home Instead \U0001f4b0",
    "I Wish I Knew This {topic} Trick 10 Years Ago \u23f0",
    # Authority angle
    "Professional Chef Reveals The Real Secret To {topic} \U0001f468\u200d\U0001f373",
    "This Is How Restaurant {topic} Actually Gets Made \U0001f3e0",
    "The Science Behind Perfect {topic} Finally Explained \U0001f9ea",
    # Urgency / FOMO angle
    "Make {topic} Tonight — You Will Never Order Takeout Again \U0001f6d2",
    "Everyone Is Talking About This {topic} And Here Is Why \U0001f4c8",
    "The Viral {topic} Recipe That Has 50 Million Views \U0001f525",
]


def _fill_template(template: str, topic: str) -> str:
    """Replace ``{topic}`` in *template* with the actual topic string."""
    filled = template.replace("{topic}", topic)
    return re.sub(r"\s+", " ", filled).strip()


def generate_title_variants(topic: str, base_title: str, n: int = 3) -> list[str]:
    """Generate *n* A/B title variants for the given *topic*.

    Always includes the original *base_title* as the first option, then
    generates novel variants from ``_TITLE_VARIANT_TEMPLATES`` using a
    topic-seeded RNG for reproducibility within the same hour.

    Args:
        topic:      The food topic being covered.
        base_title: The original AI- or template-generated title.
        n:          Total number of variants to return (including base).

    Returns:
        List of title strings, starting with *base_title*.
    """
    seed = int(hashlib.md5(topic.encode()).hexdigest()[:8], 16) ^ (int(time.time()) // 3600)
    rng = random.Random(seed)

    templates = _TITLE_VARIANT_TEMPLATES.copy()
    rng.shuffle(templates)

    variants = [base_title]
    for tmpl in templates:
        if len(variants) >= n:
            break
        variant = _fill_template(tmpl, topic.title())
        if len(variant) <= 100 and variant not in variants:
            variants.append(variant)

    return variants[:n]


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _score_hook(hook: str, script: str) -> float:
    """Return a 0–1 hook-strength score based on linguistic signals."""
    combined = (hook + " " + script[:200]).lower()
    hits = sum(1 for sig in _STRONG_HOOK_SIGNALS if sig in combined)
    # Check if it starts with an action/curiosity statement
    first_sentence = re.split(r"[.!?]", hook.strip())[0].lower() if hook else ""
    bonus = 0.15 if any(w in first_sentence for w in ("secret", "trick", "wrong", "never", "hack")) else 0.0
    score = min(1.0, hits * 0.15 + bonus)
    return round(score, 3)


def _score_emotional_impact(script: str) -> float:
    """Return a 0–1 emotional impact score based on trigger word density."""
    words = script.lower().split()
    if not words:
        return 0.0
    hits = sum(1 for w in words if any(t in w for t in _EMOTIONAL_TRIGGER_WORDS))
    density = hits / len(words)
    return round(min(1.0, density * 20), 3)  # scale: ~5% density = 1.0


def _score_cta_placement(script: str) -> float:
    """Return a 0–1 score for how strategically CTAs are distributed.

    The ideal pattern hits CTAs at ~25%, ~50%, ~75%, and ~95% of the script.
    """
    words = script.lower().split()
    n = len(words)
    if n < 20:
        return 0.0

    cta_positions: list[float] = []
    for i, word in enumerate(words):
        if any(cta in word for cta in _CTA_MARKERS):
            cta_positions.append(i / n)

    if not cta_positions:
        return 0.0

    ideal = [0.25, 0.50, 0.75, 0.95]
    matched = 0
    for target in ideal:
        if any(abs(p - target) < 0.12 for p in cta_positions):
            matched += 1

    return round(matched / len(ideal), 3)


def _score_topic_trendiness(topic: str) -> float:
    """Return a 0–1 score for how trend-hungry the topic is."""
    lower = topic.lower()
    hits = sum(1 for kw in _TRENDING_FOOD_KEYWORDS if kw in lower)
    return round(min(1.0, hits * 0.25), 3)


def _score_title_clickthrough(title: str) -> float:
    """Return a 0–1 click-through rate estimate based on title signals."""
    lower = title.lower()

    power_hits = sum(1 for pw in _TITLE_POWER_WORDS if pw in lower)
    question_bonus = 0.15 if any(p.search(title) for p in _TITLE_QUESTION_PATTERNS) else 0.0
    number_bonus = 0.10 if re.search(r"\b[1-9]\b", title) else 0.0
    emoji_bonus = 0.10 if re.search(r"[\U00010000-\U0010ffff\U0001F300-\U0001F9FF]", title) else 0.0
    length_bonus = 0.10 if 40 <= len(title) <= 70 else 0.0

    score = min(1.0, power_hits * 0.12 + question_bonus + number_bonus + emoji_bonus + length_bonus)
    return round(score, 3)


def _estimate_retention(hook_score: float, emotional_score: float, cta_score: float) -> float:
    """Predict viewer-retention rate from sub-scores.

    Based on the pattern that strong hooks, emotional resonance, and
    well-placed CTAs are the three biggest drivers of Shorts retention.
    Returns a value between 0 and 1 (e.g. 0.65 = ~65% retention).
    """
    weighted = (hook_score * 0.45) + (emotional_score * 0.35) + (cta_score * 0.20)
    # Add a base retention floor (average Shorts gets ~40%)
    base = 0.40
    return round(min(1.0, base + weighted * 0.40), 3)


def _classify_label(overall: float) -> str:
    """Map overall score to a human-readable tier label."""
    if overall >= 0.80:
        return "viral"
    if overall >= 0.65:
        return "high_potential"
    if overall >= 0.45:
        return "standard"
    return "below_average"


# ---------------------------------------------------------------------------
# Suggestion engine
# ---------------------------------------------------------------------------

def _generate_suggestions(
    script: str,
    hook: str,
    title: str,
    hook_score: float,
    emotional_score: float,
    cta_score: float,
    topic_score: float,
    ctr_score: float,
) -> list[str]:
    """Generate a list of actionable improvement suggestions."""
    suggestions: list[str] = []

    if hook_score < 0.3:
        suggestions.append(
            "Hook is weak — open with a curiosity gap, shocking fact, or pattern interrupt "
            "(e.g. 'You have been making {topic} wrong your entire life')"
        )
    if emotional_score < 0.25:
        suggestions.append(
            "Add more emotional trigger words: 'secret', 'transform', 'restaurant-quality', "
            "'mistake', or 'incredible' to boost emotional resonance"
        )
    if cta_score < 0.5:
        suggestions.append(
            "CTAs are missing or poorly timed — add Like CTA at ~25%, Subscribe at ~50%, "
            "Comment at ~75%, and Share near the end"
        )
    if topic_score < 0.2:
        suggestions.append(
            "Topic lacks trending keywords — consider incorporating 'hack', 'secret', "
            "'quick', 'perfect', or 'viral' into the topic angle"
        )
    if ctr_score < 0.3:
        suggestions.append(
            "Title CTR could be higher — add a power word ('secret', 'viral', 'hack'), "
            "a number, or an emoji to the title"
        )
    if len(hook) < 20:
        suggestions.append(
            "Hook text is very short — expand it to at least 1-2 complete sentences "
            "that create suspense or challenge an assumption"
        )
    words = script.split()
    if len(words) < 80:
        suggestions.append(
            f"Script is short ({len(words)} words) — aim for 120–180 words for better "
            "narration depth and retention"
        )

    return suggestions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_script(script_data: dict[str, Any], topic: str) -> ViralScore:
    """Calculate a :class:`ViralScore` for the given *script_data* and *topic*.

    Args:
        script_data: Dict with keys ``script``, ``hook``, ``title``, etc.
        topic:       The food topic the video covers.

    Returns:
        A fully populated :class:`ViralScore` instance.
    """
    script = script_data.get("script", "")
    hook = script_data.get("hook", "")
    title = script_data.get("title", "")

    h = _score_hook(hook, script)
    e = _score_emotional_impact(script)
    c = _score_cta_placement(script)
    t = _score_topic_trendiness(topic)
    r = _score_title_clickthrough(title)

    # Weighted composite (hook & CTR drive most value)
    overall = round(h * 0.30 + e * 0.20 + c * 0.20 + t * 0.10 + r * 0.20, 3)
    retention = _estimate_retention(h, e, c)
    label = _classify_label(overall)

    suggestions = _generate_suggestions(script, hook, title, h, e, c, t, r)

    return ViralScore(
        hook_strength=h,
        emotional_impact=e,
        cta_placement=c,
        topic_trendiness=t,
        title_clickthrough=r,
        overall=overall,
        label=label,
        retention_estimate=retention,
        suggestions=suggestions,
    )


def _inject_engagement_boosters(script: str) -> str:
    """Subtly enhance engagement by inserting micro-CTA phrases at strategic positions.

    Only adds phrases that are not already present. Inserts at the natural sentence
    boundaries closest to the 25%, 50%, 75%, and 95% word-count targets.
    """
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())
    n = len(sentences)
    if n < 4:
        return script

    script_lower = script.lower()

    # Define micro-CTAs to inject if missing
    injections: list[tuple[float, str]] = []

    if not any(kw in script_lower for kw in ("like", "hit like", "tap like")):
        injections.append((0.25, "Hit like if this is already changing how you think about cooking."))
    if not any(kw in script_lower for kw in ("subscribe", "follow")):
        injections.append((0.50, "Follow for more kitchen secrets that actually work."))
    if not any(kw in script_lower for kw in ("comment", "let me know", "drop a comment")):
        injections.append((0.75, "Comment below with your results — I read every single one."))

    if not injections:
        return script

    for target_ratio, phrase in sorted(injections, key=lambda x: x[0]):
        insert_at = max(0, min(n - 1, int(n * target_ratio)))
        sentences.insert(insert_at, phrase)
        n = len(sentences)

    return " ".join(sentences)


def _boost_title(title: str, topic: str) -> str:
    """Add a power word and emoji to a title that is lacking them, if possible.

    Returns the original title unchanged if it already scores well.
    """
    if _score_title_clickthrough(title) >= 0.50:
        return title

    # Add emoji if missing
    has_emoji = bool(re.search(r"[\U00010000-\U0010ffff\U0001F300-\U0001F9FF]", title))
    food_emoji = "\U0001f373"  # 🍳
    if not has_emoji:
        title = title + " " + food_emoji

    # Add a power word if none present
    lower = title.lower()
    if not any(pw in lower for pw in ("secret", "viral", "hack", "perfect", "wrong")):
        title = "The Secret to " + title.lstrip("The the ")

    if len(title) > 100:
        title = title[:97] + "..."

    return title


def optimize_script_data(
    script_data: dict[str, Any], topic: str
) -> tuple[ViralScore, dict[str, Any]]:
    """Score and enhance *script_data* for maximum viral potential.

    Applies the following optimizations when ``VIRAL_OPTIMIZATION_ENABLED`` is True:
    - Injects missing engagement CTAs at strategic positions (when ``VIRAL_ENGAGEMENT_BOOST``).
    - Boosts the title with a power word / emoji if its CTR score is low.
    - Generates A/B title variants for reporting (when ``VIRAL_A_B_TITLES``).
    - Adds ``viral_score``, ``title_variants``, and ``retention_estimate`` to the result.

    Args:
        script_data: Dict from :func:`src.scriptwriter.generate_script`.
        topic:       The food topic the video covers.

    Returns:
        Tuple of (:class:`ViralScore`, enhanced *script_data* dict).
    """
    enhanced = dict(script_data)

    if not getattr(config, "VIRAL_OPTIMIZATION_ENABLED", True):
        score = score_script(enhanced, topic)
        return score, enhanced

    # 1. Inject engagement boosters into script
    if getattr(config, "VIRAL_ENGAGEMENT_BOOST", True):
        enhanced["script"] = _inject_engagement_boosters(enhanced.get("script", ""))
        enhanced["caption_script"] = re.sub(r"\s+", " ", enhanced["script"]).strip()

    # 2. Boost title if CTR score is low
    enhanced["title"] = _boost_title(enhanced.get("title", ""), topic)

    # 3. Generate A/B title variants
    if getattr(config, "VIRAL_A_B_TITLES", True):
        n_variants = getattr(config, "VIRAL_TITLE_VARIANTS", 3)
        enhanced["title_variants"] = generate_title_variants(
            topic, enhanced["title"], n=n_variants
        )
    else:
        enhanced["title_variants"] = [enhanced["title"]]

    # 4. Score the enhanced script
    score = score_script(enhanced, topic)
    enhanced["viral_score"] = score.overall
    enhanced["viral_label"] = score.label
    enhanced["retention_estimate"] = score.retention_estimate

    # 5. Log suggestions for transparency
    if score.suggestions:
        logger.info(
            "Viral optimizer — score %.2f (%s) | %d suggestions for topic '%s':",
            score.overall, score.label, len(score.suggestions), topic,
        )
        for s in score.suggestions:
            logger.info("  • %s", s)
    else:
        logger.info(
            "Viral optimizer — score %.2f (%s) | no improvements needed for topic '%s'",
            score.overall, score.label, topic,
        )

    return score, enhanced
