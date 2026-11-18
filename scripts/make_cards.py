"""Generate the pinned-project cards in assets/cards/. Edit PROJECTS and run:
    python3 scripts/make_cards.py
"""
from pathlib import Path
from textwrap import wrap
from html import escape

OUT = Path(__file__).resolve().parent.parent / "assets" / "cards"

LANG_COLORS = {
    "Python": "#3572A5", "Swift": "#F05138", "TypeScript": "#3178C6",
    "C": "#555555", "C++": "#F34B7D", "JavaScript": "#F1E05A", "Rust": "#DEA584",
}

PROJECTS = [
    ("batsy", "Python", "Voice assistant for Fedora powered by Claude. Runs commands, sees the screen, programs Arduinos and writes new skills for itself.", ["voice", "agents", "linux"]),
    ("helm", "Swift", "macOS screensaver that shows Apple Notes and Reminders on frosted glass over a Ken Burns slideshow. Ships via Homebrew.", ["macos", "screensaver", "brew"]),
    ("scrapee", "Python", "Turn any website into an MCP server. Crawls a site, indexes it with FTS5 and embeddings, and serves it to Claude, Copilot or Cursor.", ["mcp", "search", "llm"]),
    ("semmal", "TypeScript", "Robot-as-a-service marketplace where every robot is its own agent: it hires AI specialists, pays them and answers for the result.", ["robotics", "agents", "web3"]),
    ("robotic-arm", "C", "6-DOF arm firmware with a live 3D digital twin, a hardware-faithful simulator and camera-guided YOLO pick and place.", ["esp32", "yolo", "3d"]),
    ("cairn", "TypeScript", "Autonomous drone patrol system on Hedera: drones as on-chain agents, boundary zones and verified missions.", ["drones", "hedera", "ai"]),
]

W, H = 420, 160
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
YELLOW = "#FFE81F"


def card(i, name, lang, desc, tags):
    lines = wrap(desc, 56)[:3]
    desc_svg = "".join(
        f'<tspan x="22" dy="{0 if n == 0 else 17}">{escape(l)}</tspan>' for n, l in enumerate(lines)
    )
    x = 22
    tag_svg = ""
    for t in tags:
        tw = 7 * len(t) + 16
        tag_svg += (
            f'<rect x="{x}" y="128" width="{tw}" height="18" rx="9" fill="none" stroke="#3a3a3a"/>'
            f'<text x="{x + tw / 2}" y="141" text-anchor="middle" class="tag">{escape(t)}</text>'
        )
        x += tw + 6
    color = LANG_COLORS.get(lang, "#888")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(name)}: {escape(desc)}">
<style>
.label{{font:600 10px {MONO};fill:{YELLOW};letter-spacing:2px}}
.title{{font:700 19px {FONT};fill:#F5F5F5}}
.desc{{font:400 12.5px {FONT};fill:#A8A8A8}}
.lang{{font:500 11.5px {FONT};fill:#C8C8C8}}
.tag{{font:500 10.5px {MONO};fill:#9A9A9A}}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="8" fill="#0B0B0B" stroke="#2A2A2A"/>
<rect x="0.5" y="0.5" width="4" height="{H - 1}" rx="2" fill="{YELLOW}"/>
<text x="22" y="26" class="label">CASE FILE {i:02d}</text>
<circle cx="{W - 30 - 6.1 * len(lang)}" cy="22" r="5" fill="{color}"/>
<text x="{W - 20}" y="26" text-anchor="end" class="lang">{escape(lang)}</text>
<text x="22" y="52" class="title">{escape(name)}</text>
<text y="74" class="desc">{desc_svg}</text>
{tag_svg}
</svg>
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (name, lang, desc, tags) in enumerate(PROJECTS, 1):
        (OUT / f"{name}.svg").write_text(card(i, name, lang, desc, tags))
        print("wrote", name)


if __name__ == "__main__":
    main()
