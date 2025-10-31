#!/usr/bin/env python3
import json
import os
import tomllib
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "readme.svg"
WIDTH = 800
BG = "#0d1117"
FG = "#e6edf3"
MUTED = "#7d8590"
BORDER = "#30363d"
FONT = "ui-monospace, SFMono-Regular, Menlo, monospace"
GRAPHQL = "https://api.github.com/graphql"


def graphql(query, variables, token):
    req = urllib.request.Request(
        GRAPHQL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "readme-svg"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0]["message"])
    return payload["data"]


def load_profile(path=ROOT / "profile.toml"):
    with open(path, "rb") as f:
        return tomllib.load(f)


def text(x, y, s, size=14, fill=FG):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" font-size="{size}">{escape(s)}</text>'


def pills(items, x, y):
    out = []
    for item in items:
        w = len(item) * 8 + 24
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="13" fill="none" stroke="{BORDER}"/>')
        out.append(text(x + 12, y + 18, item, 13))
        x += w + 8
    return out


def render(profile):
    body = [
        text(32, 56, profile["name"], 24),
        text(32, 84, f'{profile["location"]} · {profile["tagline"]}', 14, MUTED),
        text(32, 128, "stack", 12, MUTED),
        *pills(profile["stack"], 32, 140),
        text(32, 210, "now building", 12, MUTED),
    ]
    y = 238
    for item in profile.get("now", []):
        body.append(text(32, y, f'▸ {item["name"]}', 14))
        body.append(text(220, y, item["desc"], 13, MUTED))
        y += 24
    height = y + 16
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">\n'
        f'  <rect width="100%" height="100%" rx="12" fill="{BG}"/>\n'
        + "".join(f"  {line}\n" for line in body)
        + "</svg>\n"
    )


def main():
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(load_profile()))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
