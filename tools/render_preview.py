#!/usr/bin/env python3
"""Preview the profile the way GitHub will actually render it.

The README is handed to GitHub's own /markdown endpoint, so what you get back
is the real parse -- <picture>, <table> and all -- not a local guess. The
returned HTML is then served over a throwaway local HTTP server and shot with
headless Chrome, once per colour scheme.

Usage:
    python tools/render_preview.py
    python tools/render_preview.py --width 900 --theme dark
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / "preview"
README = ROOT / "README.md"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

GH_BG = {"dark": "#0d1117", "light": "#ffffff"}
GH_FG = {"dark": "#e6edf3", "light": "#1f2328"}
GH_MUTED = {"dark": "#8b949e", "light": "#59636e"}


def token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok.strip()
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True,
                           text=True, timeout=20)
        if r.returncode == 0:
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def github_markdown(md: str, context: str, attempts: int = 4) -> str:
    """Render markdown through GitHub so the preview matches production.

    The API is reached over TLS from CI and laptops alike, so transient
    handshake timeouts get retried rather than failing the whole preview.
    """
    body = json.dumps({"text": md, "mode": "gfm", "context": context}).encode()
    last: Exception | None = None
    for i in range(attempts):
        req = urllib.request.Request(
            "https://api.github.com/markdown",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "User-Agent": "huanyu-a-profile-readme",
                **({"Authorization": f"Bearer {token()}"} if token() else {}),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            wait = 2 ** i
            print(f"  /markdown attempt {i + 1}/{attempts} failed ({exc}); "
                  f"retrying in {wait}s")
            time.sleep(wait)
    raise SystemExit(f"could not reach the GitHub markdown API: {last}")


def shell(inner: str, theme: str, width: int) -> str:
    # `width` is the content column; the window adds 16px of gutter each side,
    # which is roughly GitHub's own 880px reading column.
    return f"""<!doctype html>
<html data-color-mode="{theme}" data-dark-theme="dark" data-light-theme="light">
<head><meta charset="utf-8"><title>profile preview ({theme})</title>
<style>
  html,body{{margin:0;padding:0;}}
  body{{background:{GH_BG[theme]};color:{GH_FG[theme]};
    color-scheme:{theme};
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',
      'PingFang SC','Microsoft YaHei',Helvetica,Arial,sans-serif;
    font-size:16px;line-height:1.5;}}
  .wrap{{width:{width + 32}px;margin:0 auto;padding:24px 16px 48px;
    box-sizing:border-box;}}
  .markdown-body p{{margin:0 0 16px;}}
  .markdown-body ul{{margin:0 0 16px;padding-left:2em;}}
  .markdown-body li{{margin-top:0.25em;}}
  .markdown-body img{{max-width:100%;box-sizing:content-box;}}
  .markdown-body a{{color:{GH_MUTED[theme]};text-decoration:none;}}
  .markdown-body hr{{border:0;border-bottom:1px solid {GH_MUTED[theme]}33;
    margin:24px 0;}}
  .markdown-body h1,.markdown-body h2{{font-size:1.5em;margin:24px 0 16px;
    padding-bottom:.3em;border-bottom:1px solid {GH_MUTED[theme]}33;}}
  .markdown-body table{{border-collapse:separate;border-spacing:0;
    display:block;width:100%;overflow:auto;}}
  .markdown-body td{{padding:0;}}
  .markdown-body code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:85%;background:{GH_MUTED[theme]}26;padding:.2em .4em;
    border-radius:6px;}}
  .markdown-body strong{{font-weight:600;}}
  .markdown-body details{{margin:0 0 16px;}}
  .markdown-body summary{{cursor:pointer;font-weight:600;}}
</style></head>
<body><div class="wrap"><article class="markdown-body">
{inner}
</article></div></body></html>"""


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    found = shutil.which("chrome") or shutil.which("google-chrome") \
        or shutil.which("chromium") or shutil.which("msedge")
    if found:
        return found
    raise SystemExit("no Chrome/Edge binary found")


def shoot(chrome: str, url: str, out: Path, width: int, height: int,
          scale: float, theme: str, virtual_ms: int = 0) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Headless Chrome has no OS colour preference to inherit, so the media
    # query has to be forced or <source> always resolves to light.
    # preferredColorScheme: 0 = dark, 1 = light, absent = no preference.
    mute = "--blink-settings=preferredColorScheme=" + ("0" if theme == "dark"
                                                       else "1")
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check", mute,
        "--force-device-scale-factor=" + str(scale),
        f"--window-size={width},{height}",
        f"--screenshot={out}", url,
    ]
    if virtual_ms:
        # lets SMIL animations be inspected at a deterministic instant
        cmd.insert(-1, f"--virtual-time-budget={virtual_ms}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists():
        # older builds reject --headless=new for screenshots
        cmd[1] = "--headless"
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists():
        raise SystemExit(f"chrome produced no screenshot:\n{r.stderr[-1500:]}")


def trim(path: Path, bg: str) -> None:
    """Crop the uniform trailing background left by the oversized viewport."""
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(path).convert("RGB")
    want = tuple(int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    w, h = im.size
    px = im.load()
    last = h - 1
    while last > 0:
        row_same = all(px[x, last] == want for x in range(0, w, 7))
        if not row_same:
            break
        last -= 1
    im.crop((0, 0, w, min(h, last + 48))).save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--height", type=int, default=5200)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--theme", default="dark,light")
    ap.add_argument("--virtual-ms", type=int, default=0,
                    help="advance SMIL animations to this instant before "
                         "shooting (e.g. 7500 to catch the typewriter mid-line)")
    ap.add_argument("--context", default="huanyu-a/huanyu-a")
    args = ap.parse_args()

    md = README.read_text(encoding="utf-8")
    html = github_markdown(md, args.context)
    print(f"github /markdown -> {len(html):,} chars of html")

    # the preview pages live one level down, so relative asset paths need ../.
    # a bare "assets/ is safe here because GitHub always emits unquoted-ish
    # src/srcset attributes for repo-relative images.
    for pat in ('src="assets/', 'srcset="assets/'):
        html = html.replace(pat, pat.replace('assets/', '../assets/'))

    PREVIEW.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    port = free_port()
    handler = partial(Quiet, directory=str(ROOT))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)

    try:
        for theme in [t for t in args.theme.split(",") if t]:
            page = PREVIEW / f"{theme}.html"
            page.write_text(shell(html, theme, args.width), encoding="utf-8")
            url = f"http://127.0.0.1:{port}/preview/{theme}.html"
            out = PREVIEW / f"{theme}.png"
            time.sleep(0.2)
            shoot(chrome, url, out, args.width + 32, args.height, args.scale,
                  theme, args.virtual_ms)
            trim(out, GH_BG[theme])
            print(f"wrote {out.relative_to(ROOT)}")
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
