"""Curated content for the profile README.

Everything the generator cannot derive from the GitHub API lives here: the
one-line positioning, the hand-picked project blurbs, and the pipeline story.
Editing this file is how you retune the profile without touching the SVG code.
"""

# ---------------------------------------------------------------- identity ---

BANNER = {
    "name": "寰宇",
    "latin": "HUANYU",
    "role": "INDEPENDENT DEVELOPER · TOOLSMITH",
    "tagline": "一个人，把想法做成能上线的工具",
}

# Rotating lines under the banner. The "$ " prompt is drawn statically by the
# generator, so it must not be repeated here. Keep each under ~40 CJK chars so
# the typewriter clip never runs past the card edge.
TYPING = [
    "正在把 FavsHub 从浏览器扩展做成 web 工作台",
    "在写 MarkFlow —— Markdown 到公众号长图文的一条龙",
    "白天做医疗健康站点的运营与 SEO，晚上把工具做出来",
    "把踩过的坑沉淀成能复用的方案，而不是一次性脚本",
    "信奉「先做出来，再做好」",
]

# --------------------------------------------------------------- terminal ---
# (kind, text) where kind is one of: prompt | out | dim | ok

TERMINAL_TITLE = "huanyu@github: ~"

TERMINAL_LINES = [
    ("prompt", "whoami"),
    ("ok", "寰宇 · huanyu-a —— 独立开发者，工具匠"),
    ("prompt", "cat focus.txt"),
    ("out", "信息管理 · 内容排版 · 本地优先 · 医疗健康 SEO"),
    ("prompt", "ls ~/projects"),
    ("out", "FavsHub/    FavsHub_web/   MarkFlow/"),
    ("out", "FavsSnap/   toolbox/      wx-auth/"),
    ("prompt", "cat motto.txt"),
    ("ok", "先做出来，再做好。"),
]

# --------------------------------------------------------------- pipeline ---
# The signature graphic: the four-stage chain every tool in this account sits
# on. Keep chips to 6 CJK chars or fewer.

PIPELINE = [
    {
        "latin": "COLLECT",
        "name": "采集",
        # order of glyph presets defined in make_assets.draw_pipeline_icon
        "icon": "inbox",
        "chips": ["文章剪藏", "网页爬虫", "收录推送"],
    },
    {
        "latin": "ORGANIZE",
        "name": "整理",
        "icon": "grid",
        "chips": ["书签导航", "搜索聚合", "Prompt 库"],
    },
    {
        "latin": "CRAFT",
        "name": "加工",
        "icon": "spark",
        "chips": ["Markdown 排版", "AI 生成", "主题模板"],
    },
    {
        "latin": "DISTRIBUTE",
        "name": "分发",
        "icon": "send",
        "chips": ["公众号", "GEO · SEO", "站点运营"],
    },
]

# --------------------------------------------------------------- projects ---
# Only genuine original repos belong here. `repo` must match a non-fork repo
# name from data/profile.json; stars and language are read from the API.

FEATURED = [
    {
        "repo": "FavsHub",
        "kicker": "浏览器扩展",
        "blurb": "把浏览器收藏夹变成可视化卡片网格，聚合约 29 款搜索引擎做多窗口"
        "对比检索，PromptPro 负责提示词管理并支持版本回溯与差异对比。"
        "书签、搜索、提示词三个模块都装在新标签页里，Chrome 与 Edge 都能直接装。",
    },
    {
        "repo": "MarkFlow",
        "kicker": "排版工作台",
        "blurb": "纯前端、零后端的 Markdown / HTML 多场景排版与导出工作台。"
        "与外部 AI 协作，把内容渲染成 A4 正式文档、公众号长图文、小红书图文卡片"
        "或风格化 HTML 画布，再导出为富文本、高清 PNG、矢量 PDF、Word 与 PPT。",
    },
    {
        "repo": "FavsHub_web",
        "kicker": "Nuxt 3 服务端",
        "blurb": "FavsHub 的 SSR web 工作台：卡片式书签主页、搜索引擎聚合、"
        "精选集市场与 PromptPro 一站齐备。同时开放 PAT 与 MCP 两条通道的 AI "
        "数据接口，让 AI 助手直接读写数据，而不是靠截图和粘贴。",
    },
    {
        "repo": "toolbox",
        "kicker": "在线工具集",
        "blurb": "47 款免安装的在线开发 / 运维 / 站长工具：JSON 格式化、代码格式化、"
        "编码转换、加密解密、单位换算、IP 查询、实时汇率等等。"
        "基于 ThinkPHP 构建，所有数据都在浏览器本地处理，打开即用，不上传任何内容。",
    },
]

# Smaller originals, rendered as a compact link list.
MORE = [
    ("FavsSnap_wechat-article-clip_ext", "微信文章剪藏扩展（MV3 侧边栏）"),
    ("FavsSnap_wechat-article-clip", "剪藏工具 Python 版"),
    ("ScriptDeck_Script_Manager", "Windows 脚本启动器"),
    ("wx-auth", "公众号扫码认证系统 · wx-auth-sdk"),
    ("generate_shortcut_poster", "Windows 快捷键速查海报生成"),
    ("gzh-design-skill11", "公众号排版 skill"),
    ("ai-docs-mirror", "AI 技术文档镜像站"),
]

# ------------------------------------------------------------ stack badges ---
# Self-drawn pills -- no shields.io, so the profile has zero external image
# dependencies that could be slow or unreachable. (name, light, dark)

STACK_ROWS = [
    (
        "前端与运行时",
        [
            ("TypeScript", "#3178C6", "#4F93DE"),
            ("JavaScript", "#C9A227", "#F1E05A"),
            ("Vue", "#41B883", "#41D69B"),
            ("Nuxt", "#00A26A", "#00DC82"),
            ("Vite", "#646CFF", "#8B90FF"),
            ("CSS", "#563D7C", "#9B7CC4"),
        ],
    ),
    (
        "服务端与工程",
        [
            ("Python", "#3572A5", "#5C9BD1"),
            ("PHP", "#4F5D95", "#828FCB"),
            ("Node.js", "#4E8A3E", "#5FA04E"),
            ("SQLite", "#2A6A8A", "#4E9BC0"),
            ("Docker", "#2496ED", "#4FB0F5"),
            ("Git", "#C4432B", "#F0654A"),
        ],
    ),
]

# (text, light colour, dark colour)
# The two amber/mint light values are a step deeper than the theme accents on
# purpose: each label sits on a 10% tint of its *own* hue, and that pill eats
# ~0.4 of the ratio, which dropped the plain theme mint to 3.3:1 -- under WCAG
# AA at this text size. All four now clear 4.5:1 against their own pill.
TAGS = [
    ("独立开发者", "#92400E", "#FBBF24"),
    ("医疗健康 · SEO", "#115E59", "#2DD4BF"),
    ("本地优先", "#1D4ED8", "#60A5FA"),
    ("信息管线", "#7C3AED", "#A78BFA"),
]

FOOTER_PILLS = [
    ("status", "building", "#059669", "#34D399"),
    ("PRs", "welcome", "#0284C7", "#38BDF8"),
    ("素材", "自绘 SVG", "#B45309", "#FBBF24"),
]

# ------------------------------------------------------------------ notes ---

FOCUS = [
    ("信息整理", "书签、导航与搜索聚合 —— 让找东西这件事不再靠记忆"),
    ("内容排版", "Markdown 一次写好，输出到 A4 文档、公众号、图文卡片"),
    ("本地优先", "能跑在浏览器和本地的，就不经过第三方服务器"),
    ("AI 可操作", "把数据接口做成一等公民，让 AI 助手直接读写而不是截图粘贴"),
]
