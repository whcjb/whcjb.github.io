#!/usr/bin/env python3
"""
Local-only sermon manuscript fetcher.

Pulls comments from the BRC YouTube channel using yt-dlp, identifies the
uploader's long-form comments (which are the sermon manuscript split across
multiple comments due to YouTube's per-comment char limit), and saves them
concatenated as plain text files under ~/Documents/sermons_brc/.

For personal study use. Output stays on local filesystem; nothing is published.

Usage:
    python3 /tmp/fetch_brc_sermons.py [N_VIDEOS]
"""

from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from pathlib import Path

YT_DLP = "/Users/yanpeifa/labelme-env/bin/yt-dlp"
CHANNEL = "https://www.youtube.com/@biblereformedchurch4112/videos"
OUT_DIR = Path.home() / "Documents" / "sermons_brc"
TMP_DIR = Path("/tmp/brc_sermons_tmp")
UPLOADER_HANDLE = "@biblereformedchurch4112"
MIN_MANUSCRIPT_CHARS = 1500  # threshold for "long-form uploader comment"

# Map common book name keywords found in titles → directory slugs
BOOK_KEYWORDS = {
    "創世記": "01-创世记", "出埃及記": "02-出埃及记", "利未記": "03-利未记",
    "民數記": "04-民数记", "申命記": "05-申命记", "約書亞記": "06-约书亚记",
    "士師記": "07-士师记", "路得記": "08-路得记",
    "撒母耳記上": "09-撒母耳记上", "撒母耳記下": "10-撒母耳记下",
    "列王紀上": "11-列王纪上", "列王紀下": "12-列王纪下",
    "歷代志上": "13-历代志上", "歷代志下": "14-历代志下",
    "以斯拉記": "15-以斯拉记", "尼希米記": "16-尼希米记",
    "以斯帖記": "17-以斯帖记", "約伯記": "18-约伯记",
    "詩篇": "19-诗篇", "箴言": "20-箴言", "傳道書": "21-传道书",
    "雅歌": "22-雅歌", "以賽亞書": "23-以赛亚书",
    "耶利米書": "24-耶利米书", "耶利米哀歌": "25-耶利米哀歌",
    "以西結書": "26-以西结书", "但以理書": "27-但以理书",
    "何西阿書": "28-何西阿书", "約珥書": "29-约珥书", "阿摩司書": "30-阿摩司书",
    "俄巴底亞書": "31-俄巴底亚书", "約拿書": "32-约拿书", "彌迦書": "33-弥迦书",
    "那鴻書": "34-那鸿书", "哈巴谷書": "35-哈巴谷书",
    "西番雅書": "36-西番雅书", "哈該書": "37-哈该书",
    "撒迦利亞書": "38-撒迦利亚书", "瑪拉基書": "39-玛拉基书",
    "馬太福音": "40-马太福音", "馬可福音": "41-马可福音",
    "路加福音": "42-路加福音", "約翰福音": "43-约翰福音",
    "使徒行傳": "44-使徒行传", "羅馬書": "45-罗马书",
    "哥林多前書": "46-哥林多前书", "哥林多後書": "47-哥林多后书",
    "加拉太書": "48-加拉太书", "以弗所書": "49-以弗所书",
    "腓立比書": "50-腓立比书", "歌羅西書": "51-歌罗西书",
    "帖撒羅尼迦前書": "52-帖撒罗尼迦前书", "帖撒羅尼迦後書": "53-帖撒罗尼迦后书",
    "提摩太前書": "54-提摩太前书", "提摩太後書": "55-提摩太后书",
    "提多書": "56-提多书", "腓利門書": "57-腓利门书",
    "希伯來書": "58-希伯来书", "雅各書": "59-雅各书",
    "彼得前書": "60-彼得前书", "彼得後書": "61-彼得后书",
    "約翰一書": "62-约翰一书", "約翰二書": "63-约翰二书",
    "約翰三書": "64-约翰三书", "猶大書": "65-犹大书",
    "啟示錄": "66-启示录",
    # ─── abbreviated forms (must come AFTER full forms; iteration order matters) ───
    "創": "01-创世记", "出": "02-出埃及记", "利": "03-利未记",
    "民": "04-民数记", "申": "05-申命记", "書": "06-约书亚记",
    "士": "07-士师记", "得": "08-路得记",
    "撒上": "09-撒母耳记上", "撒下": "10-撒母耳记下",
    "王上": "11-列王纪上", "王下": "12-列王纪下",
    "代上": "13-历代志上", "代下": "14-历代志下",
    "拉": "15-以斯拉记", "尼": "16-尼希米记", "斯": "17-以斯帖记",
    "伯": "18-约伯记", "詩": "19-诗篇", "箴": "20-箴言",
    "傳": "21-传道书", "歌": "22-雅歌", "賽": "23-以赛亚书",
    "耶": "24-耶利米书", "哀": "25-耶利米哀歌",
    "結": "26-以西结书", "但": "27-但以理书",
    "何": "28-何西阿书", "珥": "29-约珥书", "摩": "30-阿摩司书",
    "俄": "31-俄巴底亚书", "拿": "32-约拿书", "彌": "33-弥迦书",
    "鴻": "34-那鸿书", "哈": "35-哈巴谷书",
    "番": "36-西番雅书", "該": "37-哈该书",
    "亞": "38-撒迦利亚书", "瑪": "39-玛拉基书",
    "太": "40-马太福音", "可": "41-马可福音",
    "路": "42-路加福音", "約": "43-约翰福音",
    "徒": "44-使徒行传", "羅": "45-罗马书",
    "林前": "46-哥林多前书", "林後": "47-哥林多后书",
    "加": "48-加拉太书", "弗": "49-以弗所书",
    "腓": "50-腓立比书", "西": "51-歌罗西书",
    "帖前": "52-帖撒罗尼迦前书", "帖後": "53-帖撒罗尼迦后书",
    "提前": "54-提摩太前书", "提後": "55-提摩太后书",
    "多": "56-提多书", "門": "57-腓利门书",
    "來": "58-希伯来书", "雅": "59-雅各书",
    "彼前": "60-彼得前书", "彼後": "61-彼得后书",
    "約壹": "62-约翰一书", "約貳": "63-约翰二书",
    "約叄": "64-约翰三书", "猶": "65-犹大书",
    "啟": "66-启示录",
}


def safe_name(s: str) -> str:
    s = re.sub(r"[/\\:*?\"<>|]", "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120]


def parse_title(title: str) -> dict:
    """Extract date, sermon-title, book, ch:verse from a video title like
    '聖經歸正教會 主日證道 5/24/2026 因著信: 亞伯拉罕和撒拉, 希伯來書11:8-12'."""
    out: dict = {"raw": title}
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", title)
    if m:
        mm, dd, yy = m.groups()
        out["date"] = f"{yy}-{int(mm):02d}-{int(dd):02d}"
    else:
        out["date"] = "unknown"
    # Strip leading channel name + 主日證道 + date
    after = re.sub(r"^.*?\d{1,2}/\d{1,2}/\d{4}\s*", "", title)
    # Split on the last "," — convention: "<topic>, <书卷ch:vv>"
    parts = after.rsplit(",", 1)
    if len(parts) == 2:
        out["topic"] = parts[0].strip()
        ref = parts[1].strip()
    else:
        out["topic"] = after.strip()
        ref = ""
    out["ref"] = ref
    # Identify book in ref or topic
    out["book_slug"] = "_uncategorized"
    for keyword, slug in BOOK_KEYWORDS.items():
        if keyword in ref or keyword in after:
            out["book_slug"] = slug
            break
    # Extract ch:verse
    cv = re.search(r"(\d+)\s*[:：]\s*([\d\-－,]+)", ref)
    if cv:
        out["ch"] = int(cv.group(1))
        out["verses"] = cv.group(2)
    return out


def list_videos(n: int) -> list[dict]:
    res = subprocess.run(
        [YT_DLP, "--flat-playlist", "--dump-json", "--playlist-end", str(n), CHANNEL],
        capture_output=True, text=True, timeout=180,
    )
    if res.returncode != 0:
        print(f"yt-dlp video list failed:\n{res.stderr[:600]}", file=sys.stderr)
        return []
    out = []
    for line in res.stdout.splitlines():
        if not line.strip(): continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def fetch_comments(video_id: str) -> list[dict]:
    """Use yt-dlp to fetch comments → returns list of {text, author, length}."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    info_path = TMP_DIR / f"{video_id}.info.json"
    if info_path.exists():
        info_path.unlink()
    res = subprocess.run(
        [
            YT_DLP, "--skip-download", "--write-info-json", "--write-comments",
            "--no-write-thumbnail",
            "--extractor-args", "youtube:max_comments=all,200,all,200;comment_sort=top",
            "-o", f"{TMP_DIR}/%(id)s.%(ext)s",
            f"https://www.youtube.com/watch?v={video_id}",
        ],
        capture_output=True, text=True, timeout=240,
    )
    if not info_path.exists():
        print(f"  [warn] no info.json for {video_id}: {res.stderr[-300:]}", file=sys.stderr)
        return []
    with info_path.open(encoding="utf-8") as f:
        data = json.load(f)
    comments = data.get("comments") or []
    return comments


def select_manuscript_pieces(comments: list[dict]) -> list[dict]:
    """Filter to long uploader comments, sorted by original posting order
    (which YouTube tends to put oldest-of-thread first)."""
    pieces = []
    for c in comments:
        text = c.get("text", "") or ""
        if len(text) < MIN_MANUSCRIPT_CHARS:
            continue
        is_uploader = c.get("author_is_uploader", False) or c.get("author") == UPLOADER_HANDLE
        if not is_uploader:
            continue
        pieces.append(c)
    # Sort by timestamp ascending if available, else preserve incoming order
    pieces.sort(key=lambda c: c.get("timestamp") or 0)
    return pieces


def write_manuscript(meta: dict, pieces: list[dict]) -> Path | None:
    if not pieces:
        return None
    book_dir = OUT_DIR / meta["book_slug"]
    book_dir.mkdir(parents=True, exist_ok=True)
    # filename: {date}_{topic}_{video_id}.txt
    parts = [meta.get("date", "unknown")]
    topic = meta.get("topic", "").strip()
    if topic:
        parts.append(safe_name(topic))
    parts.append(meta["video_id"])
    fname = "_".join(parts) + ".txt"
    out_path = book_dir / fname
    header_lines = [
        f"标题：{meta['raw']}",
        f"日期：{meta.get('date', 'unknown')}",
        f"经文：{meta.get('ref', '')}",
        f"视频：https://www.youtube.com/watch?v={meta['video_id']}",
        f"片段数：{len(pieces)}",
        "—" * 30,
        "",
    ]
    body = []
    for i, c in enumerate(pieces, 1):
        body.append(f"【片段 {i} / {len(pieces)}】")
        body.append(c.get("text", "").rstrip())
        body.append("")
    out_path.write_text("\n".join(header_lines) + "\n".join(body), encoding="utf-8")
    return out_path


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"== listing latest {n} videos ==")
    videos = list_videos(n)
    print(f"got {len(videos)} videos")

    # Idempotent: collect video IDs of sermons already on disk
    # (any .txt under OUT_DIR whose stem ends with `_{video_id}`).
    # YouTube IDs are exactly 11 chars of [A-Za-z0-9_-] and may themselves
    # contain underscores, so split-on-underscore won't work — anchor with
    # a regex at end-of-stem.
    YT_ID_TAIL_RE = re.compile(r"_([A-Za-z0-9_-]{11})$")
    existing: set[str] = set()
    for p in OUT_DIR.rglob("*.txt"):
        m = YT_ID_TAIL_RE.search(p.stem)
        if m:
            existing.add(m.group(1))
    print(f"already have {len(existing)} sermons on disk")

    summary_rows = []
    for i, v in enumerate(videos, 1):
        vid = v["id"]
        title = v.get("title", "")
        meta = parse_title(title)
        meta["video_id"] = vid
        print(f"\n[{i}/{len(videos)}] {vid}  {title[:60]}")
        if vid in existing:
            print(f"  → CACHED (on disk, skipping)")
            summary_rows.append((meta.get("date", "?"), meta["book_slug"], 0, "(cached)"))
            continue
        print(f"  parsed: date={meta.get('date')}  book={meta['book_slug']}  ref={meta.get('ref','')[:30]}")
        comments = fetch_comments(vid)
        print(f"  comments fetched: {len(comments)}")
        pieces = select_manuscript_pieces(comments)
        print(f"  uploader manuscript pieces (≥{MIN_MANUSCRIPT_CHARS} chars): {len(pieces)}")
        out = write_manuscript(meta, pieces)
        total_chars = sum(len(c.get("text", "")) for c in pieces)
        if out:
            print(f"  → {out.relative_to(Path.home())} ({total_chars:,} chars)")
            summary_rows.append((meta["date"], meta["book_slug"], total_chars, str(out.relative_to(Path.home()))))
        else:
            print(f"  → SKIPPED (no qualifying comments)")
            summary_rows.append((meta["date"], meta["book_slug"], 0, "(skipped)"))

    print("\n== summary ==")
    print(f"{'date':<12} {'book':<22} {'chars':>8}  path")
    for d, b, c, p in summary_rows:
        print(f"{d:<12} {b:<22} {c:>8,}  {p}")


if __name__ == "__main__":
    main()
