"""tests/test_trend_scorer.py — Unit tests for src/trend_scorer.py"""

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import os


class TestDeduplicate(unittest.TestCase):
    def setUp(self):
        from src.trend_scorer import deduplicate_topics
        self.dedup = deduplicate_topics

    def test_exact_duplicates_removed(self):
        topics = ["pasta recipe", "pasta recipe", "easy pasta"]
        result = self.dedup(topics)
        self.assertIn("pasta recipe", result)
        # "pasta recipe" should appear only once
        self.assertEqual(result.count("pasta recipe"), 1)

    def test_near_duplicates_removed(self):
        # Jaccard >= 0.75 should remove near-dups
        topics = ["how to make crispy chicken", "how to make crispy chicken perfectly"]
        result = self.dedup(topics)
        self.assertLessEqual(len(result), 2)

    def test_distinct_topics_preserved(self):
        topics = ["pasta recipe", "smoothie bowl", "street tacos", "chocolate cake"]
        result = self.dedup(topics)
        self.assertEqual(len(result), 4)

    def test_empty_list(self):
        self.assertEqual(self.dedup([]), [])


class TestScoreTopics(unittest.TestCase):
    def setUp(self):
        from src.trend_scorer import score_topics
        self.score = score_topics

    def test_food_topic_scores_higher_than_non_food(self):
        topics = ["best pasta recipe", "stock market crash"]
        scored = self.score(topics)
        food = next(s for s in scored if "pasta" in s.topic)
        non_food = next(s for s in scored if "stock market" in s.topic)
        self.assertGreater(food.raw_score, non_food.raw_score)

    def test_blacklisted_topic_rejected(self):
        topics = ["politics in the kitchen", "easy pasta recipe"]
        scored = self.score(topics)
        blacklisted = next((s for s in scored if "politics" in s.topic), None)
        self.assertIsNotNone(blacklisted)
        self.assertTrue(blacklisted.rejected)
        self.assertEqual(blacklisted.raw_score, 0.0)

    def test_scores_in_range(self):
        topics = ["pasta recipe", "chocolate cake", "quick dinner"]
        scored = self.score(topics)
        for s in scored:
            self.assertGreaterEqual(s.raw_score, 0.0)
            self.assertLessEqual(s.raw_score, 1.0)

    def test_velocity_from_source_membership(self):
        topics = ["pasta recipe", "quick dinner"]
        source_membership = {
            "google": ["pasta recipe", "quick dinner"],
            "youtube": ["pasta recipe"],
        }
        scored = self.score(topics, source_membership=source_membership)
        pasta = next(s for s in scored if "pasta" in s.topic)
        dinner = next(s for s in scored if "dinner" in s.topic)
        # pasta appears in 2 sources → higher velocity
        self.assertGreaterEqual(pasta.velocity_score, dinner.velocity_score)

    def test_empty_list(self):
        self.assertEqual(self.score([]), [])


class TestFilterNovelTopics(unittest.TestCase):
    def setUp(self):
        from src.trend_scorer import filter_novel_topics, score_topics
        self.filter_novel = filter_novel_topics
        self.score = score_topics

    def test_recently_used_topic_penalised(self):
        import tempfile, json, time
        topics = ["pasta recipe", "quick dinner"]
        scored = self.score(topics)

        # Write a history file marking "pasta recipe" as recently used
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"pasta recipe": time.time() - 60}, f)
            history_path = f.name

        try:
            result = self.filter_novel(scored, history_path=history_path)
            pasta = next(s for s in result if "pasta" in s.topic)
            self.assertFalse(pasta.is_novel)
            # Score should be halved
            original = next(s for s in self.score(topics) if "pasta" in s.topic)
            self.assertAlmostEqual(pasta.raw_score, original.raw_score * 0.5, places=3)
        finally:
            os.unlink(history_path)

    def test_old_history_not_penalised(self):
        import tempfile, json, time
        topics = ["pasta recipe"]
        scored = self.score(topics)

        # Write a history file with an entry older than the novelty window
        old_time = time.time() - (86_400 * 10)  # 10 days ago
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"pasta recipe": old_time}, f)
            history_path = f.name

        try:
            result = self.filter_novel(scored, history_path=history_path)
            pasta = next(s for s in result if "pasta" in s.topic)
            self.assertTrue(pasta.is_novel)
        finally:
            os.unlink(history_path)


class TestSelectBestTopic(unittest.TestCase):
    def setUp(self):
        from src.trend_scorer import select_best_topic
        self.select = select_best_topic

    def test_returns_string_and_list(self):
        topics = ["easy pasta recipe", "chocolate cake recipe", "quick stir fry"]
        with tempfile.TemporaryDirectory() as tmpdir:
            history = os.path.join(tmpdir, "history.json")
            topic, scored = self.select(topics, history_path=history)
        self.assertIsInstance(topic, str)
        self.assertIsInstance(scored, list)
        self.assertIn(topic, topics)

    def test_fallback_on_all_rejected(self):
        topics = ["politics war violence death crime"]
        with tempfile.TemporaryDirectory() as tmpdir:
            history = os.path.join(tmpdir, "history.json")
            topic, scored = self.select(topics, history_path=history)
        # Should still return a string (fallback)
        self.assertIsInstance(topic, str)

    def test_food_topic_wins(self):
        topics = ["the best crispy chicken recipe ever", "stock market analysis"]
        with tempfile.TemporaryDirectory() as tmpdir:
            history = os.path.join(tmpdir, "history.json")
            topic, scored = self.select(topics, top_k=1, history_path=history)
        self.assertIn("chicken", topic.lower())


class TestSaveTrendDigest(unittest.TestCase):
    def setUp(self):
        from src.trend_scorer import save_trend_digest, score_topics
        self.save_digest = save_trend_digest
        self.score = score_topics

    def test_digest_written(self):
        scored = self.score(["pasta recipe", "chocolate cake"])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.save_digest(scored, "pasta recipe", output_dir=tmpdir)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["selected_topic"], "pasta recipe")
            self.assertIn("top_20", data)
            self.assertIn("stats", data)


class TestRecordUsedTopic(unittest.TestCase):
    def setUp(self):
        from src.trend_scorer import record_used_topic
        self.record = record_used_topic

    def test_records_topic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = os.path.join(tmpdir, "history.json")
            self.record("pasta recipe", history_path=history_path)
            data = json.loads(Path(history_path).read_text())
            self.assertIn("pasta recipe", data)

    def test_evicts_old_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = os.path.join(tmpdir, "history.json")
            # Manually write an old entry
            old = {"stale topic": time.time() - 86_400 * 10}
            Path(history_path).write_text(json.dumps(old))
            self.record("new topic", history_path=history_path)
            data = json.loads(Path(history_path).read_text())
            # Old entry should be evicted
            self.assertNotIn("stale topic", data)
            self.assertIn("new topic", data)


if __name__ == "__main__":
    unittest.main()
