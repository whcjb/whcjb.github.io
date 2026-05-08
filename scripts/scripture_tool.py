#!/usr/bin/env python3
"""
Scripture lookup and formatting tool for whengracecomes chapters.
- Parses Chinese scripture references  e.g. （羅九20-22）
- Looks up canonical text from downloaded 和合本
- Replaces standalone Bible quotation blocks with styled <div class="scripture-block">
- Splits paragraphs that contain a scripture quote introduced by "呼喊道：" / "他說：" etc.
"""
import json, re
from pathlib import Path

# ── Load Bible ─────────────────────────────────────────────────────────────
_bible = json.load(open("/tmp/bible/json/zh_cuv.json", encoding="utf-8-sig"))

# Build index: abbrev → book array  (0-indexed books, chapters, verses)
_BOOK_BY_ABBR = {b["abbrev"]: b for b in _bible}

# Chinese book name abbreviation → internal abbrev
BOOK_MAP = {
    # OT
    "創": "gn",   "出": "ex",   "利": "lv",   "民": "nm",   "申": "dt",
    "書": "js",   "士": "jud",  "得": "rt",
    "撒上": "1sm", "撒下": "2sm",
    "王上": "1kgs","王下": "2kgs",
    "代上": "1ch", "代下": "2ch",
    "拉": "ezr",  "尼": "ne",   "斯": "et",
    "伯": "job",  "詩": "ps",   "箴": "prv",  "傳": "ec",   "歌": "so",
    "賽": "is",   "耶": "jr",   "哀": "lm",   "結": "ez",   "但": "dn",
    "何": "ho",   "珥": "jl",   "摩": "am",   "俄": "ob",   "拿": "jn",
    "彌": "mi",   "鴻": "na",   "哈": "hk",   "番": "zp",   "該": "hg",
    "亞": "zc",   "瑪": "ml",
    # NT
    "太": "mt",   "可": "mk",   "路": "lk",   "約": "jo",
    "徒": "act",  "羅": "rm",
    "林前": "1co", "林後": "2co",
    "加": "gl",   "弗": "eph",  "腓": "ph",   "西": "cl",
    "帖前": "1ts", "帖後": "2ts",
    "提前": "1tm", "提後": "2tm",
    "多": "tt",   "門": "phm",  "來": "hb",
    "雅": "jm",   "彼前": "1pe","彼後": "2pe",
    "約壹": "1jo","約貳": "2jo","約參": "3jo",
    "猶": "jd",   "啟": "re",
}

# Display names
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

# Chinese number → int
_CN_ONES = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}
_CN_TENS = {"十":10,"二十":20,"三十":30,"四十":40,"五十":50,
            "六十":60,"七十":70,"八十":80,"九十":90}

def cn2int(s: str) -> int:
    """Convert Chinese number string to int (handles 一-九十九)."""
    s = s.strip()
    if re.match(r'^\d+$', s):
        return int(s)
    if s in _CN_ONES:
        return _CN_ONES[s]
    # 十x or 二十x etc.
    m = re.match(r'^([二三四五六七八九]?十)([一二三四五六七八九]?)$', s)
    if m:
        tens = _CN_TENS.get(m.group(1), 10)
        ones = _CN_ONES.get(m.group(2), 0)
        return tens + ones
    return int(s) if s.isdigit() else 1

def lookup_verses(book_cn: str, ch_str: str, v_start: int, v_end: int) -> list[str]:
    """Return list of verse texts for given reference."""
    abbr = BOOK_MAP.get(book_cn)
    if not abbr:
        return []
    book = _BOOK_BY_ABBR.get(abbr)
    if not book:
        return []
    ch = cn2int(ch_str) - 1   # 0-indexed
    if ch < 0 or ch >= len(book["chapters"]):
        return []
    chapter = book["chapters"][ch]
    result = []
    for v in range(v_start - 1, v_end):
        if 0 <= v < len(chapter):
            result.append(chapter[v].replace(" ", ""))
    return result

def lookup_ref(ref_str: str):
    """
    Parse a reference string like '羅九20-22' or '弗一4-6' or '林前一26-29'.
    Returns (book_cn, ch_str, v_start, v_end, [verse_texts], display_ref) or None.
    """
    # Try multi-char book prefixes first (林前, 撒上, etc.)
    book_cn = None
    rest = None
    for prefix in sorted(BOOK_MAP.keys(), key=len, reverse=True):
        if ref_str.startswith(prefix):
            book_cn = prefix
            rest = ref_str[len(prefix):]
            break
    if not book_cn:
        return None

    # rest = "九20-22" or "一4-6" or "十一33-36"
    # chapter = leading Chinese chars, verses = trailing digits
    m = re.match(r'^([一二三四五六七八九十百]+)(\d+)(?:-(\d+))?', rest)
    if not m:
        return None
    ch_str   = m.group(1)
    v_start  = int(m.group(2))
    v_end    = int(m.group(3)) if m.group(3) else v_start

    verses = lookup_verses(book_cn, ch_str, v_start, v_end)
    abbr   = BOOK_MAP.get(book_cn, "")
    name   = BOOK_DISPLAY.get(abbr, book_cn)
    ch_num = cn2int(ch_str)
    if v_start == v_end:
        display = f"{name} {ch_num}:{v_start}"
    else:
        display = f"{name} {ch_num}:{v_start}-{v_end}"
    return (book_cn, ch_str, v_start, v_end, verses, display)

# ── HTML formatting ─────────────────────────────────────────────────────────

def make_scripture_block(ref_result, extra_note: str = "") -> str:
    """Return HTML for a formatted scripture block."""
    _, _, _, _, verses, display = ref_result
    if not verses:
        return ""
    lines = "\n".join(f"<span class='sv'>{v}</span>" for v in verses)
    note_html = f"<span class='scripture-note'>{extra_note}</span>" if extra_note else ""
    return (
        f'<div class="scripture-block">\n'
        f'<div class="scripture-text">{lines}</div>\n'
        f'<div class="scripture-ref">{display}{note_html}</div>\n'
        f'</div>'
    )

# ── Reference pattern ───────────────────────────────────────────────────────
# Matches （羅九20-22）or （弗一4-6）inside text
REF_PAT = re.compile(r'（([^）]{1,20}?)）')

def find_refs(text: str):
    """Find all scripture references in text, return list of (match, parsed_result)."""
    results = []
    for m in REF_PAT.finditer(text):
        inner = m.group(1)
        r = lookup_ref(inner)
        if r:
            results.append((m, r))
    return results

# ── Block processor ─────────────────────────────────────────────────────────

def _char_overlap(a: str, b: str) -> float:
    """Simple char-set overlap ratio."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def process_block(block: str) -> str:
    """
    Given an HTML block string (e.g. <p>...</p>), detect and format
    any standalone scripture quotations it contains.
    Returns transformed HTML.
    """
    # Only process <p> tags
    if not block.startswith("<p>"):
        return block

    inner = block[3:-4]  # strip <p> and </p>
    refs = find_refs(inner)
    if not refs:
        return block

    result_parts = []
    pos = 0

    for match, ref_result in refs:
        _, _, v_start, v_end, verses, _ = ref_result
        if not verses:
            continue

        ref_start = match.start()
        ref_end   = match.end()

        # Text before this reference
        before = inner[pos:ref_start].strip()

        # Check if `before` text closely matches the looked-up Bible verses
        bible_combined = "".join(verses)
        if before and _char_overlap(before, bible_combined) > 0.45:
            # `before` IS the scripture quote — find where it starts in the paragraph
            # Emit everything before `before` as a <p>, then a scripture block
            # We need to know what came before `before` in the running inner text
            # `before` starts at pos in inner (after previous ref)
            pre_quote = inner[pos:ref_start - len(before)].strip() if ref_start > len(before) else ""
            # Actually ref_start includes space; let's find actual quote start
            # Simpler: split on the before text from inner[pos:]
            segment = inner[pos:ref_end]
            quote_idx = segment.rfind(before)
            if quote_idx >= 0:
                pre_text = segment[:quote_idx].strip()
                if pre_text:
                    result_parts.append(f"<p>{pre_text}</p>")
                result_parts.append(make_scripture_block(ref_result))
            else:
                result_parts.append(make_scripture_block(ref_result))
        else:
            # Reference is inline within commentary — keep original text up to and including ref
            result_parts.append(f"<p>{inner[pos:ref_end]}</p>")

        pos = ref_end

    # Remaining text after last reference
    tail = inner[pos:].strip()
    if tail:
        result_parts.append(f"<p>{tail}</p>")

    return "\n\n".join(result_parts) if result_parts else block


def process_html(html: str) -> str:
    """Process full chapter HTML, reformatting scripture blocks."""
    blocks = re.split(r'(?=<(?:p|h3|blockquote|div)[\s>])', html)
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        out.append(process_block(b))
    return "\n\n".join(out)


# ── Self-test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick sanity checks
    r = lookup_ref("羅九20-22")
    assert r, "羅九20-22 lookup failed"
    print("羅馬書 9:20-22")
    for v in r[4]:
        print(" ", v)

    r2 = lookup_ref("弗一4-6")
    assert r2
    print("\n以弗所書 1:4-6")
    for v in r2[4]:
        print(" ", v)

    r3 = lookup_ref("林前一26-29")
    assert r3
    print("\n哥林多前書 1:26-29")
    for v in r3[4]:
        print(" ", v)

    print("\nAll lookups OK")
