#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "readme.svg"
SAMPLE = ROOT / "data" / "sample_user.json"
WIDTH = 800
BG = "#0d1117"
FG = "#e6edf3"
MUTED = "#7d8590"
BORDER = "#30363d"
ACCENT = "#3fb950"
FONT = "ui-monospace, SFMono-Regular, Menlo, monospace"
GRAPHQL = "https://api.github.com/graphql"


def graphql(query, variables, token, attempts=3):
    req = urllib.request.Request(
        GRAPHQL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "readme-svg"},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == attempts - 1:
                raise
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
        time.sleep(2**attempt)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0]["message"])
    return payload["data"]


def load_profile(path=ROOT / "profile.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_user(login, token):
    user = graphql(QUERY, {"login": login}, token)["user"]
    page = user["repositories"]
    while page["pageInfo"]["hasNextPage"]:
        page = graphql(QUERY, {"login": login, "after": page["pageInfo"]["endCursor"]}, token)["user"]["repositories"]
        user["repositories"]["nodes"] += page["nodes"]
    return user


def current_streak(weeks):
    days = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    if days and days[-1] == 0:
        days.pop()
    streak = 0
    for count in reversed(days):
        if count == 0:
            break
        streak += 1
    return streak


def contribution_stats(user):
    cc = user["contributionsCollection"]
    return {
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "streak": current_streak(cc["contributionCalendar"]["weeks"]),
        "weekly": [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cc["contributionCalendar"]["weeks"]],
    }


def top_languages(repos, n=6):
    totals = {}
    colors = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or MUTED
    total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [(name, size / total, colors[name]) for name, size in ranked]


def human(n):
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"


def text(x, y, s, size=14, fill=FG):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}">{escape(s)}</text>'


def label(y, s):
    return text(32, y + 12, s, 12, MUTED)


def pills(items, x, y):
    out = []
    left = x
    for item in items:
        w = len(item) * 8 + 24
        if x + w > WIDTH - 32:
            x, y = left, y + 34
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="13" fill="none" stroke="{BORDER}"/>')
        out.append(text(x + 12, y + 18, item, 13))
        x += w + 8
    return out, y + 26


def header(profile, y):
    return [
        text(32, y + 32, profile["name"], 24),
        text(32, y + 60, f'{profile["location"]} · {profile["tagline"]}', 14, MUTED),
    ], 80


def stack(profile, y):
    lines, bottom = pills(profile["stack"], 32, y + 24)
    return [label(y, "stack"), *lines], bottom - y + 20


def stats(profile, y):
    st = profile.get("stats")
    if not st:
        return [], 0
    cells = [
        ("contributions", st["contributions"]),
        ("commits", st["commits"]),
        ("prs", st["prs"]),
        ("issues", st["issues"]),
        ("stars", st["stars"]),
        ("day streak", st["streak"]),
    ]
    col_w = (WIDTH - 64) // len(cells)
    out = [label(y, "last year")]
    for i, (name, value) in enumerate(cells):
        x = 32 + i * col_w
        out.append(text(x, y + 44, human(value), 22))
        out.append(text(x, y + 64, name, 12, MUTED))
    return out, 84


def activity(profile, y):
    weekly = (profile.get("stats") or {}).get("weekly")
    if not weekly:
        return [], 0
    peak = max(weekly) or 1
    step = (WIDTH - 64) / len(weekly)
    out = [label(y, "activity")]
    for i, count in enumerate(weekly):
        h = max(2, round(count / peak * 40))
        out.append(f'<rect x="{32 + i * step:.1f}" y="{y + 64 - h}" width="{step * 0.7:.1f}" height="{h}" rx="1" fill="{ACCENT if count else BORDER}"/>')
    return out, 80


def languages(profile, y):
    langs = profile.get("languages")
    if not langs:
        return [], 0
    bar_w = WIDTH - 64
    out = [
        label(y, "top languages"),
        f'<clipPath id="bar"><rect x="32" y="{y + 24}" width="{bar_w}" height="8" rx="4"/></clipPath>',
    ]
    x = 32.0
    for name, share, color in langs:
        w = share * bar_w
        out.append(f'<rect x="{x:.1f}" y="{y + 24}" width="{w:.1f}" height="8" fill="{color}" clip-path="url(#bar)"/>')
        x += w
    col_w = bar_w // 3
    for i, (name, share, color) in enumerate(langs):
        cx = 32 + (i % 3) * col_w
        cy = y + 56 + (i // 3) * 22
        out.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>')
        out.append(text(cx + 16, cy, f"{name} {share * 100:.1f}%", 13))
    rows = (len(langs) + 2) // 3
    return out, 48 + rows * 22


def now_building(profile, y):
    out = [label(y, "now building")]
    row = y + 40
    for item in profile.get("now", []):
        out.append(text(32, row, f'▸ {item["name"]}', 14))
        out.append(text(220, row, item["desc"], 13, MUTED))
        row += 24
    return out, row - y


def render(profile):
    body = []
    y = 24
    for section in (header, stack, stats, activity, languages, now_building):
        lines, h = section(profile, y)
        body += lines
        y += h
    if profile.get("updated"):
        body.append(f'<text x="{WIDTH - 32}" y="{y + 8}" fill="{BORDER}" font-size="11" text-anchor="end">updated {profile["updated"]}</text>')
        y += 16
    height = y + 16
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="{FONT}">\n'
        f'  <rect width="100%" height="100%" rx="12" fill="{BG}"/>\n'
        + "".join(f"  {line}\n" for line in body)
        + "</svg>\n"
    )


def main():
    parser = argparse.ArgumentParser(description="render assets/readme.svg")
    parser.add_argument("--offline", action="store_true", help="use data/sample_user.json instead of the api")
    args = parser.parse_args()

    profile = load_profile()
    if args.offline:
        user = json.loads(SAMPLE.read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is not set (use --offline to render sample data)")
        user = fetch_user(profile["handle"], token)
    profile["stats"] = contribution_stats(user)
    profile["languages"] = top_languages(user["repositories"]["nodes"])
    profile["updated"] = datetime.datetime.now(datetime.UTC).date().isoformat()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(profile))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
