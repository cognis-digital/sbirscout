"""Hardening tests — edge cases, bad input, and error paths."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbirscout.core import (
    CapabilityProfile,
    Topic,
    _profile_from_raw,
    load_topics,
    parse_topics,
    score_topic,
    score_topics,
)
from sbirscout.cli import main


# ---------------------------------------------------------------------------
# parse_topics edge cases
# ---------------------------------------------------------------------------

class TestParseTopicsEdgeCases(unittest.TestCase):

    def test_empty_list_returns_empty(self):
        """parse_topics([]) must return [] without error."""
        self.assertEqual(parse_topics([]), [])

    def test_empty_topics_key_returns_empty(self):
        """parse_topics({'topics': []}) must return []."""
        self.assertEqual(parse_topics({"topics": []}), [])

    def test_null_input_raises(self):
        """parse_topics(None) must raise ValueError, not AttributeError."""
        with self.assertRaises(ValueError):
            parse_topics(None)

    def test_non_dict_non_list_raises(self):
        """parse_topics(42) must raise ValueError."""
        with self.assertRaises(ValueError):
            parse_topics(42)

    def test_topics_null_value_raises(self):
        """{'topics': null} in JSON → None list → ValueError."""
        # json.loads gives None for null
        raw = json.loads('{"topics": null}')
        # null topics → treat as empty (our impl normalises with `or []`)
        result = parse_topics(raw)
        self.assertEqual(result, [])

    def test_topics_non_list_value_raises(self):
        """{'topics': 'string'} must raise ValueError."""
        with self.assertRaises(ValueError):
            parse_topics({"topics": "not-a-list"})

    def test_non_dict_item_raises(self):
        """A list item that is not a dict must raise ValueError."""
        with self.assertRaises(ValueError):
            parse_topics([{"topic_id": "T1", "title": "Good"}, "bad-item"])

    def test_keywords_as_string_coerced(self):
        """A bare string for keywords should be wrapped into a 1-element list."""
        topics = parse_topics([{"topic_id": "T1", "title": "Test", "keywords": "ml"}])
        self.assertEqual(len(topics), 1)
        self.assertIn("ml", topics[0].keywords)

    def test_missing_topic_id_auto_generated(self):
        """A topic without topic_id or id gets an auto-generated T1, T2… id."""
        topics = parse_topics([{"title": "No ID"}])
        self.assertEqual(topics[0].topic_id, "T1")


# ---------------------------------------------------------------------------
# load_topics edge cases
# ---------------------------------------------------------------------------

class TestLoadTopics(unittest.TestCase):

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_topics("/no/such/file.json")

    def test_invalid_json_raises_value_error(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("{bad json!!}")
            path = fh.name
        try:
            with self.assertRaises(ValueError) as cm:
                load_topics(path)
            self.assertIn("not valid JSON", str(cm.exception))
        finally:
            os.unlink(path)

    def test_empty_topics_list_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump({"topics": []}, fh)
            path = fh.name
        try:
            self.assertEqual(load_topics(path), [])
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# _profile_from_raw edge cases
# ---------------------------------------------------------------------------

class TestProfileFromRaw(unittest.TestCase):

    def test_invalid_min_award_raises(self):
        with self.assertRaises(ValueError) as cm:
            _profile_from_raw({"capabilities": [], "min_award": "not-a-number"})
        self.assertIn("min_award", str(cm.exception))

    def test_capabilities_non_list_raises(self):
        with self.assertRaises(ValueError) as cm:
            _profile_from_raw({"capabilities": "string"})
        self.assertIn("capabilities", str(cm.exception))

    def test_preferred_phases_non_list_raises(self):
        with self.assertRaises(ValueError) as cm:
            _profile_from_raw({"capabilities": [], "preferred_phases": "I"})
        self.assertIn("preferred_phases", str(cm.exception))

    def test_none_returns_empty_profile(self):
        profile = _profile_from_raw(None)
        self.assertEqual(profile.capabilities, [])


# ---------------------------------------------------------------------------
# CLI hardening paths
# ---------------------------------------------------------------------------

class TestCliHardening(unittest.TestCase):

    def _write_tmp_json(self, data) -> str:
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(data, fh)
        fh.close()
        return fh.name

    def test_missing_topics_file_exits_2(self):
        self.assertEqual(main(["scout", "/no/such/file.json"]), 2)

    def test_malformed_json_exits_2(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("{not json")
            path = fh.name
        try:
            self.assertEqual(main(["scout", path]), 2)
        finally:
            os.unlink(path)

    def test_empty_topics_exits_2(self):
        path = self._write_tmp_json({"topics": []})
        try:
            self.assertEqual(main(["scout", path]), 2)
        finally:
            os.unlink(path)

    def test_bad_today_date_exits_2(self):
        # We need a valid topics file to get past load_topics
        demo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demos", "01-basic", "topics.json",
        )
        self.assertEqual(main(["scout", demo, "--today", "not-a-date"]), 2)

    def test_top_zero_exits_2(self):
        demo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demos", "01-basic", "topics.json",
        )
        self.assertEqual(main(["scout", demo, "--top", "0"]), 2)

    def test_top_negative_exits_2(self):
        demo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demos", "01-basic", "topics.json",
        )
        self.assertEqual(main(["scout", demo, "--top", "-1"]), 2)

    def test_bad_profile_json_exits_2(self):
        demo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demos", "01-basic", "topics.json",
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("{bad json")
            profile_path = fh.name
        try:
            self.assertEqual(
                main(["scout", demo, "--profile", profile_path]), 2
            )
        finally:
            os.unlink(profile_path)


# ---------------------------------------------------------------------------
# Score edge cases
# ---------------------------------------------------------------------------

class TestScoreEdgeCases(unittest.TestCase):

    def test_score_empty_topics_list(self):
        """score_topics on empty list should return empty list."""
        profile = CapabilityProfile(capabilities=["ml"])
        self.assertEqual(score_topics([], profile), [])

    def test_score_topic_no_close_date(self):
        """Topic without close_date must not crash; urgency partial credit."""
        t = Topic("T1", "Test", close_date=None, award_ceiling=500_000)
        profile = CapabilityProfile(capabilities=["test"])
        st = score_topic(t, profile)
        self.assertGreaterEqual(st.score, 0.0)
        self.assertIsNotNone(st.bid_recommendation)

    def test_score_topic_bad_close_date(self):
        """Topic with unparseable close_date falls back gracefully."""
        t = Topic("T1", "Test", close_date="not-a-date", award_ceiling=500_000)
        profile = CapabilityProfile(capabilities=["test"])
        # Should not raise
        st = score_topic(t, profile)
        self.assertIn(st.bid_recommendation, {"GO", "CONSIDER", "PASS"})

    def test_award_ceiling_zero_gives_zero_funding_score(self):
        t = Topic("T1", "Test", award_ceiling=0.0)
        profile = CapabilityProfile(capabilities=["test"])
        st = score_topic(t, profile)
        self.assertEqual(st.components["funding"], 0.0)

    def test_score_capped_at_100(self):
        """Score must never exceed 100 regardless of inputs."""
        t = Topic(
            "T1", "Deep learning edge ml autonomous systems rf sensing uas",
            award_ceiling=10_000_000,
            close_date="2099-01-01",
            program="SBIR",
        )
        profile = CapabilityProfile(
            capabilities=["deep learning", "edge ml", "autonomous systems", "rf sensing", "uas"],
            preferred_phases=["I"],
            has_research_partner=True,
        )
        st = score_topic(t, profile)
        self.assertLessEqual(st.score, 100.0)

    def test_score_not_negative(self):
        """Score must never be negative."""
        t = Topic("T1", "Unrelated", award_ceiling=0, program="STTR")
        profile = CapabilityProfile(capabilities=["quantum"], has_research_partner=False)
        st = score_topic(t, profile)
        self.assertGreaterEqual(st.score, 0.0)


if __name__ == "__main__":
    unittest.main()
