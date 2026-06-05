#!/usr/bin/env python3
"""
Inject a per-book custom_style block into each mhenry/<book>/index.html
so the chapter directory page uses that book's water-crystal theme palette.

Source of truth: mhenry/<book>/1.md  — its <style> already encodes the book's
palette.  We extract the relevant tokens via fixed CSS selectors and re-emit
them in the index.html front matter.

Skips books that already have `custom_style:` in their index.html front matter,
so the eight previously hand-tuned palettes (haggai, habakkuk, jonah, malachi,
micah, nahum, zechariah, zephaniah) are not touched.

Two derived colors (very_dark text for the preface button, pale_bg for the
preface button background) are synthesized from the palette:
  very_dark = each channel of text_dark × 0.6
  pale_bg   = pale_base brightened by a fixed offset
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"

# Books with the water-crystal theme already in 1.md
BOOKS = [
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
    "joshua", "judges", "ruth",
    "1samuel", "2samuel", "1kings", "2kings", "1chronicles", "2chronicles",
    "ezra", "nehemiah", "esther",
    "job", "psalms", "proverbs", "ecclesiastes", "songofsolomon",
    "isaiah", "jeremiah", "lamentations", "ezekiel", "daniel",
    "hosea", "joel", "amos", "obadiah",
]

PATTERNS = {
    "gradient":      r"#mhenry-col\s*\{[^}]*background:\s*linear-gradient\(160deg,\s*(#[0-9A-Fa-f]{6})\s+0%,\s*(#[0-9A-Fa-f]{6})\s+30%,\s*(#[0-9A-Fa-f]{6})\s+60%,\s*(#[0-9A-Fa-f]{6})\s+100%",
    "text_dark":     r"\.mh-nav-bar a\s*\{\s*color:\s*(#[0-9A-Fa-f]{6})",
    "text_light":    r"\.mh-expand-tab\s*\{[^}]*color:\s*(#[0-9A-Fa-f]{6})",
    "mid_strong":    r"\.mh-l1\s*\{[^}]*border-left:\s*3px\s+solid\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "strong":        r"\.mh-l1\s*>\s*\.mh-label\s*\{[^}]*background:\s*rgba\((\d+),\s*(\d+),\s*(\d+)",
    "mid_acc":       r"\.mh-l1\s*>\s*\.mh-label\s*\{[^}]*border:\s*1px\s+solid\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "dark_acc":      r"\.mh-l1\s*>\s*\.mh-label\s*\{[^}]*box-shadow:\s*0\s+1px\s+6px\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "strong2":       r"\.mh-footer\s*>?\s*div[^}]*?color:\s*rgba\((\d+),\s*(\d+),\s*(\d+)",
    "light_acc":     r"\.tts-bar\s*\{[^}]*border:\s*1px\s+solid\s+rgba\((\d+),\s*(\d+),\s*(\d+)",
    "pale_base":     r"\.tts-bar\s*\{[^}]*background:\s*rgba\((\d+),\s*(\d+),\s*(\d+)",
    "overview_text": r"\.mh-overview\s*\{[^}]*color:\s*(#[0-9A-Fa-f]{6})",
    "h2_text":       r"#mhenry-col\s*>\s*h2\s*\{[^}]*color:\s*(#[0-9A-Fa-f]{6})",
}


def parse_palette(md_text: str) -> dict:
    out = {}
    for key, pat in PATTERNS.items():
        m = re.search(pat, md_text, re.DOTALL)
        if not m:
            raise RuntimeError(f"selector for {key!r} not found")
        out[key] = m.groups()
    return out


def hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{c:02X}" for c in rgb)


def darken_hex(hex_color: str, factor: float = 0.6) -> str:
    return rgb_to_hex(tuple(max(0, int(c * factor)) for c in hex_to_rgb(hex_color)))


def brighten_rgb(triple, delta=(0, 10, 20)) -> tuple[int, int, int]:
    r, g, b = (int(x) for x in triple)
    return (
        min(255, r + delta[0]),
        min(255, g + delta[1]),
        min(255, b + delta[2]),
    )


CUSTOM_STYLE_TEMPLATE = """custom_style: |
  body {{ background: linear-gradient(160deg, {g1} 0%, {g2} 30%, {g3} 60%, {g4} 100%) !important; min-height: 100vh; }}
  .navbar-default {{ background: rgba(255,255,255,0.30) !important; backdrop-filter: blur(10px) !important; border-bottom: 1px solid rgba({la},0.40) !important; box-shadow: none !important; }}
  .navbar-default .navbar-nav > li > a {{ color: {td} !important; }}
  .navbar-default .navbar-brand {{ color: {td} !important; }}
  .intro-header {{ opacity: 0.85; }}
  .mhenry-chapter-btn--has-content {{ background: rgba(255,255,255,0.38) !important; border: 2px solid rgba({ma},0.65) !important; color: {td} !important; border-radius: 10px !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 2px 8px rgba({da},0.12) !important; backdrop-filter: blur(8px) !important; font-weight: 600 !important; transition: background 0.2s, border-color 0.2s, color 0.2s !important; }}
  .mhenry-chapter-btn--has-content:hover {{ background: rgba({st},0.38) !important; border-color: rgba({s2},0.80) !important; color: {tl} !important; box-shadow: 0 4px 16px rgba({st},0.22) !important; }}
  .mhenry-chapter-btn--preface {{ background: rgba({pb},0.50) !important; border-color: rgba({s2},0.65) !important; color: {vd} !important; }}
  .mhenry-chapter-btn--preface:hover {{ background: rgba({st},0.45) !important; border-color: rgba({st},0.45) !important; color: {tl} !important; }}
  .mh-section-title {{ border-bottom: 2px solid rgba({ms},0.50) !important; color: {h2} !important; }}
  .mh-book-chapters-col {{ background: rgba(255,255,255,0.22); border-radius: 16px; padding: 20px 16px 12px !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.60), 0 4px 24px rgba({da},0.10); backdrop-filter: blur(12px); }}
  footer {{ background: rgba(255,255,255,0.20) !important; backdrop-filter: blur(8px) !important; border-top: 1px solid rgba({la},0.35) !important; }}
  footer .copyright, footer a {{ color: {ot} !important; }}"""


def build_custom_style(pal: dict) -> str:
    g1, g2, g3, g4 = pal["gradient"]
    td = pal["text_dark"][0]
    tl = pal["text_light"][0]
    ot = pal["overview_text"][0]
    h2 = pal["h2_text"][0]

    rgba = lambda key: ",".join(pal[key])
    ms = rgba("mid_strong")
    st = rgba("strong")
    ma = rgba("mid_acc")
    da = rgba("dark_acc")
    s2 = rgba("strong2")
    la = rgba("light_acc")

    pb = ",".join(str(c) for c in brighten_rgb(pal["pale_base"]))
    vd = darken_hex(td, 0.6)

    return CUSTOM_STYLE_TEMPLATE.format(
        g1=g1, g2=g2, g3=g3, g4=g4,
        td=td, tl=tl, ot=ot, h2=h2,
        ms=ms, st=st, ma=ma, da=da, s2=s2, la=la,
        pb=pb, vd=vd,
    )


FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def has_custom_style(index_text: str) -> bool:
    m = FRONT_MATTER_RE.match(index_text)
    return bool(m and "custom_style:" in m.group(1))


def inject(book: str) -> str:
    idx_path = MHENRY / book / "index.html"
    md_path = MHENRY / book / "1.md"
    if not idx_path.exists() or not md_path.exists():
        return f"[skip] {book}: missing files"
    idx_text = idx_path.read_text(encoding="utf-8")
    if has_custom_style(idx_text):
        return f"[skip] {book}: already has custom_style"
    md_text = md_path.read_text(encoding="utf-8")
    try:
        pal = parse_palette(md_text)
    except RuntimeError as e:
        return f"[fail] {book}: {e}"
    css = build_custom_style(pal)
    m = FRONT_MATTER_RE.match(idx_text)
    if not m:
        return f"[fail] {book}: no front matter"
    fm_body = m.group(1).rstrip()
    new_fm = fm_body + "\n" + css + "\n"
    new_text = f"---\n{new_fm}---\n" + idx_text[m.end():]
    idx_path.write_text(new_text, encoding="utf-8")
    return f"[ok] {book}: {len(css)} chars custom_style"


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    only = [a for a in argv[1:] if not a.startswith("--")]
    targets = only if only else BOOKS
    for book in targets:
        if dry:
            md = (MHENRY / book / "1.md").read_text(encoding="utf-8")
            try:
                pal = parse_palette(md)
                css = build_custom_style(pal)
                print(f"[dry-run] {book}: would emit {len(css)} chars")
            except RuntimeError as e:
                print(f"[fail] {book}: {e}")
        else:
            print(inject(book))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
