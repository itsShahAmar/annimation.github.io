"""
trending.py — Fetch trending topics for the Food Making Videos Factory.

Returns a deduplicated list of trending topic strings and picks the
best topic using a food-awareness scoring heuristic.  Prefers topics that
have high food, cooking, and recipe potential so the generated shorts are
more engaging and shareable with food audiences.
"""

import logging
import random
import re
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
# Food-specific fallback topics — universally appealing, cooking-friendly
# ---------------------------------------------------------------------------
FALLBACK_TOPICS: list[str] = [
    "5-ingredient pasta that tastes like a restaurant made it",
    "The secret to perfectly crispy chicken every time",
    "Why your scrambled eggs are never as good as a chef's",
    "One-pan meals that require almost zero cleanup",
    "Food hacks that actually save you time in the kitchen",
    "How to make the fluffiest pancakes you have ever tasted",
    "The easiest homemade bread recipe with no kneading",
    "Why adding pasta water makes your sauce so much better",
    "Budget meals that taste expensive under ten dollars",
    "The trick professional chefs use for perfect caramelized onions",
    "Viral air fryer recipes that changed everything",
    "How to meal prep a whole week in under an hour",
    "The ultimate guide to making restaurant-quality pizza at home",
    "Secrets to making the crispiest french fries at home",
    "Why room-temperature butter makes cookies so much better",
    "Five minutes meals that are actually delicious and healthy",
    "The simple technique that makes any steak taste like a steakhouse",
    "Why your homemade soup always tastes bland and how to fix it",
    "The fastest way to chop onions without crying",
    "How to make creamy pasta sauce without any cream",
    "Unexpected ingredients that level up any dish instantly",
    "Why salt your pasta water and how much is actually right",
    "The secret ingredient that makes your baked goods taste better",
    "How to make the perfect fried egg every time",
    "Why your homemade fried rice never tastes like takeout",
    "The easiest way to make authentic ramen at home",
    "Overnight oats variations that make healthy eating easy",
    "How to properly season a cast iron pan and why it matters",
    "The viral cottage cheese recipes everyone is obsessed with",
    "How to make the smoothest, creamiest hummus at home",
    # Pakistani cuisine
    "The secret to perfectly layered biryani rice every single time",
    "Why your chicken karahi never tastes like the dhaba version",
    "How to make authentic nihari that falls off the bone",
    "Crispy samosa recipe with the perfect golden flaky shell",
    "The spice blend Pakistani grandmothers use for seekh kabab",
    "How to make fluffy naan without a tandoor oven at home",
    "Haleem recipe that cooks itself while you go about your day",
    "Why chapli kabab from Peshawar tastes better than everywhere else",
    "The trick to making daal makhani as rich as a restaurant",
    "Mutton biryani secrets that make it taste like Karachi street food",
    "Crispy pakora batter that does not go soggy after frying",
    "How to make soft paratha layers that peel apart perfectly",
    "Chicken tikka marinade that is actually used in Pakistani restaurants",
    "The real way to make shahi tukray for Eid dessert",
    "How to make keema that is juicy and full of flavor every time",
    # Afghan cuisine
    "Kabuli palaw recipe that tastes exactly like it came from Kabul",
    "How to make bolani with crispy edges and savory potato filling",
    "The secret to perfectly fluffy Afghan rice every single time",
    "Mantu dumplings with yogurt sauce that melt in your mouth",
    "How to make Afghan qorma with caramelized onions and tender meat",
    "Shami kabab recipe with herbs that is better than any restaurant",
    "Afghan bolani stuffed with spinach and leeks the traditional way",
    "How to make aushak dumplings with the perfect thin dough",
    "The Afghan spice blend that makes every dish taste incredible",
    "Shorwa soup recipe that warms you from the inside out",
    "How to make Afghan bread that is chewy and perfect for dipping",
    "Lamb qabuli pulao that is the pride of every Afghan dinner table",
    # Indian cuisine
    "Butter chicken that tastes like it took all day but only takes thirty minutes",
    "How to make restaurant-quality tikka masala at home",
    "The secret to perfectly crispy dosa with golden edges",
    "Idli batter fermentation trick that guarantees fluffy results",
    "Paneer tikka marinade that makes every bite smoky and delicious",
    "How to make dal makhani with the creamiest texture imaginable",
    "The chaat masala blend that makes street food taste authentic",
    "How to make perfectly layered hyderabadi biryani at home",
    "Tandoori chicken marinade secret that makes it restaurant-worthy",
    "Palak paneer that is creamy, smooth, and full of flavor",
    "How to make masala chai that tastes better than any coffee shop",
    "The lassi recipe that is thick, refreshing, and never watery",
    "Sambar recipe with the perfect balance of sour, spicy, and savory",
    "How to make pani puri shells that are perfectly crispy and hollow",
    "The chole bhature recipe that is absolutely worth the indulgence",
]

# ---------------------------------------------------------------------------
# Food-boosting keywords — topics with these words get a food score bonus
# ---------------------------------------------------------------------------
_FOOD_KEYWORDS: list[str] = [
    "recipe", "recipes", "cook", "cooking", "food", "foods", "meal", "meals",
    "eat", "eating", "bake", "baking", "grill", "grilling", "fry", "frying",
    "ingredient", "ingredients", "kitchen", "chef", "restaurant", "homemade",
    "easy", "quick", "healthy", "delicious", "tasty", "crispy", "creamy",
    "pasta", "chicken", "beef", "fish", "vegetable", "dessert", "breakfast",
    "lunch", "dinner", "snack", "hack", "hacks", "trick", "tricks", "secret",
    "tip", "tips", "guide", "perfect", "best", "viral", "trending", "air fryer",
    "slow cooker", "instant pot", "sheet pan", "one pot", "budget", "cheap",
    "protein", "keto", "vegan", "vegetarian", "gluten", "dairy", "sauce",
    "marinade", "seasoning", "spice", "herb", "flavor", "texture",
    # South Asian cuisine keywords
    "biryani", "karahi", "nihari", "haleem", "korma", "kebab", "kabab",
    "samosa", "pakora", "paratha", "naan", "roti", "chapati", "puri",
    "tikka", "tandoori", "masala", "curry", "dal", "daal", "lentil",
    "seekh", "chapli", "keema", "mutton", "lamb", "paneer", "ghee",
    "cumin", "coriander", "turmeric", "cardamom", "cinnamon", "clove",
    "chaat", "lassi", "chai", "raita", "chutney", "biryani rice",
    "dosa", "idli", "sambar", "rasam", "uttapam", "vada", "upma",
    "butter chicken", "tikka masala", "palak paneer", "chole", "bhature",
    "kabuli", "palaw", "pulao", "bolani", "mantu", "aushak", "qorma",
    "pani puri", "gol gappa", "bhel puri", "sev puri", "pav bhaji",
    "dhaba", "dum", "biryani pot", "handi", "tawa", "kadai",
]

# ---------------------------------------------------------------------------
# Food-specific viral niche pools
# ---------------------------------------------------------------------------
_FOOD_SHORTS_NICHES: list[str] = [
    # Quick recipes and hacks
    "5-ingredient pasta that tastes like a restaurant made it",
    "One-pan chicken dinner with almost zero cleanup",
    "Air fryer crispy chicken wings better than deep fried",
    "Overnight oats that keep you full all morning",
    "Sheet pan dinner that cooks itself while you relax",
    "Budget pasta meal under five dollars that tastes gourmet",
    "The fastest weeknight dinner that looks impressive",
    "Meal prep five lunches in twenty minutes flat",
    # Secrets and science
    "Why adding pasta water makes your sauce stick perfectly",
    "The secret to crispy roasted vegetables every time",
    "Why restaurant eggs taste so much better than yours",
    "The one ingredient that makes baked goods taste homemade",
    "Why your fried rice never tastes like takeout and the fix",
    "The real reason professional chefs use so much butter",
    "Why your garlic always burns and how to prevent it",
    "The salt secret that makes everything taste better",
    # Trending food content
    "Viral cottage cheese toast recipe the internet cannot stop making",
    "TikTok pasta bake that everyone is obsessed with right now",
    "Feta cheese pasta that went completely viral and for good reason",
    "Cloud eggs the trendy breakfast everyone should try once",
    "Birria tacos that are worth every single messy bite",
    "Dubai chocolate bar recipe that is taking over social media",
    "Smash burgers at home better than any fast food chain",
    "Butter board trend that changed how we think about cheese",
    # Cooking techniques
    "How to properly season a cast iron skillet once and for all",
    "The knife skill that makes chopping vegetables ten times faster",
    "How to make a perfect pan sauce from scratch every time",
    "The braising technique that makes cheap cuts taste luxurious",
    "How to properly caramelize onions without burning them",
    "The emulsification trick for silky smooth pasta every time",
    # Comfort food upgrades
    "Homemade pizza dough that is better than delivery",
    "Grilled cheese upgrade that changes everything you thought you knew",
    "The best homemade mac and cheese recipe with a crispy top",
    "French onion soup that warms your soul on any cold night",
    "Chocolate chip cookies with the chewiest center imaginable",
    # Healthy eating made exciting
    "High-protein meals that actually taste indulgent and delicious",
    "Vegetable recipes that even picky eaters will actually enjoy",
    "Smoothie bowl combinations that look as good as they taste",
    "Salad dressings so good you will forget store-bought exists",
    "Healthy meal prep ideas that do not feel like diet food",
    # International and fusion
    "Authentic ramen broth you can make at home in an hour",
    "Korean fried chicken that is crunchier than any restaurant",
    "Homemade sushi rolls that are easier than you think",
    "Indian butter chicken that tastes like it took all day",
    "Thai peanut noodles ready in fifteen minutes or less",
    # Pakistani cuisine viral niches
    "Chicken biryani recipe with perfectly separated aromatic rice",
    "Crispy samosa with flaky pastry and perfectly spiced potato filling",
    "Restaurant-style chicken karahi with smoky charred tomatoes",
    "Seekh kabab technique that keeps them juicy and full of herbs",
    "Nihari slow-cooked beef that falls apart and coats every spoon",
    "Fluffy naan without a tandoor using just a cast iron pan",
    "Haleem recipe that develops deep flavor over hours of cooking",
    "Chapli kabab with crispy edges and a burst of cumin and coriander",
    "Mutton biryani layered with saffron rice and fried onions",
    "Crispy pakora batter that stays crunchy long after frying",
    "Chicken tikka marinade with yogurt and spices for perfect char",
    "Dal tadka with the smoky tarka that transforms every bite",
    "Shahi tukray fried bread pudding soaked in sweet cardamom milk",
    "Keema matar with perfectly cooked peas and fragrant spices",
    "Soft layered paratha that separates into flaky golden ribbons",
    # Afghan cuisine viral niches
    "Kabuli palaw with caramelized carrots and raisins over tender lamb",
    "Bolani flatbread stuffed with potato and leeks and pan-fried crispy",
    "Afghan mantu dumplings with yogurt and tomato sauce on top",
    "Qorma with slow-cooked onions and aromatic Afghan spices",
    "Shami kabab with fresh herbs that are tender on the inside",
    "Aushak dumplings filled with scallions and topped with yogurt",
    "Afghan lamb soup shorwa with vegetables and warming spices",
    "Afghan naan bread from a stone oven with chewy perfect texture",
    "Lamb qabuli pulao the national dish of Afghanistan made at home",
    "Afghan bolani with spinach filling and golden crispy edges",
    # Indian cuisine viral niches
    "Butter chicken with the creamiest tomato sauce you have ever made",
    "Restaurant-style tikka masala at home in under forty-five minutes",
    "Crispy golden dosa with perfectly fermented batter from scratch",
    "Soft fluffy idli with the secret fermentation ratio that works",
    "Paneer tikka grilled in a pan with smoky marinade and charred edges",
    "Dal makhani slow-cooked for hours until it is silky and rich",
    "Hyderabadi biryani with dum cooking and saffron-stained rice",
    "Tandoori chicken in a regular oven with restaurant-quality char",
    "Palak paneer with smooth vibrant spinach sauce and soft paneer",
    "Masala chai from scratch with ginger and cardamom that warms you",
    "Mango lassi so thick and creamy you will never buy it again",
    "Pani puri with crispy hollow shells and tangy tamarind water",
    "Chole bhature the ultimate indulgent breakfast from North India",
    "Sambar with fresh vegetables and a perfect balance of tamarind",
    "Chaat masala blend that makes any snack taste like Indian street food",
    # Baking and desserts
    "No-knead bread that bakes perfectly in a Dutch oven",
    "Three-ingredient banana ice cream with no ice cream maker",
    "Mug cake recipe ready in sixty seconds for late-night cravings",
    "Croissant hack using crescent roll dough that actually works",
    "The best chocolate lava cake recipe for date night at home",
]


def _food_score(topic: str) -> float:
    """Return a food engagement potential score for a topic string.

    Topics that contain food-friendly keywords receive bonus points.
    Shorter, punchier recipe topics tend to score higher.  Topics that
    include secrets, hacks, or viral references get the highest scores.

    Args:
        topic: The topic string to evaluate.

    Returns:
        A float food score where higher means more food/recipe potential.
    """
    score = 0.0
    topic_lower = topic.lower()

    # Keyword bonus
    for kw in _FOOD_KEYWORDS:
        if kw in topic_lower:
            score += 2.5

    # Length bonus — focused recipe topics tend to be punchier
    word_count = len(topic.split())
    if word_count <= 6:
        score += 2.0
    elif word_count <= 10:
        score += 1.0

    # Engagement indicators — questions, "why", "how", "secret" are viral gold
    food_starters = ["why ", "how ", "the secret", "what if", "the best", "viral", "easy"]
    for starter in food_starters:
        if topic_lower.startswith(starter) or f" {starter}" in topic_lower:
            score += 3.0
            break

    # Numbers signal listicles which perform well
    if re.search(r'\b\d+\b', topic):
        score += 2.0

    # Relatability and curiosity markers
    relatable = ["you", "your", "we", "us", "our", "everyone", "always", "never"]
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


def _get_food_niches(count: int = 15) -> list[str]:
    """Return a rotating subset of food-optimised viral YouTube Shorts niche topics.

    Uses time-seeded randomization so that each hourly pipeline run picks
    a different batch of niches, keeping content fresh and varied.
    """
    seed = int(time.time()) // _SEED_TIME_GRANULARITY
    rng = random.Random(seed)
    selected = rng.sample(_FOOD_SHORTS_NICHES, min(count, len(_FOOD_SHORTS_NICHES)))
    logger.info("Food niches selected %d topics (seed=%d)", len(selected), seed)
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
    """Combine all topic sources into a deduplicated list with food niches first.

    Returns at least 10 topic strings, falling back to :data:`FALLBACK_TOPICS`
    if the external sources cannot provide enough results.
    """
    google_topics = _fetch_google_trends()
    yt_topics = _fetch_youtube_trending_rss()
    niche_topics = _get_food_niches()
    newsapi_topics = _fetch_newsapi_trending()

    seen: set[str] = set()
    combined: list[str] = []
    for topic in google_topics + yt_topics + niche_topics + newsapi_topics:
        normalised = topic.strip()
        if normalised and normalised.lower() not in seen:
            seen.add(normalised.lower())
            combined.append(normalised)

    if len(combined) < _MIN_TOPICS:
        logger.info("Fewer than %d topics found (%d); padding with food fallbacks", _MIN_TOPICS, len(combined))
        for fallback in FALLBACK_TOPICS:
            if fallback.lower() not in seen:
                seen.add(fallback.lower())
                combined.append(fallback)
            if len(combined) >= _MIN_TOPICS:
                break

    logger.info("Total unique topics available: %d", len(combined))
    return combined


def get_best_topic() -> str:
    """Pick the most viral food topic using a food-awareness scoring heuristic.

    Fetches from each source once, then scores topics so that those appearing
    in multiple sources rank higher AND those with high food/recipe potential
    (via :func:`_food_score`) receive an additional boost.  Picks randomly
    from the top 5 to ensure variety across runs.
    """
    google_topics = _fetch_google_trends()
    yt_topics = _fetch_youtube_trending_rss()
    niche_topics = _get_food_niches()
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

    # Apply food score bonus — topics with food/recipe potential rank higher
    all_topics_raw = google_topics + yt_topics + niche_topics + newsapi_topics
    original: dict[str, str] = {}
    for topic in all_topics_raw:
        key = topic.strip().lower()
        if key not in original:
            original[key] = topic.strip()
        # Add food bonus to every scored topic
        if key in scores:
            scores[key] += _food_score(topic)

    if not scores:
        logger.warning("No trending topics found; using random food fallback topic")
        return random.choice(FALLBACK_TOPICS)

    sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
    top_keys = sorted_keys[:min(5, len(sorted_keys))]
    best_key = random.choice(top_keys)
    best_topic = original.get(best_key, FALLBACK_TOPICS[0])
    logger.info(
        "Food topic selected: '%s' (score=%.1f, food_bonus=%.1f, from top %d)",
        best_topic, scores[best_key], _food_score(best_topic), len(top_keys),
    )

    # Pad with food fallbacks to keep get_trending_topics() consistent
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
