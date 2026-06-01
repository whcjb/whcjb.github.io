#!/usr/bin/env python3
"""
Build a password-encrypted, mobile-friendly static page for personal
sermon-study access.

Plaintext sermons in ~/Documents/sermons_brc/ are bundled into a single
JSON, encrypted with AES-256-GCM using a PBKDF2-SHA256 key derived from
a user-supplied passphrase (600 000 iterations, per OWASP 2023), and
written as `bundle.bin` into the chosen output dir under the repo.
Only ciphertext + the password-prompt HTML go into the public repo;
plaintext stays on the user's local disk.

Usage:
    SX_PASSWORD='your-strong-pass' python3 scripts/build_sx_sermons.py \
        --src ~/Documents/sermons_brc \
        --out sx-275b182e

Re-run any time to refresh the bundle (new sermons get included
automatically as long as the source dir is up-to-date).
"""

from __future__ import annotations
import argparse
import base64
import json
import os
import re
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parent.parent

PBKDF2_ITERS = 600_000
SALT_LEN = 16
IV_LEN = 12  # AES-GCM standard
KEY_LEN = 32  # AES-256

HEADER_RE = re.compile(r"^标题：(.*)$", re.MULTILINE)
DATE_RE = re.compile(r"^日期：(.*)$", re.MULTILINE)
REF_RE = re.compile(r"^经文：(.*)$", re.MULTILINE)
VIDEO_RE = re.compile(r"^视频：(.*)$", re.MULTILINE)

# Bible book abbreviations → full traditional names (for display_title)
BOOK_FULL = {
    "創": "創世記", "出": "出埃及記", "利": "利未記", "民": "民數記", "申": "申命記",
    "書": "約書亞記", "士": "士師記", "得": "路得記",
    "撒上": "撒母耳記上", "撒下": "撒母耳記下",
    "王上": "列王紀上", "王下": "列王紀下",
    "代上": "歷代志上", "代下": "歷代志下",
    "拉": "以斯拉記", "尼": "尼希米記", "斯": "以斯帖記",
    "伯": "約伯記", "詩": "詩篇", "箴": "箴言", "傳": "傳道書", "歌": "雅歌",
    "賽": "以賽亞書", "耶": "耶利米書", "哀": "耶利米哀歌",
    "結": "以西結書", "但": "但以理書",
    "何": "何西阿書", "珥": "約珥書", "摩": "阿摩司書", "俄": "俄巴底亞書",
    "拿": "約拿書", "彌": "彌迦書", "鴻": "那鴻書", "哈": "哈巴谷書",
    "番": "西番雅書", "該": "哈該書", "亞": "撒迦利亞書", "瑪": "瑪拉基書",
    "太": "馬太福音", "可": "馬可福音", "路": "路加福音", "約": "約翰福音",
    "徒": "使徒行傳", "羅": "羅馬書",
    "林前": "哥林多前書", "林後": "哥林多後書",
    "加": "加拉太書", "弗": "以弗所書", "腓": "腓立比書", "西": "歌羅西書",
    "帖前": "帖撒羅尼迦前書", "帖後": "帖撒羅尼迦後書",
    "提前": "提摩太前書", "提後": "提摩太後書", "多": "提多書", "門": "腓利門書",
    "來": "希伯來書", "雅": "雅各書",
    "彼前": "彼得前書", "彼後": "彼得後書",
    "約壹": "約翰一書", "約貳": "約翰二書", "約叄": "約翰三書",
    "猶": "猶大書", "啟": "啟示錄",
}


def arabic_to_chinese(n: int) -> str:
    """1 → '一', 11 → '十一', 150 → '一百五十'. Covers all biblical chapter numbers."""
    digits = "零一二三四五六七八九"
    if n < 10:
        return digits[n]
    if n < 20:
        return "十" + (digits[n - 10] if n > 10 else "")
    if n < 100:
        tens, ones = divmod(n, 10)
        return digits[tens] + "十" + (digits[ones] if ones else "")
    # 100..199 only (Psalms max 150)
    hundreds, rest = divmod(n, 100)
    head = (digits[hundreds] if hundreds > 1 else "一") + "百"
    if rest == 0:
        return head
    if rest < 10:
        return head + "零" + digits[rest]
    return head + arabic_to_chinese(rest)


def compute_display_title(raw_title: str) -> str:
    """
    Convert a video title like
        '聖經歸正教會 主日證道 5/24/2026 因著信: 亞伯拉罕和撒拉, 希伯來書11:8-12'
    into the strict format
        '20260524希伯來書十一章8-12因著信: 亞伯拉罕和撒拉'
    (日期YYYYMMDD + 書卷 + 中文章 + 阿拉伯數字節 + 主題)

    Falls back to a partial format if the title doesn't fully match.
    """
    # Date YYYYMMDD
    dm = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw_title)
    yyyymmdd = "00000000"
    if dm:
        mm, dd, yy = dm.groups()
        yyyymmdd = f"{yy}{int(mm):02d}{int(dd):02d}"

    # Strip channel prefix + date to leave "{topic}, {ref}" (best effort)
    after = re.sub(r"^.*?\d{1,2}[/-]\d{1,2}[/-]\d{4}[\s.,]*", "", raw_title)

    # Try to find book+ch:verses at end (after last ',')
    topic = after.strip()
    book_full = ""
    ch_cn = ""
    verses = ""

    # Match book(abbr or full) + chapter digits + (optional :verses)
    # Use the longest-prefix match by checking abbreviations sorted by length desc
    book_candidates = sorted(BOOK_FULL.keys(), key=len, reverse=True) + list(set(BOOK_FULL.values()))
    ref_match = None
    for b in book_candidates:
        pat = re.compile(r"(?:^|[,，\s.])" + re.escape(b) + r"\s*(\d+)\s*[:：]?\s*([\d\-－,，]*)\s*$")
        m = pat.search(after)
        if m:
            ref_match = (b, m.group(1), m.group(2), m.start())
            break

    if ref_match:
        b_key, ch_str, verses_raw, ref_start = ref_match
        book_full = BOOK_FULL.get(b_key, b_key)
        try:
            ch_cn = arabic_to_chinese(int(ch_str)) + "章"
        except ValueError:
            ch_cn = ch_str + "章"
        # Normalize verses: keep digits and dashes/commas
        verses = re.sub(r"[－]", "-", verses_raw).strip(",，")
        # Topic = everything before the matched ref, trimmed of trailing punctuation
        topic = after[: ref_start].rstrip(",，. \t").strip()

    return f"{yyyymmdd}{book_full}{ch_cn}{verses}{topic}"


def load_sermons(src: Path) -> list[dict]:
    out: list[dict] = []
    for p in sorted(src.rglob("*.txt")):
        if "_tools" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        title_m = HEADER_RE.search(text)
        date_m = DATE_RE.search(text)
        ref_m = REF_RE.search(text)
        video_m = VIDEO_RE.search(text)
        sep_idx = text.find("\n—" * 4)
        if sep_idx < 0:
            sep_idx = text.find("———")
        body_start = text.find("\n", sep_idx) + 1 if sep_idx > 0 else 0
        body = text[body_start:].strip() if body_start else text.strip()
        raw_title = title_m.group(1).strip() if title_m else p.stem
        out.append({
            "id": p.stem,
            "book": p.parent.name,
            "title": raw_title,
            "display_title": compute_display_title(raw_title),
            "date": date_m.group(1).strip() if date_m else "",
            "ref": ref_m.group(1).strip() if ref_m else "",
            "video": video_m.group(1).strip() if video_m else "",
            "body": body,
        })
    return out


def encrypt(plaintext: bytes, password: str) -> bytes:
    salt = secrets.token_bytes(SALT_LEN)
    iv = secrets.token_bytes(IV_LEN)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=PBKDF2_ITERS,
    )
    key = kdf.derive(password.encode("utf-8"))
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, plaintext, associated_data=None)
    # Layout: salt | iv | iters(big-endian u32) | ciphertext+tag
    return salt + iv + PBKDF2_ITERS.to_bytes(4, "big") + ct


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta http-equiv="X-Robots-Tag" content="noindex, nofollow, noarchive, nosnippet">
<title>📖</title>
<style>
:root {
    --bg: #f7f5ee;
    --card: #ffffff;
    --text: #2a2014;
    --muted: #8a7d6a;
    --accent: #8b5a2b;
    --border: rgba(139,90,43,0.18);
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #14130f;
        --card: #1d1c18;
        --text: #e8e4d6;
        --muted: #8a8478;
        --accent: #d4a574;
        --border: rgba(212,165,116,0.20);
    }
}
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text); }
body {
    font-family: "LXGW WenKai TC", "PingFang SC", "Songti SC", "Noto Serif SC", serif;
    font-size: 16px; line-height: 1.7;
    padding: max(env(safe-area-inset-top), 12px) 14px max(env(safe-area-inset-bottom), 12px);
    max-width: 760px; margin: 0 auto;
}
@import url('https://fonts.googleapis.com/css2?family=LXGW+WenKai+TC&display=swap');

#auth { display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 60px 0; }
#auth h1 { font-size: 22px; margin: 0; letter-spacing: 0.3em; color: var(--accent); font-weight: 400; }
#auth .lock { font-size: 56px; line-height: 1; opacity: 0.7; }
#auth input {
    width: 100%; max-width: 320px; padding: 12px 14px; font-size: 16px;
    border: 1px solid var(--border); border-radius: 8px; background: var(--card);
    color: var(--text); text-align: center; letter-spacing: 0.1em;
    font-family: ui-monospace, "SF Mono", monospace;
}
#auth button {
    padding: 12px 32px; font-size: 16px; border: none; border-radius: 8px;
    background: var(--accent); color: #fff; cursor: pointer; letter-spacing: 0.2em;
}
#auth button:disabled { opacity: 0.5; cursor: wait; }
#auth #err { color: #c0392b; font-size: 14px; min-height: 20px; text-align: center; }

#app { display: none; }
#search-bar {
    position: sticky; top: 0; z-index: 10; background: var(--bg);
    padding: 10px 0; margin: 0 0 8px; border-bottom: 1px solid var(--border);
}
#search-bar input {
    width: 100%; padding: 10px 14px; font-size: 15px;
    border: 1px solid var(--border); border-radius: 6px;
    background: var(--card); color: var(--text);
}
#stat { font-size: 12px; color: var(--muted); padding: 4px 4px 12px; letter-spacing: 0.1em; }
.book-group { margin-bottom: 24px; }
.book-title {
    font-size: 14px; color: var(--accent); margin: 16px 0 8px;
    padding-left: 8px; border-left: 3px solid var(--accent);
    letter-spacing: 0.15em;
}
.sermon { background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; margin-bottom: 8px; overflow: hidden; }
.sermon summary {
    list-style: none; padding: 12px 14px; cursor: pointer;
    display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
}
.sermon summary::-webkit-details-marker { display: none; }
.sermon summary::before {
    content: '▸'; color: var(--accent); margin-right: 6px;
    transition: transform 0.15s; display: inline-block;
}
.sermon[open] summary::before { transform: rotate(90deg); }
.sermon-topic { flex: 1; font-size: 15px; }
.sermon-meta { font-size: 11px; color: var(--muted); white-space: nowrap; }
.sermon-body {
    padding: 0 16px 16px; font-size: 15.5px; line-height: 1.95;
    white-space: pre-wrap; word-break: break-word;
    border-top: 1px dashed var(--border); padding-top: 12px;
    color: var(--text);
}
.sermon-ref { font-size: 12px; color: var(--accent); padding: 0 16px 4px; letter-spacing: 0.06em; }
.sermon-video { font-size: 11px; padding: 0 16px 8px; }
.sermon-video a { color: var(--muted); text-decoration: none; }
.sermon-video a:hover { text-decoration: underline; }
</style>
</head>
<body>

<div id="auth">
    <div class="lock">🔒</div>
    <h1>個人學習</h1>
    <input id="pwd" type="password" autocomplete="off" autocapitalize="off"
           autocorrect="off" spellcheck="false" inputmode="text"
           placeholder="密碼">
    <button id="go">解 鎖</button>
    <div id="err"></div>
</div>

<div id="app">
    <div id="search-bar"><input id="q" placeholder="搜索 标题 / 经文 / 日期"></div>
    <div id="stat"></div>
    <div id="list"></div>
</div>

<script>
const $ = (id) => document.getElementById(id);

async function deriveKey(password, salt, iterations) {
    const enc = new TextEncoder();
    const baseKey = await crypto.subtle.importKey(
        'raw', enc.encode(password),
        {name: 'PBKDF2'}, false, ['deriveKey']);
    return await crypto.subtle.deriveKey(
        {name: 'PBKDF2', salt, iterations, hash: 'SHA-256'},
        baseKey,
        {name: 'AES-GCM', length: 256},
        false, ['decrypt']);
}

async function unlock(password) {
    const resp = await fetch('bundle.bin', {cache: 'no-store'});
    if (!resp.ok) throw new Error('bundle.bin not found');
    const buf = new Uint8Array(await resp.arrayBuffer());
    const salt = buf.slice(0, 16);
    const iv   = buf.slice(16, 28);
    const iters = new DataView(buf.buffer, 28, 4).getUint32(0, false);
    const ct   = buf.slice(32);
    const key = await deriveKey(password, salt, iters);
    const pt = await crypto.subtle.decrypt({name: 'AES-GCM', iv}, key, ct);
    const json = new TextDecoder('utf-8').decode(pt);
    return JSON.parse(json);
}

function esc(s) {
    return String(s).replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

let DATA = null;

function render(filter) {
    const q = (filter || '').toLowerCase().trim();
    const groups = {};
    let total = 0, shown = 0;
    for (const s of DATA) {
        total++;
        const hay = (s.title + ' ' + s.ref + ' ' + s.date).toLowerCase();
        if (q && !hay.includes(q)) continue;
        (groups[s.book] = groups[s.book] || []).push(s);
        shown++;
    }
    $('stat').textContent = q
        ? `匹配 ${shown} / ${total} 篇`
        : `共 ${total} 篇 · ${Object.keys(groups).length} 卷`;
    const ord = Object.keys(groups).sort();
    const html = ord.map(book => {
        const items = groups[book].sort((a, b) => (b.date || '').localeCompare(a.date || ''));
        return `<div class="book-group">
            <div class="book-title">${esc(book)}</div>
            ${items.map(s => `<details class="sermon">
                <summary>
                    <span class="sermon-topic">${esc(s.display_title)}</span>
                </summary>
                <div class="sermon-ref">${esc(s.ref)}</div>
                <div class="sermon-video"><a href="${esc(s.video)}" target="_blank" rel="noopener noreferrer">▶ 视频</a></div>
                <div class="sermon-body">${esc(s.body)}</div>
            </details>`).join('')}
        </div>`;
    }).join('');
    $('list').innerHTML = html;
}

$('go').addEventListener('click', async () => {
    const btn = $('go'); btn.disabled = true; $('err').textContent = '';
    try {
        DATA = await unlock($('pwd').value);
        $('auth').style.display = 'none';
        $('app').style.display = 'block';
        render('');
    } catch (e) {
        $('err').textContent = '密碼錯誤或文件損毀';
        btn.disabled = false;
    }
});
$('pwd').addEventListener('keydown', e => { if (e.key === 'Enter') $('go').click(); });
$('q').addEventListener('input', e => render(e.target.value));
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path.home() / "Documents" / "sermons_brc")
    ap.add_argument("--out", required=True, help="output dir name under repo root, e.g. sx-275b182e")
    args = ap.parse_args()

    password = os.environ.get("SX_PASSWORD")
    if not password:
        print("error: set SX_PASSWORD env var", file=sys.stderr)
        return 1
    if len(password) < 12:
        print("error: password must be ≥ 12 chars", file=sys.stderr)
        return 1

    src: Path = args.src.expanduser()
    if not src.is_dir():
        print(f"error: src not found: {src}", file=sys.stderr)
        return 1

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    sermons = load_sermons(src)
    print(f"loaded {len(sermons)} sermons from {src}")
    if not sermons:
        return 1

    plaintext = json.dumps(sermons, ensure_ascii=False).encode("utf-8")
    print(f"plaintext: {len(plaintext):,} bytes")

    blob = encrypt(plaintext, password)
    print(f"ciphertext blob: {len(blob):,} bytes (PBKDF2 iters={PBKDF2_ITERS})")

    (out_dir / "bundle.bin").write_bytes(blob)
    (out_dir / "index.html").write_text(HTML_TEMPLATE, encoding="utf-8")
    # Marker file to keep dir present but make Jekyll skip processing inner files
    # by NOT putting it under _-prefixed dirs (we want it published).
    print(f"wrote {out_dir / 'bundle.bin'} and {out_dir / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
