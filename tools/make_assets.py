#!/usr/bin/env python3
"""Generate every SVG asset for the profile README.

All artwork is drawn here -- no third-party image host, no external fonts and
no JavaScript, so the files render identically inside a GitHub README <img>.

Theme "Amber Forge": deep ink-blue ground, mint primary, amber accent.
Each asset ships in a dark and a light variant; README.md picks between them
with <picture> + prefers-color-scheme.

Usage:
    python tools/make_assets.py
    python tools/make_assets.py --only banner,divider
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_config as cfg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
PROFILE = ROOT / "data" / "profile.json"

FONT = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
    "'Hiragino Sans GB','Microsoft YaHei','Helvetica Neue',Arial,sans-serif"
)
MONO = (
    "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
    "'Liberation Mono','Courier New',monospace"
)

# ------------------------------------------------------------------ themes ---

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg0": "#060A12",
        "bg1": "#0A1421",
        "bg2": "#0D1B2B",
        "panel": "#0B1624",
        "panel_hi": "#11202F",
        "stroke": "#1D3548",
        "stroke2": "#152A3A",
        "text": "#E8F3FF",
        "soft": "#B6C9DE",
        "muted": "#8399B5",
        "dim": "#4C6076",
        "mint": "#2DD4BF",
        "mint_soft": "#5EEAD4",
        "teal": "#14B8A6",
        "cyan": "#38BDF8",
        "amber": "#FBBF24",
        "amber_soft": "#FCD34D",
        "green": "#34D399",
        "grid_dot": "#2DD4BF",
        "track": "#122232",
        "shadow_op": "0.55",
    },
    "light": {
        "bg0": "#FFFFFF",
        "bg1": "#F5FAFB",
        "bg2": "#EAF3F5",
        "panel": "#FFFFFF",
        "panel_hi": "#F4F9FA",
        "stroke": "#D3E2E7",
        "stroke2": "#E4EDF0",
        "text": "#0F2431",
        "soft": "#33505F",
        "muted": "#5B7484",
        "dim": "#93A9B4",
        "mint": "#0D9488",
        "mint_soft": "#14B8A6",
        "teal": "#0F766E",
        "cyan": "#0284C7",
        "amber": "#B45309",
        "amber_soft": "#D97706",
        "green": "#059669",
        "grid_dot": "#0D9488",
        "track": "#E2EDF0",
        "shadow_op": "0.10",
    },
}

# Stage colours for the pipeline graphic, (light, dark).
STAGE_COLORS = [
    ("#0284C7", "#38BDF8"),
    ("#0D9488", "#2DD4BF"),
    ("#B45309", "#FBBF24"),
    ("#059669", "#34D399"),
]

# GitHub language colours as (light, dark) -- dark variants are lifted so they
# stay legible on the deep ground.
LANG_COLORS = {
    "TypeScript": ("#3178C6", "#4F93DE"),
    "JavaScript": ("#C9A227", "#F1E05A"),
    "HTML": ("#E34C26", "#F0754F"),
    "CSS": ("#563D7C", "#9B7CC4"),
    "PHP": ("#4F5D95", "#828FCB"),
    "Vue": ("#41B883", "#41D69B"),
    "Python": ("#3572A5", "#5C9BD1"),
    "Rust": ("#B06C3E", "#DEA584"),
    "Shell": ("#4E9A28", "#89E051"),
    "Java": ("#B07219", "#D9913F"),
    "Go": ("#00ADD8", "#22C3E8"),
    "Smarty": ("#C08A18", "#F0C040"),
    "Dockerfile": ("#384D54", "#6E8A94"),
    "Batchfile": ("#C1F12E", "#C1F12E"),
    "VBScript": ("#15DCDC", "#15DCDC"),
}


def lang_color(name: str, theme: str) -> str:
    pair = LANG_COLORS.get(name)
    if not pair:
        return THEMES[theme]["muted"]
    return pair[1] if theme == "dark" else pair[0]


# ----------------------------------------------------------- svg utilities ---

def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def n(x: float) -> str:
    """Compact number formatting for SVG coordinates."""
    r = round(float(x), 2)
    return str(int(r)) if r == int(r) else f"{r:g}"


def text_width(s: str, size: float, mono: bool = False) -> float:
    """Estimate rendered width. Over-estimating is safe, under is not."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x2E80 or o in (0x2018, 0x2019, 0x201C, 0x201D):
            w += 1.0
        elif mono:
            w += 0.60
        elif ch in "iljI|!.,:;'\"()[]":
            w += 0.32
        elif ch in "·—–":
            w += 0.55
        elif ch.isupper():
            w += 0.68
        elif ch == " ":
            w += 0.30
        else:
            w += 0.55
    return w * size


def wrap(s: str, size: float, max_w: float, mono: bool = False) -> list[str]:
    """Greedy wrap that keeps ASCII words whole and lets CJK break anywhere."""
    out: list[str] = []
    for para in s.split("\n"):
        cur = ""
        for tok in re.findall(r"[A-Za-z0-9_./+:#-]+|\s+|[^\sA-Za-z0-9]", para):
            if text_width(cur + tok, size, mono) > max_w and cur.strip():
                out.append(cur.rstrip())
                cur = "" if tok.isspace() else tok
            else:
                cur += tok
        if cur.strip():
            out.append(cur.rstrip())
    return out


def t(
    x: float,
    y: float,
    s: str,
    *,
    size: float = 13,
    weight: int = 400,
    fill: str = "#fff",
    anchor: str = "start",
    spacing: float | None = None,
    mono: bool = False,
    opacity: float | None = None,
) -> str:
    a = f'<text x="{n(x)}" y="{n(y)}" font-family="{MONO if mono else FONT}"'
    a += f' font-size="{n(size)}" font-weight="{weight}" fill="{fill}"'
    if anchor != "start":
        a += f' text-anchor="{anchor}"'
    if spacing is not None:
        a += f' letter-spacing="{n(spacing)}"'
    if opacity is not None:
        a += f' opacity="{n(opacity)}"'
    return a + f">{esc(s)}</text>"


def rect(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    rx: float = 0,
    fill: str = "none",
    stroke: str | None = None,
    sw: float = 1,
    opacity: float | None = None,
    stroke_opacity: float | None = None,
) -> str:
    a = f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"'
    if rx:
        a += f' rx="{n(rx)}"'
    a += f' fill="{fill}"'
    if stroke:
        a += f' stroke="{stroke}" stroke-width="{n(sw)}"'
    if stroke_opacity is not None:
        a += f' stroke-opacity="{n(stroke_opacity)}"'
    if opacity is not None:
        a += f' opacity="{n(opacity)}"'
    return a + "/>"


def circle(
    cx: float,
    cy: float,
    r: float,
    *,
    fill: str = "none",
    stroke: str | None = None,
    sw: float = 1,
    opacity: float | None = None,
) -> str:
    a = f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}" fill="{fill}"'
    if stroke:
        a += f' stroke="{stroke}" stroke-width="{n(sw)}"'
    if opacity is not None:
        a += f' opacity="{n(opacity)}"'
    return a + "/>"


def path(
    d: str,
    *,
    fill: str = "none",
    stroke: str | None = None,
    sw: float = 1,
    cap: str = "round",
    join: str = "round",
    opacity: float | None = None,
) -> str:
    a = f'<path d="{d}" fill="{fill}"'
    if stroke:
        a += (
            f' stroke="{stroke}" stroke-width="{n(sw)}"'
            f' stroke-linecap="{cap}" stroke-linejoin="{join}"'
        )
    if opacity is not None:
        a += f' opacity="{n(opacity)}"'
    return a + "/>"


def lin_grad(gid: str, stops: list[tuple[float, str, float]]) -> str:
    """stops: (offset, color, opacity)"""
    s = f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
    for off, col, op in stops:
        s += f'<stop offset="{n(off)}" stop-color="{col}" stop-opacity="{n(op)}"/>'
    return s + "</linearGradient>"


def lin_grad_v(gid: str, stops: list[tuple[float, str, float]]) -> str:
    s = f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
    for off, col, op in stops:
        s += f'<stop offset="{n(off)}" stop-color="{col}" stop-opacity="{n(op)}"/>'
    return s + "</linearGradient>"


def rad_grad(gid: str, col: str, peak: float) -> str:
    return (
        f'<radialGradient id="{gid}">'
        f'<stop offset="0" stop-color="{col}" stop-opacity="{n(peak)}"/>'
        f'<stop offset="1" stop-color="{col}" stop-opacity="0"/>'
        f"</radialGradient>"
    )


def sweep(x0: float, y: float, w: float, h: float, gid: str, dur: float) -> str:
    """A highlight bar that travels left to right, forever."""
    return (
        f'<rect x="{n(x0)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" '
        f'rx="{n(h / 2)}" fill="url(#{gid})">'
        f'<animate attributeName="x" values="{n(x0)};{n(x0 + 1400)}" '
        f'dur="{n(dur)}s" repeatCount="indefinite"/></rect>'
    )


def star_points(cx: float, cy: float, r_out: float) -> str:
    r_in = r_out * 0.42
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append(f"{n(cx + r * math.cos(ang))},{n(cy + r * math.sin(ang))}")
    return " ".join(pts)


def svg_open(w: float, h: float, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" '
        f'viewBox="0 0 {n(w)} {n(h)}" fill="none" role="img" '
        f'aria-label="{esc(label)}">'
    )


# ------------------------------------------------------------- icon paths ---
# Every icon is drawn inside a square tile; these return shapes for a tile
# whose top-left is (tx, ty) and whose side is `s`.

def icon_person(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    cx, cy = tx + 28 * k, ty + 21 * k
    return circle(cx, cy, 7.5 * k, stroke=col, sw=sw) + path(
        f"M{n(tx + 15 * k)} {n(ty + 45 * k)} C{n(tx + 15 * k)} {n(ty + 34 * k)} "
        f"{n(tx + 20.5 * k)} {n(ty + 30 * k)} {n(cx)} {n(ty + 30 * k)} "
        f"C{n(tx + 35.5 * k)} {n(ty + 30 * k)} {n(tx + 41 * k)} {n(ty + 34 * k)} "
        f"{n(tx + 41 * k)} {n(ty + 45 * k)}",
        stroke=col,
        sw=sw,
    )


def icon_layers(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    out = ""
    for i, (dy, op) in enumerate(((0, 1.0), (10, 0.7), (20, 0.42))):
        out += rect(
            tx + 13 * k,
            ty + (17 + dy) * k,
            30 * k,
            7.5 * k,
            rx=3.75 * k,
            fill=col,
            opacity=op,
        )
    return out


def icon_pipeline(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    cy = ty + 28 * k
    xs = [tx + 16 * k, tx + 28 * k, tx + 40 * k]
    out = path(
        f"M{n(xs[0])} {n(cy)} L{n(xs[2])} {n(cy)}", stroke=col, sw=sw, opacity=0.4
    )
    for i, x in enumerate(xs):
        out += circle(x, cy, 5 * k, fill=col if i == 1 else "none",
                      stroke=col, sw=sw)
    return out


def icon_grid(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    out = ""
    for dx, dy in ((0, 0), (16, 0), (0, 16), (16, 16)):
        out += rect(tx + (14 + dx) * k, ty + (14 + dy) * k, 13 * k, 13 * k,
                    rx=3.5 * k, stroke=col, sw=sw)
    return out


def icon_bars(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    out = ""
    for i, (dx, hh) in enumerate(((0, 13), (9, 22), (18, 31))):
        out += rect(tx + (15 + dx) * k, ty + (45 - hh) * k, 6.5 * k, hh * k,
                    rx=3.25 * k, fill=col, opacity=0.5 + 0.25 * i)
    return out


def icon_doc(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    return rect(tx + 15 * k, ty + 13 * k, 26 * k, 30 * k, rx=4 * k,
                stroke=col, sw=sw) + "".join(
        path(
            f"M{n(tx + 21 * k)} {n(ty + (22 + 6 * i) * k)} "
            f"L{n(tx + (35 - i * 4) * k)} {n(ty + (22 + 6 * i) * k)}",
            stroke=col,
            sw=sw * 0.9,
        )
        for i in range(3)
    )


def icon_server(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    out = ""
    for i in range(2):
        y = ty + (16 + i * 14) * k
        out += rect(tx + 14 * k, y, 28 * k, 11 * k, rx=3 * k, stroke=col, sw=sw)
        out += circle(tx + 20 * k, y + 5.5 * k, 1.9 * k, fill=col)
        out += path(
            f"M{n(tx + 25 * k)} {n(y + 5.5 * k)} L{n(tx + 37 * k)} {n(y + 5.5 * k)}",
            stroke=col,
            sw=sw * 0.9,
            opacity=0.55,
        )
    return out


def icon_sliders(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    out = ""
    for i, kx in enumerate((0.30, 0.68, 0.44)):
        y = ty + (18 + i * 10) * k
        out += path(
            f"M{n(tx + 14 * k)} {n(y)} L{n(tx + 42 * k)} {n(y)}",
            stroke=col,
            sw=sw,
            opacity=0.55,
        )
        out += circle(tx + (14 + 28 * kx) * k, y, 3.6 * k, fill=col)
    return out


def icon_inbox(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    return (
        path(
            f"M{n(tx + 14 * k)} {n(ty + 30 * k)} L{n(tx + 14 * k)} {n(ty + 20 * k)} "
            f"L{n(tx + 21 * k)} {n(ty + 14 * k)} L{n(tx + 35 * k)} {n(ty + 14 * k)} "
            f"L{n(tx + 42 * k)} {n(ty + 20 * k)} L{n(tx + 42 * k)} {n(ty + 30 * k)} "
            f"L{n(tx + 35 * k)} {n(ty + 36 * k)} L{n(tx + 21 * k)} {n(ty + 36 * k)} Z",
            stroke=col,
            sw=sw,
        )
        + path(
            f"M{n(tx + 14 * k)} {n(ty + 26 * k)} L{n(tx + 23 * k)} {n(ty + 26 * k)} "
            f"L{n(tx + 26 * k)} {n(ty + 31 * k)} L{n(tx + 30 * k)} {n(ty + 31 * k)} "
            f"L{n(tx + 33 * k)} {n(ty + 26 * k)} L{n(tx + 42 * k)} {n(ty + 26 * k)}",
            stroke=col,
            sw=sw,
            opacity=0.75,
        )
    )


def icon_spark(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    cx, cy = tx + 28 * k, ty + 28 * k
    d = 14 * k
    return (
        path(
            f"M{n(cx)} {n(cy - d)} C{n(cx + 2 * k)} {n(cy - 4 * k)} "
            f"{n(cx + 4 * k)} {n(cy - 2 * k)} {n(cx + d)} {n(cy)} "
            f"C{n(cx + 4 * k)} {n(cy + 2 * k)} {n(cx + 2 * k)} {n(cy + 4 * k)} "
            f"{n(cx)} {n(cy + d)} C{n(cx - 2 * k)} {n(cy + 4 * k)} "
            f"{n(cx - 4 * k)} {n(cy + 2 * k)} {n(cx - d)} {n(cy)} "
            f"C{n(cx - 4 * k)} {n(cy - 2 * k)} {n(cx - 2 * k)} {n(cy - 4 * k)} "
            f"{n(cx)} {n(cy - d)} Z",
            fill=col,
            opacity=0.92,
        )
        + circle(cx + 13 * k, cy - 13 * k, 3 * k, fill=col, opacity=0.6)
    )


def icon_send(tx: float, ty: float, s: float, col: str, sw: float) -> str:
    k = s / 56
    return path(
        f"M{n(tx + 14 * k)} {n(ty + 28 * k)} L{n(tx + 42 * k)} {n(ty + 16 * k)} "
        f"L{n(tx + 30 * k)} {n(ty + 42 * k)} L{n(tx + 26 * k)} {n(ty + 31 * k)} Z",
        stroke=col,
        sw=sw,
    ) + path(
        f"M{n(tx + 26 * k)} {n(ty + 31 * k)} L{n(tx + 42 * k)} {n(ty + 16 * k)}",
        stroke=col,
        sw=sw * 0.9,
        opacity=0.6,
    )


PIPELINE_ICONS = {
    "inbox": icon_inbox,
    "grid": icon_grid,
    "spark": icon_spark,
    "send": icon_send,
}

# ------------------------------------------------------------ asset: banner ---

def asset_banner(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W, H = 1000, 264
    p = [svg_open(W, H, "寰宇 · HUANYU")]
    p.append("<defs>")
    p.append(lin_grad_v("bgbg", [(0, T["bg0"], 1), (0.55, T["bg1"], 1), (1, T["bg2"], 1)]))
    p.append(lin_grad("bname", [(0, T["mint"], 1), (0.6, T["cyan"], 1)]))
    p.append(lin_grad("brule", [
        (0, T["mint"], 0), (0.18, T["mint"], 0.85),
        (0.5, T["cyan"], 0.7), (0.82, T["amber"], 0.5), (1, T["amber"], 0),
    ]))
    p.append(lin_grad("bsweep", [
        (0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.85), (1, "#FFFFFF", 0),
    ]))
    p.append(lin_grad("bline", [(0, T["mint"], 0.7), (0.5, T["cyan"], 0.5),
                                (1, T["cyan"], 0.05)]))
    p.append(rad_grad("bglowA", T["mint"], 0.20 if theme == "dark" else 0.10))
    p.append(rad_grad("bglowB", T["amber"], 0.16 if theme == "dark" else 0.08))
    p.append(
        f'<pattern id="bdots" width="24" height="24" patternUnits="userSpaceOnUse">'
        f'<circle cx="1.6" cy="1.6" r="1.1" fill="{T["grid_dot"]}" '
        f'fill-opacity="{0.13 if theme == "dark" else 0.16}"/></pattern>'
    )
    p.append("</defs>")

    # ground
    p.append(rect(0, 0, W, H, rx=24, fill="url(#bgbg)"))
    p.append(rect(0, 0, W, H, rx=24, fill="url(#bdots)"))
    p.append(
        f'<ellipse cx="180" cy="40" rx="360" ry="220" fill="url(#bglowA)"/>'
        f'<ellipse cx="900" cy="240" rx="320" ry="200" fill="url(#bglowB)"/>'
    )
    p.append(rect(0, 0, W - 0.5, H - 0.5, rx=24, stroke=T["stroke"], sw=1))
    # inner top light
    p.append(rect(1, 1, W - 2, 1, fill=T["text"],
                  opacity=0.06 if theme == "dark" else 0.5))

    # monogram tile
    tx, ty, ts = 56, 70, 104
    p.append(rect(tx, ty, ts, ts, rx=28, fill=T["mint"],
                  opacity=0.10 if theme == "dark" else 0.08,
                  stroke=T["mint"], sw=1.2, stroke_opacity=0.42))
    p.append(t(tx + ts / 2, ty + 74, "寰", size=54, weight=800,
               fill="url(#bname)", anchor="middle"))

    # name block
    p.append(t(190, 124, cfg.BANNER["name"], size=58, weight=800,
               fill="url(#bname)"))
    p.append(t(192, 156, f'{cfg.BANNER["latin"]} · {cfg.BANNER["role"]}',
               size=12, weight=700, fill=T["muted"], spacing=2.6))
    p.append(t(192, 194, cfg.BANNER["tagline"], size=17, weight=600,
               fill=T["soft"]))

    # right motif: the four-stage spine, abstracted
    sep_x = 676
    p.append(rect(sep_x, 92, 1, 116, fill=T["stroke2"]))
    nx = [726, 800, 874, 948]
    cy = 150
    p.append(rect(nx[0], cy - 1, nx[-1] - nx[0], 2, rx=1, fill="url(#bline)"))
    for i, x in enumerate(nx):
        col = STAGE_COLORS[i][1] if theme == "dark" else STAGE_COLORS[i][0]
        p.append(circle(x, cy, 8, fill=T["bg0"], opacity=0.9))
        p.append(circle(x, cy, 8, stroke=col, sw=1.6, opacity=0.85))
        p.append(
            f'<circle cx="{n(x)}" cy="{n(cy)}" r="3.4" fill="{col}">'
            f'<animate attributeName="r" values="2.6;4;2.6" dur="2.4s" '
            f'begin="{n(i * 0.35)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.55;1;0.55" dur="2.4s" '
            f'begin="{n(i * 0.35)}s" repeatCount="indefinite"/></circle>'
        )
    for i in range(3):
        p.append(
            f'<circle cx="{n(nx[0])}" cy="{n(cy)}" r="2" fill="{T["mint_soft"]}">'
            f'<animate attributeName="cx" values="{n(nx[0])};{n(nx[-1])}" '
            f'dur="3.6s" begin="{n(i * 1.2)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0.95;0.95;0" '
            f'keyTimes="0;0.1;0.8;1" dur="3.6s" begin="{n(i * 1.2)}s" '
            f'repeatCount="indefinite"/></circle>'
        )

    # bottom rule with travelling highlight
    p.append(rect(40, 230, W - 80, 2, rx=1, fill="url(#brule)"))
    p.append(sweep(40 - 180, 228.5, 180, 5, "bsweep", 5.2))
    p.append("</svg>")
    return "".join(p), H


# ------------------------------------------------------------ asset: typing ---

def asset_typing(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W, H = 1000, 64
    lines = cfg.TYPING
    n_lines = len(lines)
    per = 5.0
    total = per * n_lines
    X0 = 46
    p = [svg_open(W, H, "正在做的事")]
    p.append("<defs>")
    p.append(lin_grad("trule", [(0, T["mint"], 0.6), (1, T["cyan"], 0.1)]))
    p.append("</defs>")
    p.append(rect(0, 0, W, H, rx=16, fill=T["panel"]))
    p.append(rect(0.5, 0.5, W - 1, H - 1, rx=16, stroke=T["stroke"], sw=1))
    # left rail
    p.append(rect(0, 0, 3, H, rx=1.5, fill="url(#trule)"))

    for i, line in enumerate(lines):
        wid = text_width(line, 15, mono=True) + 6
        t_start = i * per
        # the first line starts typing on load; later lines wait their turn
        t_begin = t_start + (0.0 if i == 0 else 0.45)
        kt = [0.0,
              t_begin / total,
              (t_start + 1.55) / total,
              (t_start + 4.20) / total,
              (t_start + 4.40) / total,
              1.0]
        if kt[0] >= kt[1]:
            kt[1] = min(kt[0] + 0.0005, 1.0)
        ktv = ";".join(n(v) for v in kt)
        p.append(f'<clipPath id="tc{i}">')
        # All five lines are drawn at the same spot -- SMIL turns this into a
        # one-line ticker, revealing each in turn. So the static fallback must
        # be ONE line in full: left at 0 the card goes blank without SMIL, and
        # opened up for all five they overprint each other into noise.
        base_w = wid if i == 0 else 0
        p.append(
            f'<rect x="{n(X0)}" y="0" width="{n(base_w)}" height="{n(H)}">'
            f'<animate attributeName="width" dur="{n(total)}s" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{ktv}" '
            f'values="0;0;{n(wid)};{n(wid)};0;0"/></rect></clipPath>'
        )
        p.append(f'<g clip-path="url(#tc{i})">')
        p.append(t(X0, 39, line, size=15, weight=500, fill=T["soft"], mono=True))
        p.append("</g>")
        # cursor tracks the reveal edge
        vis = [0, 1, 1, 1, 0, 0]
        p.append(
            f'<g opacity="0"><animate attributeName="opacity" dur="{n(total)}s" '
            f'repeatCount="indefinite" keyTimes="{ktv}" '
            f'values="{";".join(str(v) for v in vis)}"/><rect x="0" y="19" '
            f'width="9" height="22" rx="2" fill="{T["mint"]}" opacity="1">'
            f'<animate attributeName="x" dur="{n(total)}s" '
            f'repeatCount="indefinite" keyTimes="{ktv}" '
            f'values="{n(X0)};{n(X0)};{n(X0 + wid)};{n(X0 + wid)};'
            f'{n(X0)};{n(X0)}"/>'
            f'<animate attributeName="opacity" values="1;0;1" dur="0.92s" '
            f'repeatCount="indefinite"/></rect></g>'
        )

    # static prompt glyph
    p.append(t(28, 39, "$", size=15, weight=700, fill=T["mint"], mono=True))
    p.append("</svg>")
    return "".join(p), H


# ----------------------------------------------------------- asset: divider ---

def asset_divider(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W, H = 1000, 26
    p = [svg_open(W, H, "")]
    p.append("<defs>")
    p.append(lin_grad("dline", [
        (0, T["mint"], 0), (0.07, T["mint"], 0.85), (0.5, T["cyan"], 0.85),
        (0.9, T["amber"], 0.62), (1, T["amber"], 0),
    ]))
    p.append(lin_grad("dsweep", [(0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.9),
                                 (1, "#FFFFFF", 0)]))
    p.append(rad_grad("dglow", T["mint"], 0.5))
    p.append("</defs>")
    p.append(rect(0, 12, W, 2, rx=1, fill="url(#dline)"))
    for x in (250, 500, 750):
        p.append(circle(x, 13, 7, fill="url(#dglow)"))
        p.append(circle(x, 13, 3.2, fill=T["mint"]))
    p.append(sweep(-180, 10.5, 180, 5, "dsweep", 5.6))
    p.append("</svg>")
    return "".join(p), H


# ------------------------------------------------------------- asset: pills ---

def _pill(
    x: float,
    y: float,
    h: float,
    label: str,
    col: str,
    T: dict,
    *,
    size: float = 12.5,
    dot: bool = True,
    weight: int = 600,
    fill_bg: str | None = None,
) -> tuple[float, str]:
    """Draw one pill at (x, y) and return (width, markup)."""
    tw = text_width(label, size)
    w = tw + 26 + (17 if dot else 0)
    p = [rect(x, y, w, h, rx=h / 2, fill=fill_bg or T["panel_hi"],
              stroke=col, sw=1, stroke_opacity=0.34)]
    cx = x + 13
    if dot:
        p.append(circle(cx + 4.5, y + h / 2, 4.5, fill=col))
        cx += 17
    p.append(t(cx, y + h / 2 + size * 0.36, label, size=size, weight=weight,
               fill=T["soft"]))
    return w, "".join(p)


def asset_tags(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W, H = 1000, 44
    pills = [(lbl, dk if theme == "dark" else lt) for lbl, lt, dk in cfg.TAGS]
    size, ph, gap = 12.5, 30, 12
    widths = [text_width(lbl, size) + 30 for lbl, _ in pills]
    total = sum(widths) + gap * (len(pills) - 1)
    x = (W - total) / 2
    p = [svg_open(W, H, " ".join(lbl for lbl, _ in pills))]
    for (lbl, col), w in zip(pills, widths):
        p.append(rect(x, (H - ph) / 2, w, ph, rx=ph / 2, fill=col,
                      opacity=0.13 if theme == "dark" else 0.10,
                      stroke=col, sw=1, stroke_opacity=0.5))
        p.append(t(x + w / 2, (H - ph) / 2 + ph / 2 + size * 0.36, lbl,
                   size=size, weight=700, fill=col, anchor="middle"))
        x += w + gap
    p.append("</svg>")
    return "".join(p), H


def asset_stack(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W = 1000
    ph, row_gap, first_row_y = 32, 20, 0
    label_w = 166
    size = 12.5
    H = int(first_row_y + ph * 2 + row_gap)
    p = [svg_open(W, H, "技术栈")]
    p.append("<defs>")
    p.append(rad_grad("stglow", T["mint"], 0.09 if theme == "dark" else 0.05))
    p.append("</defs>")
    p.append(rect(0, 0, W, H, rx=18, fill=T["panel"]))
    p.append(rect(0, 0, W, H, rx=18, fill="url(#stglow)"))
    p.append(rect(0.5, 0.5, W - 1, H - 1, rx=18, stroke=T["stroke"], sw=1))
    p.append(rect(label_w, 12, 1, H - 24, fill=T["stroke2"]))
    for r, (label, items) in enumerate(cfg.STACK_ROWS):
        y = first_row_y + r * (ph + row_gap)
        p.append(t(24, y + ph / 2 + 4.5, label, size=13, weight=700,
                   fill=T["muted"]))
        x = label_w + 24
        for name, lt, dk in items:
            col = dk if theme == "dark" else lt
            w = text_width(name, size) + 26 + 17
            if x + w > W - 20:
                break
            _, svg = _pill(x, y, ph, name, col, T, size=size)
            p.append(svg)
            x += w + 10
    p.append("</svg>")
    return "".join(p), H


def asset_footer(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W, H = 1000, 40
    ph, gap, size = 28, 14, 11.5
    items = []
    for key, val, lt, dk in cfg.FOOTER_PILLS:
        items.append((key, val, dk if theme == "dark" else lt))
    widths = [
        text_width(k, size) + 10 + text_width(v, size) + 34
        for k, v, _ in items
    ]
    total = sum(widths) + gap * (len(items) - 1)
    x = (W - total) / 2
    p = [svg_open(W, H, "status")]
    for (key, val, col), w in zip(items, widths):
        p.append(rect(x, (H - ph) / 2, w, ph, rx=ph / 2, fill=T["panel"],
                      stroke=T["stroke"], sw=1))
        cx = x + 14
        p.append(circle(cx + 4, H / 2, 4, fill=col))
        cx += 16
        p.append(t(cx, H / 2 + size * 0.36, key, size=size, weight=600,
                   fill=T["dim"]))
        cx += text_width(key, size) + 10
        p.append(t(cx, H / 2 + size * 0.36, val, size=size, weight=700,
                   fill=col))
        x += w + gap
    p.append("</svg>")
    return "".join(p), H


# -------------------------------------------------------------- asset: hdr ---
HDR_SPECS = {
    "about": ("关于我", "ABOUT", icon_person),
    "pipeline": ("我在做的事", "WHAT I BUILD", icon_pipeline),
    "stack": ("技术栈", "STACK", icon_layers),
    "projects": ("在做的东西", "PROJECTS", icon_grid),
    "stats": ("一些数字", "BY THE NUMBERS", icon_bars),
}


def asset_hdr(theme: str, data: dict, key: str) -> tuple[str, int]:
    T = THEMES[theme]
    cn, en, icon = HDR_SPECS[key]
    W, H = 1000, 92
    p = [svg_open(W, H, cn)]
    p.append("<defs>")
    p.append(lin_grad("hhz", [(0, T["mint"], 1), (0.55, T["cyan"], 1)]))
    p.append(lin_grad("hrule", [
        (0, T["mint"], 0.85), (0.5, T["cyan"], 0.4), (1, T["cyan"], 0),
    ]))
    p.append(lin_grad("hsweep", [(0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.7),
                                 (1, "#FFFFFF", 0)]))
    p.append("</defs>")
    p.append(rect(0, 16, 56, 56, rx=16, fill=T["mint"],
                  opacity=0.10 if theme == "dark" else 0.08,
                  stroke=T["mint"], sw=1.1, stroke_opacity=0.38))
    p.append(icon(0, 16, 56, T["mint"], 2.1))
    p.append(t(76, 47, cn, size=30, weight=800, fill="url(#hhz)"))
    p.append(t(78, 68, en, size=11, weight=700, fill=T["dim"], spacing=3.2))
    p.append(rect(0, 89, W, 2, rx=1, fill="url(#hrule)"))
    p.append(sweep(-220, 87.5, 220, 5, "hsweep", 5.0))
    p.append("</svg>")
    return "".join(p), H


# --------------------------------------------------------- asset: terminal ---

def asset_terminal(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W = 1000
    line_h, size = 23, 14
    y0 = 76
    H = int(y0 + line_h * (len(cfg.TERMINAL_LINES) - 1) + 30)
    p = [svg_open(W, H, "终端名片")]
    p.append("<defs>")
    p.append(lin_grad_v("tbar", [(0, T["panel_hi"], 0.95), (1, T["panel_hi"], 0.4)]))
    p.append(lin_grad("tsweep", [(0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.5),
                                 (1, "#FFFFFF", 0)]))
    p.append("</defs>")
    p.append(rect(0, 0, W, H, rx=18, fill=T["panel"]))
    p.append(rect(0, 0, W, 44, rx=18, fill="url(#tbar)"))
    p.append(rect(0, 26, W, 18, fill="url(#tbar)"))
    p.append(rect(0.5, 0.5, W - 1, H - 1, rx=18, stroke=T["stroke"], sw=1))
    p.append(rect(0, 43.5, W, 1, fill=T["stroke2"]))
    for i, col in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        p.append(circle(30 + i * 22, 22, 6, fill=col, opacity=0.9))
    p.append(t(W / 2, 27, cfg.TERMINAL_TITLE, size=12, weight=600,
               fill=T["dim"], anchor="middle", mono=True))
    p.append(rect(44, 0, 1, 44, fill=T["stroke2"]))

    for i, (kind, body) in enumerate(cfg.TERMINAL_LINES):
        y = y0 + i * line_h
        if kind == "prompt":
            p.append(t(32, y, "$", size=size, weight=700, fill=T["mint"], mono=True))
            p.append(t(50, y, body, size=size, weight=600, fill=T["text"],
                       mono=True))
        else:
            col = T["mint_soft"] if kind == "ok" else T["muted"]
            p.append(t(50, y, body, size=size, weight=400, fill=col, mono=True))

    last_y = y0 + (len(cfg.TERMINAL_LINES) - 1) * line_h
    last_text = cfg.TERMINAL_LINES[-1][1]
    cx = 50 + text_width(last_text, size, mono=True) + 6
    p.append(
        f'<rect x="{n(cx)}" y="{n(last_y - 12)}" width="9" height="17" rx="2" '
        f'fill="{T["mint"]}">'
        f'<animate attributeName="opacity" values="1;0;1" dur="1.05s" '
        f'repeatCount="indefinite"/></rect>'
    )
    p.append("</svg>")
    return "".join(p), H


# --------------------------------------------------------- asset: pipeline ---

def asset_pipeline(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W = 1000
    card_w, gap = 230, 26
    cy0, card_h = 16, 155
    H = cy0 + card_h + 19
    p = [svg_open(W, H, "采集 · 整理 · 加工 · 分发")]
    p.append("<defs>")
    for i in range(4):
        col = STAGE_COLORS[i][1] if theme == "dark" else STAGE_COLORS[i][0]
        p.append(lin_grad(f"pg{i}", [(0, col, 1), (1, col, 0.55)]))
        p.append(rad_grad(f"pgl{i}", col, 0.16 if theme == "dark" else 0.10))
    p.append(lin_grad("psweep", [(0, "#FFFFFF", 0), (0.5, "#FFFFFF", 0.85),
                                 (1, "#FFFFFF", 0)]))
    p.append("</defs>")

    xs = [1 + i * (card_w + gap) for i in range(4)]
    stage_mid_y = cy0 + card_h / 2

    # connectors first so cards paint over their ends
    for i in range(3):
        x_start = xs[i] + card_w + 5
        x_end = xs[i + 1] - 5
        mid = (x_start + x_end) / 2
        col = STAGE_COLORS[i + 1][1] if theme == "dark" else STAGE_COLORS[i + 1][0]
        p.append(rect(x_start, stage_mid_y - 1, (x_end - x_start) * 0.55, 2,
                      rx=1, fill=T["stroke"]))
        p.append(path(
            f"M{n(mid - 2)} {n(stage_mid_y - 5.5)} L{n(mid + 3.5)} "
            f"{n(stage_mid_y)} L{n(mid - 2)} {n(stage_mid_y + 5.5)}",
            stroke=col, sw=2, opacity=0.85))
        p.append(
            f'<circle cx="{n(x_start)}" cy="{n(stage_mid_y)}" r="2.2" '
            f'fill="{col}">'
            f'<animate attributeName="cx" values="{n(x_start)};{n(x_end)}" '
            f'dur="2.6s" begin="{n(i * 0.3)}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" '
            f'keyTimes="0;0.15;0.75;1" dur="2.6s" begin="{n(i * 0.3)}s" '
            f'repeatCount="indefinite"/></circle>'
        )

    for i, stage in enumerate(cfg.PIPELINE):
        x = xs[i]
        col = STAGE_COLORS[i][1] if theme == "dark" else STAGE_COLORS[i][0]
        p.append(rect(x, cy0, card_w, card_h, rx=18, fill=T["panel"]))
        p.append(rect(x, cy0, card_w, card_h, rx=18, fill=f"url(#pgl{i})"))
        p.append(rect(x + 0.5, cy0 + 0.5, card_w - 1, card_h - 1, rx=18,
                      stroke=T["stroke"], sw=1))
        # top accent in the stage colour
        p.append(
            f'<clipPath id="pc{i}"><rect x="{n(x)}" y="{n(cy0)}" '
            f'width="{n(card_w)}" height="{n(card_h)}" rx="18"/></clipPath>'
        )
        p.append(f'<g clip-path="url(#pc{i})">'
                 + rect(x, cy0, card_w, 3, fill=col)
                 + sweep(x - card_w, cy0, card_w, 3, "psweep", 6.0 + i * 0.5)
                 + "</g>")
        p.append(
            f'<text x="{n(x + card_w - 18)}" y="{n(cy0 + 30)}" '
            f'font-family="{MONO}" font-size="11" font-weight="700" '
            f'fill="{T["dim"]}" text-anchor="end" letter-spacing="1">'
            f'0{i + 1}</text>'
        )
        PIPELINE_ICONS[stage["icon"]](x + 18, cy0 + 20, 34, col, 2.0)
        p.append(t(x + 64, cy0 + 40, stage["name"], size=21, weight=800, fill=col))
        p.append(t(x + 65, cy0 + 56, stage["latin"], size=9, weight=700,
                   fill=T["dim"], spacing=2.0))
        p.append(rect(x + 18, cy0 + 72, card_w - 36, 1, fill=T["stroke2"]))

        # chips: first spans the row, the other two sit side by side
        rows = [[stage["chips"][0]], stage["chips"][1:]]
        for r, row in enumerate(rows):
            cx = x + 18
            for chip in row:
                cw = text_width(chip, 11) + 22
                cw = min(cw, card_w - 36)
                cht = 24
                cyd = cy0 + 86 + r * 33
                p.append(rect(cx, cyd, cw, cht, rx=12, fill=T["panel_hi"],
                              stroke=col, sw=1, stroke_opacity=0.34))
                p.append(t(cx + cw / 2, cyd + 16, chip, size=11, weight=600,
                           fill=T["muted"], anchor="middle"))
                cx += cw + 9
    p.append("</svg>")
    return "".join(p), H


# ------------------------------------------------------------- asset: lang ---

def asset_lang(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W = 1000
    langs = data.get("languages") or {}
    total = sum(langs.values()) or 1
    ranked = sorted(langs.items(), key=lambda kv: -kv[1])
    top = ranked[:7]
    rest = sum(v for _, v in ranked[7:])
    if rest:
        top.append(("其他", rest))
    # merge anything below 1% into 其他 so the legend stays honest but short
    bar_y, bar_h = 8, 24
    H = 96
    p = [svg_open(W, H, "代码语言构成")]
    p.append(
        f'<clipPath id="lclip"><rect x="0" y="{n(bar_y)}" width="{n(W)}" '
        f'height="{n(bar_h)}" rx="{n(bar_h / 2)}"/></clipPath>'
    )
    p.append(rect(0, bar_y, W, bar_h, rx=bar_h / 2, fill=T["track"]))
    p.append('<g clip-path="url(#lclip)">')
    x = 0.0
    for i, (name, val) in enumerate(top):
        w = W * val / total
        if i == len(top) - 1:
            w = W - x  # absorb rounding
        col = lang_color(name, theme)
        p.append(rect(x, bar_y, max(w, 1), bar_h, fill=col))
        p.append(rect(x, bar_y, max(w, 1), 1.5, rx=0.75, fill="#FFFFFF",
                      opacity=0.16 if theme == "dark" else 0.32))
        if i:
            p.append(rect(x - 0.75, bar_y, 1.5, bar_h, fill=T["panel"]))
        x += w
    p.append("</g>")
    p.append(rect(0.5, bar_y + 0.5, W - 1, bar_h - 1, rx=bar_h / 2 - 0.5,
                  stroke=T["stroke"], sw=1))

    # legend, one row if it fits, otherwise two
    items = []
    for name, val in top:
        items.append((name, val / total, lang_color(name, theme)))
    size = 11.5
    gapx = 26
    widths = [16 + text_width(nm, size) + 8 + text_width(f"{v * 100:.1f}%", size)
              for nm, v, _ in items]
    rows: list[list[int]] = [[]]
    xs = 0.0
    for i, w in enumerate(widths):
        if xs + w > W and rows[-1]:
            rows.append([])
            xs = 0.0
        rows[-1].append(i)
        xs += w + gapx
    for r, idxs in enumerate(rows):
        cx = 2.0
        for i in idxs:
            name, val, col = items[i]
            y = bar_y + bar_h + 26 + r * 22
            p.append(circle(cx + 4, y - 4, 4, fill=col))
            p.append(t(cx + 16, y, name, size=size, weight=600, fill=T["text"]))
            cx += 16 + text_width(name, size) + 8
            p.append(t(cx, y, f"{val * 100:.1f}%", size=size, weight=400,
                       fill=T["muted"], mono=True))
            cx += text_width(f"{val * 100:.1f}%", size, mono=True) + gapx
    p.append("</svg>")
    return "".join(p), H


# ------------------------------------------------------------ asset: stats ---

def asset_stats(theme: str, data: dict) -> tuple[str, int]:
    T = THEMES[theme]
    W, H = 1000, 116
    s = data["stats"]
    latest = (s.get("latest_push") or "")[:10]
    cells = [
        (str(data["public_repos"]), "公开仓库"),
        (str(s["own_repos"]), "原创项目"),
        (str(s["total_stars"]), "累计 Star"),
        (latest or "—", "最近提交"),
    ]
    p = [svg_open(W, H, "一些数字")]
    p.append("<defs>")
    p.append(lin_grad("svgrad", [(0, T["amber"], 1), (0.62, T["mint"], 1),
                                 (1, T["cyan"], 1)]))
    p.append(rad_grad("svglow", T["mint"], 0.12 if theme == "dark" else 0.07))
    p.append("</defs>")
    p.append(rect(0, 6, W, H - 12, rx=18, fill=T["panel"]))
    p.append(rect(0, 6, W, H - 12, rx=18, fill="url(#svglow)"))
    p.append(rect(0.5, 6.5, W - 1, H - 13, rx=18, stroke=T["stroke"], sw=1))
    for i, (value, label) in enumerate(cells):
        cxc = W / 4 * (i + 0.5)
        vsize = 30 if len(value) <= 8 else 21
        p.append(t(cxc, 60, value, size=vsize, weight=800,
                   fill="url(#svgrad)", anchor="middle"))
        p.append(t(cxc, 86, label, size=12, weight=600, fill=T["muted"],
                   anchor="middle"))
        if i:
            p.append(rect(W / 4 * i, 28, 1, 56, fill=T["stroke2"]))
    p.append("</svg>")
    return "".join(p), H


# ------------------------------------------------------------ asset: proj ---

PROJ_ICONS = {
    "浏览器扩展": icon_grid,
    "排版工作台": icon_doc,
    "Nuxt 3 服务端": icon_server,
    "在线工具集": icon_sliders,
}


def asset_proj(theme: str, data: dict, item: dict) -> tuple[str, int]:
    T = THEMES[theme]
    repo = next((r for r in data["repos"] if r["name"] == item["repo"]), None)
    if repo is None:
        raise SystemExit(f"featured repo not found in profile.json: {item['repo']}")
    W, H = 1000, 136
    p = [svg_open(W, H, repo["name"])]
    p.append("<defs>")
    p.append(lin_grad("prglow", [(0, T["mint"], 0.14 if theme == "dark" else 0.08),
                                 (1, T["cyan"], 0)]))
    p.append(rad_grad("prspot", T["mint"], 0.10 if theme == "dark" else 0.05))
    p.append("</defs>")
    p.append(rect(0, 6, W, H - 12, rx=18, fill=T["panel"]))
    p.append(rect(0, 6, W, H - 12, rx=18, fill="url(#prglow)"))
    p.append(f'<ellipse cx="120" cy="70" rx="260" ry="120" fill="url(#prspot)"/>')
    p.append(rect(0.5, 6.5, W - 1, H - 13, rx=18, stroke=T["stroke"], sw=1))
    p.append(rect(0, 6, 3, H - 12, rx=1.5, fill=T["mint"], opacity=0.55))

    # icon tile
    icon = PROJ_ICONS.get(item["kicker"], icon_grid)
    p.append(rect(24, 40, 56, 56, rx=16, fill=T["mint"],
                  opacity=0.10 if theme == "dark" else 0.07,
                  stroke=T["mint"], sw=1.1, stroke_opacity=0.36))
    p.append(icon(24, 40, 56, T["mint"], 1.9))

    # name + stars
    p.append(t(104, 45, repo["name"], size=19, weight=800, fill=T["text"]))
    stars = repo["stars"]
    star_x = 976 - text_width(str(stars), 14, mono=True) - 18
    p.append(f'<polygon points="{star_points(star_x, 40, 6.4)}" '
             f'fill="{T["amber"]}" opacity="{0.95 if stars else 0.35}"/>')
    p.append(t(976, 45, str(stars), size=14, weight=700, fill=T["amber"],
               anchor="end", mono=True))

    # description -- two lines, so the blurbs are written to fill them
    dl = wrap(item["blurb"], 12.5, 872)[:2]
    for line, by in zip(dl, (73, 92)):
        p.append(t(104, by, line, size=12.5, weight=400, fill=T["muted"]))

    # footer
    lang = repo["language"] or "—"
    p.append(circle(110, 114, 4.5, fill=lang_color(lang, theme)))
    p.append(t(122, 118, lang, size=12, weight=600, fill=T["muted"]))
    kicker = item["kicker"]
    kw = text_width(kicker, 11.5) + 24
    p.append(rect(976 - kw, 104, kw, 23, rx=11.5, fill=T["panel_hi"],
                  stroke=T["mint"], sw=1, stroke_opacity=0.3))
    p.append(t(976 - kw / 2, 119, kicker, size=11.5, weight=600,
               fill=T["muted"], anchor="middle"))
    p.append("</svg>")
    return "".join(p), H


# ------------------------------------------------------------------- main ---

BUILDERS = {
    "banner": lambda th, d: asset_banner(th, d),
    "typing": lambda th, d: asset_typing(th, d),
    "tags": lambda th, d: asset_tags(th, d),
    "divider": lambda th, d: asset_divider(th, d),
    "terminal": lambda th, d: asset_terminal(th, d),
    "pipeline": lambda th, d: asset_pipeline(th, d),
    "stack": lambda th, d: asset_stack(th, d),
    "lang": lambda th, d: asset_lang(th, d),
    "stats": lambda th, d: asset_stats(th, d),
    "footer": lambda th, d: asset_footer(th, d),
}
for _k in HDR_SPECS:
    BUILDERS[f"hdr-{_k}"] = (
        lambda th, d, _key=_k: asset_hdr(th, d, _key)
    )
for _i, _item in enumerate(cfg.FEATURED):
    BUILDERS[f"proj-{_i}"] = (
        lambda th, d, _it=_item: asset_proj(th, d, _it)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma separated asset names")
    args = ap.parse_args()

    data = json.loads(PROFILE.read_text(encoding="utf-8"))
    ASSETS.mkdir(parents=True, exist_ok=True)
    wanted = {s for s in args.only.split(",") if s} or set(BUILDERS)

    # a stale asset is worse than a missing one: wipe before regenerating
    if not args.only:
        for old in ASSETS.glob("*.svg"):
            old.unlink()

    written = 0
    for name, build in BUILDERS.items():
        if name not in wanted:
            continue
        for theme in ("dark", "light"):
            body, h = build(theme, data)
            out = ASSETS / f"{name}-{theme}.svg"
            out.write_text(body, encoding="utf-8")
            written += 1
    print(f"wrote {written} svg files into {ASSETS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
