#!/usr/bin/env python3
"""Render README.md from data/profile.json + tools/profile_config.py.

House rules that keep the output rendering correctly on GitHub:
  * every image is wrapped in <picture> so dark/light both work
  * HTML blocks never contain blank lines, so CommonMark keeps them raw
  * nothing points outside the repo -- no shields.io, no badges host
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_config as cfg  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "README.md"
PROFILE = ROOT / "data" / "profile.json"


def pic(name: str, alt: str, width: str = "100%", indent: str = "") -> str:
    """A dark/light aware <picture> block for one generated asset."""
    body = (
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" '
        f'srcset="assets/{name}-dark.svg">\n'
        f'  <source media="(prefers-color-scheme: light)" '
        f'srcset="assets/{name}-light.svg">\n'
        f'  <img src="assets/{name}-dark.svg" alt="{alt}" width="{width}">\n'
        "</picture>"
    )
    return indent + body.replace("\n", "\n" + indent) if indent else body


def repo_by_name(data: dict, name: str) -> dict:
    for r in data["repos"]:
        if r["name"] == name:
            return r
    raise SystemExit(f"repo not in profile.json: {name}")


def build(data: dict) -> str:
    s = data["stats"]
    out: list[str] = []

    # ------------------------------------------------------------- header ---
    out.append('<div align="center">')
    out.append("")
    out.append(pic("banner", "寰宇 · HUANYU"))
    out.append("")
    out.append(pic("typing", "正在做的事"))
    out.append("")
    out.append(pic("tags", "独立开发者 · 医疗健康 SEO · 本地优先 · 信息管线"))
    out.append("")
    out.append("</div>")
    out.append("")

    # -------------------------------------------------------------- about ---
    out.append(pic("divider", ""))
    out.append("")
    out.append(pic("hdr-about", "关于我"))
    out.append("")
    out.append("")
    out.append("- **独立开发者** —— 主业做医疗健康方向的站点运营与 SEO，"
               "副业把想用的工具一个个做出来")
    out.append("- **一条链路** —— 采集 → 整理 → 加工 → 分发，找信息、排内容、"
               "发出去，每个环节都留了一个能用的轮子")
    out.append("- **主力技术栈** —— TypeScript / Vue / Nuxt，服务端 "
               "Python / PHP，需要落在本地就交给浏览器和 SQLite")
    out.append("- **本地优先** —— FavsHub 的书签与提示词、toolbox 的 47 款工具，"
               "数据都不经过第三方服务器")
    out.append("- **先做出来，再做好** —— 也喜欢把踩过的坑沉淀成能复用的方案，"
               "而不是一次性脚本")
    out.append(f"- **交流** —— 走 Issue 就行，每个仓库都开着；博客 "
               f"[bx9y.com.cn]({data['blog'].rstrip('/')})")
    out.append("")
    out.append(pic("terminal", "终端名片"))
    out.append("")

    # ----------------------------------------------------------- pipeline ---
    out.append(pic("divider", ""))
    out.append("")
    out.append(pic("hdr-pipeline", "我在做的事"))
    out.append("")
    out.append("")
    out.append(pic("pipeline", "采集 · 整理 · 加工 · 分发"))
    out.append("")

    # -------------------------------------------------------------- stack ---
    out.append(pic("divider", ""))
    out.append("")
    out.append(pic("hdr-stack", "技术栈"))
    out.append("")
    out.append("")
    out.append(pic("stack", "技术栈"))
    out.append("")
    out.append(pic("lang", "代码语言构成"))
    out.append("")

    # ----------------------------------------------------------- projects ---
    out.append(pic("divider", ""))
    out.append("")
    out.append(pic("hdr-projects", "在做的东西"))
    out.append("")
    out.append("")
    for i, item in enumerate(cfg.FEATURED):
        repo = repo_by_name(data, item["repo"])
        stars = repo["stars"]
        out.append("<p align=\"center\">")
        out.append(f'  <a href="{repo["html_url"]}">')
        out.append(pic(f"proj-{i}", repo["name"], "100%", indent="    "))
        out.append("  </a>")
        out.append("</p>")
        out.append("")
    out.append("")

    # --------------------------------------------------------- more repos ---
    out.append("<details>")
    out.append("<summary>还有一些小工具</summary>")
    out.append("")
    for name, blurb in cfg.MORE:
        repo = repo_by_name(data, name)
        out.append(f"- [{name}]({repo['html_url']}) —— {blurb}")
    out.append("")
    out.append("</details>")
    out.append("")

    # --------------------------------------------------------------- stats ---
    out.append(pic("divider", ""))
    out.append("")
    out.append(pic("hdr-stats", "一些数字"))
    out.append("")
    out.append("")
    out.append(pic("stats", "一些数字"))
    out.append("")
    out.append("")
    out.append("上面这张卡片和这个页面的所有素材，都是本仓库自绘的 SVG："
               "没有第三方图床，没有 shields.io，深浅色各一套。"
               f"数据由 GitHub Action 每天自动重新抓取并重绘，"
               f"最后一次更新于 {date.today().isoformat()}。")
    out.append("")
    out.append(f"原创项目 {s['own_repos']} 个，累计 {s['total_stars']} 个 Star。"
               "如果哪个仓库对你有用，点个 ⭐ 就是最好的鼓励。")
    out.append("")
    out.append("<p align=\"center\">")
    out.append(pic("footer", "status building", indent="  "))
    out.append("</p>")
    out.append("")

    # --------------------------------------------------- markdown hygiene ---
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main() -> int:
    data = json.loads(PROFILE.read_text(encoding="utf-8"))
    md = build(data)
    OUT.write_text(md, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(md):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
