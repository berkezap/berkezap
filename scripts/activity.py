"""Draws the daily activity card (light + dark SVG) from the public contribution calendar.

Usage: GITHUB_TOKEN=... GH_LOGIN=berkezap python3 scripts/activity.py <out_dir>
Private contributions are counted too, as long as the profile shares them.
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""

THEMES = {
    "dark": {"fg": "#e6edf3", "muted": "#8b949e", "empty": "#21262d",
             "levels": ["#0e4429", "#006d32", "#26a641", "#39d353"]},
    "light": {"fg": "#1f2328", "muted": "#656d76", "empty": "#ebedf0",
              "levels": ["#9be9a8", "#40c463", "#30a14e", "#216e39"]},
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], sorted(days)


def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if counts and counts[i] == 0:  # today not started yet, streak still alive
        i -= 1
    current = 0
    while i >= 0 and counts[i]:
        current += 1
        i -= 1
    return current, longest


def card(theme, total, days, now):
    t = THEMES[theme]
    last30 = days[-30:]
    week = sum(c for _, c in days[-7:])
    current, longest = streaks(days)
    stats = [
        (f"{total:,}", "last 12 months"),
        (f"{week}", "last 7 days"),
        (f"{current} {'day' if current == 1 else 'days'}", "current streak"),
        (f"{longest} days", "longest streak"),
    ]
    W, H = 880, 212
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'role="img" aria-label="{total} contributions in the last year, {current} day streak">']
    for i, (value, label) in enumerate(stats):
        x = i * 220
        out.append(f'<text x="{x}" y="34" font-family="{SANS}" font-size="30" font-weight="600" fill="{t["fg"]}">{value}</text>')
        out.append(f'<text x="{x + 1}" y="56" font-family="{MONO}" font-size="12" fill="{t["muted"]}">{label}</text>')

    top, base = 84, 184
    peak = max((c for _, c in last30), default=0) or 1
    slot = W / len(last30)
    bw = slot - 6
    for i, (d, c) in enumerate(last30):
        x = i * slot + 3
        if c == 0:
            out.append(f'<rect x="{x:.1f}" y="{base - 3}" width="{bw:.1f}" height="3" rx="1.5" fill="{t["empty"]}"/>')
            continue
        h = max(6, (base - top) * c / peak)
        level = min(3, int(4 * c / (peak + 1)))
        out.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{t["levels"][level]}">'
                   f'<title>{d:%b %-d}: {c}</title></rect>')

    first = last30[0][0] if last30 else now.date()
    out.append(f'<text x="3" y="206" font-family="{MONO}" font-size="12" fill="{t["muted"]}">{first:%b %-d}</text>')
    out.append(f'<text x="{W / 2}" y="206" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
               f'daily contributions, last 30 days</text>')
    out.append(f'<text x="{W - 3}" y="206" text-anchor="end" font-family="{MONO}" font-size="12" fill="{t["muted"]}">'
               f'updated {now:%b %-d, %H:%M} UTC</text>')
    out.append("</svg>\n")
    return "\n".join(out)


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    out_dir.mkdir(parents=True, exist_ok=True)
    total, days = fetch(os.environ.get("GH_LOGIN", "berkezap"), os.environ["GITHUB_TOKEN"])
    now = datetime.now(timezone.utc)
    for theme in THEMES:
        (out_dir / f"activity-{theme}.svg").write_text(card(theme, total, days, now), encoding="utf-8")
    current, longest = streaks(days)
    print(f"total={total} last7={sum(c for _, c in days[-7:])} streak={current} longest={longest}")


if __name__ == "__main__":
    main()
