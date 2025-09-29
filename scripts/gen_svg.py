#!/usr/bin/env python3
import sys

WIDTH = 800
BG = "#0d1117"
FG = "#e6edf3"
MUTED = "#7d8590"


def render(profile):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="120" viewBox="0 0 {WIDTH} 120">
  <rect width="100%" height="100%" rx="12" fill="{BG}"/>
  <text x="32" y="56" fill="{FG}" font-family="ui-monospace, monospace" font-size="24">{profile["name"]}</text>
  <text x="32" y="84" fill="{MUTED}" font-family="ui-monospace, monospace" font-size="14">{profile["location"]} · {profile["tagline"]}</text>
</svg>
"""


if __name__ == "__main__":
    sys.stdout.write(render({"name": "Aditya Verma", "location": "San Francisco", "tagline": "building ai agents & devtools"}))
