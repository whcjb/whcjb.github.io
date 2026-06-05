#!/usr/bin/env python3
"""
Bootstrap mhenry/ezra/preface.md.

The source PDF (15马太亨利完整圣经注释-以斯拉记.pdf) was originally a corrupted
download (SharePoint error HTML), so ezra was the one OT book with no preface.md.

This script:
  1. Extracts the preface body from PDF page 2 (start: '犹太会众在本书' → end: '第一章').
  2. Copies mhenry/nehemiah/preface.md as a structural template (nehemiah and ezra
     are both green-themed OT historical books; structure is identical).
  3. Rewrites front matter for ezra (book_id / book_name / date).
  4. Replaces the chapter <style> block with ezra's (from mhenry/ezra/1.md).
  5. Maps nehemiah's RGBA palette tokens to ezra's (extracted from same selectors
     in each book's 1.md) inside the preface decoration <style>.
  6. Replaces nehemiah-specific hex text colors (#1A500D, #143D0A, etc.) with
     ezra's equivalents.
  7. Replaces the body <p>…</p> content.
  8. Sets the preface-label to '历史简介'.

After this runs, ezra/preface.md follows the same haggai-style structure as the
other 30 migrated OT prefaces.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path
from datetime import datetime

import fitz  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"
PDF = Path.home() / "Documents/论文/matthew_henry/15马太亨利完整圣经注释-以斯拉记.pdf"

# ── Palette extraction (same regex as theme_book_index.py) ─────────────────
PALETTE_PATTERNS = {
    "gradient":      r"#mhenry-col\s*\{[^}]*background:\s*linear-gradient\(160deg,\s*(#[0-9A-Fa-f]{6})\s+0%,\s*(#[0-9A-Fa-f]{6})\s+30%,\s*(#[0-9A-Fa-f]{6})\s+60%,\s*(#[0-9A-Fa-f]{6})\s+100%",
    "text_dark":     r"\.mh-nav-bar a\s*\{\s*color:\s*(#[0-9A-Fa-f]{6})",
    "h2_text":       r"#mhenry-col\s*>\s*h2\s*\{[^}]*color:\s*(#[0-9A-Fa-f]{6})",
    "overview_text": r"\.mh-overview\s*\{[^}]*color:\s*(#[0-9A-Fa-f]{6})",
    "verse_text":    r"\.mh-unit\s*>\s*\.mh-verse\s*\{[^}]*color:\s*(#[0-9A-Fa-f]{6})",
    "mid_strong":    r"\.mh-l1\s*\{[^}]*border-left:\s*3px\s+solid\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "strong":        r"\.mh-l1\s*>\s*\.mh-label\s*\{[^}]*background:\s*rgba\((\d+),\s*(\d+),\s*(\d+)",
    "mid_acc":       r"\.mh-l1\s*>\s*\.mh-label\s*\{[^}]*border:\s*1px\s+solid\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "dark_acc":      r"\.mh-l1\s*>\s*\.mh-label\s*\{[^}]*box-shadow:\s*0\s+1px\s+6px\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "strong2":       r"\.mh-footer\s*>?\s*div[^}]*?color:\s*rgba\((\d+),\s*(\d+),\s*(\d+)",
    "light_acc":     r"\.tts-bar\s*\{[^}]*border:\s*1px\s+solid\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "pale_base":     r"\.tts-bar\s*\{[^}]*background:\s*rgba\((\d+),\s*(\d+),\s*(\d+)",
}


def parse_palette(md_text: str) -> dict:
    out = {}
    for key, pat in PALETTE_PATTERNS.items():
        m = re.search(pat, md_text, re.DOTALL)
        out[key] = m.groups() if m else None
    return out


# ── PDF extraction (same cleaning as fix_contaminated_prefaces.py) ─────────
def clean_preface_text(raw: str) -> str:
    raw = re.sub(r"马太亨利完整圣经注释[^\n]*\n", "", raw)
    raw = re.sub(r"第\s*\d+\s*页\s*\n", "", raw)
    raw = re.sub(r"\n\d+[^\n]+（\d{3,4}[-－]\d{3,4}）[^\n]*", "", raw)
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    joined = []
    for line in lines:
        if not joined:
            joined.append(line)
            continue
        if joined[-1][-1] in "。！？.!?":
            joined.append(line)
        else:
            joined[-1] = joined[-1] + line
    return "\n".join(joined)


def extract_preface_from_pdf() -> str:
    doc = fitz.open(PDF)
    full = "".join(doc[i].get_text() + "\n" for i in range(len(doc)))
    s = full.find("犹太会众在本书")
    e = full.find("第一章", s)
    if s < 0 or e < 0:
        raise RuntimeError(f"preface anchors not found in PDF (start={s}, end={e})")
    return clean_preface_text(full[s:e])


# ── Style block extraction ─────────────────────────────────────────────────
STYLE_BLOCK_RE = re.compile(r"<style>\s*\n?(.*?)</style>", re.DOTALL)


def extract_style_blocks(text: str) -> list[str]:
    return STYLE_BLOCK_RE.findall(text)


# ── Color substitution ────────────────────────────────────────────────────
def rgba_token(triple) -> str:
    return ",".join(str(c) for c in triple)


def build_color_subs(src_palette: dict, dst_palette: dict) -> list[tuple[str, str]]:
    """
    Build a list of (search, replace) string pairs for substituting source palette
    colors with destination palette colors.

    Order matters: hex codes are case-insensitive but we keep input case. Longer
    strings first to avoid partial overlaps.
    """
    subs: list[tuple[str, str]] = []

    # Hex tokens
    hex_keys = ["text_dark", "h2_text", "overview_text", "verse_text"]
    for k in hex_keys:
        if src_palette.get(k) and dst_palette.get(k):
            subs.append((src_palette[k][0], dst_palette[k][0]))

    # 4 gradient hex
    src_grad = src_palette.get("gradient")
    dst_grad = dst_palette.get("gradient")
    if src_grad and dst_grad:
        for i in range(4):
            subs.append((src_grad[i], dst_grad[i]))

    # RGBA triples
    rgba_keys = [
        "mid_strong", "strong", "mid_acc", "dark_acc",
        "strong2", "light_acc", "pale_base",
    ]
    for k in rgba_keys:
        if src_palette.get(k) and dst_palette.get(k):
            subs.append((rgba_token(src_palette[k]), rgba_token(dst_palette[k])))

    # Sort by source length descending to avoid prefix collisions
    subs.sort(key=lambda p: -len(p[0]))
    return subs


def apply_subs(text: str, subs: list[tuple[str, str]]) -> str:
    """Two-pass substitution: first to placeholders, then to final values, to
    avoid one substitution disturbing the input of another."""
    placeholders = []
    for i, (src, _) in enumerate(subs):
        ph = f"__SUB_{i}__"
        text = text.replace(src, ph)
        placeholders.append((ph, subs[i][1]))
    for ph, dst in placeholders:
        text = text.replace(ph, dst)
    return text


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> int:
    template_path = MHENRY / "nehemiah" / "preface.md"
    ezra_dir = MHENRY / "ezra"
    out_path = ezra_dir / "preface.md"
    one_md = ezra_dir / "1.md"

    if out_path.exists():
        print(f"[abort] {out_path} already exists; refusing to overwrite", file=sys.stderr)
        return 1

    # 1. Extract preface text from PDF
    body = extract_preface_from_pdf()
    print(f"[info] extracted {len(body)} chars of preface text from PDF")

    # 2. Read nehemiah template
    template = template_path.read_text(encoding="utf-8")

    # 3. Read ezra's 1.md (chapter style)
    ezra_md = one_md.read_text(encoding="utf-8")
    nehemiah_md = (MHENRY / "nehemiah" / "1.md").read_text(encoding="utf-8")

    # 4. Build palette substitution table
    src_pal = parse_palette(nehemiah_md)
    dst_pal = parse_palette(ezra_md)
    missing = [k for k, v in dst_pal.items() if v is None]
    if missing:
        raise RuntimeError(f"ezra/1.md missing palette tokens: {missing}")
    subs = build_color_subs(src_pal, dst_pal)
    print(f"[info] {len(subs)} color substitutions prepared")

    # 5. Replace front matter
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    template = re.sub(r"^book_id:.*$", "book_id: ezra", template, count=1, flags=re.MULTILINE)
    template = re.sub(r"^book_name:.*$", "book_name: 以斯拉记", template, count=1, flags=re.MULTILINE)
    template = re.sub(r"^date:.*$", f"date: {now}", template, count=1, flags=re.MULTILINE)
    # header-img: keep nehemiah's category (history) — pick same image family
    template = re.sub(r"^header-img:.*$", "header-img: psalm-bg-44.jpg", template, count=1, flags=re.MULTILINE)

    # 6. Replace the first <style> block (chapter style) with ezra's
    ezra_blocks = extract_style_blocks(ezra_md)
    if not ezra_blocks:
        raise RuntimeError("no <style> block in ezra/1.md")
    ezra_chapter_style = ezra_blocks[0]

    def _replace_first(match):
        return f"<style>\n{ezra_chapter_style}</style>"

    template = STYLE_BLOCK_RE.sub(_replace_first, template, count=1)

    # 7. Apply palette substitutions (affects preface decoration block, etc.)
    #    Note: we already replaced the chapter style block with ezra's, so the
    #    subs run safely against the decoration block (which still has nehemiah palette).
    template = apply_subs(template, subs)

    # 8. Replace book name in title block
    template = template.replace("尼希米记", "以斯拉记")

    # 9. Replace body <p>...</p>
    body_html_lines = [l for l in body.split("\n") if l.strip()]
    new_body = "<br/>".join(body_html_lines)
    template = re.sub(
        r'(<div class="preface-body">\s*\n<p>)(.*?)(</p>\s*\n</div>)',
        lambda m: m.group(1) + new_body + m.group(3),
        template,
        count=1,
        flags=re.DOTALL,
    )

    out_path.write_text(template, encoding="utf-8")
    print(f"[ok] wrote {out_path} ({len(template)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
