#!/usr/bin/env python3
"""
Convert the Ages-format intermediate produced by `ages_phil` extractor
(`[H1] / [H2] / [BODY] / [FOOTNOTE] / [TABLE_LEFT] / [TABLE_RIGHT]` tags)
into publish-ready Markdown.

Usage:
    python3 scripts/structured_to_md.py <input_structured.txt> <output.md>

Handles:
 - Strips leading page-number BODY items (`[BODY] N` matching the current page)
 - `[H1]/[H2]` → `# /` ## ` Markdown headings
 - `[BODY] text` → paragraph (with Ages Greek transliteration → Unicode)
 - `[FOOTNOTE] FtN text` → `[^fN]: text` footnote definition
 - `[FOOTNOTE] <NNNNNN>JOHN N:M` → `## JOHN N:M` scripture-section H2
 - Inline `[FOOTNOTE] (<NNNNNN>Book N:M.)` → inline cross-reference cleaned
 - `[TABLE_LEFT] / [TABLE_RIGHT]` → grouped into `<table class="calvin-scripture">`
 - Spaced-caps cleanup (`B o o k s` → `Books`, `TRANSLATOR'SPREFACE` keeps as-is)
 - Page boundaries preserved as `<!-- PAGE N -->`
"""

from __future__ import annotations
import re
import sys
import unicodedata
from pathlib import Path

# ── Ages Greek transliteration → Unicode ─────────────────────────────────
# Diacritic combining marks (must follow base letter):
#   j = smooth breathing (psilon), J = rough breathing (dasia)
#   > = acute,  < = grave, ~ = circumflex
#   | = iota subscript,  + = diaeresis,  ] = treat like > (Ages variant)
_GCOMB = {'j': '̓', 'J': '̔', '>': '́', '<': '̀', '~': '͂', '|': 'ͅ', '+': '̈', ']': '́'}
_GBASE = {
    'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε', 'z': 'ζ', 'h': 'η', 'q': 'θ',
    'i': 'ι', 'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 'x': 'ξ', 'o': 'ο', 'p': 'π',
    'r': 'ρ', 's': 'σ', 't': 'τ', 'u': 'υ', 'v': 'ς', 'f': 'φ', 'c': 'χ', 'y': 'ψ', 'w': 'ω',
    'A': 'Α', 'B': 'Β', 'G': 'Γ', 'D': 'Δ', 'E': 'Ε', 'Z': 'Ζ', 'H': 'Η', 'Q': 'Θ',
    'I': 'Ι', 'K': 'Κ', 'L': 'Λ', 'M': 'Μ', 'N': 'Ν', 'X': 'Ξ', 'O': 'Ο', 'P': 'Π',
    'R': 'Ρ', 'S': 'Σ', 'T': 'Τ', 'U': 'Υ', 'V': 'Σ', 'F': 'Φ', 'C': 'Χ', 'Y': 'Ψ', 'W': 'Ω',
}
_GVOWELS = set('aehiouwAEHIOUW')
_GDIPH = {'a': 'iu', 'e': 'iu', 'o': 'iu', 'h': 'u', 'u': 'i',
          'A': 'IU', 'E': 'IU', 'O': 'IU', 'H': 'U', 'U': 'I'}


def _ages_token(tok: str) -> str:
    res = []
    i = 0
    n = len(tok)
    pend = ''
    while i < n:
        ch = tok[i]
        if ch not in _GBASE:
            i += 1
            continue
        base = _GBASE[ch]
        i += 1
        comb = pend
        pend = ''
        if ch in _GVOWELS:
            # Breathing marks: j (smooth), J (rough), { (rough alt)
            if i < n and tok[i] in 'jJ{':
                mark = 'J' if tok[i] in 'J{' else 'j'
                comb += _GCOMB[mark]; i += 1
            # Diaeresis: +
            if i < n and tok[i] == '+':
                comb += _GCOMB['+']; i += 1
            # Accent: > acute, < grave, ~ circumflex, ] acute-alt
            if i < n and tok[i] in '><~]':
                acc = tok[i]
                nxt = tok[i + 1] if i + 1 < n else ''
                if nxt in _GVOWELS and nxt in _GDIPH.get(ch, ''):
                    pend = _GCOMB[acc]; i += 1
                else:
                    comb += _GCOMB[acc]; i += 1
            # Iota subscript
            if i < n and tok[i] == '|':
                comb += _GCOMB['|']; i += 1
            elif i + 1 < n and tok[i] == '\\' and tok[i + 1] == '|':
                comb += _GCOMB['|']; i += 2
        res.append(unicodedata.normalize('NFC', base + comb))
    return ''.join(res)


# Match Ages Greek tokens: must contain at least ONE diacritic from
# [><~|{}+\]] (real Greek-only markers, NOT j/J alone since "John"/"jot" have
# them as English letters). j/J as breathing marks are caught via the
# vowel-followed pattern below.
_AGES_GR_PAT = re.compile(
    r'(<[a-zA-Z/!][^>]*>)'                                # group 1: HTML tag
    r'|([a-zA-Z][a-zA-Z><~jJ|\\{}+\]]*'
    r'(?:[><~{}+\]]|\\[|]|\|)'
    r'[a-zA-Z><~jJ|\\{}+\]]*)'                            # group 2: Greek token w/ accent
    # Group 3: vowel + breathing pattern: `oJ`, `aj`, `ej`, `oJ`, `e{`, `o{`, etc.
    # These don't have other accents but ARE valid Greek.
    r'|(\b[aeiouhwAEIOUHW][jJ{]\b)'
)


_AGES_ELISION = {
    'kat': 'κατ',
    'met': 'μετ',
    'ap': 'ἀπ',
    'ep': 'ἐπ',
    'di': 'δι',
    'par': 'παρ',
    'an': 'ἀν',
    'ouk': 'οὐκ',
}


def convert_ages_greek(text: str) -> str:
    # Hide <sty>/</sty> markers from the Greek regex (the `<` would otherwise
    # be consumed by the Greek-accent alternative as if it were a combining mark).
    # Replace each <sty c="..." i="..."> with a fixed-length placeholder to keep
    # downstream regexes simple; restore at the end.
    sty_opens = []
    def _stash_open(m):
        sty_opens.append(m.group(0))
        return f'\x00S{len(sty_opens)-1:04d}\x00'
    text = re.sub(r'<sty c="[0-9a-fA-F]{6}" i="[01]">', _stash_open, text)
    text = text.replace('</sty>', '\x00E\x00')
    # Hide KJV-supplied [word] brackets — Ages uses `[his]` / `[he saith]` for
    # KJV translator-inserted words. Inside `[...]` the trailing `]` looks like
    # a Greek acute marker to _AGES_GR_PAT (hebrews v.2 `[his]` → `[ηις`).
    # Stash short `[word...]` blocks (letters + spaces only, no digits/tags).
    kjv_brackets = []
    def _stash_kjv(m):
        kjv_brackets.append(m.group(0))
        return f'\x00K{len(kjv_brackets)-1:04d}\x00'
    text = re.sub(r'\[[A-Za-z][A-Za-z\s]{0,30}\]', _stash_kjv, text)
    def _repl(m):
        if m.group(1):
            return m.group(1)
        tok = m.group(2) or m.group(3)
        if not tok:
            return m.group(0)
        c = _ages_token(tok.replace('\\|', '|'))
        if any('Ͱ' <= x <= 'Ͽ' or 'ἀ' <= x <= '῿' for x in c):
            return c
        return tok
    text = _AGES_GR_PAT.sub(_repl, text)
    # Specific Ages short tokens without `><~{}+\]\|` markers (otherwise main
    # regex misses, and we can't add `jJ` to trigger since "John"/"Bejart"
    # would false-positive).
    _GREEK_WORDS = {
        'ejn': 'ἐν', 'ejx': 'ἐξ', 'ejk': 'ἐκ', 'ejpi': 'ἐπί', 'ejpi>': 'ἐπί',
        'oJ': 'ὁ', 'hJ': 'ἡ', 'oiJ': 'οἱ', 'aiJ': 'αἱ',
        'wJv': 'ὡς', 'wJ': 'ὡ', 'a@n': 'ἄν',
    }
    for ages, greek in _GREEK_WORDS.items():
        text = re.sub(r'\b' + re.escape(ages) + r'\b', greek, text)
    # Handle Ages elision forms: `kat j <greek>` → `κατ' <greek>` (the
    # consonant cluster has no `<>~` accent marks so the main regex misses it).
    def _elision(m):
        prefix = m.group(1)
        return _AGES_ELISION.get(prefix, prefix) + "'"
    text = re.sub(
        r'\b(' + '|'.join(_AGES_ELISION) + r') j(?=\s+[ἀ-῿Ͱ-Ͽ])',
        _elision, text,
    )
    # Restore <sty> placeholders
    def _restore_open(m):
        idx = int(m.group(1))
        return sty_opens[idx]
    text = re.sub(r'\x00S(\d{4})\x00', _restore_open, text)
    text = text.replace('\x00E\x00', '</sty>')
    # Restore KJV [word] brackets
    def _restore_kjv(m):
        return kjv_brackets[int(m.group(1))]
    text = re.sub(r'\x00K(\d{4})\x00', _restore_kjv, text)
    return text


# ── Spaced-caps cleanup (B o o k s → Books) ──────────────────────────────
def collapse_spaced_caps(text: str) -> str:
    """Collapse 'B o o k s' / 'T H E A G E S' / 'J OHN' style spaced-out heading.

    - First pass: runs of ≥ 3 single-letter "words" separated by single spaces.
    - Second pass: lone capital + space + capital-run, BUT skip when:
      - preceded by apostrophe ('S PREFACE / 'S MAIESTIE — real word break)
      - lone cap is "A" or "I" (English single-letter words — "A MAN" / "I AM"
        should stay as 2 words, not glue to "AMAN" / "IAM")
    """
    def _glue(m):
        return ''.join(m.group(0).split())
    text = re.sub(r'\b(?:[A-Za-z] ){2,}[A-Za-z]\b', _glue, text)
    # Only collapse 'X YYYY' if X is NOT 'A' or 'I' (English words) and
    # NOT preceded by ' or ’ (apostrophe-S etc.).
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(?<!['‘’])\b(?![AI]\b)([A-Z]) ([A-Z]+)\b", r'\1\2', text)
    return text


# ── Scripture-ref detection ──────────────────────────────────────────────
# Group 1: Ages code (e.g. "430101") — OPTIONAL (some books like Philemon
# don't have Ages cross-ref codes in H2 headers)
# Group 2: book+verse range (e.g. "JOHN 1:1-5" / "Colossians 1:1-8" /
# "PHILEMON 1-7" — Philemon as single-chapter has verse-only range)
SCRIPTURE_SECTION_RE = re.compile(
    r'^\s*(?:<(\d{6,7})>\s*)?'
    r'([1-3]?\s*[A-Z][A-Za-z]*(?:\s\d)?[A-Za-z\s]*?\s*(?:\d+:\d+|\d+)(?:[-,]\d+)?)\s*$'
)

# Inline scripture cross-references like "(<540416>1 Timothy 4:16.)"
INLINE_REF_RE = re.compile(r'<\d{6,7}>')


# ── Footnote definition detection ────────────────────────────────────────
# 允许 fn label 后面跟可选 dot（Ages 2cor 前半部分的 ftNN. 风格 def 用了这种格式）
FN_DEF_RE = re.compile(r'^\s*([fF][tT]?\d+)\.?\s+(.*)$', re.DOTALL)


def normalize_fn_label(label: str) -> str:
    """Ft18 → f18 (so refs in body match definitions)."""
    return re.sub(r'^ft', 'f', label.lower())


def format_inline(text: str) -> str:
    """Apply inline transformations: strip Ages markers, convert refs, Greek.
    Leaves <sty>...</sty> tags intact for the caller to style."""
    # Strip Ages scripture-code wrappers `[<NNNNNN>]` or `<NNNNNN>` — even when
    # wrapped in a coloring <sty>...</sty> (PyMuPDF often colors the code).
    text = re.sub(r'<sty\s[^>]*>\s*<(\d{6,7})>\s*</sty>', '', text)
    # 诗篇附录脚注标记 fa/fb/fc/fe(2字母前缀+数字)指向 AGES 版省略的 Additional
    # Criticisms 附录, 本源无定义 → 删除, 否则残留成乱码文本("...man. fa19 The")。
    # [a-e] 排除 ft(章末脚注定义)与单 f\d(常规脚注), 对 phil/heb/john 等书卷安全。
    text = re.sub(r'<sty\s[^>]*>\s*f[a-e]\d+\s*</sty>', '', text)
    text = INLINE_REF_RE.sub('', text)
    # Bracketed footnote refs `[fN]` or `[FtN]` → `[^fN]`
    text = re.sub(r'\[([fF][tT]?\d+)\]', lambda m: f'[^{normalize_fn_label(m.group(1))}]', text)
    # Bare footnote refs `fN` / `FN` (Ages PDF: ". f8 In Scripture..." / "F44"
    # / "*parvulum*f12") → `[^fN]`. Accept both lowercase & uppercase F (PDF
    # OCR sometimes flips case for Symbol-font glyphs). Preceded by any
    # non-letter (space / punct / italic-close `*` / span-close `</span>` etc.)
    # to avoid English words containing "fN".
    text = re.sub(
        r'(?<![A-Za-z])[Ff](\d{1,4}[A-Z]?)\b',
        lambda m: f'[^f{m.group(1)}]', text)
    # Pipe-escape for Kramdown table safety (but not inside HTML <verse> tags)
    text = re.sub(r'(?<!\\)\|', r'\\|', text)
    # Greek transliteration → Unicode
    text = convert_ages_greek(text)
    # Leave <verse>...</verse> tags in place; the caller decides whether to
    # render them as red-italic (commentary) or plain italic (front-matter).
    return text


_STY_RE = re.compile(r'<sty c="([0-9a-fA-F]{6})" i="([01])">(.*?)</sty>', re.DOTALL)


def apply_verse_styling(body: str, red: bool = False) -> str:
    """Convert `<sty c="rrggbb" i="0|1">X</sty>` to the appropriate rendering
    based on the actual PDF color (not on paragraph context). The `red` arg is
    ignored — kept for API compatibility with old call sites.

    Color-to-render mapping:
      #000000 + i=0 → plain text (drop wrapper)
      #000000 + i=1 → markdown italic `*X*`
      #800000 + i=1 → red italic `<span style="color:#800000">*X*</span>`
      #800000 + i=0 → red plain `<span style="color:#800000">X</span>`
      <other>  + i=1 → colored italic `<span style="color:#rrggbb">*X*</span>`
      <other>  + i=0 → colored plain `<span style="color:#rrggbb">X</span>`

    CRITICAL: leading/trailing whitespace inside <sty> must be moved OUTSIDE
    the wrap (otherwise kramdown sees `*X *Y* Z*` as closed italic touching
    letters with no word boundary).
    """
    def _wrap(color_hex: str, italic: bool, inner: str) -> str:
        if not inner.strip():
            return inner
        m = re.match(r'^(\s*)(.+?)(\s*)$', inner, re.DOTALL)
        lead, core, trail = m.group(1), m.group(2), m.group(3)
        color_hex_lower = color_hex.lower()
        is_black = color_hex_lower == '000000'
        # 脚注标记 [^fN] / [^fNa] 不要被任何 span 包裹 —— 包了 kramdown
        # 当 raw HTML 不处理内部，渲染成行内大字而非可点击上标链接
        if re.fullmatch(r'\[\^f\w+\]', core):
            return lead + core + trail
        # 红色 + 非斜体 + 纯数字: 多是丢了 [^f] 括号的脚注上标残骸，
        # 改用真上标 <sup>N</sup>（kramdown 不再当大字渲染）
        if color_hex_lower == '800000' and not italic and re.fullmatch(r'\d+', core):
            return f'{lead}<sup>{core}</sup>{trail}'
        # 红色 + 非斜体 + AGES Digital Library 圣经引用编码（<19B001> 等）：
        # 用 .ages-code class 出，匹配 scripture-box 已有样式（小号上标暗红）
        ages_m = re.fullmatch(r'<([0-9A-Za-z][0-9A-Za-z ]*)>', core)
        if color_hex_lower == '800000' and not italic and ages_m:
            return f'{lead}<span class="ages-code">&lt;{ages_m.group(1)}&gt;</span>{trail}'
        if is_black and not italic:
            return lead + core + trail
        if is_black and italic:
            if len(core) < 2:
                return lead + core + trail
            return f'{lead}*{core}*{trail}'
        # Non-black color → emit explicit span
        rendered = f'*{core}*' if italic else core
        return f'{lead}<span style="color:#{color_hex_lower}">{rendered}</span>{trail}'
    def _repl(m):
        return _wrap(m.group(1), m.group(2) == '1', m.group(3))
    body = _STY_RE.sub(_repl, body)
    if True:
        # Merge consecutive red-italic spans separated only by whitespace
        body = re.sub(
            r'\*</span>(\s+)<span style="color:#800000">\*',
            r'\1',
            body,
        )
    return body


def bold_leading_verse_num(text: str) -> str:
    """Convert leading `N. Capital` to `**N.** Capital` (skill §6).

    Kramdown parses paragraph-leading `N. ` as ordered list item; bolding
    prevents that and matches the Calvin verse-number convention.
    Also accepts an immediately-following `<` (HTML span opening a verse phrase).
    """
    return re.sub(r'^(\d+)\. (?=[A-Z<])', r'**\1.** ', text)


# ── Main converter ───────────────────────────────────────────────────────
PAGE_HEADER_RE = re.compile(r'^--- PAGE (\d+) ---\s*$')
TAG_RE = re.compile(r'^\[([A-Z0-9_]+)\]\s*(.*)$', re.DOTALL)


def _is_sentence_end(text: str) -> bool:
    """Does the trimmed text end with a sentence-terminating punctuation?
    Strips trailing HTML close tags AND footnote markers `[^fN]` / `[^fNa]`
    before testing — otherwise `…end.[^f18]` would test `]` as last char and
    erroneously return False, causing the next paragraph to be merged in."""
    t = text.rstrip()
    if not t:
        return True
    # Repeatedly strip trailing tags/markers until stable
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r'(?:</[a-zA-Z]+(?:\s[^>]*)?>|</?(?:verse|sty)(?:\s[^>]*)?>)+$', '', t).rstrip()
        t = re.sub(r'\[\^[A-Za-z0-9]+\]$', '', t).rstrip()
    if not t:
        return True
    return t[-1] in '.?!:;"”\'’)'  # closing paren also counts as sentence end


_BLOCK_PREFIXES = (
    '#', '[^', '>', '<!--',
    '<div', '<h1', '<h2', '<h3', '<h4',
    '<p ', '<p>', '<p\t',
    '<table', '<tr', '<td', '<th', '<thead', '<tbody',
    '</div', '</p', '</table',
    '---', '|', '{',
)


def _is_paragraph_line(line: str) -> bool:
    """Is this a normal body paragraph (not heading / box / fence / marker /
    centered block)? Accept inline-tag starts like <span>, <verse>, <sup>."""
    s = line.lstrip()
    if not s:
        return False
    if s.startswith(_BLOCK_PREFIXES):
        return False
    return True


def _starts_with_continuation(line: str, prev_tail: str = '', prev_full: str = '') -> bool:
    """Does this body line start in a way that suggests it's a continuation of
    the prior paragraph? Signals:
      - Lowercase letter, digit (non-verse-num), punctuation start
      - Prev ends with `(` or `(N` + next is Bible book name
      - Prev ends with conjunction + next is uppercase
      - **Prev ends with all-caps phrase (no punct) + next starts all-caps**
        (covers "ON THE SON" + "OF MAN," cross-block phrase split)
      - **Same-style continuation**: prev ends with `<sty c="X" i="Y">...</sty>`
        and next opens with the SAME `<sty c="X" i="Y">` — clearly same phrase
    """
    # Strip leading markdown bold/italic markers to peek at first real char
    s = re.sub(r'^(?:\*+|\s)+', '', line.lstrip())
    # Also peek past leading <sty>, <verse>, or <span> open tag (but remember
    # the original line for same-style check below)
    line_for_style = line.lstrip()
    s = re.sub(r'^<sty[^>]*>', '', s)
    s = re.sub(r'^<verse>', '', s)
    s = re.sub(r'^<span[^>]*>\*?', '', s)
    if not s:
        return False
    c = s[0]
    if c.islower():
        return True
    if c in '(,;:)':
        return True
    # Digit-led: accept ONLY if NOT a verse-num pattern. Verse-num markdown
    # is `**N.** ` (bold-wrapped) — accept `\d+\.\**\s` to recognize both raw
    # `N. ` and bolded `N.** ` forms as verse-num (i.e., NOT continuation,
    # should start new paragraph).
    if c.isdigit() and not re.match(r'^\d+\.\**\s', s):
        return True
    # Same-style continuation: prev's tail and next's head both open with the
    # same `<sty c="X" i="Y">`. PDF wraps a multi-line phrase by emitting two
    # blocks with identical styling — clear continuation signal.
    next_sty = re.match(r'^<sty c="([0-9a-fA-F]{6})" i="([01])">', line_for_style)
    if next_sty and prev_full:
        prev_last_sty = re.search(
            r'<sty c="([0-9a-fA-F]{6})" i="([01])">[^<]*</sty>\s*$', prev_full)
        if prev_last_sty:
            if (prev_last_sty.group(1) == next_sty.group(1)
                    and prev_last_sty.group(2) == next_sty.group(2)):
                return True
    if prev_tail:
        # Open-paren + Bible book name split
        if re.search(r'\(\s*\d?\s*$', prev_tail):
            if re.match(r'^(?:[1-3]\s+)?[A-Z][a-z]+(?:\s+\d+:\d+)?', s):
                return True
        # Conjunction + capitalized continuation
        if re.search(r'\b(?:and|or|but|nor|for|yet|so)\s*$', prev_tail):
            if c.isupper():
                return True
        # Article / preposition + capitalized continuation (mid-sentence break).
        # E.g. "...2. The | Gentiles were 'aliens'..." should merge.
        if re.search(r'\b(?:The|A|An|Of|In|On|At|To|For|With|By|From|Through)\s*$', prev_tail):
            return True
        # All-caps phrase wrap: prev ends with all-caps word(s) (no punct),
        # next starts with all-caps word(s). E.g. "ON THE SON" + "OF MAN,".
        prev_tail_stripped = re.sub(r'</?(?:sty(?:\s[^>]*)?|span(?:\s[^>]*)?|verse)>', '', prev_tail).rstrip()
        if re.search(r'\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\s*$', prev_tail_stripped):
            # Strip leading style tags from s to peek the actual first letters
            s_clean = re.sub(r'^(?:<sty[^>]*>|<span[^>]*>|<verse>)+', '', s)
            if re.match(r'^[A-Z]{2,}\b', s_clean):
                return True
    return False


def _merge_paragraph_fragments(out: list[str]) -> list[str]:
    """Walk `out` and merge consecutive body paragraphs that were split by
    block/page boundaries. Cross-page boundaries (lines like `<!-- PAGE N -->`)
    are passed through unchanged but do not block merging if the surrounding
    paragraphs satisfy the merge condition.
    """
    if not out:
        return out
    new_out = []
    i = 0
    while i < len(out):
        line = out[i]
        # Skip empty separators initially
        if not line.strip():
            new_out.append(line)
            i += 1
            continue
        # If this is a paragraph line, try to merge any later paragraph lines.
        if _is_paragraph_line(line):
            buf = line.rstrip()
            j = i + 1
            while j < len(out):
                # Allow empty lines and page markers between candidates
                k = j
                page_markers = []
                while k < len(out) and (
                    not out[k].strip()
                    or out[k].lstrip().startswith('<!-- PAGE')
                ):
                    if out[k].lstrip().startswith('<!-- PAGE'):
                        page_markers.append(out[k])
                    k += 1
                if k >= len(out):
                    break
                nxt = out[k]
                if not _is_paragraph_line(nxt):
                    break
                # Only merge if current does NOT end sentence AND next is continuation
                prev_tail = buf[-25:] if buf else ''
                if _is_sentence_end(buf) or not _starts_with_continuation(nxt, prev_tail, buf):
                    break
                # Merge: append next paragraph to buf, keep page markers BEFORE buf
                # (so PDF reference position survives) — but since we're already
                # past i, just emit page markers into new_out unchanged before buf.
                for pm in page_markers:
                    if pm not in new_out[-3:]:  # avoid dup if just emitted
                        new_out.append(pm)
                buf = buf + ' ' + nxt.lstrip()
                j = k + 1
            new_out.append(buf)
            i = j
        else:
            new_out.append(line)
            i += 1
    return new_out


def _build_ref_banner(ages_code, book_verse: str) -> str:
    """Render the scripture-ref banner with separable Ages code / book / verse spans
    so per-book CSS can style them PDF-faithfully (small-caps book name, dark-red
    Ages code, bold verse range). Returns a single <p> tag.

    Accepts:
    - all-caps "JOHN 1:1-5" (PDF small-caps font)
    - title-case "Colossians 1:1-8" (PDF normal font)
    - single-chapter book "PHILEMON 1-7" (verse-only range, no chapter)
    `ages_code` may be None for books without Ages cross-ref codes.
    """
    m = re.match(
        r'^([1-3]?\s*[A-Z][A-Za-z\s]*?)\s+(\d+:\d+(?:[-,]\d+)?|\d+(?:-\d+)?)\s*$',
        book_verse,
    )
    if m:
        book = m.group(1).strip()
        verse = m.group(2)
        book_html = book.title()
        ages_html = f'<span class="ages-code">&lt;{ages_code}&gt;</span>' if ages_code else ''
        return (
            f'<p class="scripture-ref">'
            f'{ages_html}'
            f'<span class="book-name">{book_html}</span> '
            f'<span class="verse-range">{verse}</span>'
            f'</p>'
        )
    return f'<p class="scripture-ref">{book_verse}</p>'


def convert(structured_path: Path, out_path: Path) -> None:
    text = structured_path.read_text(encoding='utf-8')
    lines = text.split('\n')

    out: list[str] = []
    current_page = 0
    in_table = False
    table_left: list[str] = []
    table_right: list[str] = []
    table_header: str | None = None
    in_scripture = False
    scripture_lines: list[str] = []
    # 双语经文 2 列模式：每条 (verse_num, en, la) 由 extractor 的 [SCRIPTURE_ROW] 投递
    scripture_rows: list[tuple[str, str, str]] = []
    scripture_ref: str | None = None
    in_commentary_section = False  # True after first scripture-section header in chapter; reset on H1
    pending_blockquote_continuation = False
    # When we emit a `[^fN]: ...` back-section fn def, the next BODY/CENTERED
    # blocks are continuation lines that PyMuPDF split off (the fn body wraps
    # to multiple PDF blocks). Append them onto the fn line until we hit
    # another fn def or a heading. Index of the line in `out` to append to.
    pending_fn_idx: int | None = None

    def flush_scripture():
        nonlocal in_scripture, scripture_lines, scripture_rows, scripture_ref
        if not scripture_lines and not scripture_rows:
            in_scripture = False
            scripture_ref = None
            return
        out.append('')
        out.append('<div class="scripture-box scripture-box--bilingual" markdown="1">' if scripture_rows
                   else '<div class="scripture-box" markdown="1">')
        if scripture_ref:
            out.append(scripture_ref)
        out.append('')
        if scripture_rows:
            # 双语 2 列经文表：英文左列，拉丁文右列
            out.append('<table class="scripture-bilingual">')
            out.append('<tbody>')
            fn_refs_in_table: list[str] = []
            for n, en, la in scripture_rows:
                # 节号 <strong> 化，便于 verse-anchor JS 识别
                en_html = f'<strong>{n}.</strong> {en}' if en else ''
                la_html = f'<strong>{n}.</strong> {la}' if la else ''
                out.append(
                    f'<tr><td class="scripture-en">{en_html}</td>'
                    f'<td class="scripture-la">{la_html}</td></tr>'
                )
                # 收集 td 内出现的 [^fN]/[^N] 编号（已经被 _md_to_html_inline
                # 转成 <sup id="fnref:N">，从 sup id 反向提取）
                for m_sup in re.finditer(r'id="fnref:([Ff]?\d+[A-Za-z]?)"',
                                          en_html + ' ' + la_html):
                    fn_refs_in_table.append(m_sup.group(1))
            out.append('</tbody>')
            out.append('</table>')
            # Kramdown stub：让 <td> 内的 <sup> 跳转目标 <li id="fn:N"> 仍由 kramdown
            # 生成。隐藏段含一行 markdown 引用，CSS .scripture-fnref-stub 设
            # display:none。保序去重。
            seen: set[str] = set()
            ordered: list[str] = []
            for n in fn_refs_in_table:
                if n not in seen:
                    seen.add(n)
                    ordered.append(n)
            if ordered:
                stub = ' '.join(f'[^{n}]' for n in ordered)
                out.append('')
                out.append(stub)
                out.append('{:.scripture-fnref-stub}')
        else:
            # 单语：单段并排（acts/john/romans 单列模式）
            def bold_verse_nums(s: str) -> str:
                return re.sub(r'(?:^|(?<=\s))(\d+)\s*\.\s+', r'<strong>\1.</strong> ', s)
            non_empty = [s.strip() for s in scripture_lines if s.strip()]
            if len(non_empty) == 1:
                out.append(bold_verse_nums(non_empty[0]))
            else:
                for s in non_empty:
                    out.append(bold_verse_nums(s))
                    out.append('')
        out.append('')
        out.append('</div>')
        out.append('')
        in_scripture = False
        scripture_lines = []
        scripture_rows = []
        scripture_ref = None

    def flush_table():
        nonlocal in_table, table_left, table_right, table_header
        if not (table_left or table_right):
            in_table = False
            table_header = None
            return
        # Render as HTML table (Ages two-column scripture format)
        out.append('')
        out.append('<table class="calvin-scripture">')
        if table_header:
            out.append(f'<thead><tr><th colspan="2" style="text-align:center">{table_header}</th></tr></thead>')
        out.append('<tbody>')
        rows = max(len(table_left), len(table_right))
        for i in range(rows):
            lcell = table_left[i] if i < len(table_left) else ''
            rcell = table_right[i] if i < len(table_right) else ''
            out.append(f'<tr><td>{lcell}</td><td>{rcell}</td></tr>')
        out.append('</tbody>')
        out.append('</table>')
        out.append('')
        in_table = False
        table_left = []
        table_right = []
        table_header = None

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue

        # Page boundary
        pm = PAGE_HEADER_RE.match(line)
        if pm:
            flush_table()
            flush_scripture()
            current_page = int(pm.group(1))
            out.append('')
            out.append(f'<!-- PAGE {current_page} -->')
            out.append('')
            i += 1
            continue

        tm = TAG_RE.match(line)
        if not tm:
            i += 1
            continue

        tag, content = tm.group(1), tm.group(2).strip()

        # Strip the leading "page-number" BODY item (e.g. "[BODY] 47" at top of page 47)
        if tag == 'BODY' and content.strip().isdigit() and int(content.strip()) == current_page:
            i += 1
            continue

        # Tables
        if tag in ('TABLE_LEFT', 'TABLE_RIGHT'):
            if not in_table:
                in_table = True
            cell_html = format_inline(content)
            cell_html = re.sub(r'\\\|', '|', cell_html)  # un-escape pipes inside HTML cells
            if tag == 'TABLE_LEFT':
                table_left.append(cell_html)
            else:
                table_right.append(cell_html)
            i += 1
            continue
        elif in_table:
            flush_table()

        if tag == 'H1':
            cleaned = collapse_spaced_caps(content)
            cleaned = format_inline(cleaned)
            # Strip any <verse> wrappers in headings — they're noise.
            cleaned = re.sub(r'</?(?:verse|sty[^>]*)>', '', cleaned)
            # H1 = chapter/section break → leave commentary mode + clear fn merge
            in_commentary_section = False
            pending_fn_idx = None
            out.append('')
            out.append(f'# {cleaned}')
            out.append('')
        elif tag == 'SCRIPTURE_ROW':
            # 1cor 双语经文：extractor 已配对英文/拉丁文，编码 N|||EN|||en|||LA|||la
            m_row = re.match(
                r'^(\d+)\|\|\|EN\|\|\|(.*?)\|\|\|LA\|\|\|(.*)$',
                content, flags=re.DOTALL)
            if m_row:
                n_str, en_raw, la_raw = m_row.group(1), m_row.group(2), m_row.group(3)

                def _md_to_html_inline(s: str) -> str:
                    """Convert *X* → <em>X</em>, **X** → <strong>X</strong>,
                    [^fN]/[^N] → <sup id="fnref:N"><a href="#fn:N">N</a></sup>.
                    Kramdown 不处理 <td> 内 markdown，必须在塞进 td 前手工转。
                    [^fN] 风格的脚注标签也支持（1cor 用 f-prefix）。"""
                    s = format_inline(s)
                    s = apply_verse_styling(s, red=False)
                    s = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', s)
                    # 强调标记
                    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
                    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
                    # 脚注引用 [^N] / [^fN]
                    s = re.sub(
                        r'\[\^([Ff]?\d+[A-Za-z]?)\]',
                        r'<sup id="fnref:\1"><a href="#fn:\1" class="footnote">\1</a></sup>',
                        s,
                    )
                    return s.strip()

                en = _md_to_html_inline(en_raw)
                la = _md_to_html_inline(la_raw)
                scripture_rows.append((n_str, en, la))
            i += 1
            continue
        elif tag == 'H2':
            # Check if this H2 is a scripture-section header (carries `<NNNNNN>BOOK Ch:V-V'`).
            # If so, route through the same scripture-box mechanism as FOOTNOTE-emitted
            # section headers (so Romans bilingual-extracted [H2]<NNNNNN>...
            # gets a scripture-box too).
            line_for_sec = re.sub(r'</?sty(?:\s[^>]*)?>', '', content)
            sec_h2 = SCRIPTURE_SECTION_RE.match(line_for_sec.strip())
            if sec_h2:
                flush_scripture()
                ages_code = sec_h2.group(1)
                ref_text = collapse_spaced_caps(sec_h2.group(2).strip())
                anchor_id = re.sub(r'[^a-z0-9-]+', '-', ref_text.lower()).strip('-')
                out.append('')
                out.append(f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref_text}" style="display:none">{ref_text}</h2>')
                out.append('')
                scripture_ref = _build_ref_banner(ages_code, ref_text)
                in_scripture = True
                in_commentary_section = True
                scripture_lines = []
            else:
                cleaned = collapse_spaced_caps(content)
                cleaned = format_inline(cleaned)
                cleaned = re.sub(r'</?(?:verse|sty[^>]*)>', '', cleaned)
                out.append('')
                out.append(f'## {cleaned}')
                out.append('')
        elif tag == 'FOOTNOTE':
            # Try to detect three sub-types:
            # (a) Scripture-section header: starts with <NNNNNN>BOOK N:M (alone on line)
            # (b) Footnote definition: starts with FtN or fN (alphanumeric label)
            # (c) Inline cross-reference: bare <NNNNNN>... (often closes a body sentence)
            # Strip <sty> wraps before applying section-header regex (PyMuPDF
            # often colors the <NNNNNN> Ages code separately so it ends up
            # wrapped in <sty c="800000" i="0">...</sty>).
            line_for_sec = re.sub(r'</?sty(?:\s[^>]*)?>', '', line)
            sec_m = SCRIPTURE_SECTION_RE.match(line_for_sec.replace('[FOOTNOTE]', '').strip())
            if sec_m:
                # Flush any pending scripture box, then prep next-scripture ref.
                flush_scripture()
                ages_code = sec_m.group(1)
                ref_text = collapse_spaced_caps(sec_m.group(2).strip())
                # No more `## BOOK Ch:V-V'` H2 — the scripture-ref banner inside
                # the box already shows the same text. Emit an invisible anchor
                # only for verse-nav JS (`<h2 class="scripture-anchor" id="...">`).
                anchor_id = re.sub(r'[^a-z0-9-]+', '-', ref_text.lower()).strip('-')
                out.append('')
                out.append(f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref_text}" style="display:none">{ref_text}</h2>')
                out.append('')
                # Structured banner with Ages code + small-caps book + verse range.
                scripture_ref = _build_ref_banner(ages_code, ref_text)
                in_scripture = True
                in_commentary_section = True  # subsequent body italics → red
                scripture_lines = []
            else:
                # Strip leading <sty c="..." i="...">ftN</sty> wrap before
                # testing FN_DEF_RE (extractor colors the ftN label red).
                # Allow whitespace inside the sty (e.g., `<sty>ft306 </sty>`).
                content_for_fn = re.sub(
                    r'^\s*<sty\s[^>]*>\s*([Ff][Tt]\d+[A-Za-z]?)\.?\s*</sty>\s*',
                    r'\1 ', content)
                fn_m = FN_DEF_RE.match(content_for_fn)
                # Reject only when fn body starts with an Ages bible-ref marker
                # `<NNNNNN>` (that's an inline cross-ref disguised as fn).
                # `<sty>` wrap is legitimate (colored word inside fn body).
                fn_body_starts_with_ages_ref = bool(
                    fn_m and re.match(r'^<\d{6,7}>', fn_m.group(2)))
                if fn_m and not fn_body_starts_with_ages_ref:
                    label = normalize_fn_label(fn_m.group(1))
                    body = format_inline(fn_m.group(2))
                    body = apply_verse_styling(body, red=False)
                    out.append('')
                    out.append(f'[^{label}]: {body}')
                    out.append('')
                    # Arm continuation merge — next BODY/CENTERED will append here
                    pending_fn_idx = len(out) - 2
                else:
                    # Inline cross-reference fragment — fold into preceding paragraph
                    body = format_inline(content)
                    body = apply_verse_styling(body, red=in_commentary_section)
                    # If we're mid back-section fn def (pending_fn_idx armed),
                    # this inline cross-ref is part of the fn body — append.
                    if pending_fn_idx is not None:
                        body_clean = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', body)
                        body_clean = re.sub(r'\s+', ' ', body_clean).strip()
                        if body_clean:
                            # Avoid double-space when prior ends with `(`
                            peek = re.sub(r'(?:</span>|</sty>|\s)+$', '', out[pending_fn_idx].rstrip())
                            sep = '' if peek.endswith(('(', '[')) else ' '
                            out[pending_fn_idx] = out[pending_fn_idx].rstrip() + sep + body_clean
                        i += 1
                        continue
                    j = len(out) - 1
                    while j >= 0 and not out[j].strip():
                        j -= 1
                    # Accept appending into body paragraphs even if they start
                    # with an inline tag (<span>, <verse>, **N.**, *italic*).
                    # Reject only block-level / heading / fence prefixes.
                    BLOCK_PREFIXES = ('#', '[^', '>', '<!--', '<div', '<h1',
                                      '<h2', '<h3', '<h4', '<p ', '<p>',
                                      '<table', '<tr', '<td', '<th', '<thead',
                                      '<tbody', '</div', '</p', '</table',
                                      '---', '|', '{')
                    # SPECIAL: navy scripture-quote <p> — its Ages cross-ref `(BookN:M)`
                    # often comes as a separate [FOOTNOTE] line right after. Inject the
                    # ref text INSIDE the closing </p> so the whole quote stays one block.
                    prior = out[j] if j >= 0 else ''
                    is_navy_quote_p = bool(re.match(r'\s*<p\s+style="[^"]*color:#000080', prior))
                    if is_navy_quote_p and prior.rstrip().endswith('</p>'):
                        # Insert body before the closing </p>. Avoid double-space
                        # when prior ends with `(` (the Ages bible-ref opener).
                        before_close = re.sub(r'\s*</p>\s*$', '', out[j])
                        # Peek at the last visible char (strip trailing </span> wraps too)
                        peek = before_close.rstrip()
                        peek = re.sub(r'(?:</span>|</sty>|\s)+$', '', peek)
                        sep = '' if peek.endswith(('(', '[')) else ' '
                        # If injecting body, also wrap it in <span> so it inherits
                        # the navy color (otherwise plain text shows in default body color).
                        body_styled = body if '<span' in body else f'<span style="color:#000080">{body}</span>'
                        out[j] = before_close.rstrip() + sep + body_styled + '</p>'
                    elif j >= 0 and not out[j].lstrip().startswith(BLOCK_PREFIXES):
                        out[j] = out[j].rstrip() + ' ' + body
                    else:
                        out.append('')
                        out.append(body)
                        out.append('')
        elif tag in ('CENTERED_H1', 'CENTERED_H2'):
            # Strip <sty> and Ages markers to test the plain text content.
            test_text = re.sub(r'</?(?:verse|sty[^>]*)>', '', content)
            # Check scripture-section first（含 <NNNNNN> 的章节经文头），同 H2 一样
            # 路由进 scripture-box，否则同一章首段会变成裸 <p> 居中标题（1cor 踩过）。
            line_for_sec = test_text
            sec_h_centered = SCRIPTURE_SECTION_RE.match(line_for_sec.strip())
            if sec_h_centered:
                flush_scripture()
                ages_code = sec_h_centered.group(1)
                ref_text = collapse_spaced_caps(sec_h_centered.group(2).strip())
                anchor_id = re.sub(r'[^a-z0-9-]+', '-', ref_text.lower()).strip('-')
                out.append('')
                out.append(f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref_text}" style="display:none">{ref_text}</h2>')
                out.append('')
                scripture_ref = _build_ref_banner(ages_code, ref_text)
                in_scripture = True
                in_commentary_section = True
                scripture_lines = []
                pending_fn_idx = None
                i += 1
                continue
            test_text = re.sub(r'<\d{6,7}>', '', test_text).strip()
            # SKIP: back-matter footnote-page header "CHAPTER N" (dark green
            # #006411 in Ages PDF, vs real chapter head which is H1 blue).
            # PDF doesn't display these on text — they're internal page
            # markers. Emit nothing.
            if re.match(r'^CHAPTER\s+\d+\s*$', test_text):
                # If this falls right after a fn def, it's a back-matter
                # page header — also reset pending_fn_idx so following fns
                # don't try to merge into the dropped marker.
                pending_fn_idx = None
                i += 1
                continue
            # Otherwise: clear pending fn merge and emit as styled <p>.
            # Preserve original PDF color via apply_verse_styling — DO NOT
            # strip <sty> tags before that, or color info is lost.
            pending_fn_idx = None
            cleaned = collapse_spaced_caps(format_inline(content))
            cleaned = apply_verse_styling(cleaned)  # <sty c="..." i="..."> → <span style="color:#...">
            # Now strip any leftover <verse>/<sty> wraps (defensive)
            cleaned = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cleaned)
            if cleaned.strip():
                size_class = 'title-block-h1' if tag == 'CENTERED_H1' else 'title-block-h2'
                font_size = '22px' if tag == 'CENTERED_H1' else '16px'
                font_weight = 'bold' if tag == 'CENTERED_H1' else 'bold'
                # markdown="1" so kramdown still expands [^fN] refs inside.
                out.append('')
                out.append(f'<p class="{size_class}" style="text-align:center; font-size:{font_size}; font-weight:{font_weight}; margin:18px 0 12px;" markdown="1">{cleaned}</p>')
                out.append('')
        elif tag == 'INDENT':
            # PDF outline subitem (indented from body), e.g. "1. A proof of its
            # necessity ..." at x=44 (body is x=26). Clear pending fn merge.
            pending_fn_idx = None
            # If we're inside a scripture section and the INDENT block looks like
            # a verse passage (`N. Capital` start, no leading italic phrase marker),
            # route into scripture-box. 1cor 经文区 PDF 用 INDENT（左缩进英文）+
            # RIGHT（右缩进拉丁文）交替，必须并入同一 scripture-box。
            if in_scripture:
                stripped_content = content.lstrip()
                starts_with_verse = bool(re.match(r'^\d+\s*\.\s+', stripped_content))
                # 注释段以「红色斜体短语」(`<sty c="800000" i="1">`) 开场；
                # 经文段允许出现普通黑斜体（`<sty c="000000" i="1">`，如 KJV 风格的
                # 强调词 *to be*）。只用红色斜体作为注释标志，避免误把经文当注释。
                has_red_italic_marker = bool(re.search(
                    r'<sty\s+c="800000"\s+i="1">', stripped_content[:60]))
                if starts_with_verse and not has_red_italic_marker:
                    body = format_inline(content)
                    body = apply_verse_styling(body, red=False)
                    scripture_lines.append(body)
                    i += 1
                    continue
            body = format_inline(content)
            body = apply_verse_styling(body)
            body = bold_leading_verse_num(body)
            # markdown="1" so kramdown still expands *italic* / [^fN] / **bold** inside
            out.append('')
            out.append(f'<p style="margin-left:2em;" markdown="1">{body}</p>')
            out.append('')
            i += 1
            continue
        elif tag == 'RIGHT':
            # PDF right-aligned narrow byline (e.g. "by John Calvin" at x=278-350)
            pending_fn_idx = None
            # 同 INDENT：scripture 区内的 RIGHT 是拉丁文经节续接，并入 scripture-box
            if in_scripture:
                stripped_content = content.lstrip()
                starts_with_verse = bool(re.match(r'^\d+\s*\.\s+', stripped_content))
                has_red_italic_marker = bool(re.search(
                    r'<sty\s+c="800000"\s+i="1">', stripped_content[:60]))
                if starts_with_verse and not has_red_italic_marker:
                    body = format_inline(content)
                    body = apply_verse_styling(body, red=False)
                    scripture_lines.append(body)
                    i += 1
                    continue
            body = format_inline(content)
            body = apply_verse_styling(body)
            out.append('')
            out.append(f'<p style="text-align:right;" markdown="1">{body}</p>')
            out.append('')
            i += 1
            continue
        elif tag == 'CENTERED':
            # Back-section fn continuation: append to pending [^fN]: line
            if pending_fn_idx is not None:
                cleaned = format_inline(content)
                cleaned = apply_verse_styling(cleaned)
                cleaned = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cleaned)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    out[pending_fn_idx] = out[pending_fn_idx].rstrip() + ' ' + cleaned
                i += 1
                continue
            # If we're inside a scripture section and this CENTERED block holds
            # the actual verse passage (≥1 verse-num anchor + starts with verse),
            # route through the scripture-box path instead of emitting <p center>.
            if in_scripture:
                stripped_content = content.lstrip()
                anchor_count = len(re.findall(r'(?:^|\s)\d+\s*\.\s', stripped_content))
                starts_with_verse = bool(re.match(r'^\d+\s*\.\s+[A-Z]', stripped_content))
                # Commentary opens with italic verse-phrase marker (now <sty c="800000" i="1">).
                # Scripture passage opens with plain `N. Capital`. Detect the marker presence.
                has_leading_italic = bool(re.search(r'<sty\s+c="[0-9a-fA-F]{6}"\s+i="1">', stripped_content[:60]))
                if anchor_count >= 1 and starts_with_verse and not has_leading_italic:
                    body = format_inline(content)
                    body = apply_verse_styling(body, red=False)
                    scripture_lines.append(body)
                    flush_scripture()
                    i += 1
                    continue
            # Preserve color/italic via apply_verse_styling before stripping tags
            cleaned = collapse_spaced_caps(format_inline(content))
            cleaned = apply_verse_styling(cleaned)
            cleaned = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cleaned)
            if cleaned.strip():
                out.append('')
                out.append(f'<p style="text-align:center" markdown="1">{cleaned}</p>')
                out.append('')
        elif tag in ('BODY', 'VERSE'):
            # Some PDFs (Romans) have back-section fn defs tagged [BODY] instead
            # of [FOOTNOTE]. Detect `<sty>ftN</sty> body...` pattern at start →
            # treat as fn def (same logic as FOOTNOTE branch).
            body_strip_ftN = re.sub(
                r'^\s*<sty\s[^>]*>\s*([Ff][Tt]\d+[A-Za-z]?)\.?\s*</sty>\s*',
                r'\1 ', content)
            body_fn_m = FN_DEF_RE.match(body_strip_ftN)
            body_fn_is_ages_ref = bool(body_fn_m and re.match(r'^<\d{6,7}>', body_fn_m.group(2)))
            if body_fn_m and not body_fn_is_ages_ref:
                label = normalize_fn_label(body_fn_m.group(1))
                fn_body = format_inline(body_fn_m.group(2))
                fn_body = apply_verse_styling(fn_body, red=False)
                out.append('')
                out.append(f'[^{label}]: {fn_body}')
                out.append('')
                pending_fn_idx = len(out) - 2
                i += 1
                continue
            # Back-section fn continuation: append to pending [^fN]: line.
            if pending_fn_idx is not None:
                cont_body = format_inline(content)
                cont_body = apply_verse_styling(cont_body)
                cont_body = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cont_body)
                cont_body = re.sub(r'\s+', ' ', cont_body).strip()
                if cont_body:
                    out[pending_fn_idx] = out[pending_fn_idx].rstrip() + ' ' + cont_body
                i += 1
                continue
            # Detect "navy scripture quote" block: content is wholly (or near-
            # wholly) wrapped in <sty c="000080" i="0">...</sty>. In the PDF
            # these are short centered bible-quote blocks set apart from the
            # body (e.g. "in the beginning God created the heaven and the
            # earth, (Genesis 1:1)" between commentary paragraphs).
            # Detection: strip all 000080 <sty>...</sty> wraps + Ages codes +
            # whitespace; if residue is < 8 chars, it's a navy quote block.
            navy_test = content
            navy_test = re.sub(r'<sty c="000080" i="[01]">(.*?)</sty>', r'\1', navy_test, flags=re.DOTALL)
            navy_test_no_navy = re.sub(r'<sty c="000080" i="[01]">.*?</sty>', '', content, flags=re.DOTALL)
            navy_test_no_navy = re.sub(r'<\d{6,7}>', '', navy_test_no_navy)
            navy_test_no_navy = re.sub(r'<sty\s[^>]*>|</sty>', '', navy_test_no_navy)
            navy_test_no_navy = navy_test_no_navy.strip()
            has_navy = '<sty c="000080"' in content
            is_navy_quote = has_navy and len(navy_test_no_navy) < 8
            if is_navy_quote:
                # Route to centered output. Strip the navy wrap (we'll color via class).
                body = format_inline(content)
                body = apply_verse_styling(body)  # converts <sty c="000080" ...> → <span style=...>
                # Remove residual <sty> tags
                body = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', body)
                body = re.sub(r'\s+', ' ', body).strip()
                if body:
                    out.append('')
                    out.append(f'<p style="text-align:center; color:#000080; margin:14px 2em;" markdown="1">{body}</p>')
                    out.append('')
                i += 1
                continue

            body = format_inline(content)
            # Detect scripture-passage block: first BODY after a section header.
            # Accept ≥1 verse-number anchor (covers single-verse refs like JOHN 1:14)
            # AND require the leading text to start with a verse number to avoid
            # absorbing commentary (which starts with `**N.** *VersePhrase*`).
            if in_scripture:
                stripped_content = content.lstrip()
                anchor_count = len(re.findall(r'(?:^|\s)\d+\s*\.\s', stripped_content))
                starts_with_verse = bool(re.match(r'^\d+\s*\.\s+[A-Z]', stripped_content))
                # The scripture passage in Ages PDF always starts with `N. Capital`
                # plain text (no italic verse-phrase markup before commentary kicks in).
                # Commentary starts with `N. <verse>...</verse>` (italic phrase).
                # Commentary opens with italic verse-phrase marker (now <sty c="800000" i="1">).
                # Scripture passage opens with plain `N. Capital`. Detect the marker presence.
                has_leading_italic = bool(re.search(r'<sty\s+c="[0-9a-fA-F]{6}"\s+i="1">', stripped_content[:60]))
                if anchor_count >= 1 and starts_with_verse and not has_leading_italic:
                    body = apply_verse_styling(body, red=False)
                    scripture_lines.append(body)
                    flush_scripture()
                    i += 1
                    continue
                else:
                    # 不是经文段 → 注释开始；若已收集 scripture_lines 或 scripture_rows
                    # 但还未 flush，现在 flush（确保经文 box 在注释之前出现）
                    if scripture_lines or scripture_rows:
                        flush_scripture()
                    in_scripture = False  # not a scripture passage, fall through
            # Red-italic for any body in a chapter's commentary section (after first
            # scripture-section header, before next H1). Outside that → plain italic
            # (front-matter book titles, signatures, dedications).
            body = apply_verse_styling(body, red=in_commentary_section)
            body = bold_leading_verse_num(body)
            out.append('')
            out.append(body)
            out.append('')
        else:
            # Unknown tag — emit raw for debugging
            out.append(f'<!-- UNKNOWN-TAG {tag}: {content[:80]} -->')

        i += 1

    flush_table()
    flush_scripture()

    # ── SEV-3 post-pass: tidy bible-ref spaces + merge adjacent italic ──
    for k, line in enumerate(out):
        if not line.strip():
            continue
        # Fix `( Book N:N)` → `(Book N:N)` (Ages stripped <NNNNNN> left a space)
        line = re.sub(r'\(\s+([A-Z1-3])', r'(\1', line)
        # Merge adjacent italic spans separated only by a single space:
        # `*X* *Y*` → `*X Y*`. Skip when followed by `</span>` (red-italic).
        prev = None
        while prev != line:
            prev = line
            line = re.sub(r'(?<!\*)\*([^*\n<]+?)\* \*(?!\*)([^*\n<]+?)\*(?!\*)',
                          r'*\1 \2*', line)
        out[k] = line

    # ── Cross-block paragraph merge ──────────────────────────────────────
    # PyMuPDF often splits one logical paragraph across multiple blocks (page
    # boundaries, line-group gaps). Merge when: prev body ends without
    # sentence-end punctuation AND next body starts with a lowercase letter
    # (or a continuation token like `<verse>`, `(`, `[^`). Skip if either
    # side is a heading, fence, footnote def, scripture-box, page marker.
    out = _merge_paragraph_fragments(out)

    # Collapse multiple blank lines to single
    result = '\n'.join(out)
    result = re.sub(r'\n{3,}', '\n\n', result)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result + '\n', encoding='utf-8')


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: structured_to_md.py <input.txt> <output.md>', file=sys.stderr)
        return 1
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    convert(inp, out)
    sz = out.stat().st_size
    n_lines = sum(1 for _ in out.open(encoding='utf-8'))
    print(f'[ok] {inp.name} → {out.relative_to(out.parent.parent)}')
    print(f'    {sz:,} bytes, {n_lines:,} lines')
    return 0


if __name__ == '__main__':
    sys.exit(main())
