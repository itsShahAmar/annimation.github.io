"""tests/test_cta_engine.py — Unit tests for src/cta_engine.py"""

from __future__ import annotations

import unittest


class TestGenerateHook(unittest.TestCase):
    def setUp(self):
        from src.cta_engine import generate_hook
        self.gen = generate_hook

    def test_returns_string_with_topic(self):
        hook = self.gen("pasta carbonara", ab_variant="A")
        self.assertIsInstance(hook, str)
        self.assertIn("pasta carbonara", hook)

    def test_variant_b_returns_string(self):
        hook = self.gen("chocolate cake", ab_variant="B")
        self.assertIsInstance(hook, str)
        self.assertGreater(len(hook), 10)

    def test_hook_not_empty(self):
        hook = self.gen("stir fry", ab_variant="A")
        self.assertTrue(hook.strip())


class TestSelectCTAStrategy(unittest.TestCase):
    def setUp(self):
        from src.cta_engine import select_cta_strategy, CTAContext, CTAStrategy
        self.select = select_cta_strategy
        self.Context = CTAContext
        self.Strategy = CTAStrategy

    def test_explicit_strategy_respected(self):
        ctx = self.Context(topic="pasta", style="urgency")
        result = self.select(ctx)
        self.assertEqual(result, self.Strategy.URGENCY)

    def test_community_cue_selects_community(self):
        ctx = self.Context(topic="pasta", style="auto", engagement_cue="high_retention")
        result = self.select(ctx)
        self.assertEqual(result, self.Strategy.COMMUNITY)

    def test_trending_cue_selects_urgency(self):
        ctx = self.Context(topic="pasta", style="auto", engagement_cue="trending")
        result = self.select(ctx)
        self.assertEqual(result, self.Strategy.URGENCY)

    def test_educational_cue_selects_value(self):
        ctx = self.Context(topic="pasta", style="auto", engagement_cue="educational tip")
        result = self.select(ctx)
        self.assertEqual(result, self.Strategy.VALUE)

    def test_invalid_style_falls_back_to_soft_or_random(self):
        ctx = self.Context(topic="pasta", style="nonexistent_style")
        result = self.select(ctx)
        self.assertIsInstance(result, self.Strategy)

    def test_auto_returns_valid_strategy(self):
        ctx = self.Context(topic="pasta", style="auto")
        for _ in range(10):
            result = self.select(ctx)
            self.assertIsInstance(result, self.Strategy)


class TestInjectCTAIntoScript(unittest.TestCase):
    def setUp(self):
        from src.cta_engine import inject_cta_into_script, CTAContext
        self.inject = inject_cta_into_script
        self.Context = CTAContext

    def test_returns_injected_script(self):
        script = (
            "Welcome. Today we make pasta. Add water. Boil it. "
            "Add pasta. Stir gently. Drain and serve. Enjoy your meal!"
        )
        ctx = self.Context(topic="pasta", style="soft")
        result = self.inject(script, ctx)
        self.assertIsInstance(result.text, str)
        self.assertGreater(len(result.text), len(script))

    def test_hook_set(self):
        script = "Short. Script. Here."
        ctx = self.Context(topic="steak", style="soft")
        result = self.inject(script, ctx)
        self.assertTrue(result.hook)
        self.assertIn("steak", result.hook)

    def test_ending_card_set(self):
        script = "A. B. C. D. E."
        ctx = self.Context(topic="soup")
        result = self.inject(script, ctx)
        self.assertTrue(result.ending_card)

    def test_cta_positions_recorded(self):
        script = " ".join(["Sentence number %d." % i for i in range(20)])
        ctx = self.Context(topic="noodles", style="urgency")
        result = self.inject(script, ctx)
        self.assertGreater(len(result.cta_positions), 0)

    def test_strategy_used_returned(self):
        script = "A. B. C."
        ctx = self.Context(topic="stir fry", style="community")
        result = self.inject(script, ctx)
        from src.cta_engine import CTAStrategy
        self.assertEqual(result.strategy_used, CTAStrategy.COMMUNITY)

    def test_short_script_still_works(self):
        script = "Quick recipe!"
        ctx = self.Context(topic="salad")
        result = self.inject(script, ctx)
        self.assertIsInstance(result.text, str)
        self.assertTrue(result.hook)


class TestGenerateABVariants(unittest.TestCase):
    def setUp(self):
        from src.cta_engine import generate_ab_variants
        self.gen = generate_ab_variants

    def test_returns_two_variants(self):
        a, b = self.gen("Test script.", "pasta")
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)

    def test_variants_have_different_ab_labels(self):
        a, b = self.gen("Test script sentence.", "pasta")
        self.assertEqual(a.ab_variant, "A")
        self.assertEqual(b.ab_variant, "B")


class TestEndingCard(unittest.TestCase):
    def setUp(self):
        from src.cta_engine import get_ending_card_text
        self.get = get_ending_card_text

    def test_returns_non_empty_string(self):
        card = self.get()
        self.assertIsInstance(card, str)
        self.assertTrue(card.strip())


class TestSubscribePrompt(unittest.TestCase):
    def setUp(self):
        from src.cta_engine import get_subscribe_prompt_for_caption
        self.get = get_subscribe_prompt_for_caption

    def test_variant_a(self):
        prompt = self.get("A")
        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())

    def test_variant_b(self):
        prompt = self.get("B")
        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
