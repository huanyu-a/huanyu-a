#!/usr/bin/env python3
"""Fetch GitHub profile + repository data into data/profile.json.

The token is read from GITHUB_TOKEN (GitHub Actions) and falls back to the
local `gh auth token` for development. Only public data is collected, so the
short-lived Actions token is sufficient -- no PAT is required.

Usage:
    python tools/fetch_data.py            # write data/profile.json
    python tools/fetch_data.py --login=x  # override the profile login
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "profile.json"
API = "https://api.github.com"

DEFAULT_LOGIN = "huanyu-a"

# Repos that exist in the account but must not feed the derived numbers.
# Forks of other people's work never count as own projects; ai-docs-mirror is a
# ~130 MB mirror of third-party docs and would otherwise flatten the language
# bar to a single 93% HTML slab.
EXCLUDE_FROM_STATS = {"Administrative-divisions-of-China"}
EXCLUDE_FROM_LANGUAGES = {"Administrative-divisions-of-China", "ai-docs-mirror"}


def resolve_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=20
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def make_client(token: str | None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "huanyu-a-profile-readme",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    def get(path: str):
        req = urllib.request.Request(f"{API}{path}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    return get


def collect(get, login: str) -> dict:
    user = get(f"/users/{login}")
    if user is None:
        raise SystemExit(f"GitHub user not found: {login}")

    repos: list[dict] = []
    page = 1
    while True:
        batch = get(f"/users/{login}/repos?per_page=100&page={page}&sort=pushed")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    languages: dict[str, int] = {}
    repo_rows: list[dict] = []

    for repo in repos:
        name = repo["name"]
        counted = not repo["fork"] and name not in EXCLUDE_FROM_STATS
        lang_bytes: dict[str, int] = {}
        if counted and name not in EXCLUDE_FROM_LANGUAGES:
            # Cheap enough at this account size; a per-repo language split is
            # far more honest than counting each repo as one language.
            lang_bytes = get(f"/repos/{login}/{name}/languages") or {}
            for lang, size in lang_bytes.items():
                languages[lang] = languages.get(lang, 0) + size

        repo_rows.append(
            {
                "name": name,
                "description": (repo.get("description") or "").strip(),
                "html_url": repo["html_url"],
                "homepage": repo.get("homepage") or "",
                "language": repo.get("language") or "",
                "languages": lang_bytes,
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "topics": repo.get("topics") or [],
                "fork": repo["fork"],
                "archived": repo.get("archived", False),
                "created_at": repo.get("created_at"),
                "pushed_at": repo.get("pushed_at"),
            }
        )

    repo_rows.sort(key=lambda r: (r["stars"], r["pushed_at"] or ""), reverse=True)

    own = [r for r in repo_rows if not r["fork"] and r["name"] not in EXCLUDE_FROM_STATS]
    total_stars = sum(r["stars"] for r in own)
    latest_push = max((r["pushed_at"] or "" for r in own), default="")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "login": user["login"],
        "name": user.get("name") or user["login"],
        "bio": user.get("bio") or "",
        "blog": user.get("blog") or "",
        "location": user.get("location") or "",
        "avatar_url": user.get("avatar_url") or "",
        "created_at": user.get("created_at"),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "stats": {
            "own_repos": len(own),
            "total_stars": total_stars,
            "latest_push": latest_push,
        },
        "languages": languages,
        "repos": repo_rows,
    }


def write_if_changed(out: Path, data: dict) -> bool:
    """Write profile.json, but keep the old timestamp when nothing else moved.

    Without this the daily Action would commit a file whose only difference is
    `generated_at`, which is noise. With it, the timestamp means "when the data
    last actually changed" and a run that changes nothing is a no-op.
    """
    if out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = None
        if prev is not None:
            cur = {k: v for k, v in data.items() if k != "generated_at"}
            old = {k: v for k, v in prev.items() if k != "generated_at"}
            if cur == old and prev.get("generated_at"):
                data["generated_at"] = prev["generated_at"]
                return False

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", default=DEFAULT_LOGIN)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()

    token = resolve_token()
    print(f"token: {'yes' if token else 'no (anonymous, 60 req/h)'}")

    data = collect(make_client(token), args.login)

    out = Path(args.out)
    changed = write_if_changed(out, data)

    s = data["stats"]
    print(
        f"{'wrote' if changed else 'unchanged'} {out.relative_to(ROOT)}: "
        f"{len(data['repos'])} repos, {s['own_repos']} own, "
        f"{s['total_stars']} stars, {len(data['languages'])} languages"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())