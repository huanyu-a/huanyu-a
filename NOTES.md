# NOTES — 这个仓库怎么运转

这个仓库是 GitHub **profile 仓库**（仓库名和用户名同名），`README.md` 就是
[github.com/huanyu-a](https://github.com/huanyu-a) 首页显示的内容。

设计参考了 [daniei-chen/daniei-chen](https://github.com/daniei-chen/daniei-chen) 的思路：
**所有视觉素材都是本仓库自绘的 SVG，深浅色各一套，数据由 GitHub Action
每天重新抓取并重绘。**

和参考实现的一处不同：参考仓库的技术栈徽章用的是 shields.io，本仓库连徽章
也是自绘的，因此**整页零外部图片依赖** —— 没有第三方图床，不会因为
shields.io 在国内访问慢而出现裂图。

## 目录

```
README.md                 生成物 —— 不要手改，改 tools/ 里的源
assets/*.svg              生成物 —— 22 个素材 × 深浅 2 套 = 38 个文件
data/profile.json         生成物 —— 抓取到的用户 / 仓库 / 语言字节数
tools/fetch_data.py       抓 GitHub API  -> data/profile.json
tools/profile_config.py   策划内容（文案、项目挑选、技术栈、链路四段）
tools/make_assets.py      读 data + config -> assets/*.svg
tools/make_readme.py      读 data + config -> README.md
tools/render_preview.py   本地预览：走 GitHub 官方 /markdown 接口 + 无头浏览器截图
.github/workflows/update-assets.yml   每天 15:30 (Asia/Shanghai) 自动刷新
```

## 改内容

| 想改什么 | 改哪里 |
|---|---|
| 标语、打字机轮播文案、终端名片 | `tools/profile_config.py` 顶部 |
| 「在做的东西」展示哪 4 个项目、一句话简介 | `tools/profile_config.py` 的 `FEATURED` |
| 链路图的四段与标签 | `tools/profile_config.py` 的 `PIPELINE` |
| 技术栈药丸、顶部标签、页脚徽章 | `tools/profile_config.py` 的 `STACK_ROWS` / `TAGS` / `FOOTER_PILLS` |
| 关于我那段的话术 | `tools/make_readme.py` 的 `build()` 里 about 段 |
| 配色、图标、版式 | `tools/make_assets.py` 顶部的 `THEMES` |

改完重新生成（顺序不能反，`make_assets` 依赖 `fetch_data` 的产物）：

```bash
python tools/fetch_data.py
python tools/make_assets.py
python tools/make_readme.py
```

只想重画某一个素材时用 `--only`：

```bash
python tools/make_assets.py --only banner,divider
```

## 本地预览

`tools/render_preview.py` 会把 `README.md` 交给 **GitHub 官方的 `/markdown`
接口**渲染，再把返回的 HTML 用无头 Chrome 截图 —— 所以看到的就是线上真实排版，
不是本地 Markdown 解析器的近似。

```bash
python tools/render_preview.py            # preview/dark.png + preview/light.png
python tools/render_preview.py --theme dark --width 880
```

两个已知的坑，都已在这个脚本里处理掉：

1. **无头 Chrome 没有操作系统的颜色偏好**，不强制的话
   `prefers-color-scheme` 永远匹配 light，深色主题会拿到浅色素材。
   脚本通过 `--blink-settings=preferredColorScheme=0|1` 强制（0 = 深色，1 = 浅色）。
   `--force-dark-mode` 也能生效，但它会额外触发页面自动反色，所以没用它。
2. **`--virtual-time-budget` 不会推进 SMIL 动画**，所以打字机效果只能截到
   起始帧。要检查某一行文案的宽度是否超出卡片，直接按上面 `--only` 重画后
   看 SVG 更可靠。

`preview/` 已在 `.gitignore` 里，不会被提交。

## SVG 的几条硬约束

在 GitHub README 里显示的 SVG 是当 `<img>` 加载的独立文档，所以：

- **不能用外部字体**（字体文件不会被加载）。全部走系统回退栈，
  并显式列出中文字体（PingFang SC / Microsoft YaHei）。
- **不能跑 JavaScript**。动效一律用 SMIL `<animate>`，它在 `<img>` 语境下有效。
- 动效只是点缀，**去掉动效后信息必须完整**。
- 文字宽度是靠 `make_assets.text_width()` 估算的（CJK 记 1.0 em，ASCII 约 0.55 em）。
  这个估算**故意偏大**：估大了只是留白，估小了会截断文字。

## 数据口径

三处刻意的取舍，都在 `tools/fetch_data.py` 里注释说明了：

- **`ai-docs-mirror` 排除在语言统计之外。** 它是第三方文档的镜像，
  有约 130 MB 的 HTML，不排除的话语言构成条会变成「HTML 93.6%」一根柱子。
- **只展示非 fork 的原创仓库。** `wechat-article-bot`、`GEOFlow`、`panseek`、
  `NavHub` 等是从别人项目 fork 来的（描述也是从上游继承的），
  算进「原创项目」不诚实。`own_repos` 和 `total_stars` 都只统计原创仓库。
- **本仓库自己（用户名同名仓库）也排除在 `own_repos` / 语言统计 / `latest_push` 之外。**
  它是个 meta 仓库，不是作品；而且 Action 每天都会往这里提交，
  算进去的话「最近提交」会永远显示成今天。抓取脚本按「仓库名 == 用户名」识别它。

## 权限

Action 用的是 `secrets.GITHUB_TOKEN`，只对本仓库有效。这里用到的接口
（`/users/{login}`、`/users/{login}/repos`、`/repos/{login}/{name}/languages`）
全是公开数据，所以**不需要配置 PAT**。工作流声明的 `permissions: contents: write`
只为把重绘结果推回仓库。
