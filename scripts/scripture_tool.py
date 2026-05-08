#!/usr/bin/env python3
"""
Scripture lookup and formatting tool for reading chapter files.

Two modes:
  1. INLINE  — Bible quote embedded within a commentary paragraph
               → wrap 「...」（ref） with <span class="scripture-inline">
  2. BLOCK   — Entire paragraph is a standalone Bible quotation
               → replace with <div class="scripture-block"> using 和合本 text
"""
import json, re
from pathlib import Path

# ── Load Bible ─────────────────────────────────────────────────────────────
_BIBLE_PATH = Path(__file__).parent / "zh_cuv.json"
_bible = json.load(open(_BIBLE_PATH, encoding="utf-8-sig"))
_BOOK_BY_ABBR = {b["abbrev"]: b for b in _bible}

# Chinese book abbreviation → internal abbrev
BOOK_MAP = {
    "創":"gn","出":"ex","利":"lv","民":"nm","申":"dt",
    "書":"js","士":"jud","得":"rt",
    "撒上":"1sm","撒下":"2sm","王上":"1kgs","王下":"2kgs",
    "代上":"1ch","代下":"2ch",
    "拉":"ezr","尼":"ne","斯":"et",
    "伯":"job","詩":"ps","箴":"prv","傳":"ec","歌":"so",
    "賽":"is","耶":"jr","哀":"lm","結":"ez","但":"dn",
    "何":"ho","珥":"jl","摩":"am","俄":"ob","拿":"jn",
    "彌":"mi","鴻":"na","哈":"hk","番":"zp","該":"hg",
    "亞":"zc","瑪":"ml",
    "太":"mt","可":"mk","路":"lk","約":"jo",
    "徒":"act","羅":"rm",
    "林前":"1co","林後":"2co",
    "加":"gl","弗":"eph","腓":"ph","西":"cl",
    "帖前":"1ts","帖後":"2ts","提前":"1tm","提後":"2tm",
    "多":"tt","門":"phm","來":"hb",
    "雅":"jm","彼前":"1pe","彼後":"2pe",
    "約壹":"1jo","約貳":"2jo","約參":"3jo",
    "猶":"jd","啟":"re",
}

BOOK_DISPLAY = {
    "gn":"創世記","ex":"出埃及記","lv":"利未記","nm":"民數記","dt":"申命記",
    "js":"約書亞記","jud":"士師記","rt":"路得記","1sm":"撒母耳記上","2sm":"撒母耳記下",
    "1kgs":"列王紀上","2kgs":"列王紀下","1ch":"歷代志上","2ch":"歷代志下",
    "ezr":"以斯拉記","ne":"尼希米記","et":"以斯帖記",
    "job":"約伯記","ps":"詩篇","prv":"箴言","ec":"傳道書","so":"雅歌",
    "is":"以賽亞書","jr":"耶利米書","lm":"耶利米哀歌","ez":"以西結書","dn":"但以理書",
    "ho":"何西阿書","jl":"約珥書","am":"阿摩司書","ob":"俄巴底亞書",
    "jn":"約拿書","mi":"彌迦書","na":"那鴻書","hk":"哈巴谷書",
    "zp":"西番雅書","hg":"哈該書","zc":"撒迦利亞書","ml":"瑪拉基書",
    "mt":"馬太福音","mk":"馬可福音","lk":"路加福音","jo":"約翰福音",
    "act":"使徒行傳","rm":"羅馬書",
    "1co":"哥林多前書","2co":"哥林多後書",
    "gl":"加拉太書","eph":"以弗所書","ph":"腓立比書","cl":"歌羅西書",
    "1ts":"帖撒羅尼迦前書","2ts":"帖撒羅尼迦後書",
    "1tm":"提摩太前書","2tm":"提摩太後書",
    "tt":"提多書","phm":"腓利門書","hb":"希伯來書",
    "jm":"雅各書","1pe":"彼得前書","2pe":"彼得後書",
    "1jo":"約翰一書","2jo":"約翰二書","3jo":"約翰三書",
    "jd":"猶大書","re":"啟示錄",
}

def cn2int(s: str) -> int:
    s = s.strip()
    if re.match(r'^\d+$', s):
        return int(s)
    ones = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
    tens_map = {"十":10,"二十":20,"三十":30,"四十":40,"五十":50,
                "六十":60,"七十":70,"八十":80,"九十":90}
    if s in ones:
        return ones[s]
    m = re.match(r'^([二三四五六七八九]?十)([一二三四五六七八九]?)$', s)
    if m:
        return tens_map.get(m.group(1), 10) + ones.get(m.group(2), 0)
    return 1

def lookup_verses(book_cn: str, ch_str: str, v_start: int, v_end: int):
    abbr  = BOOK_MAP.get(book_cn)
    book  = _BOOK_BY_ABBR.get(abbr) if abbr else None
    if not book:
        return []
    ch = cn2int(ch_str) - 1
    if ch < 0 or ch >= len(book["chapters"]):
        return []
    chapter = book["chapters"][ch]
    return [chapter[v].replace(" ", "")
            for v in range(v_start-1, v_end)
            if 0 <= v < len(chapter)]

def lookup_ref(ref_str: str):
    """
    Parse '羅九20-22' → (book_cn, ch_str, v_start, v_end, [verses], display)
    Returns None if not a valid reference.
    """
    book_cn = None
    for prefix in sorted(BOOK_MAP, key=len, reverse=True):
        if ref_str.startswith(prefix):
            book_cn = prefix
            rest = ref_str[len(prefix):]
            break
    if not book_cn:
        return None
    m = re.match(r'^([一二三四五六七八九十百]+)(\d+)(?:-(\d+))?', rest)
    if not m:
        return None
    ch_str  = m.group(1)
    v_start = int(m.group(2))
    v_end   = int(m.group(3)) if m.group(3) else v_start
    verses  = lookup_verses(book_cn, ch_str, v_start, v_end)
    abbr    = BOOK_MAP.get(book_cn, "")
    name    = BOOK_DISPLAY.get(abbr, book_cn)
    ch_num  = cn2int(ch_str)
    display = f"{name} {ch_num}:{v_start}" if v_start == v_end \
              else f"{name} {ch_num}:{v_start}-{v_end}"
    return (book_cn, ch_str, v_start, v_end, verses, display)

# ── Reference pattern ───────────────────────────────────────────────────────
REF_PAT = re.compile(r'（([^）]{1,20}?)）')

def find_refs(text: str):
    results = []
    for m in REF_PAT.finditer(text):
        r = lookup_ref(m.group(1))
        if r:
            results.append((m, r))
    return results

def _char_overlap(a: str, b: str) -> float:
    sa, sb = set(re.sub(r'\s', '', a)), set(re.sub(r'\s', '', b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

# ── HTML builders ───────────────────────────────────────────────────────────

def make_scripture_block(ref_result) -> str:
    """Standalone block: 和合本 verse text + reference."""
    _, _, _, _, verses, display = ref_result
    if not verses:
        return ""
    lines = "\n".join(f"  <span class='sv'>{v}</span>" for v in verses)
    return (
        f'<div class="scripture-block">\n'
        f'<div class="scripture-text">\n{lines}\n</div>\n'
        f'<div class="scripture-ref">{display}</div>\n'
        f'</div>'
    )

def wrap_inline_quotes(text: str) -> str:
    """
    Wrap 「quoted text」（scripture ref） with <span class="scripture-inline">.
    Also wraps bare quoted text without brackets when followed by （ref）.
    """
    # Pattern 1: 「...」（ref）
    def replace_bracket(m):
        quote = m.group(1)   # text inside 「」
        raw   = m.group(2)   # ref string inside （）
        r = lookup_ref(raw)
        ref_span = f'<span class="scripture-ref-inline">（{raw}）</span>'
        if r:
            ref_span = f'<span class="scripture-ref-inline">（{r[5]}）</span>'
        return f'<span class="scripture-inline">「{quote}」</span>{ref_span}'

    text = re.sub(r'「([^」]{1,300})」（([^）]{1,20})）', replace_bracket, text)

    # Pattern 2: bare reference （ref） not already wrapped — just style the ref
    def replace_bare_ref(m):
        raw = m.group(1)
        r = lookup_ref(raw)
        if r:
            return f'<span class="scripture-ref-inline">（{r[5]}）</span>'
        return m.group(0)

    text = re.sub(r'（([^）]{1,20})）', replace_bare_ref, text)
    return text

# ── Block processor ─────────────────────────────────────────────────────────

def process_block(block: str) -> str:
    if not block.startswith("<p>"):
        return block

    inner = block[3:]
    if inner.endswith("</p>"):
        inner = inner[:-4]

    refs = find_refs(inner)
    if not refs:
        return block

    # ── Check if the whole paragraph is a standalone scripture quote ─────
    # Strategy: find the last reference; check if text before it matches Bible text
    last_match, last_ref = refs[-1]
    _, _, _, _, verses, _ = last_ref
    bible_text = "".join(verses)
    before_last_ref = inner[:last_match.start()].strip()

    # A quote wrapped in 「」 is an inline citation, not a standalone block.
    # Block quotes in Chinese Reformed books are NOT wrapped in 「」 marks.
    # Key heuristic: if before_last_ref ends with a closing quote mark (」or 』),
    # the citation is embedded inline in narrative text.
    stripped_before = before_last_ref.strip()
    is_inline_quoted = bool(re.search(r'[」』][。？！…]*$', stripped_before))

    if verses and before_last_ref and not is_inline_quoted and _char_overlap(before_last_ref, bible_text) > 0.42:
        # Standalone block: find if there is any intro text before the scripture
        # Look for a natural sentence boundary before the quote
        # Heuristic: if before_last_ref starts with 「 it might have intro + quote
        # Try to find the quote start by matching verses against text
        first_verse_chars = verses[0][:8] if verses else ""
        intro_end = before_last_ref.find(first_verse_chars) if first_verse_chars else -1

        if intro_end > 10:
            intro = before_last_ref[:intro_end].strip()
            parts = []
            if intro:
                parts.append(f"<p>{intro}</p>")
            parts.append(make_scripture_block(last_ref))
        else:
            # Check for any leading commentary text before the whole quote
            # If the block is entirely scripture (high overlap from start), emit block
            parts = [make_scripture_block(last_ref)]

        # Append anything after the last ref
        after = inner[last_match.end():].strip()
        if after:
            parts.append(f"<p>{after}</p>")
        return "\n\n".join(p for p in parts if p)

    # ── Inline mode: wrap 「quotes」（refs） with special span ─────────────
    new_inner = wrap_inline_quotes(inner)
    return f"<p>{new_inner}</p>"


def _merge_refs(ref1: str, ref2: str) -> str:
    """Combine two scripture refs if same book+chapter, else join with ；"""
    m1 = re.match(r'^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$', ref1.strip())
    m2 = re.match(r'^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$', ref2.strip())
    if m1 and m2 and m1.group(1) == m2.group(1) and m1.group(2) == m2.group(2):
        v_end = m2.group(4) or m2.group(3)
        return f"{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{v_end}"
    return ref1 + "；" + ref2


def _merge_adjacent_scripture_blocks(html: str) -> str:
    """Merge consecutive scripture-block divs (same or adjacent chapters) into one."""
    pattern = re.compile(
        r'<div class="scripture-block">\s*\n'
        r'<div class="scripture-text">(.*?)</div>\s*\n'
        r'<div class="scripture-ref">([^<]+)</div>\s*\n'
        r'</div>'
        r'\s*\n\n\s*'
        r'<div class="scripture-block">\s*\n'
        r'<div class="scripture-text">(.*?)</div>\s*\n'
        r'<div class="scripture-ref">([^<]+)</div>\s*\n'
        r'</div>',
        re.DOTALL
    )
    def merge(m):
        text1, ref1, text2, ref2 = m.group(1), m.group(2), m.group(3), m.group(4)
        combined_ref = _merge_refs(ref1.strip(), ref2.strip())
        combined_text = text1.strip() + "\n" + text2.strip()
        return (f'<div class="scripture-block">\n'
                f'<div class="scripture-text">{combined_text}</div>\n'
                f'<div class="scripture-ref">{combined_ref}</div>\n'
                f'</div>')
    # Apply repeatedly (handles 3+ consecutive blocks)
    while True:
        new_html = pattern.sub(merge, html)
        if new_html == html:
            break
        html = new_html
    return html


def _clean_ocr_artifacts(html: str) -> str:
    """
    Fix common OCR column-break artifacts in HTML:
    1. Remove <p> containing only punctuation/whitespace (e.g. <p>。</p>)
    2. Strip leading sentence-final punctuation from paragraph openings
    """
    # 1. Remove bare-punctuation paragraphs
    html = re.sub(r'\n*<p>[\s　。，、；：！？…]+</p>', '', html)
    # 2. Strip leading 。 or ， from paragraph text
    html = re.sub(r'(<p>)[。，]', r'\1', html)
    return html


def process_html(html: str) -> str:
    """Process full chapter HTML body."""
    html = _clean_ocr_artifacts(html)
    # Split into top-level blocks
    blocks = re.split(r'(?=\n?<(?:p|h[1-6]|blockquote|div)[\s>])', html)
    out = []
    for b in blocks:
        b = b.strip()
        if b:
            out.append(process_block(b))
    return "\n\n".join(out)


# ── Self-test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("羅九20-22", "羅馬書 9:20-22"),
        ("弗一4-6",   "以弗所書 1:4-6"),
        ("林前一26-29","哥林多前書 1:26-29"),
        ("羅十一33-36","羅馬書 11:33-36"),
        ("路七47",    "路加福音 7:47"),
    ]
    for ref, expected in tests:
        r = lookup_ref(ref)
        assert r and r[5] == expected, f"FAIL {ref}: got {r[5] if r else None}"
        print(f"✓ {ref} → {r[5]}")
        for v in r[4]:
            print(f"  {v}")
    print("\nAll tests passed")
