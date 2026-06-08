"""Smoke tests for SBIRSCOUT. No network. Standard library only."""
import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbirscout import (  # noqa: E402
    TOOL_NAME,
    TOOL_VERSION,
    CapabilityProfile,
    Topic,
    digest,
    normalize_source,
    parse_topics,
    score_topic,
    score_topics,
)
from sbirscout.cli import main  # noqa: E402

TODAY = date(2026, 6, 8)
DEMO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demos",
    "01-basic",
    "topics.json",
)


class TestCore(unittest.TestCase):
    def setUp(self):
        with open(DEMO, encoding="utf-8") as fh:
            self.topics = parse_topics(json.load(fh))
        self.profile = CapabilityProfile(
            capabilities=["autonomous systems", "edge ml", "rf sensing", "uas"],
            preferred_phases=["I", "DIRECT_II"],
            has_research_partner=False,
        )

    def test_meta(self):
        self.assertEqual(TOOL_NAME, "sbirscout")
        self.assertTrue(TOOL_VERSION)

    def test_parse_count(self):
        self.assertEqual(len(self.topics), 5)

    def test_source_normalization(self):
        self.assertEqual(normalize_source("DoD"), "dsip")
        self.assertEqual(normalize_source("HHS"), "nih")
        self.assertEqual(normalize_source("SBA"), "sbir_gov")
        self.assertEqual(normalize_source(""), "sbir_gov")

    def test_phase_normalization(self):
        self.assertEqual(Topic("x", "t", phase="Phase 2").phase, "II")
        self.assertEqual(Topic("x", "t", phase="direct to ii").phase, "DIRECT_II")

    def test_top_topic_is_go(self):
        ranked = score_topics(self.topics, self.profile, today=TODAY)
        self.assertEqual(ranked[0].topic.topic_id, "AF252-D015")
        self.assertEqual(ranked[0].bid_recommendation, "GO")
        self.assertGreater(ranked[0].score, 60)

    def test_closed_topic_forced_pass(self):
        ranked = {s.topic.topic_id: s for s in score_topics(self.topics, self.profile, today=TODAY)}
        self.assertEqual(ranked["A252-EXP"].bid_recommendation, "PASS")

    def test_sttr_partner_penalty(self):
        nih = next(t for t in self.topics if t.program == "STTR")
        no_partner = score_topic(nih, self.profile, today=TODAY)
        with_partner = score_topic(
            nih,
            CapabilityProfile(
                capabilities=self.profile.capabilities,
                preferred_phases=self.profile.preferred_phases,
                has_research_partner=True,
            ),
            today=TODAY,
        )
        self.assertGreater(with_partner.score, no_partner.score)
        self.assertEqual(no_partner.components["sttr_partner_penalty"], -40.0)

    def test_digest_rollups(self):
        d = digest(self.topics, self.profile, today=TODAY)
        self.assertEqual(d["total_topics"], 5)
        self.assertEqual(sum(d["by_recommendation"].values()), 5)
        self.assertEqual(sum(d["by_source"].values()), 5)

    def test_no_capabilities_no_match(self):
        s = score_topic(self.topics[0], CapabilityProfile(capabilities=[]), today=TODAY)
        self.assertEqual(s.components["capability_match"], 0.0)


class TestCli(unittest.TestCase):
    def test_version(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_scout_json(self):
        rc = main(
            [
                "--format",
                "json",
                "scout",
                DEMO,
                "--capabilities",
                "autonomous systems,edge ml,rf sensing,uas",
                "--phases",
                "I,DIRECT_II",
                "--today",
                "2026-06-08",
            ]
        )
        self.assertEqual(rc, 0)

    def test_scout_table(self):
        rc = main(["scout", DEMO, "--capabilities", "edge ml", "--today", "2026-06-08"])
        self.assertEqual(rc, 0)

    def test_sources(self):
        self.assertEqual(main(["sources"]), 0)

    def test_missing_file(self):
        self.assertEqual(main(["scout", "/no/such/file.json"]), 2)

    def test_no_command_returns_1(self):
        self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
