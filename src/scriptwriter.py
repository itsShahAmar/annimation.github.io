"""
scriptwriter.py — Comedy Animation Script Generator for the Funny Animation Shorts Factory.

Uses deterministic templates with topic-aware variations to produce structured
scripts complete with title, narration, scene descriptions, tags, and a
YouTube description.  Designed to generate hilarious, animated-style comedy
content — no paid API keys required.
"""

import hashlib
import logging
import random
import re
import time
from typing import TypedDict

logger = logging.getLogger(__name__)

# Minimum / maximum acceptable word counts for the narration script
_MIN_WORDS = 70
_MAX_WORDS = 200


class ScriptData(TypedDict):
    """Structured output from the comedy script generator."""

    title: str
    script: str
    caption_script: str
    hook: str
    scenes: list[str]
    tags: list[str]
    description: str


# ---------------------------------------------------------------------------
# Comedy Hook Templates — first 3-5 seconds that hook viewers with absurd/funny premises
# ---------------------------------------------------------------------------
_HOOKS: list[str] = [
    # Absurd premise hooks
    "What if {topic} was actually run by a council of angry cats?",
    "POV: You explained {topic} to your grandma and she started a business.",
    "Nobody: ... Absolutely Nobody: ... {topic}: chaos ensues.",
    "{topic} but it is explained by two neurons fighting in your brain.",
    "Me trying to understand {topic} at 3 AM be like...",
    "If {topic} was a cartoon character, this is exactly what would happen.",
    "Plot twist: {topic} has been a raccoon in a trenchcoat this whole time.",
    "Your brain at 3 AM: What if {topic} was actually a soap opera?",
    "The universe explaining {topic} to you using only emojis and chaos.",
    "When {topic} walks into the room like it owns the place.",
    # Gen-Z / meme culture hooks
    "POV: {topic} just sent you a passive-aggressive text.",
    "Me explaining {topic} to my goldfish who has a three-second memory.",
    "Sir, this is a Wendy's — and {topic} just ordered everything on the menu.",
    "Main character energy: {topic} edition. Buckle up.",
    "The villain origin story of {topic} — no one saw this coming.",
    "Not me thinking about {topic} again at the worst possible time.",
    "{topic} said hold my juice box and then absolutely went feral.",
    "Every explanation of {topic} ever, but make it unhinged.",
    "The last two brain cells trying to process {topic} together.",
    "Okay but what if {topic} had feelings? Because it clearly does.",
    # Situational comedy hooks
    "How it started vs how it is going with {topic}.",
    "If {topic} was a job interview, and everyone was lying.",
    "First day vs last day of understanding {topic}.",
    "Things {topic} does when no one is watching.",
    "{topic} explained by someone who has absolutely no idea what it is.",
    "The five stages of grief when you finally understand {topic}.",
    "A documentary about {topic} narrated by someone who misread Wikipedia.",
    "If {topic} had a customer service hotline, here is how it would go.",
    "The internal monologue of someone encountering {topic} for the first time.",
    # Time / perspective comedy hooks
    "If someone from 2050 came back to explain {topic} to us right now.",
    "Medieval knight reacting to {topic} for the first time.",
    "Your future self calling to warn you about {topic} at two in the morning.",
    "{topic} — a horror story, a love story, and a cooking show all at once.",
    "Breaking news: {topic} has gone completely off the rails and we are here for it.",
]

# ---------------------------------------------------------------------------
# Body Templates — several comedy patterns
# ---------------------------------------------------------------------------

# Pattern 1: Character Dialogue — two funny characters debating the topic
_BODIES_DIALOGUE: list[str] = [
    (
        "Imagine two stick figures arguing about this. Stick Figure One says: "
        "Okay so {topic} is basically the universe trolling us. Stick Figure Two "
        "replies: That tracks. That absolutely tracks. Meanwhile their tiny laptop "
        "is on fire and papers are flying everywhere because nobody read the manual. "
        "The manual, it turns out, was just a drawing of a confused cat. Classic "
        "{topic} behaviour if you ask me."
    ),
    (
        "Picture two chibi characters standing in front of a whiteboard covered in "
        "question marks. Character One points dramatically and yells: {topic} is "
        "the reason I cannot sleep at night. Character Two nods so hard their "
        "oversized head wobbles like a bobblehead. They both stare into the camera "
        "with the same energy as someone who just watched a documentary that raised "
        "more questions than it answered. Because it did."
    ),
    (
        "Two blob characters are having a very important meeting about {topic}. "
        "Blob One slaps the table and announces: I have done zero research but I "
        "have very strong feelings. Blob Two pulls out a single crumpled sticky "
        "note that just says the word yes in giant letters. They high-five and "
        "declare the meeting a success. This is genuinely how most decisions about "
        "{topic} get made and nobody is talking about it."
    ),
    (
        "The neurons in your brain have called an emergency summit about {topic}. "
        "Neuron One enters wearing a tiny tie and carrying a briefcase that is "
        "entirely empty. Neuron Two has printed forty slides and the printer ran "
        "out of ink on slide three. Together they represent the full intellectual "
        "capacity being deployed on {topic} right now. The meeting ends with a "
        "fire alarm and everyone just agrees to wing it."
    ),
]

# Pattern 2: Narrator + Chaos — calm narrator while animated chaos happens
_BODIES_NARRATOR: list[str] = [
    (
        "Narrator voice calm and serene: Today we observe {topic} in its natural "
        "habitat. A small cartoon character approaches cautiously. Everything seems "
        "fine. The narrator continues: Note how it appears perfectly normal and "
        "harmless. Suddenly three explosions happen simultaneously for no reason. "
        "A rubber hose cartoon runs in circles screaming while a disco ball drops "
        "from the ceiling. The narrator, completely unfazed, adds: This is typical "
        "{topic} behaviour. Scientists are baffled. Audiences are delighted."
    ),
    (
        "Welcome to the nature documentary nobody asked for but everyone needed. "
        "Today: {topic}. Our subject has been spotted in the wild. The pixel art "
        "sprite is moving with suspicious confidence toward something labeled "
        "do not touch. The narrator whispers dramatically: It is going to touch it. "
        "It touches it. Chaos erupts. A tiny cartoon dog somewhere in the background "
        "is just vibing with sunglasses on. He knows. He always knew."
    ),
    (
        "And now a message from your brain regarding {topic}. Everything is fine. "
        "The cartoon brain sits at a tiny desk surrounded by filing cabinets that "
        "are all labeled urgent and also on fire. This is fine says the brain, "
        "pouring coffee into a mug that says I function. Meanwhile {topic} enters "
        "the scene with a kazoo and immediately starts reorganizing the filing "
        "system using a method described only as vibes. The brain gives a thumbs up."
    ),
]

# Pattern 3: Tutorial Gone Wrong — how-to that goes hilariously off the rails
_BODIES_TUTORIAL: list[str] = [
    (
        "Step one: simply understand {topic}. Easy. You have got this. Step two: "
        "do a little research. The little research has become a six-hour spiral "
        "and a chibi character is now surrounded by seventeen open browser tabs. "
        "Step three: apply what you learned. Apply key smashes the keyboard. "
        "Step four: accept the results. The result is a rubber hose cartoon doing "
        "a victory dance in the wreckage of your original plan. Step five: become "
        "one with {topic}. You are {topic} now. This was always the plan."
    ),
    (
        "A complete beginner guide to {topic} in under a minute. First: act "
        "confident even if you have no idea what is happening. The stick figure "
        "nods aggressively. Second: say the words as if they explain themselves. "
        "Third: when someone asks a follow-up question, point enthusiastically "
        "at the nearest wall and say exactly. Fourth: realize {topic} is actually "
        "fascinating and spiral into genuine interest at three in the morning. "
        "Fifth: become the person everyone calls about {topic} at parties. "
        "Congratulations. You are now an expert. Sort of."
    ),
]

# Pattern 4: Inner Monologue — character's inner thoughts vs reality
_BODIES_MONOLOGUE: list[str] = [
    (
        "What they say about {topic}: perfectly simple and straightforward. "
        "What your brain hears: an ancient prophecy written in a language "
        "only confused squirrels can read. What you say out loud: yes, totally, "
        "I get it. What you are actually thinking: why is there a tiny cartoon "
        "version of me inside my own head doing panicked cartwheels. What happens "
        "next: you google it, find three answers that all contradict each other, "
        "and the chibi character in your brain sits down on the floor and eats "
        "a snack and decides to nap on it instead."
    ),
    (
        "The confident face you make when someone mentions {topic}: smooth, "
        "knowledgeable, a hint of been there. What is actually happening inside: "
        "a full cartoon orchestra is tuning instruments but nobody brought the "
        "sheet music. The conductor, a tiny blob character in a tuxedo, looks "
        "directly into the audience and shrugs with his entire body. This is fine. "
        "You nod along. You say interesting. You pull out your phone the second "
        "the conversation ends and search what is {topic} actually and why is it "
        "like that. You were right to ask."
    ),
]

# Pattern 5: News Anchor — fake news broadcast with ridiculous takes
_BODIES_NEWS: list[str] = [
    (
        "Breaking news from the cartoon dimension. I am your anchor reporting "
        "live from a desk that is inexplicably floating. Our top story: {topic} "
        "has done something again and the people are divided. Sources describe "
        "the situation as unprecedented, chaotic, and honestly kind of hilarious. "
        "Our correspondent, a stick figure with a notepad full of question marks, "
        "reports from the scene. Back to you. We do not know what is back to you "
        "means anymore. More updates as this develops, which it will, immediately."
    ),
    (
        "This just in. {topic} has entered the chat and the chat is not ready. "
        "A panel of animated experts featuring a nervous chibi, a confident blob, "
        "and one rubber hose character who has already started celebrating for no "
        "reason are discussing the implications. The chibi says: this is significant. "
        "The blob says: I made a chart. The chart is a drawing of a confused cat. "
        "We are all the confused cat at this point. Weather report: chaotic with "
        "a high chance of plot twist. Stay tuned."
    ),
]

# Pattern 6: Time Travel — future or past perspective
_BODIES_TIME: list[str] = [
    (
        "Imagine someone from 2050 beaming back to explain {topic} to us. They "
        "appear in a flash of light, pixel art shimmer included. They look around "
        "at how we currently understand {topic} and immediately start stress-eating "
        "a holographic sandwich. Future person breathes deeply and says: okay so "
        "first of all. They do not finish the sentence. They just start drawing "
        "diagrams in the air with increasing urgency while a chibi time police "
        "officer in the background is frantically waving at them to stop. Too late."
    ),
    (
        "A medieval knight has just encountered {topic} for the first time. "
        "The knight, drawn in the most dramatic rubber hose cartoon style possible, "
        "does a full body recoil that sends their armour flying in five directions. "
        "They consult their scroll. The scroll is blank. They consult their wizard. "
        "The wizard is also blank. The knight turns to the camera and says in a "
        "very serious voice: yonder topic doth go completely off the rails and yet "
        "I am here for it. The wizard nods slowly. The armour is still in orbit."
    ),
]

# Combine all body patterns
_ALL_BODIES: list[str] = (
    _BODIES_DIALOGUE
    + _BODIES_NARRATOR
    + _BODIES_TUTORIAL
    + _BODIES_MONOLOGUE
    + _BODIES_NEWS
    + _BODIES_TIME
)

# ---------------------------------------------------------------------------
# Punchline / CTA Templates
# ---------------------------------------------------------------------------
_PUNCHLINES: list[str] = [
    "If this made your brain hurt in a funny way, smash that subscribe button!",
    "Plot twist: you just learned something AND laughed. Subscribe for more chaos!",
    "Your humor taste is immaculate. Subscribe before the algorithm forgets you!",
    "And that is {topic} explained by your last remaining brain cell. Follow for more.",
    "Subscribe or the confused cat gets the chart. You have been warned.",
    "If you laughed even once, the cartoon characters win. Subscribe to confirm their victory.",
    "Follow for daily animation chaos that somehow makes sense in the end.",
    "Subscribe now and I promise the next one gets even more unhinged.",
    "The stick figures worked hard on this. Reward them with a follow.",
    "That is all from the cartoon dimension today. Subscribe for tomorrow's episode.",
    "Your neurons called. They want more content like this. Subscribe and tell them you did.",
]

# ---------------------------------------------------------------------------
# Comedy Title Templates
# ---------------------------------------------------------------------------
_TITLES: list[str] = [
    "When {topic} Goes HILARIOUSLY Wrong \U0001f602\U0001f480",
    "{topic} But Make It UNHINGED \U0001f923",
    "POV: {topic} Explained By Your Last Brain Cell",
    "If {topic} Was a Cartoon Character \U0001f62d\U0001f525",
    "{topic} And The Two Neurons Fighting About It \U0001f9e0\U0001f4a5",
    "Nobody Expected {topic} To Be This Chaotic \U0001f631",
    "{topic} Walked So The Chaos Could Run \U0001f480",
    "Me Explaining {topic} To My Goldfish \U0001f41f\U0001f602",
    "The {topic} Documentary Nobody Asked For \U0001f3ac",
    "{topic}: A Horror Story But Make It Funny \U0001f631\U0001f923",
    "When {topic} Has Main Character Energy \U0001f525",
    "{topic} Has Done It Again And We Are ALL The Confused Cat \U0001f408",
    "Your Brain At 3 AM: Okay But What About {topic} \U0001f62d",
    "Sir This Is A Wendy's And {topic} Just Ordered Everything \U0001f602",
    "{topic} In The Wild: A Nature Documentary \U0001f40d\U0001f4f9",
    "The Last Two Brain Cells Processing {topic} Right Now \U0001f9e0\U0001f923",
    "{topic} Explained With Zero Chill And Maximum Chaos \U0001f4a5",
    "Plot Twist: {topic} Was A Raccoon In A Trenchcoat \U0001f99d\U0001f602",
    "How It Started Vs How It Is Going: {topic} Edition \U0001f480\U0001f525",
    "Breaking News: {topic} Has Gone Completely Off The Rails \U0001f6a8\U0001f602",
]

# ---------------------------------------------------------------------------
# Animation-friendly scene descriptions
# ---------------------------------------------------------------------------
_SCENE_POOLS: dict[str, list[str]] = {
    "intro": [
        "Cartoon character with oversized eyes doing a dramatic double-take at the camera",
        "Chibi character appearing in a flash of colorful sparkles with a big exclamation mark above their head",
        "Stick figure sliding onto screen and pointing dramatically at a glowing sign that reads the topic",
        "Rubber hose cartoon character vibrating with excitement like a cartoon alarm clock",
        "Pixel art sprite doing a spinning entrance animation with confetti exploding everywhere",
        "Minimalist blob character popping up from the bottom of frame with comically wide eyes",
    ],
    "middle": [
        "Chibi character rage-typing on a tiny laptop while papers fly everywhere in slow motion",
        "Two stick figures in a heated debate with thought bubbles full of chaos and question marks",
        "Character doing the surprised Pikachu face as explosions happen casually in the background",
        "South Park style character standing in front of a whiteboard covered entirely in confused doodles",
        "Rubber hose cartoon brain running in circles with tiny gears flying off in all directions",
        "Pixel art character opening a filing cabinet only to find another smaller filing cabinet inside",
        "Blob character pulling out a chart that is just a drawing of a confused cat with the word yes",
        "Chibi character surrounded by seventeen glowing browser tabs all showing question marks",
        "Stick figure wizard consulting a scroll that unfurls all the way off screen and still has more scroll",
        "Cartoon character checking a phone that displays only the spinning loading wheel and existential dread",
    ],
    "punchline": [
        "Character doing an exaggerated victory dance in extremely slow motion while confetti rains down",
        "Chibi character turning to camera with finger guns and winking so hard it makes a sound effect",
        "Rubber hose character doing a full body flop onto the ground in the most satisfied way possible",
        "Stick figures high-fiving so enthusiastically they both fly off screen in opposite directions",
        "Pixel art sprite pulling out a tiny subscribe button and offering it directly to the viewer",
        "Minimalist blob character turning to camera and giving the most confident thumbs up imaginable",
    ],
}

# ---------------------------------------------------------------------------
# Comedy-specific tags
# ---------------------------------------------------------------------------
_BASE_TAGS: list[str] = [
    "funny animation",
    "animated shorts",
    "comedy shorts",
    "funny cartoon",
    "animation memes",
    "hilarious",
    "viral comedy",
    "animated comedy",
    "funny video",
    "shorts funny",
    "comedy animation",
    "cartoon comedy",
    "meme animation",
    "funny animated",
    "humor shorts",
    "animated humor",
    "comedy sketch animated",
    "viral animated",
    "funny shorts 2024",
    "animated memes",
]

_TOPIC_TAG_MAP: list[tuple[list[str], list[str]]] = [
    (["cat", "cats", "pet", "animal", "dog"], ["funny animals", "animal memes", "pet humor"]),
    (["tech", "ai", "computer", "code", "software", "robot"], ["tech humor", "coding memes", "ai funny"]),
    (["school", "homework", "teacher", "study", "class"], ["school memes", "student life funny", "homework humor"]),
    (["food", "eat", "cook", "recipe", "snack"], ["food humor", "cooking fails funny", "food memes"]),
    (["wifi", "internet", "phone", "app", "social media"], ["internet humor", "wifi memes", "phone humor"]),
    (["work", "boss", "office", "job", "meeting"], ["work memes", "office humor", "job funny"]),
    (["monday", "morning", "alarm", "wake", "sleep"], ["monday memes", "morning humor", "sleep funny"]),
    (["brain", "think", "mind", "memory", "focus"], ["brain memes", "thinking humor", "mind funny"]),
    (["parent", "family", "kids", "child", "mom", "dad"], ["family humor", "parenting memes", "kids funny"]),
    (["game", "gamer", "video game", "play"], ["gamer memes", "gaming humor", "video game funny"]),
]


def _topic_seed(topic: str) -> int:
    """Generate a stable integer seed from a topic string.

    Uses MD5 (non-security use) to produce a consistent numeric seed so that
    the same topic always selects the same template structure, keeping content
    deterministic and reproducible.
    """
    digest = hashlib.md5(topic.encode("utf-8")).hexdigest()  # noqa: S324
    return int(digest[:8], 16)


def _pick(seq: list, rng: random.Random) -> str:
    """Pick a random element from a list using the provided RNG."""
    return rng.choice(seq)


def _fill(template: str, topic: str) -> str:
    """Replace ``{topic}`` placeholder in *template* with the actual *topic*.

    Also normalises whitespace and strips leading/trailing spaces.
    """
    # Capitalise the topic for natural sentence flow when used at the start
    filled = template.replace("{topic}", topic)
    filled = re.sub(r"\s+", " ", filled).strip()
    return filled


def _build_scenes(rng: random.Random) -> list[str]:
    """Build a list of animation-friendly scene descriptions."""
    intro = _pick(_SCENE_POOLS["intro"], rng)
    middle1 = _pick(_SCENE_POOLS["middle"], rng)
    remaining_middle = [s for s in _SCENE_POOLS["middle"] if s != middle1]
    middle2 = _pick(remaining_middle, rng) if remaining_middle else middle1
    punchline = _pick(_SCENE_POOLS["punchline"], rng)
    return [intro, middle1, middle2, punchline]


def _build_tags(topic: str, rng: random.Random) -> list[str]:
    """Generate a de-duplicated list of comedy animation tags for the topic.

    Starts with the base tag set, appends topic-specific tags, then adds
    a few topic-derived keyword tags.
    """
    tags: list[str] = list(_BASE_TAGS)  # copy to avoid mutation

    topic_lower = topic.lower()
    for keywords, extra_tags in _TOPIC_TAG_MAP:
        if any(kw in topic_lower for kw in keywords):
            tags.extend(extra_tags)

    # Add the raw topic words as tags (up to 3 words)
    words = re.sub(r"[^a-zA-Z0-9 ]", "", topic).split()
    tags.extend(w.lower() for w in words[:3] if len(w) > 3)

    # Shuffle and deduplicate while preserving base tags first
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)

    return deduped[:30]  # YouTube allows up to 500 chars total; 30 tags is safe


def _build_title(topic: str, rng: random.Random) -> str:
    """Generate a clickbait-comedy style title capped at 100 characters."""
    template = _pick(_TITLES, rng)
    title = _fill(template, topic)
    # Hard cap at 100 characters (YouTube limit)
    if len(title) > 100:
        title = title[:97] + "..."
    return title


def _build_description(title: str, topic: str, tags: list[str]) -> str:
    """Build a YouTube description with hashtags and a subscribe CTA."""
    hashtags = " ".join(f"#{t.replace(' ', '')}" for t in tags[:10])
    return (
        f"{title}\n\n"
        f"Welcome to the Funny Animation Shorts Factory — where trending topics "
        f"meet cartoon chaos and comedy gold! Today's episode: {topic}.\n\n"
        f"We use AI-powered comedy scripts, animated-style visuals, and expressive "
        f"voice acting to bring you hilarious animated shorts every day. "
        f"Subscribe so you never miss a laugh!\n\n"
        f"{hashtags}\n\n"
        f"#Shorts #FunnyShorts #AnimationComedy #CartoonHumor"
    )


def generate_script(topic: str) -> ScriptData:
    """Generate a complete comedy animation script for the given *topic*.

    Uses deterministic template selection seeded on the topic text so that
    identical topics always produce structurally identical (though freshened)
    scripts.  A time-based component ensures variety across hourly runs even
    when the same topic recurs.

    Args:
        topic: The trending or comedy topic to build the script around.

    Returns:
        A :class:`ScriptData` dict with keys: ``title``, ``script``,
        ``caption_script``, ``hook``, ``scenes``, ``tags``, ``description``.
    """
    topic = topic.strip() or "random chaos"

    # Combine topic seed with an hourly time component for variety across runs
    seed = _topic_seed(topic) ^ (int(time.time()) // 3600)
    rng = random.Random(seed)

    # 1. Hook
    hook_template = _pick(_HOOKS, rng)
    hook = _fill(hook_template, topic)

    # 2. Body — pick from all available patterns
    body_template = _pick(_ALL_BODIES, rng)
    body = _fill(body_template, topic)

    # 3. Punchline / CTA
    punchline_template = _pick(_PUNCHLINES, rng)
    punchline = _fill(punchline_template, topic)

    # 4. Full script
    script = f"{hook} {body} {punchline}"

    # Trim if too long while preserving sentence boundaries
    words = script.split()
    if len(words) > _MAX_WORDS:
        trimmed = " ".join(words[:_MAX_WORDS])
        # Try to end on a sentence boundary
        for punct in (".", "!", "?"):
            idx = trimmed.rfind(punct)
            if idx > len(trimmed) // 2:
                trimmed = trimmed[: idx + 1]
                break
        script = trimmed

    # 5. Caption script — same as script (plain text, no markup)
    caption_script = re.sub(r"\s+", " ", script).strip()

    # 6. Scenes
    scenes = _build_scenes(rng)

    # 7. Tags
    tags = _build_tags(topic, rng)

    # 8. Title
    title = _build_title(topic, rng)

    # 9. Description
    description = _build_description(title, topic, tags)

    logger.info(
        "Comedy script generated for topic '%s': title='%s', words=%d, scenes=%d",
        topic, title, len(script.split()), len(scenes),
    )

    return ScriptData(
        title=title,
        script=script,
        caption_script=caption_script,
        hook=hook,
        scenes=scenes,
        tags=tags,
        description=description,
    )
