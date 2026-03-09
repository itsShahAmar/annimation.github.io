"""
trending.py — Fetch trending topics for the Funny Animation Shorts Factory.

Returns a deduplicated list of trending topic strings and picks the
best topic using a comedy-aware scoring heuristic.  Prefers topics that
have high comedy and meme potential so the generated shorts are funnier
and more shareable.
"""

import logging
import random
import time
import xml.etree.ElementTree as ET

import requests

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_TOPICS = 10  # Minimum number of topics to maintain in the combined list
_SEED_TIME_GRANULARITY = 3600  # seconds — rotate niche pool every hour

# ---------------------------------------------------------------------------
# Comedy-specific fallback topics — universally funny, animation-friendly
# ---------------------------------------------------------------------------
FALLBACK_TOPICS: list[str] = [
    "Why cats think they own the house",
    "Explaining Wi-Fi to a medieval knight",
    "If animals had job interviews",
    "Things your brain does at 3 AM",
    "If autocorrect was a real person",
    "School teachers vs students battle",
    "Parents vs technology explained",
    "If Google Maps was brutally honest",
    "How introverts survive parties",
    "If food could talk back",
    "Monday mornings as an anime battle",
    "If alarm clocks had feelings",
    "WiFi signal as a dramatic soap opera",
    "Dogs explaining their daily routine",
    "If homework was a video game boss",
    "The five stages of losing your keys",
    "If your fridge could judge you",
    "Cats vs cucumbers: the full documentary",
    "When the pizza tracker stops moving",
    "If your sleep schedule was a character",
    "Explaining daylight saving time to aliens",
    "If procrastination was a superpower",
    "Your phone battery as a dramatic villain",
    "If traffic jams had feelings",
    "The inner life of a confused GPS",
    "If meetings were an anime arc",
    "When autocorrect becomes self-aware",
    "If laundry could complain back",
    "Your to-do list as a horror movie",
    "If elevators had personalities",
]

# ---------------------------------------------------------------------------
# Comedy-boosting keywords — topics with these words get a comedy score bonus
# ---------------------------------------------------------------------------
_COMEDY_KEYWORDS: list[str] = [
    "cat", "cats", "dog", "dogs", "pet", "animal", "wifi", "internet", "phone",
    "alarm", "monday", "sleep", "brain", "ai", "robot", "game", "gamer", "meme",
    "pizza", "food", "snack", "school", "teacher", "homework", "parent", "mom",
    "dad", "kid", "boss", "office", "meeting", "traffic", "airport", "procrastin",
    "laundry", "weather", "news", "social media", "tiktok", "trend", "viral",
    "grocery", "gym", "diet", "coffee", "monday", "holiday", "vacation",
    "relationship", "dating", "friend", "party", "introvert", "awkward",
]

# ---------------------------------------------------------------------------
# Comedy-specific viral niche pools
# ---------------------------------------------------------------------------
_COMEDY_SHORTS_NICHES: list[str] = [
    # Relatable everyday chaos
    "Why cats think they own the house",
    "Things your brain does at 3 AM",
    "If autocorrect was a real person",
    "How introverts survive parties",
    "Monday mornings as an anime battle",
    "If alarm clocks had feelings",
    "The five stages of losing your keys",
    "When the pizza tracker stops moving",
    "Your phone battery as a dramatic villain",
    "If your sleep schedule was a character",
    # Animal comedy
    "If animals had job interviews",
    "Dogs explaining their daily routine",
    "Cats vs cucumbers: the full documentary",
    "If pets could rate their owners",
    "What your cat is actually plotting",
    "Fish trying to understand land life",
    "Birds being absolute chaos agents",
    "If squirrels had a business plan",
    # Technology comedy
    "Explaining Wi-Fi to a medieval knight",
    "If Google Maps was brutally honest",
    "Parents vs technology explained",
    "WiFi signal as a dramatic soap opera",
    "When autocorrect becomes self-aware",
    "If the internet had a personality disorder",
    "Smart devices having an existential crisis",
    "If your GPS had road rage",
    # School and work comedy
    "School teachers vs students battle",
    "If homework was a video game boss",
    "If meetings were an anime arc",
    "The coworker who microwaves fish",
    "Explaining your job to your grandma",
    "If your resume could talk back",
    "Office printer as the final boss",
    "Group project but make it an action movie",
    # Food comedy
    "If food could talk back",
    "If your fridge could judge you",
    "Cooking recipe vs what actually happens",
    "Grocery store as an RPG quest",
    "If snacks had feelings",
    "The drama of ordering food online",
    "First bite vs last bite energy",
    "Meal prep gone completely wrong",
    # Everyday life absurdity
    "If procrastination was a superpower",
    "If laundry could complain back",
    "Your to-do list as a horror movie",
    "The inner life of a confused GPS",
    "If traffic jams had feelings",
    "Explaining daylight saving time to aliens",
    "If elevators had personalities",
    "Lost in the grocery store after five minutes",
    # Pop culture comedy
    "If social media was a real place",
    "Viral trends explained by grandparents",
    "If the algorithm was a person",
    "When notifications take over your life",
    "If streaming services could judge you",
    "The unsubscribe button has feelings",
    "If your search history was a documentary",
    "When ads know you too well",
]


def _comedy_score(topic: str) -> float:
    """Return a comedy potential score for a topic string.

    Topics that contain comedy-friendly keywords receive bonus points.
    Shorter, punchier topics tend to score higher.  Topics that already
    sound absurd or relatable get the highest scores.

    Args:
        topic: The topic string to evaluate.

    Returns:
        A float comedy score where higher means more comedy potential.
    """
    score = 0.0
    topic_lower = topic.lower()

    # Keyword bonus
    for kw in _COMEDY_KEYWORDS:
        if kw in topic_lower:
            score += 2.5

    # Length bonus — shorter topics tend to be punchier
    word_count = len(topic.split())
    if word_count <= 5:
        score += 2.0
    elif word_count <= 8:
        score += 1.0

    # Absurdity indicators — questions, "if", "vs", "when" are comedy gold
    comedy_starters = ["if ", "when ", "why ", "how ", "what if", "vs ", "vs."]
    for starter in comedy_starters:
        if topic_lower.startswith(starter) or f" {starter}" in topic_lower:
            score += 3.0
            break

    # Exclamation or question marks signal energy
    if "?" in topic or "!" in topic:
        score += 1.5

    # Relatability markers
    relatable = ["you", "your", "we", "us", "our", "me", "my"]
    for word in relatable:
        if f" {word} " in f" {topic_lower} ":
            score += 1.0
            break

    return score


def _fetch_google_trends(retries: int = 3, backoff: float = 2.0) -> list[str]:
    """Fetch daily trending searches for the US from Google Trends RSS feed.

    Uses the public Google Trends RSS endpoint which is more reliable than
    the unofficial pytrends scraping library.
    """
    url = "https://trends.google.com/trending/rss?geo=US"

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            # Python 3.7.1+ stdlib XML parser does not resolve external entities
            # and has built-in protection against entity expansion attacks.
            root = ET.fromstring(resp.text)
            topics: list[str] = []
            for item in root.iter("item"):
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    topics.append(title_el.text.strip())
            logger.info("Google Trends RSS returned %d topics", len(topics))
            return topics[:20]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google Trends RSS attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(backoff * attempt)
    return []


def _fetch_youtube_trending_rss(retries: int = 3, backoff: float = 2.0) -> list[str]:
    """Fetch trending searches on YouTube via Google Trends RSS feed.

    Uses the ``gprop=youtube`` parameter to filter Google Trends for
    YouTube-specific searches.  Completely free — no API key required.
    """
    url = "https://trends.google.com/trending/rss"
    params = {"geo": "US", "gprop": "youtube"}

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            topics: list[str] = []
            for item in root.iter("item"):
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    topics.append(title_el.text.strip())
            logger.info("YouTube Trends RSS returned %d topics", len(topics))
            return topics[:20]
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube Trends RSS attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(backoff * attempt)
    return []


def _get_comedy_niches(count: int = 15) -> list[str]:
    """Return a rotating subset of comedy-optimised viral YouTube Shorts niche topics.

    Uses time-seeded randomization so that each hourly pipeline run picks
    a different batch of niches, keeping content fresh and varied.
    """
    seed = int(time.time()) // _SEED_TIME_GRANULARITY
    rng = random.Random(seed)
    selected = rng.sample(_COMEDY_SHORTS_NICHES, min(count, len(_COMEDY_SHORTS_NICHES)))
    logger.info("Comedy niches selected %d topics (seed=%d)", len(selected), seed)
    return selected


def _fetch_newsapi_trending(retries: int = 3, backoff: float = 2.0) -> list[str]:
    """Fetch top headline titles from NewsAPI.org.

    Requires ``NEWSAPI_KEY`` to be set; returns an empty list gracefully
    if the key is absent or the request fails.
    """
    if not config.NEWSAPI_KEY:
        return []

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": "us",
        "pageSize": 20,
        "apiKey": config.NEWSAPI_KEY,
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            topics = [
                a["title"].split(" - ")[0].strip()
                for a in articles
                if a.get("title") and a["title"] != "[Removed]"
            ]
            logger.info("NewsAPI returned %d topics", len(topics))
            return topics[:20]
        except Exception as exc:  # noqa: BLE001
            logger.warning("NewsAPI attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(backoff * attempt)
    return []


def get_trending_topics() -> list[str]:
    """Combine all topic sources into a deduplicated list with comedy niches first.

    Returns at least 10 topic strings, falling back to :data:`FALLBACK_TOPICS`
    if the external sources cannot provide enough results.
    """
    google_topics = _fetch_google_trends()
    yt_topics = _fetch_youtube_trending_rss()
    niche_topics = _get_comedy_niches()
    newsapi_topics = _fetch_newsapi_trending()

    seen: set[str] = set()
    combined: list[str] = []
    for topic in google_topics + yt_topics + niche_topics + newsapi_topics:
        normalised = topic.strip()
        if normalised and normalised.lower() not in seen:
            seen.add(normalised.lower())
            combined.append(normalised)

    if len(combined) < _MIN_TOPICS:
        logger.info("Fewer than %d topics found (%d); padding with comedy fallbacks", _MIN_TOPICS, len(combined))
        for fallback in FALLBACK_TOPICS:
            if fallback.lower() not in seen:
                seen.add(fallback.lower())
                combined.append(fallback)
            if len(combined) >= _MIN_TOPICS:
                break

    logger.info("Total unique topics available: %d", len(combined))
    return combined


def get_best_topic() -> str:
    """Pick the funniest, most viral topic using a comedy-aware scoring heuristic.

    Fetches from each source once, then scores topics so that those appearing
    in multiple sources rank higher AND those with high comedy potential
    (via :func:`_comedy_score`) receive an additional boost.  Picks randomly
    from the top 5 to ensure variety across runs.
    """
    google_topics = _fetch_google_trends()
    yt_topics = _fetch_youtube_trending_rss()
    niche_topics = _get_comedy_niches()
    newsapi_topics = _fetch_newsapi_trending()

    scores: dict[str, float] = {}

    for rank, topic in enumerate(google_topics):
        key = topic.strip().lower()
        scores[key] = scores.get(key, 0) + (len(google_topics) - rank)

    for rank, topic in enumerate(yt_topics):
        key = topic.strip().lower()
        bonus = 2.0 if key in scores else 1.0
        scores[key] = scores.get(key, 0) + bonus * (len(yt_topics) - rank)

    for rank, topic in enumerate(niche_topics):
        key = topic.strip().lower()
        bonus = 2.0 if key in scores else 1.0
        scores[key] = scores.get(key, 0) + bonus * (len(niche_topics) - rank)

    for rank, topic in enumerate(newsapi_topics):
        key = topic.strip().lower()
        bonus = 2.0 if key in scores else 1.0
        scores[key] = scores.get(key, 0) + bonus * (len(newsapi_topics) - rank)

    # Apply comedy score bonus — topics with meme/comedy potential rank higher
    all_topics_raw = google_topics + yt_topics + niche_topics + newsapi_topics
    original: dict[str, str] = {}
    for topic in all_topics_raw:
        key = topic.strip().lower()
        if key not in original:
            original[key] = topic.strip()
        # Add comedy bonus to every scored topic
        if key in scores:
            scores[key] += _comedy_score(topic)

    if not scores:
        logger.warning("No trending topics found; using random comedy fallback topic")
        return random.choice(FALLBACK_TOPICS)

    sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
    top_keys = sorted_keys[:min(5, len(sorted_keys))]
    best_key = random.choice(top_keys)
    best_topic = original.get(best_key, FALLBACK_TOPICS[0])
    logger.info(
        "Comedy topic selected: '%s' (score=%.1f, comedy_bonus=%.1f, from top %d)",
        best_topic, scores[best_key], _comedy_score(best_topic), len(top_keys),
    )

    # Pad with comedy fallbacks to keep get_trending_topics() consistent
    seen: set[str] = {t.strip().lower() for t in all_topics_raw}
    combined = list(original.values())
    for fallback in FALLBACK_TOPICS:
        if fallback.lower() not in seen:
            seen.add(fallback.lower())
            combined.append(fallback)
        if len(combined) >= _MIN_TOPICS:
            break
    logger.info("Total unique topics available: %d", len(combined))

    return best_topic
