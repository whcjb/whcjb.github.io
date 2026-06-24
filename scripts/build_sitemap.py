#!/usr/bin/env python3
"""生成 sitemap.xml，扫 _site/ 所有可索引页面，lastmod 取自 git log。

用法：
  bundle exec jekyll build
  python3 scripts/build_sitemap.py            # 写到 sitemap.xml
  python3 scripts/build_sitemap.py --check    # 只打印数量和差异，不写文件

输出单一 sitemap.xml，覆盖 robots.txt 中声明的 sitemap。
sitemap-philippians.xml 保留为独立抓取探针（由用户单独提交 GSC）。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "_site"
SITE_URL = "https://whcjb.github.io"
OUT = REPO / "sitemap.xml"

# 路径前缀（相对 _site/）以这些开头的 index.html 不进 sitemap
EXCLUDE_PREFIXES = (
    "sx-275b182e/",     # 私密学习页（robots.txt Disallow）
    "calvin_raw/",      # 原始抽取文本，不发布索引
    "ocr_output/",
    "sermons_brc/",
    "logs/",
    "pages/",           # Jekyll 首页分页 /pages/N/
    "page2/",           # 首页第二页
    "page3/", "page4/", "page5/", "page6/", "page7/", "page8/", "page9/",
    "search/",          # 站内搜索 UI
    "typo-report/",
    "pwa/",
    "cf-worker/",
    "key/",
    "assets/",
    "img/",
    "css/",
    "js/",
    "fonts/",
)

# 文件名精确排除
EXCLUDE_FILES = (
    "404.html",
    "offline.html",
    "feed.xml",
    "sitemap.xml",
    "sitemap_index.xml",
    "sitemap-priority.xml",
    "sitemap-philippians.xml",
    "robots.txt",
    "search.json",
    "sw.js",
    "BingSiteAuth.xml",
    "CNAME",
    "LICENSE",
    "Gemfile", "Gemfile.lock",
)

POST_URL_RE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})/(.+?)/?$")


def url_for(rel: Path) -> str:
    """_site/foo/bar/index.html → https://.../foo/bar/"""
    if rel.name == "index.html":
        parent = rel.parent
        path = "/" if str(parent) == "." else "/" + str(parent) + "/"
    else:
        path = "/" + str(rel)
    # 非 ASCII 部分需要 percent-encode；保留 / 与 -
    encoded = urllib.parse.quote(path, safe="/-_.~")
    return SITE_URL + encoded


def source_for(url_path: str) -> Path | None:
    """根据 URL 路径在仓库中定位源文件（用于 git lastmod 查询）。"""
    p = url_path.strip("/")
    if not p:
        return REPO / "index.html"

    # 博客文章 /YYYY/MM/DD/slug/
    m = POST_URL_RE.match(p)
    if m:
        y, mo, d, slug = m.groups()
        posts = REPO / "_posts"
        for ext in (".md", ".markdown", ".html", ".index"):
            cand = posts / f"{y}-{mo}-{d}-{slug}{ext}"
            if cand.exists():
                return cand
        # CJK 文件名 + 多空格 → 模糊匹配同日期
        matches = list(posts.glob(f"{y}-{mo}-{d}-*"))
        if len(matches) == 1:
            return matches[0]
        return None

    # 普通页面：foo/bar/ → foo/bar.md 或 foo/bar/index.{md,html}
    for ext in (".md", ".markdown", ".html"):
        cand = REPO / f"{p}{ext}"
        if cand.exists() and cand.is_file():
            return cand
    for name in ("index.md", "index.markdown", "index.html"):
        cand = REPO / p / name
        if cand.exists():
            return cand
    return None


def git_lastmod(path: Path) -> str | None:
    try:
        rel = path.relative_to(REPO)
    except ValueError:
        return None
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO), "log", "-1", "--format=%cs", "--", str(rel)],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out or None
    except subprocess.CalledProcessError:
        return None


def collect_urls() -> list[tuple[str, str]]:
    if not SITE.exists():
        sys.exit(f"_site/ 不存在：{SITE}\n请先 `bundle exec jekyll build`")

    fallback = subprocess.check_output(
        ["git", "-C", str(REPO), "log", "-1", "--format=%cs"],
    ).decode().strip()

    urls: list[tuple[str, str]] = []
    seen: set[str] = set()
    no_source = 0

    for root, dirs, files in os.walk(SITE):
        rel_root = Path(root).relative_to(SITE)
        rel_str = "" if str(rel_root) == "." else str(rel_root) + "/"
        if any(rel_str.startswith(pfx) for pfx in EXCLUDE_PREFIXES):
            dirs[:] = []
            continue
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            if f != "index.html":
                continue
            rel = (Path(root) / f).relative_to(SITE)
            url = url_for(rel)
            if url in seen:
                continue
            seen.add(url)
            url_path = url[len(SITE_URL):]
            # 解码回 UTF-8 以匹配仓库源文件
            decoded_path = urllib.parse.unquote(url_path)
            src = source_for(decoded_path)
            lastmod = git_lastmod(src) if src else None
            if not lastmod:
                no_source += 1
                lastmod = fallback
            urls.append((url, lastmod))

    print(f"# 收集到 {len(urls)} 个 URL，{no_source} 个无法定位源文件（用 fallback {fallback}）",
          file=sys.stderr)
    urls.sort()
    return urls


def render(urls: list[tuple[str, str]]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in urls:
        out.append("  <url>")
        out.append(f"    <loc>{url}</loc>")
        out.append(f"    <lastmod>{lastmod}</lastmod>")
        out.append("  </url>")
    out.append('</urlset>')
    out.append('')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只统计，不写文件")
    ap.add_argument("--out", default=str(OUT), help="输出路径（默认 sitemap.xml）")
    args = ap.parse_args()

    urls = collect_urls()
    if args.check:
        # diff 当前 sitemap.xml
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        cur_urls = set(re.findall(r"<loc>([^<]+)</loc>", current))
        new_urls = {u for u, _ in urls}
        added = new_urls - cur_urls
        removed = cur_urls - new_urls
        print(f"current sitemap: {len(cur_urls)} URLs")
        print(f"new sitemap:     {len(new_urls)} URLs")
        print(f"added:   {len(added)}")
        print(f"removed: {len(removed)}")
        if added:
            print("--- sample added ---")
            for u in sorted(added)[:10]:
                print(f"  + {u}")
        if removed:
            print("--- sample removed ---")
            for u in sorted(removed)[:10]:
                print(f"  - {u}")
        return

    xml = render(urls)
    Path(args.out).write_text(xml, encoding="utf-8")
    print(f"wrote {args.out} ({len(urls)} URLs)")


if __name__ == "__main__":
    main()
