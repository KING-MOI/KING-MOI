import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gen_svg

PROFILE = {
    "name": "Aditya Verma",
    "location": "San Francisco",
    "tagline": "agents & devtools <3",
    "stack": ["rust", "swift"],
    "now": [{"name": "thing", "desc": "a thing"}],
}


class RenderTest(unittest.TestCase):
    def test_output_is_valid_xml(self):
        root = ET.fromstring(gen_svg.render(PROFILE))
        self.assertTrue(root.tag.endswith("svg"))

    def test_special_chars_survive_round_trip(self):
        root = ET.fromstring(gen_svg.render(PROFILE))
        texts = [t.text for t in root.iter("{http://www.w3.org/2000/svg}text")]
        self.assertIn("San Francisco · agents & devtools <3", texts)


def repo(*langs):
    return {"languages": {"edges": [{"size": s, "node": {"name": n, "color": "#000"}} for n, s in langs]}}


class TopLanguagesTest(unittest.TestCase):
    def test_sums_across_repos_and_ranks(self):
        repos = [repo(("Rust", 300), ("Swift", 100)), repo(("Swift", 400), ("Go", 200))]
        got = [(name, round(share, 2)) for name, share, _ in gen_svg.top_languages(repos)]
        self.assertEqual(got, [("Swift", 0.5), ("Rust", 0.3), ("Go", 0.2)])

    def test_limits_to_n(self):
        repos = [repo(*[(f"L{i}", i + 1) for i in range(10)])]
        self.assertEqual(len(gen_svg.top_languages(repos, n=3)), 3)

    def test_missing_color_falls_back(self):
        repos = [{"languages": {"edges": [{"size": 1, "node": {"name": "Nix", "color": None}}]}}]
        self.assertEqual(gen_svg.top_languages(repos)[0][2], gen_svg.MUTED)

    def test_no_repos(self):
        self.assertEqual(gen_svg.top_languages([]), [])


class ContributionStatsTest(unittest.TestCase):
    def test_sample_user(self):
        user = json.loads(gen_svg.SAMPLE.read_text())
        st = gen_svg.contribution_stats(user)
        self.assertEqual(st["commits"], 1184)
        self.assertEqual(st["prs"], 96)
        self.assertEqual(st["issues"], 23)
        self.assertEqual(st["stars"], 412 + 88 + 61 + 14 + 3)


def weeks(*counts):
    return [{"contributionDays": [{"date": "", "contributionCount": c} for c in counts]}]


class StreakTest(unittest.TestCase):
    def test_counts_trailing_run(self):
        self.assertEqual(gen_svg.current_streak(weeks(3, 0, 1, 2, 5)), 3)

    def test_zero_when_no_contributions(self):
        self.assertEqual(gen_svg.current_streak(weeks(0, 0, 0)), 0)


class HumanTest(unittest.TestCase):
    def test_formats(self):
        cases = {0: "0", 999: "999", 1000: "1k", 1184: "1.2k", 12500: "12.5k"}
        for n, want in cases.items():
            self.assertEqual(gen_svg.human(n), want)


if __name__ == "__main__":
    unittest.main()
