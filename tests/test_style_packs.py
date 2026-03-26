"""tests/test_style_packs.py — Unit tests for src/style_packs.py"""

from __future__ import annotations

import unittest


class TestGetStylePack(unittest.TestCase):
    def setUp(self):
        from src.style_packs import get_style_pack, STYLE_PACKS
        self.get = get_style_pack
        self.packs = STYLE_PACKS

    def test_known_pack_returned(self):
        pack = self.get("golden_hour")
        self.assertEqual(pack.name, "golden_hour")

    def test_unknown_returns_default(self):
        pack = self.get("nonexistent_style")
        self.assertIsNotNone(pack)
        self.assertIsInstance(pack.name, str)

    def test_all_registered_packs_retrievable(self):
        for name in self.packs:
            pack = self.get(name)
            self.assertEqual(pack.name, name)


class TestSelectStyleForTopic(unittest.TestCase):
    def setUp(self):
        from src.style_packs import select_style_for_topic
        self.select = select_style_for_topic

    def test_pasta_gets_golden_hour(self):
        pack = self.select("creamy pasta carbonara recipe")
        self.assertEqual(pack.name, "golden_hour")

    def test_cheese_pull_gets_macro_studio(self):
        pack = self.select("the ultimate cheese pull burger")
        self.assertEqual(pack.name, "macro_studio")

    def test_street_taco_gets_street_energy(self):
        pack = self.select("street tacos al pastor recipe")
        self.assertEqual(pack.name, "street_energy")

    def test_salad_bowl_gets_fresh_and_clean(self):
        pack = self.select("healthy avocado grain bowl salad")
        self.assertEqual(pack.name, "fresh_and_clean")

    def test_unknown_food_returns_pack(self):
        pack = self.select("some generic recipe")
        self.assertIsNotNone(pack)
        self.assertIsInstance(pack.name, str)


class TestBuildSceneQueries(unittest.TestCase):
    def setUp(self):
        from src.style_packs import build_scene_queries, get_style_pack
        self.build = build_scene_queries
        self.get_pack = get_style_pack

    def test_enriched_queries_longer(self):
        pack = self.get_pack("golden_hour")
        raw = ["close-up pasta", "plating finished dish"]
        enriched = self.build(raw, pack)
        self.assertEqual(len(enriched), len(raw))
        for orig, enr in zip(raw, enriched):
            self.assertIn(orig, enr)
            self.assertGreaterEqual(len(enr), len(orig))

    def test_no_enrichment_when_flags_off(self):
        pack = self.get_pack("macro_studio")
        raw = ["burger cross-section"]
        enriched = self.build(raw, pack, add_visual_cues=False, add_texture_cues=False)
        self.assertEqual(enriched, raw)

    def test_empty_scenes_returns_empty(self):
        pack = self.get_pack("street_energy")
        self.assertEqual(self.build([], pack), [])


class TestGetColorGradeParams(unittest.TestCase):
    def setUp(self):
        from src.style_packs import get_color_grade_params, get_style_pack
        self.get_params = get_color_grade_params
        self.get_pack = get_style_pack

    def test_returns_dict_with_required_keys(self):
        pack = self.get_pack("macro_studio")
        params = self.get_params(pack)
        for key in ("warmth", "saturation", "contrast", "brightness",
                    "highlight_color", "secondary_color", "style_name"):
            self.assertIn(key, params)

    def test_warmth_in_range(self):
        for name in ("golden_hour", "fresh_and_clean", "dark_luxury"):
            pack = self.get_pack(name)
            params = self.get_params(pack)
            self.assertGreaterEqual(params["warmth"], -1.0)
            self.assertLessEqual(params["warmth"], 1.0)


class TestListAvailableStyles(unittest.TestCase):
    def setUp(self):
        from src.style_packs import list_available_styles, STYLE_PACKS
        self.list_styles = list_available_styles
        self.packs = STYLE_PACKS

    def test_returns_all_packs(self):
        styles = self.list_styles()
        self.assertEqual(len(styles), len(self.packs))

    def test_each_entry_has_required_keys(self):
        for entry in self.list_styles():
            for key in ("name", "display_name", "description", "pacing", "caption_theme"):
                self.assertIn(key, entry)


if __name__ == "__main__":
    unittest.main()
