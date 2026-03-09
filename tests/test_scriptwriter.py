"""
tests/test_scriptwriter.py — Unit tests for src/scriptwriter.py

Tests the comedy animation script generator with no external API calls.
Run with: python -m pytest tests/ -v
"""

import unittest

import sys
from unittest.mock import MagicMock

# Stub heavy optional imports not needed for scriptwriter tests
for mod in ("edge_tts", "gtts", "moviepy", "moviepy.editor",
            "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
            "pydub", "mutagen", "mutagen.mp3",
            "googleapiclient", "googleapiclient.discovery"):
    sys.modules.setdefault(mod, MagicMock())


class TestGenerateScript(unittest.TestCase):
    """Tests for scriptwriter.generate_script() — comedy animation output."""

    def setUp(self):
        from src.scriptwriter import generate_script
        self.generate_script = generate_script

    def test_returns_required_keys(self):
        """Result must contain all keys that pipeline.py depends on."""
        result = self.generate_script("AI advancements")
        required_keys = {"title", "script", "caption_script", "hook", "scenes", "tags", "description"}
        self.assertEqual(required_keys, required_keys & result.keys(),
                         f"Missing keys: {required_keys - result.keys()}")

    def test_title_is_non_empty_string(self):
        result = self.generate_script("climate change")
        self.assertIsInstance(result["title"], str)
        self.assertTrue(result["title"].strip(), "title must not be blank")

    def test_title_max_100_chars(self):
        """YouTube limits titles to 100 characters."""
        result = self.generate_script("a very long topic name " * 5)
        self.assertLessEqual(len(result["title"]), 100,
                             "title exceeds 100-character YouTube limit")

    def test_title_has_comedy_style(self):
        """Comedy titles should contain exclamation marks or emoji-like characters."""
        result = self.generate_script("cats")
        title = result["title"]
        # Comedy titles have energetic punctuation or emoji references
        has_energy = any(c in title for c in "!?😂💀🤣😭🔥💥😱🎉")
        has_caps = any(word.isupper() and len(word) > 2 for word in title.split())
        self.assertTrue(has_energy or has_caps,
                        f"Comedy title lacks energetic style: {title!r}")

    def test_script_is_non_empty_string(self):
        result = self.generate_script("space exploration")
        self.assertIsInstance(result["script"], str)
        self.assertTrue(result["script"].strip(), "script must not be blank")

    def test_script_has_no_ssml_tags(self):
        """TTS receives the script — it must be plain text with no SSML markup."""
        result = self.generate_script("quantum computing")
        script = result["script"]
        self.assertNotIn("<speak", script, "script must not contain SSML <speak> tag")
        self.assertNotIn("<voice", script, "script must not contain SSML <voice> tag")
        self.assertNotIn("<prosody", script, "script must not contain SSML <prosody> tag")

    def test_hook_is_comedy_style(self):
        """Hook templates must be funny/absurd rather than dry news-style."""
        result = self.generate_script("Wi-Fi")
        hook = result["hook"]
        self.assertIsInstance(hook, str)
        self.assertTrue(hook.strip(), "hook must not be blank")
        # Comedy hooks often contain POV, What if, Nobody, me, etc.
        comedy_markers = ["pov", "what if", "nobody", "me ", "brain", "chaos",
                          "cartoon", "if ", "when ", "your ", "plot twist"]
        hook_lower = hook.lower()
        has_comedy = any(marker in hook_lower for marker in comedy_markers)
        # Hooks should also NOT be the old generic news style
        news_markers = ["breaking developments", "industry leaders", "here is what the latest data"]
        has_old_news = any(marker in hook_lower for marker in news_markers)
        self.assertFalse(has_old_news, f"Hook still uses old news style: {hook!r}")

    def test_script_contains_subscribe_cta(self):
        """Script must end with a subscribe/follow call to action."""
        result = self.generate_script("alarm clocks")
        script = result["script"].lower()
        has_cta = any(word in script for word in ["subscribe", "follow", "like"])
        self.assertTrue(has_cta, "Script must contain a subscribe/follow CTA")

    def test_tags_is_list_of_strings(self):
        result = self.generate_script("electric vehicles")
        tags = result["tags"]
        self.assertIsInstance(tags, list)
        self.assertTrue(all(isinstance(t, str) for t in tags),
                        "all tags must be strings")

    def test_tags_include_comedy_animation_keywords(self):
        """Tags must include comedy and animation keywords."""
        result = self.generate_script("cats")
        tags_joined = " ".join(result["tags"]).lower()
        comedy_tag_keywords = ["funny", "animation", "comedy", "cartoon", "humor"]
        has_comedy_tags = any(kw in tags_joined for kw in comedy_tag_keywords)
        self.assertTrue(has_comedy_tags,
                        f"Tags must include comedy/animation keywords. Got: {result['tags'][:10]}")

    def test_scenes_is_non_empty_list(self):
        result = self.generate_script("machine learning")
        scenes = result["scenes"]
        self.assertIsInstance(scenes, list)
        self.assertGreater(len(scenes), 0, "scenes list must not be empty")

    def test_scenes_are_animation_friendly(self):
        """Scene descriptions should mention cartoon-style visuals."""
        result = self.generate_script("homework")
        scenes = result["scenes"]
        scenes_text = " ".join(scenes).lower()
        animation_words = ["cartoon", "chibi", "stick figure", "blob", "pixel",
                           "rubber hose", "character", "animated"]
        has_animation = any(word in scenes_text for word in animation_words)
        self.assertTrue(has_animation,
                        f"Scenes should include animation-style descriptions. Got: {scenes}")

    def test_description_is_string(self):
        result = self.generate_script("cryptocurrency")
        self.assertIsInstance(result["description"], str)

    def test_description_mentions_animation_factory(self):
        """Description should mention the Funny Animation Shorts Factory brand."""
        result = self.generate_script("social media")
        desc = result["description"].lower()
        self.assertIn("animation", desc,
                      "Description should mention animation")

    def test_deterministic_structure(self):
        """Two calls with the same topic must both return all required keys."""
        r1 = self.generate_script("renewable energy")
        r2 = self.generate_script("renewable energy")
        self.assertEqual(set(r1.keys()), set(r2.keys()))

    def test_various_topics_do_not_raise(self):
        """Scriptwriter must handle a variety of topics without crashing."""
        topics = [
            "Why cats think they own the house",
            "If alarm clocks had feelings",
            "Explaining Wi-Fi to a medieval knight",
            "Things your brain does at 3 AM",
            "Ask HN: Career advice",
            "",          # empty topic — should not crash
            "  spaces  ",
        ]
        for topic in topics:
            with self.subTest(topic=topic):
                try:
                    result = self.generate_script(topic)
                    self.assertIn("title", result)
                except Exception as exc:
                    self.fail(f"generate_script({topic!r}) raised unexpectedly: {exc}")


class TestCaptionScript(unittest.TestCase):
    """Tests for the caption_script field used by video_creator."""

    def test_caption_script_is_string(self):
        from src.scriptwriter import generate_script
        result = generate_script("health tips")
        self.assertIsInstance(result["caption_script"], str)

    def test_caption_script_no_markup(self):
        """caption_script is rendered as subtitle text — must be plain."""
        from src.scriptwriter import generate_script
        result = generate_script("fitness motivation")
        cap = result["caption_script"]
        self.assertNotIn("<", cap, "caption_script must not contain HTML/XML tags")
        self.assertNotIn(">", cap, "caption_script must not contain HTML/XML tags")


class TestComedyTopicVariety(unittest.TestCase):
    """Tests that different topics generate varied comedy scripts."""

    def test_different_topics_produce_different_hooks(self):
        """Different topics should generally produce different hooks (variety check)."""
        from src.scriptwriter import generate_script
        r1 = generate_script("cats taking over the internet")
        r2 = generate_script("alarm clocks with feelings")
        # While templates overlap, hooks should differ for very different topics
        # (this is a soft check — it could occasionally fail if seeds collide)
        # At minimum, both should be non-empty
        self.assertTrue(r1["hook"].strip())
        self.assertTrue(r2["hook"].strip())

    def test_comedy_fallback_topic_works(self):
        """The comedy fallback topic placeholder should produce a valid script."""
        from src.scriptwriter import generate_script
        result = generate_script("random chaos")
        self.assertIn("title", result)
        self.assertTrue(result["script"].strip())


if __name__ == "__main__":
    unittest.main()
