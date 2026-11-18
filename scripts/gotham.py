"""Build the live Gotham pieces of the profile README.

  assets/gotham-skyline.svg  your last year of contributions as a Gotham skyline:
                             one building per week, one lit window per contribution,
                             the Bat-Signal shining from your busiest week.
  assets/batcomputer.svg     an animated Batcomputer boot terminal with live stats.

Uses only public data and the standard library. Runs daily from
.github/workflows/gotham.yml; run locally with:  python3 scripts/gotham.py
"""
import json
import math
import os
import random
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = os.environ.get("GOTHAM_USER", "jonathanvineet")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

YELLOW = "#FFE81F"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"


def fetch(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "gotham-readme"})
    if accept:
        req.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def contributions():
    """{date: count} for the last year, from the public contribution calendar."""
    html = fetch(f"https://github.com/users/{USER}/contributions")
    dates = dict(re.findall(r'data-date="(\d{4}-\d\d-\d\d)" id="([^"]+)"', html))
    dates = {v: k for k, v in dates.items()}  # id -> date
    days = {}
    for for_id, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        if for_id in dates:
            m = re.match(r"(\d+) contribution", text)
            days[date.fromisoformat(dates[for_id])] = int(m.group(1)) if m else 0
    if not days:
        raise SystemExit("could not parse the contribution calendar")
    return dict(sorted(days.items()))


def latest_repo():
    try:
        repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=10"))
        for r in repos:
            if not r["fork"] and r["name"] != USER:
                return r["name"], r["pushed_at"][:10]
    except Exception:
        pass
    return None, None


def streak(days):
    d = max(days)
    if days.get(d, 0) == 0:  # today not started yet
        d -= timedelta(days=1)
    n = 0
    while days.get(d, 0) > 0:
        n += 1
        d -= timedelta(days=1)
    return n


def weeks_of(days):
    weeks, cur = [], []
    for d, c in days.items():
        if d.weekday() == 6 and cur:  # calendar weeks start on Sunday
            weeks.append(cur)
            cur = []
        cur.append((d, c))
    if cur:
        weeks.append(cur)
    return weeks


# A generic bat silhouette: the right half is drawn, the left half is its mirror.
# Centered on (0, 0), about 120 x 56.
_HALF = [
    ("L", (2.6, -8)), ("L", (5.2, -21)), ("L", (7.4, -6)),
    ("C", (15, -12), (27, -22), (40, -22)), ("C", (48, -22), (55, -17), (60, -9)),
    ("C", (54, -9), (50.5, -5), (49, 5)), ("C", (44.5, -1), (38.5, 0), (36, 11)),
    ("C", (31, 5), (25, 7), (23, 17)), ("C", (17, 15), (8.5, 19), (0, 33)),
]


def _bat_path():
    f = lambda p: f"{p[0]:g} {p[1]:g}"
    m = lambda p: (-p[0], p[1])
    start, d, cur, segs = (0, -7), ["M0 -7"], (0, -7), []
    for seg in _HALF:
        d.append(seg[0] + " " + " ".join(f(p) for p in seg[1:]))
        segs.append((cur, seg))
        cur = seg[-1]
    for begin, seg in reversed(segs):
        if seg[0] == "L":
            d.append("L " + f(m(begin)))
        else:
            d.append("C " + " ".join(f(m(p)) for p in (seg[2], seg[1], begin)))
    return " ".join(d) + " Z"


BAT = _bat_path()


def _tangents(px, py, cx, cy, a, b):
    """Points where lines from (px, py) touch the ellipse centred on (cx, cy)."""
    ux, uy = (px - cx) / a, (py - cy) / b
    d = math.hypot(ux, uy)
    t0, al = math.atan2(uy, ux), math.acos(min(1, 1 / d))
    return [(cx + a * math.cos(t0 + s * al), cy + b * math.sin(t0 + s * al)) for s in (1, -1)]


def skyline(days, total, best_day, cur_streak):
    weeks = weeks_of(days)
    W, H, ground = 960, 440, 380
    bw, gap = 14, 3
    x0 = (W - len(weeks) * (bw + gap) + gap) / 2
    sums = [sum(c for _, c in w) for w in weeks]
    peak = max(sums) or 1
    busiest = sums.index(peak)
    rnd = random.Random(USER)

    out = []
    # buildings
    tops = []
    for i, (w, s) in enumerate(zip(weeks, sums)):
        x = x0 + i * (bw + gap)
        h = 18 + 165 * math.sqrt(s / peak)
        h += rnd.uniform(-4, 4) if s else 0
        y = ground - h
        tops.append((x, y))
        delay = 0.2 + i * 0.025
        out.append(
            f'<rect x="{x:.1f}" y="{ground}" width="{bw}" height="0" fill="url(#bld)">'
            f'<animate attributeName="y" from="{ground}" to="{y:.1f}" begin="{delay:.2f}s" dur="0.9s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.3 1"/>'
            f'<animate attributeName="height" from="0" to="{h:.1f}" begin="{delay:.2f}s" dur="0.9s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.3 1"/>'
            f'<title>Week of {w[0][0]:%b %d}: {s} contributions</title></rect>'
        )
        # windows: one lit window per contribution
        slots = [(cx, ry) for ry in range(int(y) + 6, ground - 6, 7) for cx in (x + 3, x + 8)]
        lit = set(rnd.sample(range(len(slots)), min(s, len(slots))))
        win = []
        for k, (cx, ry) in enumerate(slots):
            if k in lit:
                fl = ""
                if rnd.random() < 0.08:
                    b = rnd.uniform(3, 12)
                    fl = (f'<animate attributeName="opacity" values="1;0.15;1;1" keyTimes="0;0.05;0.1;1" '
                          f'dur="{rnd.uniform(5, 11):.1f}s" begin="{b:.1f}s" repeatCount="indefinite"/>')
                win.append(f'<rect x="{cx:.1f}" y="{ry}" width="3" height="3.5" fill="{YELLOW}" opacity="0.92">{fl}</rect>')
            else:
                win.append(f'<rect x="{cx:.1f}" y="{ry}" width="3" height="3.5" fill="#1d1d22"/>')
        out.append(f'<g opacity="0">{"".join(win)}'
                   f'<animate attributeName="opacity" from="0" to="1" begin="{delay + 0.9:.2f}s" dur="0.4s" fill="freeze"/></g>')
    buildings = "\n".join(out)

    # antennas with red beacons on the five tallest
    ant = []
    for i in sorted(range(len(sums)), key=lambda i: -sums[i])[:5]:
        x, y = tops[i]
        cx = x + bw / 2
        ant.append(f'<line x1="{cx}" y1="{y:.1f}" x2="{cx}" y2="{y - 14:.1f}" stroke="#2c2c33" stroke-width="1.5"/>'
                   f'<circle cx="{cx}" cy="{y - 15:.1f}" r="1.8" fill="#ff3b3b">'
                   f'<animate attributeName="opacity" values="1;0.1;1" dur="{rnd.uniform(1.6, 2.6):.1f}s" repeatCount="indefinite"/></circle>')
    antennas = "".join(ant)

    # the Bat-Signal: a searchlight on the busiest week's roof, the emblem on the clouds
    sx, sy = tops[busiest][0] + bw / 2, tops[busiest][1] - 5
    tc = sx + 130 if sx < W / 2 else sx - 130
    tc = min(max(tc, 430), 700)
    ty, a, b, amp, n = 100, 70, 34, 36, 24
    xs = [tc + amp * math.sin(2 * math.pi * k / n) for k in range(n + 1)]
    ys = [ty + 6 * math.sin(4 * math.pi * k / n) for k in range(n + 1)]
    beam_vals = []
    for x, y in zip(xs, ys):
        (p1, p2) = _tangents(sx, sy, x, y, a, b)
        beam_vals.append(f"{sx:.1f},{sy:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    anim = 'dur="16s" repeatCount="indefinite"'
    cxs = ";".join(f"{x:.1f}" for x in xs)
    cys = ";".join(f"{y:.1f}" for y in ys)
    moves = ";".join(f"{x:.1f} {y:.1f}" for x, y in zip(xs, ys))
    signal = f'''
<g opacity="0">
  <animate attributeName="opacity" from="0" to="1" begin="2.4s" dur="1.4s" fill="freeze"/>
  <polygon points="{beam_vals[0]}" fill="url(#beam)" filter="url(#edge)"><animate attributeName="points" values="{";".join(beam_vals)}" {anim}/></polygon>
  <ellipse rx="{a * 1.9}" ry="{b * 1.9}" fill="#fff3a0" opacity="0.10" filter="url(#soft)"><animate attributeName="cx" values="{cxs}" {anim}/><animate attributeName="cy" values="{cys}" {anim}/></ellipse>
  <ellipse rx="{a}" ry="{b}" fill="url(#disc)" filter="url(#edge)"><animate attributeName="cx" values="{cxs}" {anim}/><animate attributeName="cy" values="{cys}" {anim}/></ellipse>
  <g><animateTransform attributeName="transform" type="translate" values="{moves}" {anim}/>
    <path d="{BAT}" transform="scale(0.98 0.96)" fill="#0d0c08" opacity="0.88"/>
  </g>
</g>
<g>
  <rect x="{sx - 6:.1f}" y="{sy + 1:.1f}" width="12" height="4" rx="1" fill="#24242a"/>
  <circle cx="{sx:.1f}" cy="{sy:.1f}" r="4.5" fill="#2f2f36"/>
  <circle cx="{sx:.1f}" cy="{sy:.1f}" r="3" fill="#fff8c8" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="2.2s" dur="0.3s" fill="freeze"/></circle>
</g>'''

    # stars
    stars = "".join(
        f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 170):.0f}" r="{rnd.choice([0.6, 0.8, 1.1])}" fill="#fff" opacity="{rnd.uniform(0.2, 0.7):.2f}"/>'
        for _ in range(70))

    # month labels
    months, last = [], None
    for i, w in enumerate(weeks):
        m = w[0][0].month
        if m != last and w[0][0].day <= 7:
            months.append(f'<text x="{x0 + i * (bw + gap):.1f}" y="{ground + 18}" class="m">{w[0][0]:%b}</text>')
        last = m

    bd, bc = best_day
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{USER}'s contributions as a Gotham skyline: {total} contributions in the last year">
<title>Gotham, built from {total} contributions</title>
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050507"/><stop offset="0.7" stop-color="#121218"/><stop offset="1" stop-color="#1c1a14"/></linearGradient>
  <linearGradient id="bld" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16161b"/><stop offset="1" stop-color="#0b0b0e"/></linearGradient>
  <linearGradient id="beam" gradientUnits="userSpaceOnUse" x1="{sx:.1f}" y1="{sy:.1f}" x2="{tc:.1f}" y2="{ty}"><stop offset="0" stop-color="#fff6c0" stop-opacity="0.75"/><stop offset="0.6" stop-color="#fff3a0" stop-opacity="0.22"/><stop offset="1" stop-color="#fff3a0" stop-opacity="0.12"/></linearGradient>
  <radialGradient id="disc"><stop offset="0" stop-color="#fffbe0"/><stop offset="0.8" stop-color="#fbe98a"/><stop offset="1" stop-color="#e9cf45"/></radialGradient>
  <filter id="edge" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.6"/></filter>
  <radialGradient id="moon"><stop offset="0" stop-color="#f4f1e6"/><stop offset="1" stop-color="#cfcab8"/></radialGradient>
  <filter id="soft"><feGaussianBlur stdDeviation="14"/></filter>
</defs>
<style>
  .m{{font:500 10px {MONO};fill:#5a5a62}}
  .h{{font:700 11px {MONO};fill:{YELLOW};letter-spacing:3px}}
  .s{{font:500 11px {MONO};fill:#9a9aa3}}
  .n{{font:700 11px {MONO};fill:#ececec}}
</style>
<rect width="{W}" height="{H}" rx="10" fill="url(#sky)"/>
{stars}
<circle cx="{W - 90}" cy="58" r="26" fill="url(#moon)" opacity="0.9"/>
<circle cx="{W - 90}" cy="58" r="60" fill="#f4f1e6" opacity="0.06" filter="url(#soft)"/>
<rect width="{W}" height="{H}" rx="10" fill="#e8eaff" opacity="0">
  <animate attributeName="opacity" values="0;0;0.16;0;0.1;0" keyTimes="0;0.9;0.91;0.925;0.94;1" dur="17s" begin="4s" repeatCount="indefinite"/>
</rect>
{signal}
{buildings}
{antennas}
<rect x="0" y="{ground}" width="{W}" height="{H - ground}" fill="#08080a"/>
<line x1="{x0 - 10:.1f}" y1="{ground + 0.5}" x2="{W - x0 + 10:.1f}" y2="{ground + 0.5}" stroke="#2a2a2f"/>
{"".join(months)}
<text x="24" y="30" class="h">GOTHAM // PATROL LOG</text>
<text x="24" y="48" class="s">one building per week · one lit window per contribution</text>
<text x="{x0:.1f}" y="{H - 16}" class="s"><tspan class="n">{total:,}</tspan> contributions this year   ·   busiest night <tspan class="n">{bd:%b %d}</tspan> ({bc})   ·   patrol streak <tspan class="n">{cur_streak}</tspan> days</text>
<text x="{W - x0:.1f}" y="{H - 16}" text-anchor="end" class="s">updated {datetime.now(timezone.utc):%Y-%m-%d}</text>
</svg>
'''


def terminal(total, cur_streak, repo, pushed):
    W = 760
    lines = [
        ("cmd", "boot batcomputer --operator jonathanvineet"),
        ("ok", "uplink to the Batcave .................. secure"),
        ("kv", ("IDENTITY", "Jonathan Vineet")),
        ("kv", ("ALIAS", "The Dark Knight of Code")),
        ("kv", ("LOCATION", "The Batcave")),
        ("kv", ("STATUS", "Defending Gotham's Code")),
        ("kv", ("PATROL LOG", f"{total:,} contributions this year · {cur_streak}-day streak")),
    ]
    if repo:
        lines.append(("kv", ("LAST SEEN", f"pushing to {repo} on {pushed}")))
    lines.append(("cmd", "watch --city gotham"))

    H = 64 + len(lines) * 24 + 30
    body, t = [], 0.6
    for i, (kind, val) in enumerate(lines):
        y = 70 + i * 24
        if kind == "cmd":
            text = f'<tspan fill="{YELLOW}">batcave</tspan><tspan fill="#666">:~$</tspan> <tspan fill="#eee">{escape(val)}</tspan>'
            n = len(val) + 11
        elif kind == "ok":
            text = f'<tspan fill="#5fd38d">[ ok ]</tspan> <tspan fill="#9a9aa3">{escape(val)}</tspan>'
            n = len(val) + 7
        else:
            k, v = val
            text = f'<tspan fill="#6b6b74">  {k.ljust(11, " ")}</tspan><tspan fill="#ececec">{escape(v)}</tspan>'
            n = len(v) + 13
        width = n * 8.2 + 20
        dur = max(0.25, n * 0.022) if kind == "cmd" else 0.18
        body.append(
            f'<clipPath id="c{i}"><rect x="24" y="{y - 15}" height="22" width="0">'
            f'<animate attributeName="width" from="0" to="{width:.0f}" begin="{t:.2f}s" dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>'
            f'<text x="28" y="{y}" class="t" clip-path="url(#c{i})" xml:space="preserve">{text}</text>')
        t += dur + (0.35 if kind == "cmd" else 0.12)
    cy = 70 + (len(lines) - 1) * 24
    cx = 28 + (len(lines[-1][1]) + 12) * 8.2
    cursor = (f'<rect x="{cx:.0f}" y="{cy - 12}" width="8" height="15" fill="{YELLOW}" opacity="0">'
              f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.01;0.5;0.51;1" dur="1s" begin="{t:.2f}s" repeatCount="indefinite"/></rect>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Batcomputer: Jonathan Vineet, The Dark Knight of Code. {total} contributions this year.">
<style>.t{{font:500 13.5px {MONO}}} .bar{{font:700 10.5px {MONO};fill:{YELLOW};letter-spacing:3px}}</style>
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" opacity="0.025"/></pattern></defs>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="#0a0a0c" stroke="#2a2a2f"/>
<path d="M0.5 36 V10.5 a10 10 0 0 1 10 -10 H{W - 10.5} a10 10 0 0 1 10 10 V36 Z" fill="#121216"/>
<line x1="0" y1="36" x2="{W}" y2="36" stroke="#2a2a2f"/>
<path d="{BAT}" transform="translate(34 18) scale(0.22)" fill="{YELLOW}"/>
<text x="{W / 2}" y="22" text-anchor="middle" class="bar">BATCOMPUTER · WAYNE ENTERPRISES R&amp;D</text>
<circle cx="{W - 24}" cy="18" r="4" fill="#5fd38d"><animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/></circle>
{"".join(body)}
{cursor}
<rect x="0" y="37" width="{W}" height="{H - 38}" fill="url(#scan)"/>
</svg>
'''


def footer():
    W, H = 960, 190
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="I am vengeance">
<defs>
  <linearGradient id="fl" x1="1" x2="0"><stop offset="0" stop-color="{YELLOW}"/><stop offset="1" stop-color="{YELLOW}" stop-opacity="0"/></linearGradient>
  <linearGradient id="fr" x1="0" x2="1"><stop offset="0" stop-color="{YELLOW}"/><stop offset="1" stop-color="{YELLOW}" stop-opacity="0"/></linearGradient>
  <radialGradient id="glow"><stop offset="0" stop-color="{YELLOW}" stop-opacity="0.22"/><stop offset="1" stop-color="{YELLOW}" stop-opacity="0"/></radialGradient>
</defs>
<style>
  .big{{font:800 40px 'Arial Black','Helvetica Neue',Helvetica,Arial,sans-serif;fill:#f2f2f2;letter-spacing:16px}}
  .sub{{font:500 11px {MONO};fill:#76767e;letter-spacing:5px}}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="#0a0a0c" stroke="#2a2a2f"/>
<ellipse cx="{W / 2}" cy="48" rx="120" ry="40" fill="url(#glow)"/>
<g transform="translate({W / 2} 46) scale(0.42)"><path d="{BAT}" fill="{YELLOW}"/></g>
<rect x="{W / 2 - 50}" y="45" height="1.5" width="0" fill="url(#fl)">
  <animate attributeName="x" from="{W / 2 - 50}" to="{W / 2 - 380}" begin="0.3s" dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.3 1"/>
  <animate attributeName="width" from="0" to="330" begin="0.3s" dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.3 1"/></rect>
<rect x="{W / 2 + 50}" y="45" height="1.5" width="0" fill="url(#fr)">
  <animate attributeName="width" from="0" to="330" begin="0.3s" dur="1.2s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.3 1"/></rect>
<text x="{W / 2 + 8}" y="118" text-anchor="middle" class="big" opacity="0">I AM VENGEANCE
  <animate attributeName="opacity" from="0" to="1" begin="0.9s" dur="1.4s" fill="freeze"/></text>
<text x="{W / 2 + 2}" y="156" text-anchor="middle" class="sub" opacity="0">SIGNING OFF FROM THE BATCAVE
  <animate attributeName="opacity" from="0" to="1" begin="1.8s" dur="1.2s" fill="freeze"/></text>
</svg>
'''


def main():
    days = contributions()
    total = sum(days.values())
    best = max(days.items(), key=lambda kv: kv[1])
    s = streak(days)
    repo, pushed = latest_repo()
    (ASSETS / "gotham-skyline.svg").write_text(skyline(days, total, best, s))
    (ASSETS / "batcomputer.svg").write_text(terminal(total, s, repo, pushed))
    (ASSETS / "footer.svg").write_text(footer())
    print(f"{total} contributions, streak {s}, busiest {best}, last repo {repo}")


if __name__ == "__main__":
    main()
