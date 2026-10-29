import json
import sys
import tempfile
import unittest
from unittest import mock
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

    def test_renders_full_sample(self):
        user = json.loads(gen_svg.SAMPLE.read_text())
        profile = {
            **PROFILE,
            "stats": gen_svg.contribution_stats(user),
            "languages": gen_svg.top_languages(user["repositories"]["nodes"]),
        }
        texts = [t.text for t in ET.fromstring(gen_svg.render(profile)).iter("{http://www.w3.org/2000/svg}text")]
        self.assertIn("day streak", texts)
        self.assertIn("top languages", texts)

    def test_special_chars_survive_round_trip(self):
        root = ET.fromstring(gen_svg.render(PROFILE))
        texts = [t.text for t in root.iter("{http://www.w3.org/2000/svg}text")]
        self.assertIn("San Francisco · agents & devtools <3", texts)


class LoadProfileTest(unittest.TestCase):
    def test_repo_profile_loads(self):
        self.assertEqual(gen_svg.load_profile()["handle"], "KING-MOI")

    def test_missing_keys_are_named(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "profile.toml"
            path.write_text('name = "x"\n')
            with self.assertRaises(SystemExit) as cm:
                gen_svg.load_profile(path)
        self.assertIn("handle", str(cm.exception))


class PillsTest(unittest.TestCase):
    def test_wraps_before_right_edge(self):
        lines, bottom = gen_svg.pills(["typescript"] * 12, 32, 0)
        rects = [ET.fromstring(line) for line in lines if line.startswith("<rect")]
        self.assertTrue(all(int(r.get("x")) + int(r.get("width")) <= gen_svg.WIDTH - 32 for r in rects))
        self.assertGreater(bottom, 26)


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

    def test_empty_today_does_not_break_streak(self):
        self.assertEqual(gen_svg.current_streak(weeks(0, 4, 2, 0)), 2)

    def test_zero_when_no_contributions(self):
        self.assertEqual(gen_svg.current_streak(weeks(0, 0, 0)), 0)


class FetchUserTest(unittest.TestCase):
    def test_follows_repository_pages(self):
        def page(names, cursor):
            return {"user": {"repositories": {
                "pageInfo": {"hasNextPage": cursor is not None, "endCursor": cursor},
                "nodes": [{"name": n} for n in names],
            }}}

        pages = [page(["a", "b"], "c1"), page(["c"], "c2"), page(["d"], None)]
        with mock.patch.object(gen_svg, "graphql", side_effect=pages) as gql:
            user = gen_svg.fetch_user("someone", "t")
        self.assertEqual([r["name"] for r in user["repositories"]["nodes"]], ["a", "b", "c", "d"])
        self.assertEqual(gql.call_args_list[-1].args[1]["after"], "c2")


class ActivityTest(unittest.TestCase):
    def test_quiet_year_renders_flat_bars(self):
        lines, _ = gen_svg.activity({"stats": {"weekly": [0, 0, 0]}}, 0)
        bars = [ET.fromstring(line) for line in lines[1:]]
        self.assertEqual({b.get("fill") for b in bars}, {gen_svg.BORDER})

    def test_tallest_bar_is_busiest_week(self):
        lines, _ = gen_svg.activity({"stats": {"weekly": [1, 9, 3]}}, 0)
        heights = [float(ET.fromstring(line).get("height")) for line in lines[1:]]
        self.assertEqual(heights.index(max(heights)), 1)


class HumanTest(unittest.TestCase):
    def test_formats(self):
        cases = {0: "0", 999: "999", 1000: "1k", 1184: "1.2k", 12500: "12.5k"}
        for n, want in cases.items():
            self.assertEqual(gen_svg.human(n), want)


if __name__ == "__main__":
    unittest.main()
