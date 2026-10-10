#!/usr/bin/env python3
"""Build the animated SVG assets used by the GitHub profile README.

Usage:  python3 scripts/build_profile_assets.py

Inputs live in scripts/profile-src/ (portrait photo + simple-icons SVGs).
Every asset is written to assets/ in a light and a dark variant.
SVGs are rendered by GitHub as <img>, so everything is self-contained:
no JavaScript, no external fonts, the photo is embedded as base64.
All animations respect prefers-reduced-motion and fall back to a finished state.
"""

import base64
import html
import io
import math
import re
from pathlib import Path

from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "profile-src"
OUT = ROOT / "assets"

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    "dark": dict(
        bg="#0b0f17", card="#0f1521", card2="#151c2a", border="#232d40", text="#e8eef6",
        muted="#93a1b5", subtle="#5e6b80", a1="#8b6cff", a2="#22d3ee", a3="#ff5fa2",
        grid="#ffffff", grid_op="0.035", glow_op="0.55",
        kw="#c792ea", str="#a5e075", prop="#82aaff", punc="#8b98ab", com="#5c6b80", typ="#ffcb6b", num="#f78c6c",
    ),
    "light": dict(
        bg="#ffffff", card="#ffffff", card2="#f6f8fb", border="#e2e8f0", text="#0f172a",
        muted="#526075", subtle="#8a96a8", a1="#5b3df5", a2="#0891b2", a3="#db2777",
        grid="#0f172a", grid_op="0.05", glow_op="0.22",
        kw="#a626a4", str="#3f8f3a", prop="#2f6fe0", punc="#6b7686", com="#9aa3b2", typ="#b7790f", num="#c2410c",
    ),
}

ICON_COLORS = {
    # name: (dark-theme colour, light-theme colour)
    "react": ("#61dafb", "#0a7ea4"), "typescript": ("#3d8bfd", "#3178c6"), "javascript": ("#f7df1e", "#d4b106"),
    "nextdotjs": ("#ffffff", "#000000"), "tailwindcss": ("#38bdf8", "#0891b2"), "html5": ("#f06529", "#e34f26"),
    "css3": ("#3d9be9", "#1572b6"), "cplusplus": ("#5e97d0", "#00599c"), "git": ("#f05032", "#e44c30"),
    "figma": ("#ff7262", "#f24e1e"), "firebase": ("#ffca28", "#f59e0b"), "prisma": ("#c3cfdf", "#2d3748"),
}

REDUCED = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


def icon_path(name):
    svg = (SRC / "icons" / f"{name}.svg").read_text()
    return re.search(r' d="([^"]+)"', svg).group(1)


def esc(s):
    return html.escape(s, quote=True)


def svg_doc(w, h, body, css, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title><style>{css}{REDUCED}</style>{body}</svg>"
    )


def write(name, content):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(content)
    print(f"  {name:28s} {len(content) / 1024:7.1f} KB")


def pct(t, total):
    return f"{max(0.0, min(100.0, t / total * 100)):.3f}%"


def discrete(events, total):
    """events: list of (time, value) -> SMIL keyTimes/values for calcMode=discrete."""
    events = sorted(events, key=lambda e: e[0])
    if events[0][0] > 0:
        events.insert(0, (0, events[0][1]))
    kt = ";".join(f"{min(t / total, 1):.4f}" for t, _ in events)
    vals = ";".join(str(v) for _, v in events)
    return kt, vals


# ---------------------------------------------------------------------------
# Portrait: crop the photo and build a dot-matrix mosaic of it
# ---------------------------------------------------------------------------

def portrait_data():
    im = Image.open(SRC / "avatar.jpg").convert("RGB")
    # square crop around face + shoulders (tuned for the current photo)
    w, h = im.size
    s = int(min(w, h) * 0.66)
    cx, cy = int(w * 0.665), int(h * 0.425)
    box = (max(0, cx - s // 2), max(0, cy - s // 2), min(w, cx + s // 2), min(h, cy + s // 2))
    crop = im.crop(box)
    crop = ImageEnhance.Contrast(crop).enhance(1.06)
    photo = crop.resize((420, 420), Image.LANCZOS)
    buf = io.BytesIO()
    photo.save(buf, "JPEG", quality=84, optimize=True, progressive=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    grid = 42
    small = ImageEnhance.Color(crop).enhance(1.35).resize((grid, grid), Image.BOX)
    return b64, small, grid


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

ROLES = ["Software Engineer", "React & TypeScript developer", "UX-minded interface builder", "C++ problem solver"]


def header(t, b64, small, grid):
    W, H = 1200, 460
    cx, cy, R = 925, 230, 148  # portrait centre / radius
    T = 14.0  # portrait loop length

    css = f"""
    .name{{font:800 82px {SANS};letter-spacing:-2.5px}}
    .mono{{font:500 18px {MONO}}}
    .role{{font:600 28px {MONO};fill:{t['text']}}}
    .tag{{font:400 22px {SANS};fill:{t['muted']}}}
    .chip{{font:600 15px {SANS};fill:{t['text']}}}
    .fade{{}}
    @keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
    .blob{{animation:drift 18s ease-in-out infinite alternate}}
    .b2{{animation-duration:23s;animation-delay:-6s}} .b3{{animation-duration:27s;animation-delay:-12s}}
    @keyframes drift{{0%{{transform:translate(0,0)}}50%{{transform:translate(60px,-30px)}}100%{{transform:translate(-40px,40px)}}}}
    .spin{{transform-box:fill-box;transform-origin:center;animation:spin 14s linear infinite}}
    .spinr{{animation-direction:reverse;animation-duration:30s}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    .orbit{{transform-origin:{cx}px {cy}px;animation:spin 40s linear infinite}}
    .upright{{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite reverse}}
    .blink{{animation:blink 1s steps(1) infinite}}
    @keyframes blink{{50%{{opacity:0}}}}
    .d{{transform-box:fill-box;transform-origin:center;animation:dot {T}s cubic-bezier(.3,1.5,.5,1) infinite both}}
    @keyframes dot{{0%{{transform:scale(0);opacity:0}}9%{{transform:scale(1);opacity:1}}84%{{transform:scale(1);opacity:1}}94%,100%{{transform:scale(0);opacity:0}}}}
    .photo{{animation:photo {T}s ease-in-out -6s infinite both}}
    @keyframes photo{{0%,{pct(2.6,T)}{{opacity:0}}{pct(4.2,T)},{pct(10.8,T)}{{opacity:1}}{pct(11.8,T)},100%{{opacity:0}}}}
    .scan{{animation:scan {T}s linear -6s infinite both}}
    @keyframes scan{{0%,{pct(2.5,T)}{{transform:translateY(0);opacity:0}}{pct(2.6,T)}{{opacity:1}}{pct(4.3,T)}{{transform:translateY({2*R}px);opacity:1}}{pct(4.4,T)},100%{{transform:translateY({2*R}px);opacity:0}}}}
    .pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s ease-out infinite}}
    @keyframes pulse{{0%{{transform:scale(.6);opacity:.9}}100%{{transform:scale(2.4);opacity:0}}}}
    .spark{{animation:spark 4s ease-in-out infinite}}
    @keyframes spark{{0%,100%{{opacity:.15}}50%{{opacity:.9}}}}
    """
    for ring in range(15):
        css += f".r{ring}{{animation-delay:{ring * 0.07 - 6:.2f}s}}"

    defs = f"""
    <defs>
      <linearGradient id="ng" x1="0" y1="0" x2="520" y2="0" gradientUnits="userSpaceOnUse" spreadMethod="repeat">
        <stop offset="0" stop-color="{t['a1']}"/><stop offset=".33" stop-color="{t['a2']}"/>
        <stop offset=".66" stop-color="{t['a3']}"/><stop offset="1" stop-color="{t['a1']}"/>
        <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="520 0" dur="8s" repeatCount="indefinite"/>
      </linearGradient>
      <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="{t['a1']}"/><stop offset=".5" stop-color="{t['a2']}"/><stop offset="1" stop-color="{t['a3']}"/>
      </linearGradient>
      <linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{t['a2']}" stop-opacity="0"/><stop offset="1" stop-color="{t['a2']}" stop-opacity=".9"/>
      </linearGradient>
      <radialGradient id="vig" cx=".5" cy=".5" r=".5">
        <stop offset=".72" stop-color="{t['bg']}" stop-opacity="0"/><stop offset="1" stop-color="{t['bg']}" stop-opacity=".55"/>
      </radialGradient>
      <radialGradient id="gridFade" cx=".5" cy=".45" r=".7">
        <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
      </radialGradient>
      <mask id="gm"><rect width="{W}" height="{H}" fill="url(#gridFade)"/></mask>
      <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M40 0H0V40" fill="none" stroke="{t['grid']}" stroke-opacity="{t['grid_op']}"/>
      </pattern>
      <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="70"/></filter>
      <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18"/></filter>
      <clipPath id="frame"><rect width="{W}" height="{H}" rx="28"/></clipPath>
      <clipPath id="pc"><circle cx="{cx}" cy="{cy}" r="{R}"/></clipPath>
    </defs>"""

    bg = f"""
    <g clip-path="url(#frame)">
      <rect width="{W}" height="{H}" fill="{t['bg']}"/>
      <g opacity="{t['glow_op']}" filter="url(#blur)">
        <circle class="blob" cx="260" cy="120" r="170" fill="{t['a1']}"/>
        <circle class="blob b2" cx="980" cy="360" r="190" fill="{t['a2']}"/>
        <circle class="blob b3" cx="620" cy="420" r="150" fill="{t['a3']}"/>
      </g>
      <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#gm)"/>
    </g>
    <rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="28" fill="none" stroke="{t['border']}"/>"""

    sparks = ""
    for i, (x, y) in enumerate([(560, 70), (640, 160), (1140, 70), (720, 390), (1150, 400), (600, 300), (90, 420)]):
        sparks += f'<circle class="spark" style="animation-delay:{-i * 0.7:.1f}s" cx="{x}" cy="{y}" r="2" fill="{t["a2"] if i % 2 else t["a1"]}"/>'

    # --- left column -------------------------------------------------------
    x0 = 72
    left = f"""
    <g class="fade" style="animation-delay:.1s">
      <text class="mono" x="{x0}" y="98"><tspan fill="{t['a2']}">~/palani</tspan><tspan fill="{t['subtle']}"> on </tspan><tspan fill="{t['a1']}">main</tspan><tspan fill="{t['subtle']}"> $ </tspan><tspan fill="{t['text']}">whoami</tspan></text>
    </g>
    <g class="fade" style="animation-delay:.25s">
      <text class="name" x="{x0 - 4}" y="186" fill="url(#ng)">Aathish M</text>
    </g>"""

    # typing roles (SMIL, stepped per character)
    cw = 16.8
    px = x0 + 2 * cw  # after the "> " prompt
    events_cursor = []
    t_now, roles_svg, clips = 0.4, "", ""
    timings = []
    for role in ROLES:
        n = len(role)
        start = t_now
        type_end = start + n * 0.065
        hold_end = type_end + 1.7
        del_end = hold_end + n * 0.028
        timings.append((role, start, type_end, hold_end, del_end))
        t_now = del_end + 0.35
    TT = t_now
    rb = f"-{timings[0][2] + 0.05:.2f}s"
    for i, (role, start, type_end, hold_end, del_end) in enumerate(timings):
        n = len(role)
        ev = [(0, 0)]
        for k in range(1, n + 1):
            ev.append((start + k * 0.065, round(k * cw, 1)))
        for k in range(n - 1, -1, -1):
            ev.append((hold_end + (n - k) * 0.028, round(k * cw, 1)))
        kt, vals = discrete(ev, TT)
        clips += (
            f'<clipPath id="rc{i}"><rect x="{px}" y="214" width="0" height="44">'
            f'<animate attributeName="width" calcMode="discrete" keyTimes="{kt}" values="{vals}" dur="{TT:.2f}s" begin="{rb}" repeatCount="indefinite"/>'
            f"</rect></clipPath>"
        )
        roles_svg += (
            f'<text class="role" x="{px}" y="246" textLength="{n * cw:.1f}" lengthAdjust="spacing" clip-path="url(#rc{i})">{esc(role)}</text>'
        )
        events_cursor += [(e_t, e_v) for e_t, e_v in ev[1:]]
    events_cursor = [(0, 0)] + sorted(events_cursor)
    kt, vals = discrete(events_cursor, TT)
    vals = ";".join(f"{v} 0" for v in vals.split(";"))
    cursor = (
        f'<g><animateTransform attributeName="transform" type="translate" calcMode="discrete" keyTimes="{kt}" values="{vals}" dur="{TT:.2f}s" begin="{rb}" repeatCount="indefinite"/>'
        f'<rect class="blink" x="{px + 2}" y="222" width="13" height="30" rx="2" fill="{t["a2"]}"/></g>'
    )
    left += f"""
    <g class="fade" style="animation-delay:.4s">
      <defs>{clips}</defs>
      <text class="role" x="{x0}" y="246" fill="{t['a1']}" style="fill:{t['a1']}">&gt;</text>
      {roles_svg}{cursor}
    </g>
    <g class="fade" style="animation-delay:.55s">
      <text class="tag" x="{x0}" y="302">Curiosity into code. <tspan fill="{t['text']}" font-weight="600">Ideas into interfaces.</tspan></text>
    </g>"""

    chips = [("Palani, India", t["a3"]), ("CIT alumnus", t["a1"]), ("Google UX certified", t["a2"])]
    cxp = x0
    chip_svg = ""
    for i, (label, col) in enumerate(chips):
        wch = len(label) * 8.3 + 46
        chip_svg += f"""
        <g class="fade" style="animation-delay:{0.7 + i * 0.12:.2f}s">
          <rect x="{cxp}" y="340" width="{wch:.0f}" height="38" rx="19" fill="{t['card2']}" fill-opacity=".75" stroke="{t['border']}"/>
          <circle class="pulse" cx="{cxp + 20}" cy="359" r="4" fill="{col}" style="animation-delay:{i * 0.6}s"/>
          <circle cx="{cxp + 20}" cy="359" r="4" fill="{col}"/>
          <text class="chip" x="{cxp + 34}" y="364">{esc(label)}</text>
        </g>"""
        cxp += wch + 12
    left += chip_svg
    left += f"""
    <g class="fade" style="animation-delay:1.1s">
      <text class="mono" x="{x0}" y="414" style="font-size:14px" fill="{t['subtle']}">// frontend engineering · user experience · problem solving</text>
    </g>"""

    # --- portrait -------------------------------------------------------------
    dots = ""
    cell = 2 * R / grid
    half = grid / 2
    for gy in range(grid):
        for gx in range(grid):
            dx, dy = gx + 0.5 - half, gy + 0.5 - half
            dist = math.hypot(dx, dy)
            if dist > half - 0.35:
                continue
            r_, g_, b_ = small.getpixel((gx, gy))
            lum = (0.299 * r_ + 0.587 * g_ + 0.114 * b_) / 255
            k = lum if t is THEMES["dark"] else 1 - lum
            rad = cell * (0.24 + 0.2 * k)
            ring = min(14, int(dist / half * 15))
            dots += (
                f'<circle class="d r{ring}" cx="{cx - R + (gx + .5) * cell:.1f}" cy="{cy - R + (gy + .5) * cell:.1f}" '
                f'r="{rad:.2f}" fill="#{r_:02x}{g_:02x}{b_:02x}"/>'
            )

    orbit_icons = ["react", "typescript", "cplusplus", "figma", "nextdotjs"]
    orbit = ""
    OR = 196
    for i, name in enumerate(orbit_icons):
        ang = math.radians(-90 + i * 360 / len(orbit_icons) + 18)
        ox, oy = cx + OR * math.cos(ang), cy + OR * math.sin(ang)
        col = ICON_COLORS[name][0 if t is THEMES["dark"] else 1]
        orbit += f"""
        <g class="upright">
          <circle cx="{ox:.1f}" cy="{oy:.1f}" r="23" fill="{t['card']}" stroke="{t['border']}"/>
          <g transform="translate({ox - 12:.1f} {oy - 12:.1f})"><path d="{icon_path(name)}" fill="{col}"/></g>
        </g>"""

    portrait = f"""
    <circle cx="{cx}" cy="{cy}" r="{R + 30}" fill="url(#ring)" opacity=".35" filter="url(#soft)"/>
    <circle cx="{cx}" cy="{cy}" r="{OR}" fill="none" stroke="{t['border']}" stroke-dasharray="2 8"/>
    <g class="orbit">{orbit}</g>
    <circle class="spin spinr" cx="{cx}" cy="{cy}" r="{R + 22}" fill="none" stroke="{t['subtle']}" stroke-opacity=".6" stroke-dasharray="1 6"/>
    <circle class="spin" cx="{cx}" cy="{cy}" r="{R + 11}" fill="none" stroke="url(#ring)" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="300 70 90 70 120 300"/>
    <circle cx="{cx}" cy="{cy}" r="{R}" fill="{t['card']}"/>
    <g clip-path="url(#pc)">
      <g>{dots}</g>
      <image class="photo" x="{cx - R}" y="{cy - R}" width="{2 * R}" height="{2 * R}" preserveAspectRatio="xMidYMid slice"
        href="data:image/jpeg;base64,{b64}" xlink:href="data:image/jpeg;base64,{b64}"/>
      <rect class="scan" x="{cx - R}" y="{cy - R - 60}" width="{2 * R}" height="60" fill="url(#scanG)"/>
      <circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#vig)"/>
    </g>
    <circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{t['border']}" stroke-width="1.5"/>"""

    body = defs + bg + sparks + left + portrait
    return svg_doc(W, H, body, css, "Aathish M — Software Engineer. Curiosity into code. Ideas into interfaces.")


# ---------------------------------------------------------------------------
# About: animated code editor
# ---------------------------------------------------------------------------

def tok(kind, s):
    return (kind, s)


CODE = [
    [tok("com", "// hello, world — thanks for stopping by")],
    [tok("kw", "const "), tok("var", "aathish"), tok("punc", " = {")],
    [tok("ind", "  "), tok("prop", "role"), tok("punc", ":       "), tok("str", '"Software Engineer"'), tok("punc", ",")],
    [tok("ind", "  "), tok("prop", "basedIn"), tok("punc", ":    "), tok("str", '"Palani, India"'), tok("punc", ",")],
    [tok("ind", "  "), tok("prop", "alumnus"), tok("punc", ":    "), tok("str", '"Coimbatore Institute of Technology"'), tok("punc", ",")],
    [tok("ind", "  "), tok("prop", "certified"), tok("punc", ":  "), tok("str", '"Google — Foundations of UX Design"'), tok("punc", ",")],
    [tok("ind", "  "), tok("prop", "building"), tok("punc", ":   ["), tok("str", '"React"'), tok("punc", ", "), tok("str", '"JavaScript"'), tok("punc", ", "), tok("str", '"TypeScript"'), tok("punc", "],")],
    [tok("ind", "  "), tok("prop", "exploring"), tok("punc", ":  "), tok("str", '"useful interfaces & new ideas"'), tok("punc", ",")],
    [tok("ind", "  "), tok("prop", "askMeAbout"), tok("punc", ": ["), tok("str", '"frontend"'), tok("punc", ", "), tok("str", '"UI details"'), tok("punc", ", "), tok("str", '"C++"'), tok("punc", "],")],
    [tok("punc", "} "), tok("kw", "satisfies "), tok("typ", "CuriousEngineer"), tok("punc", ";")],
    [],
    [tok("kw", "export default "), tok("var", "aathish"), tok("punc", ";")],
]


def about(t):
    W = 1200
    fs, cw, lh = 18, 10.8, 31
    top, gut = 92, 92
    H = top + len(CODE) * lh + 150
    T = 22.0
    OFF = 14.0  # timeline offset so the first frame shows the finished code
    colors = dict(kw=t["kw"], str=t["str"], prop=t["prop"], punc=t["punc"], com=t["com"], typ=t["typ"], var=t["text"], ind=t["text"])

    css = f"""
    .code{{font:500 {fs}px {MONO}}}
    .ln{{font:400 {fs - 2}px {MONO};fill:{t['subtle']}}}
    .ui{{font:600 13px {SANS};fill:{t['muted']}}}
    .ui2{{font:500 12px {MONO};fill:{t['muted']}}}
    .term{{font:500 15px {MONO}}}
    .blink{{animation:blink 1s steps(1) infinite}}
    @keyframes blink{{50%{{opacity:0}}}}
    .out{{animation:out {T}s ease -{OFF}s both infinite}}
    @keyframes out{{0%,{pct(11.6, T)}{{opacity:0;transform:translateY(6px)}}{pct(12.2, T)},{pct(21.2, T)}{{opacity:1;transform:none}}{pct(21.8, T)},100%{{opacity:0}}}}
    .out2{{animation-name:out2}}
    @keyframes out2{{0%,{pct(12.6, T)}{{opacity:0;transform:translateY(6px)}}{pct(13.2, T)},{pct(21.2, T)}{{opacity:1;transform:none}}{pct(21.8, T)},100%{{opacity:0}}}}
    .bar{{animation:bar {T}s linear -{OFF}s infinite both}}
    @keyframes bar{{0%{{transform:scaleX(0)}}{pct(11.4, T)}{{transform:scaleX(1)}}{pct(21.6, T)}{{transform:scaleX(1);opacity:1}}{pct(22, T)},100%{{transform:scaleX(1);opacity:0}}}}
    .glow{{animation:glow 6s ease-in-out infinite alternate}}
    @keyframes glow{{from{{opacity:.35}}to{{opacity:.8}}}}
    """

    # timeline for typing
    t_now, lines_svg, clips, cur_ev = 0.6, "", "", [(0, f"{gut} {top}")]
    hold_until = 21.4
    line_ends = []
    for i, line in enumerate(CODE):
        y = top + i * lh
        text_len = sum(len(s) for _, s in line)
        tspans = "".join(f'<tspan fill="{colors[k]}">{esc(s)}</tspan>' for k, s in line)
        ev = [(0, 0)]
        k_done = 0
        for kind, s in line:
            if kind == "ind":
                k_done += len(s)
                ev.append((t_now, round(k_done * cw, 1)))
                cur_ev.append((t_now, f"{gut + k_done * cw:.1f} {y}"))
                continue
            for _ in s:
                t_now += 0.028
                k_done += 1
                ev.append((t_now, round(k_done * cw, 1)))
                cur_ev.append((t_now, f"{gut + k_done * cw:.1f} {y}"))
        line_ends.append(t_now)
        ev.append((hold_until, 0))
        kt, vals = discrete(ev, T)
        clips += (
            f'<clipPath id="c{i}"><rect x="{gut}" y="{y - lh + 8}" width="0" height="{lh}">'
            f'<animate attributeName="width" calcMode="discrete" keyTimes="{kt}" values="{vals}" dur="{T}s" begin="-{OFF}s" repeatCount="indefinite"/></rect></clipPath>'
        )
        lines_svg += f'<text class="ln" x="{gut - 26}" y="{y}" text-anchor="end">{i + 1}</text>'
        if text_len:
            lines_svg += (
                f'<text class="code" x="{gut}" y="{y}" textLength="{text_len * cw:.1f}" lengthAdjust="spacing" '
                f'clip-path="url(#c{i})" xml:space="preserve">{tspans}</text>'
            )
        t_now += 0.14
        if i + 1 < len(CODE):
            cur_ev.append((t_now, f"{gut} {top + (i + 1) * lh}"))
    cur_ev.append((hold_until, f"{gut} {top}"))
    kt, vals = discrete(cur_ev, T)
    cursor = (
        f'<g><animateTransform attributeName="transform" type="translate" calcMode="discrete" keyTimes="{kt}" values="{vals}" dur="{T}s" begin="-{OFF}s" repeatCount="indefinite"/>'
        f'<rect class="blink" x="1" y="-19" width="2.5" height="24" fill="{t["a2"]}"/></g>'
    )
    # current-line highlight follows the cursor's line
    hl_ev = [(0, f"0 0")]
    for i, end in enumerate(line_ends):
        if i + 1 < len(CODE):
            hl_ev.append((end + 0.14, f"0 {(i + 1) * lh}"))
    hl_ev.append((hold_until, "0 0"))
    kt2, vals2 = discrete(hl_ev, T)
    highlight = (
        f'<rect x="1" y="{top - lh + 9}" width="{W - 250}" height="{lh}" fill="{t["a1"]}" fill-opacity=".08">'
        f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" keyTimes="{kt2}" values="{vals2}" dur="{T}s" begin="-{OFF}s" repeatCount="indefinite"/></rect>'
    )

    # minimap mirrors the code lines
    mm = ""
    for i, line in enumerate(CODE):
        x = W - 190
        for kind, s in line:
            wseg = len(s) * 1.9
            if kind not in ("ind",) and s.strip():
                mm += f'<rect x="{x:.1f}" y="{top - 14 + i * 9}" width="{wseg:.1f}" height="4" rx="1" fill="{colors[kind]}" opacity=".7"/>'
            x += wseg

    term_y = top + len(CODE) * lh + 18
    body = f"""
    <defs>{clips}
      <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="{t['a1']}"/><stop offset=".5" stop-color="{t['a2']}"/><stop offset="1" stop-color="{t['a3']}"/>
      </linearGradient>
      <clipPath id="win"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18"/></clipPath>
    </defs>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="{t['card']}"/>
    <g clip-path="url(#win)">
      <rect class="glow" x="0" y="0" width="{W}" height="2" fill="url(#edge)"/>
      <rect x="0" y="2" width="{W}" height="44" fill="{t['card2']}"/>
      <circle cx="28" cy="24" r="6.5" fill="#ff5f57"/><circle cx="50" cy="24" r="6.5" fill="#febc2e"/><circle cx="72" cy="24" r="6.5" fill="#28c840"/>
      <rect x="104" y="8" width="170" height="38" rx="8" fill="{t['card']}"/>
      <rect x="104" y="44" width="170" height="2" fill="{t['card']}"/>
      <g transform="translate(118 18) scale(.75)"><path d="{icon_path('typescript')}" fill="{ICON_COLORS['typescript'][0 if t is THEMES['dark'] else 1]}"/></g>
      <text class="ui" x="146" y="32" fill="{t['text']}" style="fill:{t['text']}">aathish.ts</text>
      <text class="ui" x="254" y="32" text-anchor="middle">×</text>
      <text class="ui" x="306" y="32">README.md</text>
      <text class="ui2" x="{W - 24}" y="30" text-anchor="end">profile / src / aathish.ts</text>
      <rect x="0" y="46" width="{W}" height="1" fill="{t['border']}"/>
      {highlight}
      {lines_svg}
      {cursor}
      <rect x="{W - 206}" y="47" width="1" height="{term_y - 66}" fill="{t['border']}"/>
      {mm}
      <rect x="{W - 198}" y="{top - 22}" width="182" height="{len(CODE) * 9 + 14}" rx="3" fill="{t['text']}" fill-opacity=".05"/>
      <rect x="0" y="{term_y - 20}" width="{W}" height="1" fill="{t['border']}"/>
      <text class="ui2" x="24" y="{term_y + 4}" style="letter-spacing:1px">TERMINAL</text>
      <text class="ui2" x="120" y="{term_y + 4}" fill="{t['subtle']}" style="fill:{t['subtle']}" xml:space="preserve">OUTPUT    PROBLEMS</text>
      <g class="out"><text class="term" x="24" y="{term_y + 36}"><tspan fill="{t['a2']}">❯</tspan><tspan fill="{t['text']}"> npm run build</tspan></text></g>
      <g class="out out2"><text class="term" x="24" y="{term_y + 64}"><tspan fill="{t['str']}">✓</tspan><tspan fill="{t['muted']}"> compiled curiosity into code · </tspan><tspan fill="{t['text']}">ideas → interfaces</tspan><tspan fill="{t['subtle']}">  in 0.42s</tspan></text></g>
      <rect x="0" y="{H - 30}" width="{W}" height="30" fill="{t['a1']}" fill-opacity=".9"/>
      <rect class="bar" style="transform-origin:0 0" x="0" y="{H - 30}" width="{W}" height="2" fill="{t['a2']}"/>
      <text x="20" y="{H - 10}" style="font:600 12px {MONO}" fill="#fff" xml:space="preserve">⎇ main   ✓ 0 problems</text>
      <text x="{W - 20}" y="{H - 10}" text-anchor="end" style="font:500 12px {MONO}" fill="#fff" xml:space="preserve">Palani, IN    UTF-8    TypeScript React    Ln 12, Col 1</text>
    </g>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="none" stroke="{t['border']}"/>"""
    alt = "Code editor showing aathish.ts: Software Engineer based in Palani, India; alumnus of Coimbatore Institute of Technology; Google Foundations of UX Design certified; building with React, JavaScript and TypeScript; ask me about frontend, UI details and C++."
    return svg_doc(W, H, body, css, alt)


# ---------------------------------------------------------------------------
# Toolkit grid
# ---------------------------------------------------------------------------

STACK = [
    ("react", "React"), ("typescript", "TypeScript"), ("javascript", "JavaScript"), ("nextdotjs", "Next.js"),
    ("tailwindcss", "Tailwind CSS"), ("html5", "HTML5"), ("css3", "CSS"), ("cplusplus", "C++"),
    ("git", "Git"), ("figma", "Figma"), ("firebase", "Firebase"), ("prisma", "Prisma"),
]


def stack(t):
    W, cols, gap, tw, th = 1200, 6, 16, 0, 118
    tw = (W - 2 * 2 - (cols - 1) * gap) / cols
    rows = math.ceil(len(STACK) / cols)
    H = rows * th + (rows - 1) * gap + 4
    T = len(STACK) * 0.5
    css = f"""
    .lbl{{font:600 15px {SANS};fill:{t['text']}}}
    .tile{{transform-box:fill-box;transform-origin:center;}}
    @keyframes pop{{from{{opacity:0;transform:translateY(18px) scale(.94)}}to{{opacity:1;transform:none}}}}
    .hl{{animation:hl {T}s ease-in-out infinite both;opacity:0}}
    @keyframes hl{{0%,100%{{opacity:0}}5%{{opacity:1}}16%{{opacity:0}}}}
    .ic{{transform-box:fill-box;transform-origin:center;animation:bob {T}s ease-in-out infinite both}}
    @keyframes bob{{0%,100%{{transform:none}}5%{{transform:translateY(-5px) scale(1.08)}}16%{{transform:none}}}}
    """
    body = f"""<defs><linearGradient id="hg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{t['a1']}"/><stop offset=".5" stop-color="{t['a2']}"/><stop offset="1" stop-color="{t['a3']}"/></linearGradient></defs>"""
    for i, (name, label) in enumerate(STACK):
        r, c = divmod(i, cols)
        x, y = 2 + c * (tw + gap), 2 + r * (th + gap)
        col = ICON_COLORS[name][0 if t is THEMES["dark"] else 1]
        d = i * 0.5
        body += f"""
        <g class="tile" style="animation-delay:{i * 0.06:.2f}s">
          <rect x="{x:.1f}" y="{y}" width="{tw:.1f}" height="{th}" rx="16" fill="{t['card2']}" stroke="{t['border']}"/>
          <rect class="hl" style="animation-delay:{d:.1f}s" x="{x:.1f}" y="{y}" width="{tw:.1f}" height="{th}" rx="16" fill="{col}" fill-opacity=".08" stroke="url(#hg)" stroke-width="1.6"/>
          <g class="ic" style="animation-delay:{d:.1f}s"><g transform="translate({x + tw / 2 - 19:.1f} {y + 22}) scale(1.6)"><path d="{icon_path(name)}" fill="{col}"/></g></g>
          <text class="lbl" x="{x + tw / 2:.1f}" y="{y + th - 22}" text-anchor="middle">{esc(label)}</text>
        </g>"""
    return svg_doc(W, H, body, css, "Toolkit: " + ", ".join(l for _, l in STACK))


# ---------------------------------------------------------------------------
# Project cards (each with its own small animated illustration)
# ---------------------------------------------------------------------------

PROJECTS = [
    ("01", "Remind Me", ["A TypeScript web project built with Next.js,", "with Prisma, Clerk and a component-based UI."], ["TypeScript", "Next.js", "Prisma"], "bell"),
    ("02", "EventHub", ["A JavaScript project created for the Melinia", "hackathon — an experiment in collaboration."], ["JavaScript", "Hackathon"], "calendar"),
    ("03", "Covid Tracker", ["A web project exploring COVID-19 tracking and", "presenting data through a browser interface."], ["HTML", "Web"], "pulse"),
    ("04", "AlphaZ", ["A public discussion forum project — exploring", "the web as a place for people and conversation."], ["Community", "Forum"], "chat"),
]


def illo(kind, t, x, y):
    a1, a2, a3, st = t["a1"], t["a2"], t["a3"], t["muted"]
    if kind == "bell":
        return f"""
        <g transform="translate({x} {y})">
          <g class="swing"><path d="M0 -34c-15 0-24 11-24 26v16l-7 10h62l-7-10V-8C24-23 15-34 0-34z" fill="none" stroke="{a1}" stroke-width="3" stroke-linejoin="round"/>
          <path d="M-8 22a8 8 0 0 0 16 0" fill="none" stroke="{a1}" stroke-width="3" stroke-linecap="round"/></g>
          <circle class="ping" cx="20" cy="-28" r="7" fill="{a3}"/><circle cx="20" cy="-28" r="7" fill="{a3}"/>
        </g>"""
    if kind == "calendar":
        cells = ""
        for j in range(12):
            r_, c_ = divmod(j, 4)
            cells += f'<rect class="day" style="animation-delay:{j * 0.35:.2f}s" x="{-34 + c_ * 18}" y="{-10 + r_ * 15}" width="14" height="11" rx="3" fill="{a2}"/>'
            cells += f'<rect x="{-34 + c_ * 18}" y="{-10 + r_ * 15}" width="14" height="11" rx="3" fill="none" stroke="{st}" stroke-opacity=".45"/>'
        return f"""
        <g transform="translate({x} {y})">
          <rect x="-40" y="-36" width="80" height="78" rx="10" fill="none" stroke="{a2}" stroke-width="3"/>
          <path d="M-40 -18h80M-22 -44v14M22 -44v14" stroke="{a2}" stroke-width="3" stroke-linecap="round"/>{cells}
        </g>"""
    if kind == "pulse":
        return f"""
        <g transform="translate({x} {y})">
          <path d="M-46 30V-36M-46 30h96" stroke="{st}" stroke-opacity=".5" stroke-width="2"/>
          <path class="draw" d="M-46 18l14-6 10 4 10-22 10 14 10-30 10 20 10-6 14-10" fill="none" stroke="{a3}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" pathLength="100"/>
          <circle class="ping" cx="48" cy="-18" r="5" fill="{a3}"/><circle cx="48" cy="-18" r="4" fill="{a3}"/>
        </g>"""
    # chat
    return f"""
    <g transform="translate({x} {y})">
      <g class="b1"><rect x="-46" y="-36" width="60" height="28" rx="12" fill="{a1}" fill-opacity=".18" stroke="{a1}" stroke-width="2"/>
        <circle cx="-30" cy="-22" r="3" fill="{a1}"/><circle cx="-16" cy="-22" r="3" fill="{a1}"/><circle cx="-2" cy="-22" r="3" fill="{a1}"/></g>
      <g class="b2"><rect x="-10" y="-2" width="58" height="26" rx="12" fill="{a2}" fill-opacity=".18" stroke="{a2}" stroke-width="2"/>
        <path d="M2 11h34" stroke="{a2}" stroke-width="3" stroke-linecap="round"/></g>
      <g class="b3"><rect x="-40" y="30" width="44" height="22" rx="11" fill="{a3}" fill-opacity=".18" stroke="{a3}" stroke-width="2"/>
        <circle class="typing" cx="-28" cy="41" r="2.6" fill="{a3}"/><circle class="typing" style="animation-delay:.15s" cx="-18" cy="41" r="2.6" fill="{a3}"/><circle class="typing" style="animation-delay:.3s" cx="-8" cy="41" r="2.6" fill="{a3}"/></g>
    </g>"""


def project_card(t, num, title, desc, tags, kind):
    W, H = 600, 270
    css = f"""
    .num{{font:800 56px {SANS};letter-spacing:-2px}}
    .ttl{{font:700 28px {SANS};fill:{t['text']};letter-spacing:-.5px}}
    .dsc{{font:400 16px {SANS};fill:{t['muted']}}}
    .tg{{font:600 13px {MONO};fill:{t['text']}}}
    .cta{{font:700 15px {SANS};fill:{t['a1']}}}
    .arrow{{animation:nudge 1.6s ease-in-out infinite}}
    @keyframes nudge{{50%{{transform:translateX(6px)}}}}
    .card{{}}
    @keyframes in{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:none}}}}
    .border{{animation:trace 6s linear infinite}}
    @keyframes trace{{to{{stroke-dashoffset:-1000}}}}
    .swing{{transform-origin:0 -34px;animation:swing 2.8s ease-in-out infinite}}
    @keyframes swing{{0%,40%,100%{{transform:rotate(0)}}8%{{transform:rotate(14deg)}}16%{{transform:rotate(-12deg)}}24%{{transform:rotate(8deg)}}32%{{transform:rotate(-4deg)}}}}
    .ping{{transform-box:fill-box;transform-origin:center;animation:ping 2s ease-out infinite}}
    @keyframes ping{{from{{transform:scale(1);opacity:.7}}to{{transform:scale(2.6);opacity:0}}}}
    .day{{opacity:0;animation:day 4.2s ease-in-out infinite}}
    @keyframes day{{0%,100%{{opacity:0}}6%{{opacity:.9}}20%{{opacity:0}}}}
    .draw{{stroke-dasharray:100;animation:draw 3.2s ease-in-out infinite}}
    @keyframes draw{{0%,45%{{stroke-dashoffset:0}}65%{{stroke-dashoffset:-100}}65.1%{{stroke-dashoffset:100}}100%{{stroke-dashoffset:0}}}}
    .b1,.b2,.b3{{transform-box:fill-box;transform-origin:center;animation:bub 4.5s ease-out infinite both}}
    .b2{{animation-delay:.6s}} .b3{{animation-delay:1.2s}}
    @keyframes bub{{0%,70%{{opacity:1;transform:none}}80%,88%{{opacity:0;transform:scale(.6)}}100%{{opacity:1;transform:none}}}}
    .typing{{animation:typ 1s ease-in-out infinite}}
    @keyframes typ{{50%{{transform:translateY(-3px)}}}}
    """
    tag_svg, tx = "", 32
    for tg in tags:
        tw = len(tg) * 8.2 + 26
        tag_svg += f'<rect x="{tx}" y="182" width="{tw:.0f}" height="28" rx="8" fill="{t["card2"]}" stroke="{t["border"]}"/><text class="tg" x="{tx + 13}" y="201">{esc(tg)}</text>'
        tx += tw + 8
    desc_svg = "".join(f'<text class="dsc" x="32" y="{140 + i * 24}">{esc(line)}</text>' for i, line in enumerate(desc))
    body = f"""
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="{t['a1']}"/><stop offset=".5" stop-color="{t['a2']}"/><stop offset="1" stop-color="{t['a3']}"/></linearGradient>
      <linearGradient id="ng" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{t['a1']}" stop-opacity=".9"/><stop offset="1" stop-color="{t['a2']}" stop-opacity=".25"/></linearGradient>
      <radialGradient id="corner" cx="1" cy="0" r="1"><stop offset="0" stop-color="{t['a1']}" stop-opacity=".16"/><stop offset=".6" stop-color="{t['a1']}" stop-opacity="0"/></radialGradient>
    </defs>
    <g class="card">
      <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="{t['card']}" stroke="{t['border']}"/>
      <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="url(#corner)"/>
      <rect class="border" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="none" stroke="url(#bg)" stroke-width="2" stroke-dasharray="160 340" pathLength="1000"/>
      <text class="num" x="30" y="72" fill="url(#ng)">{num}</text>
      <text class="ttl" x="32" y="108">{esc(title)}</text>
      {desc_svg}
      {tag_svg}
      <text class="cta" x="32" y="244">Explore the repository</text>
      <g class="arrow"><text class="cta" x="214" y="244">→</text></g>
      {illo(kind, t, W - 90, 88)}
    </g>"""
    return svg_doc(W, H, body, css, f"{num} {title} — {' '.join(desc)}")


# ---------------------------------------------------------------------------
# Link buttons
# ---------------------------------------------------------------------------

def li_icon(col):
    return f'<rect x="2" y="2" width="20" height="20" rx="4" fill="{col}"/><text x="12" y="17.5" text-anchor="middle" style="font:800 13px {SANS}" fill="#fff">in</text>'


LINKS = [
    ("linkedin", "LinkedIn", None, "#0a66c2"),
    ("email", "Email", "gmail", "#ea4335"),
    ("code", "My code", "github", None),
    ("leetcode", "LeetCode", "leetcode", "#ffa116"),
]


def button(t, key, label, icon, col):
    W, H = 200, 52
    col = col or t["text"]
    css = f"""
    .l{{font:700 16px {SANS};fill:{t['text']}}}
    .shine{{animation:shine 5s ease-in-out infinite}}
    @keyframes shine{{0%,60%{{transform:translateX(-120px)}}85%,100%{{transform:translateX(320px)}}}}
    """
    ic = li_icon(col) if icon is None else f'<path d="{icon_path(icon)}" fill="{col}"/>'
    delay = {"linkedin": 0, "email": .4, "code": .8, "leetcode": 1.2}[key]
    body = f"""
    <defs><clipPath id="c"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="26"/></clipPath>
    <linearGradient id="s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['a2']}" stop-opacity="0"/><stop offset=".5" stop-color="{t['a2']}" stop-opacity=".22"/><stop offset="1" stop-color="{t['a2']}" stop-opacity="0"/></linearGradient>
    <linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t['a1']}"/><stop offset="1" stop-color="{t['a2']}"/></linearGradient></defs>
    <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="26" fill="{t['card2']}" stroke="url(#b)" stroke-width="1.5"/>
    <g clip-path="url(#c)"><rect class="shine" style="animation-delay:{delay}s" x="0" y="0" width="90" height="{H}" fill="url(#s)" transform="skewX(-20)"/></g>
    <g transform="translate(34 14)">{ic}</g>
    <text class="l" x="{W / 2 + 16}" y="32" text-anchor="middle">{esc(label)} ↗</text>"""
    return svg_doc(W, H, body, css, label)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

def footer(t):
    W, H = 1200, 220

    def wave(amp, length, y, phase):
        d = f"M{-length * 2 + phase} {y}"
        x = -length * 2 + phase
        while x < W + length * 2:
            d += f" q{length / 4} {-amp} {length / 2} 0 t{length / 2} 0"
            x += length
        return d + f" V{H} H{-length * 2} Z"

    css = f"""
    .w{{animation:wave 9s linear infinite}} .w2{{animation-duration:13s;animation-direction:reverse}} .w3{{animation-duration:17s}}
    @keyframes wave{{to{{transform:translateX(240px)}}}}
    .big{{font:800 34px {SANS};letter-spacing:-1px}}
    .sub{{font:500 17px {SANS};fill:{t['muted']}}}
    .hand{{transform-box:fill-box;transform-origin:70% 80%;animation:hand 2.4s ease-in-out infinite}}
    @keyframes hand{{0%,60%,100%{{transform:rotate(0)}}10%,30%{{transform:rotate(16deg)}}20%,40%{{transform:rotate(-8deg)}}}}
    """
    body = f"""
    <defs>
      <linearGradient id="fg" x1="0" y1="0" x2="600" y2="0" gradientUnits="userSpaceOnUse" spreadMethod="repeat">
        <stop offset="0" stop-color="{t['a1']}"/><stop offset=".5" stop-color="{t['a2']}"/><stop offset="1" stop-color="{t['a1']}"/>
        <animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="600 0" dur="6s" repeatCount="indefinite"/></linearGradient>
      <clipPath id="fc"><rect width="{W}" height="{H}" rx="28"/></clipPath>
    </defs>
    <g clip-path="url(#fc)">
      <rect width="{W}" height="{H}" fill="{t['card2']}"/>
      <path class="w w3" d="{wave(10, 240, 150, 0)}" fill="{t['a3']}" fill-opacity=".10"/>
      <path class="w w2" d="{wave(14, 240, 165, 60)}" fill="{t['a2']}" fill-opacity=".13"/>
      <path class="w" d="{wave(12, 240, 182, 120)}" fill="{t['a1']}" fill-opacity=".18"/>
    </g>
    <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="28" fill="none" stroke="{t['border']}"/>
    <text class="big" x="{W / 2}" y="86" text-anchor="middle" fill="url(#fg)">Have an interesting idea? Let's connect.</text>
    <text class="sub" x="{W / 2}" y="122" text-anchor="middle">Thanks for stopping by — I'm always happy to talk frontend, UI details and problem solving.</text>"""
    return svg_doc(W, H, body, css, "Have an interesting idea? Let's connect.")


# ---------------------------------------------------------------------------

def main():
    b64, small, grid = portrait_data()
    for mode, t in THEMES.items():
        print(f"[{mode}]")
        write(f"header-{mode}.svg", header(t, b64, small, grid))
        write(f"about-{mode}.svg", about(t))
        write(f"stack-{mode}.svg", stack(t))
        for num, title, desc, tags, kind in PROJECTS:
            slug = title.lower().replace(" ", "-")
            write(f"project-{slug}-{mode}.svg", project_card(t, num, title, desc, tags, kind))
        for key, label, icon, col in LINKS:
            write(f"btn-{key}-{mode}.svg", button(t, key, label, icon, col))
        write(f"footer-{mode}.svg", footer(t))


if __name__ == "__main__":
    main()
