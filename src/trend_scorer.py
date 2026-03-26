"""
trend_scorer.py — Trend intelligence module for the Food Making Videos Factory.

Provides weighted trend scoring based on recency, velocity, relevance to the
food niche, and engagement proxies.  Also handles deduplication, novelty
checks against previously-used topics, and produces machine-readable daily
trend digest artifacts.

Key exports
-----------
- :func:`score_topics`          — score a list of raw topic strings
- :func:`deduplicate_topics`    — remove near-duplicate topics
- :func:`filter_novel_topics`   — exclude recently-used topics
- :func:`select_best_topic`     — end-to-end selection with scoring + filters
- :func:`save_trend_digest`     — write a JSON daily digest artifact
- :class:`ScoredTopic`          — typed dataclass for a scored topic entry

Usage::

    from src.trend_scorer import select_best_topic, save_trend_digest
    topic = select_best_topic(raw_topics, source_weights)
    save_trend_digest(scored_topics, output_dir="artifacts")
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Food niche keyword sets — used to boost relevance score
# ---------------------------------------------------------------------------
_FOOD_PRIMARY_KW: frozenset[str] = frozenset({
    "recipe", "cook", "food", "eat", "meal", "dish", "ingredient", "kitchen",
    "bake", "grill", "fry", "roast", "sauce", "soup", "salad", "pasta",
    "chicken", "beef", "fish", "vegetable", "dessert", "breakfast", "lunch",
    "dinner", "snack", "healthy", "quick", "easy", "homemade", "restaurant",
    "chef", "street food", "viral", "trending", "delicious", "tasty", "crispy",
    "fluffy", "juicy", "creamy", "spicy", "sweet", "savory", "biryani",
    "ramen", "pizza", "burger", "sushi", "taco", "curry", "noodle",
})

_FOOD_SECONDARY_KW: frozenset[str] = frozenset({
    "tip", "hack", "trick", "secret", "method", "technique", "how to",
    "best", "perfect", "ultimate", "amazing", "incredible", "must try",
    "you need", "everyone", "everyone is", "viral", "asmr", "mukbang",
    "air fryer", "instant pot", "one pan", "5 ingredient", "30 minute",
    "meal prep",
})

# Topics to always reject — explicit blacklist
_FORBIDDEN_TERMS: list[str] = [
    "politics", "election", "war", "violence", "death", "accident",
    "crime", "tragedy", "controversial",
]

# Weight constants for each scoring dimension
_W_RECENCY: float = 0.20       # boosted if topic has timestamps from recent hours
_W_VELOCITY: float = 0.20      # how rapidly the topic is rising (cross-source count)
_W_RELEVANCE: float = 0.35     # food-niche keyword match strength
_W_ENGAGEMENT: float = 0.25    # engagement proxy (ranking position across sources)

# Novelty: topics used within this many seconds are penalised
_NOVELTY_WINDOW_SECONDS: int = 86_400 * 3   # 3 days


@dataclass
class ScoredTopic:
    """A raw topic string with computed scores and metadata."""

    topic: str
    raw_score: float            # weighted composite 0–1
    recency_score: float        # 0–1
    velocity_score: float       # 0–1
    relevance_score: float      # 0–1
    engagement_score: float     # 0–1
    source_count: int           # how many sources mentioned it
    is_novel: bool              # True if not recently used
    rejected: bool = False      # True if blocked by blacklist
    rejection_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _relevance_score(topic: str) -> float:
    """Compute a 0–1 food-niche relevance score for *topic*.

    Checks for primary keywords (strong signal) and secondary keywords
    (weak signal) and normalises to [0, 1].
    """
    lower = topic.lower()
    primary_hits = sum(1 for kw in _FOOD_PRIMARY_KW if kw in lower)
    secondary_hits = sum(1 for kw in _FOOD_SECONDARY_KW if kw in lower)
    raw = primary_hits * 2.0 + secondary_hits * 0.5
    # Clamp to [0, 1] — a 4-hit primary match is already "perfect"
    return min(raw / 8.0, 1.0)


def _is_blacklisted(topic: str) -> tuple[bool, str]:
    """Return (True, reason) if *topic* matches the forbidden terms list."""
    lower = topic.lower()
    for term in _FORBIDDEN_TERMS:
        if term in lower:
            return True, f"contains forbidden term '{term}'"
    return False, ""


def _normalise(topic: str) -> str:
    """Lowercase and collapse whitespace for deduplication."""
    return re.sub(r"\s+", " ", topic.strip().lower())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_topics(
    topics: Sequence[str],
    source_weights: dict[str, float] | None = None,
    source_membership: dict[str, list[str]] | None = None,
) -> list[ScoredTopic]:
    """Score a list of raw topic strings and return :class:`ScoredTopic` objects.

    Args:
        topics:             Raw topic strings (de-duplicated or not).
        source_weights:     Optional mapping of source name → weight multiplier.
                            e.g. ``{"google_trends": 1.5, "newsapi": 0.8}``
        source_membership:  Optional mapping of source name → list of topics
                            belonging to that source, used to compute velocity
                            (how many sources mention the same topic).

    Returns:
        List of :class:`ScoredTopic`, unsorted.
    """
    source_weights = source_weights or {}
    source_membership = source_membership or {}

    # Build cross-source membership for velocity calculation
    topic_source_count: dict[str, int] = {}
    for source_topics in source_membership.values():
        seen_in_source: set[str] = set()
        for t in source_topics:
            key = _normalise(t)
            if key not in seen_in_source:
                seen_in_source.add(key)
                topic_source_count[key] = topic_source_count.get(key, 0) + 1

    total_sources = max(len(source_membership), 1)
    n = len(topics)
    scored: list[ScoredTopic] = []

    for rank, topic in enumerate(topics):
        key = _normalise(topic)

        # Blacklist check
        blacklisted, reason = _is_blacklisted(topic)
        if blacklisted:
            scored.append(ScoredTopic(
                topic=topic,
                raw_score=0.0,
                recency_score=0.0,
                velocity_score=0.0,
                relevance_score=0.0,
                engagement_score=0.0,
                source_count=0,
                is_novel=True,
                rejected=True,
                rejection_reason=reason,
            ))
            logger.debug("Topic rejected: '%s' (%s)", topic, reason)
            continue

        # Engagement proxy: position-based (top-ranked = higher engagement)
        engagement = 1.0 - (rank / max(n - 1, 1))

        # Relevance: keyword match
        relevance = _relevance_score(topic)

        # Velocity: fraction of sources mentioning this topic
        src_count = topic_source_count.get(key, 1)
        velocity = min(src_count / total_sources, 1.0)

        # Recency: we don't have timestamps in the raw topics, so we use a
        # simple heuristic: topics appearing earlier in the list are more
        # recent (sources typically return newest first).
        recency = 1.0 - (rank / max(n - 1, 1)) * 0.5   # partial decay

        # Composite weighted score
        raw = (
            _W_RECENCY * recency
            + _W_VELOCITY * velocity
            + _W_RELEVANCE * relevance
            + _W_ENGAGEMENT * engagement
        )

        scored.append(ScoredTopic(
            topic=topic,
            raw_score=round(raw, 4),
            recency_score=round(recency, 4),
            velocity_score=round(velocity, 4),
            relevance_score=round(relevance, 4),
            engagement_score=round(engagement, 4),
            source_count=src_count,
            is_novel=True,   # updated by filter_novel_topics
        ))

    logger.info("Scored %d topics (%d rejected by blacklist)", len(scored), sum(1 for s in scored if s.rejected))
    return scored


def deduplicate_topics(topics: list[str]) -> list[str]:
    """Remove near-duplicate topics, keeping the first occurrence.

    Uses normalised lowercase comparison plus simple Jaccard similarity
    for near-matches (>= 0.75 overlap on word sets).

    Args:
        topics: List of raw topic strings.

    Returns:
        Deduplicated list preserving original order.
    """
    seen_keys: set[str] = set()
    seen_word_sets: list[set[str]] = []
    deduped: list[str] = []

    for topic in topics:
        key = _normalise(topic)
        if key in seen_keys:
            continue

        words = set(re.findall(r"\w+", key))

        # Jaccard near-duplicate check
        is_near_dup = False
        for existing_words in seen_word_sets:
            if not words or not existing_words:
                continue
            intersection = len(words & existing_words)
            union = len(words | existing_words)
            if union > 0 and intersection / union >= 0.75:
                is_near_dup = True
                break

        if not is_near_dup:
            seen_keys.add(key)
            seen_word_sets.append(words)
            deduped.append(topic)

    removed = len(topics) - len(deduped)
    if removed:
        logger.debug("Deduplicated %d near-duplicate topics (kept %d)", removed, len(deduped))
    return deduped


def filter_novel_topics(
    scored: list[ScoredTopic],
    history_path: str | Path = "artifacts/topic_history.json",
) -> list[ScoredTopic]:
    """Mark topics as ``is_novel=False`` if they were recently used.

    Reads the topic history from *history_path* (created by
    :func:`record_used_topic`) and penalises topics that appeared within
    the last :data:`_NOVELTY_WINDOW_SECONDS`.

    Args:
        scored:       List of :class:`ScoredTopic` to annotate.
        history_path: Path to the JSON history file.

    Returns:
        The same list with ``is_novel`` updated in place.
    """
    history_path = Path(history_path)
    history: dict[str, float] = {}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load topic history from '%s': %s", history_path, exc)

    now = time.time()
    penalised = 0
    for st in scored:
        key = _normalise(st.topic)
        last_used = history.get(key)
        if last_used is not None and (now - last_used) < _NOVELTY_WINDOW_SECONDS:
            st.is_novel = False
            # Apply 50% score penalty for recently-used topics
            st.raw_score = round(st.raw_score * 0.5, 4)
            penalised += 1

    if penalised:
        logger.info("Penalised %d recently-used topics for novelty", penalised)
    return scored


def record_used_topic(
    topic: str,
    history_path: str | Path = "artifacts/topic_history.json",
) -> None:
    """Record *topic* as used at the current timestamp in the history file.

    Creates the history file and parent directories if they don't exist.

    Args:
        topic:        The topic string that was selected.
        history_path: Path to the JSON history file.
    """
    history_path = Path(history_path)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    history: dict[str, float] = {}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass

    history[_normalise(topic)] = time.time()

    # Evict entries older than the novelty window to keep the file compact
    cutoff = time.time() - _NOVELTY_WINDOW_SECONDS
    history = {k: v for k, v in history.items() if v >= cutoff}

    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    logger.debug("Recorded used topic '%s' in history at '%s'", topic, history_path)


def select_best_topic(
    raw_topics: list[str],
    source_membership: dict[str, list[str]] | None = None,
    source_weights: dict[str, float] | None = None,
    history_path: str | Path = "artifacts/topic_history.json",
    top_k: int = 5,
) -> tuple[str, list[ScoredTopic]]:
    """End-to-end topic selection with scoring, deduplication, and novelty.

    Args:
        raw_topics:         Combined raw topic list (all sources merged).
        source_membership:  Optional per-source topic lists for velocity.
        source_weights:     Optional per-source weight multipliers.
        history_path:       Path to the topic history file.
        top_k:              Number of top candidates to choose from randomly.

    Returns:
        ``(selected_topic, all_scored_topics)`` — the winner plus the full
        scored list for digest/logging purposes.
    """
    import random

    deduped = deduplicate_topics(raw_topics)
    scored = score_topics(deduped, source_weights=source_weights, source_membership=source_membership)
    scored = filter_novel_topics(scored, history_path=history_path)

    # Only consider non-rejected topics
    candidates = [s for s in scored if not s.rejected]
    if not candidates:
        logger.warning("All topics rejected — falling back to first raw topic")
        return raw_topics[0] if raw_topics else "quick dinner recipe", scored

    # Sort by composite score descending
    candidates.sort(key=lambda s: s.raw_score, reverse=True)
    top_candidates = candidates[:top_k]

    # Weighted random selection from top-k (probability proportional to score)
    total = sum(s.raw_score for s in top_candidates)
    if total <= 0:
        chosen = random.choice(top_candidates)
    else:
        r = random.uniform(0, total)
        cumulative = 0.0
        chosen = top_candidates[-1]
        for st in top_candidates:
            cumulative += st.raw_score
            if r <= cumulative:
                chosen = st
                break

    logger.info(
        "Selected topic: '%s' (score=%.4f, relevance=%.4f, velocity=%.4f, novel=%s)",
        chosen.topic, chosen.raw_score, chosen.relevance_score, chosen.velocity_score, chosen.is_novel,
    )
    return chosen.topic, scored


def save_trend_digest(
    scored_topics: list[ScoredTopic],
    selected_topic: str,
    output_dir: str | Path = "artifacts",
) -> Path:
    """Write a machine-readable daily trend digest JSON artifact.

    The digest includes:
    - Timestamp and selected topic
    - Top-20 scored topics with all scores
    - Summary statistics

    Args:
        scored_topics:  Full scored topic list from :func:`select_best_topic`.
        selected_topic: The topic that was ultimately selected.
        output_dir:     Directory for the digest file.

    Returns:
        Path to the written digest file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%dT%H%M%S")
    digest_path = output_dir / f"trend_digest_{ts}.json"

    non_rejected = [s for s in scored_topics if not s.rejected]
    top_20 = sorted(non_rejected, key=lambda s: s.raw_score, reverse=True)[:20]

    digest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_topic": selected_topic,
        "total_topics_evaluated": len(scored_topics),
        "total_rejected": sum(1 for s in scored_topics if s.rejected),
        "total_novel": sum(1 for s in scored_topics if s.is_novel and not s.rejected),
        "top_20": [s.to_dict() for s in top_20],
        "stats": {
            "avg_relevance": round(sum(s.relevance_score for s in non_rejected) / max(len(non_rejected), 1), 4),
            "avg_velocity": round(sum(s.velocity_score for s in non_rejected) / max(len(non_rejected), 1), 4),
            "avg_raw_score": round(sum(s.raw_score for s in non_rejected) / max(len(non_rejected), 1), 4),
        },
    }

    digest_path.write_text(json.dumps(digest, indent=2), encoding="utf-8")
    logger.info("Trend digest saved to '%s'", digest_path)
    return digest_path
