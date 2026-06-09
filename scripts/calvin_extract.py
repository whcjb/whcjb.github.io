#!/usr/bin/env python3
"""
scripts/calvin_extract.py — Unified Calvin commentary PDF extraction

All Calvin commentary volumes use this single script.
Usage: python scripts/calvin_extract.py <volume>

Available volumes:
  matthew1   – Harmony Vol. 1 (CCEL single-column, Matthew 1–11)
  harmony3   – Harmony Vol. 3 (CCEL single-column, passion/resurrection)
  matthew    – Harmony Vol. 2 (CCEL parallel gospel columns)
  acts1      – Acts Vol. 1 (CCEL single-column, Acts 1–13)
  acts2      – Acts Vol. 2 (CCEL single-column, Acts 14–28)
  heb        – Hebrews (Ages Digital Library bilingual)
  1cor-vol1  – 1 Corinthians Vol. 1 (Ages Digital Library bilingual)
  1cor-vol2  – Corinthians Vol. 2 (Ages Digital Library bilingual)
  phil       – Philippians (Ages Digital Library, intermediate tagged format)
"""

import fitz
import re
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root

# ── Volume configurations ──────────────────────────────────────────────────────
VOLUMES = {
    'matthew1': {
        'format': 'ccel_harmony',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_matai_make1.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/matthew1/matthew1_raw.txt'),
        'skip_pages': 29,
        'header_y_max': 62,
        'footnote_size_max': 9.5,
        'page_num_x_min': 450,
        'page_w': 612.0,
        'body_left': 108.0,
        'body_right': 504.0,
        'centering': True,
        'extract_footnotes': True,
        # Hebrew/Greek mojibake fixes: the embedded font in this PDF lacks a
        # ToUnicode map, so PyMuPDF returns U+FFFD for every Hebrew glyph.
        # Each entry's left side is the mojibake-with-context string as it
        # appears in the raw output; the right side is the correct Hebrew
        # (verified by Qwen2.5-VL OCR on rendered pages where readable, and
        # by linguistic context + char count elsewhere). Char counts match.
        'mojibake_fixes': [
            # Luke 1:6 — חקים (chuqqim, "statutes/decrees")
            ('Hebrew word ����, which signifies statutes or decrees',
             'Hebrew word חקים, which signifies statutes or decrees'),
            ('in Scripture ���� usually denotes those services',
             'in Scripture חקים usually denotes those services'),
            # Luke 1:13 — יהוחנן (Yehohanan, "John" in 1 Chr 3:15)
            ('the authority of his office. ������, (1 Chronicles 3:15,)',
             'the authority of his office. יהוחנן, (1 Chronicles 3:15,)'),
            # Luke 1:15 — שכר (shekar, "strong drink" = Greek σίκερα)
            ('like the Hebrew word ���, it denotes any sort of manufactured wine',
             'like the Hebrew word שכר, it denotes any sort of manufactured wine'),
            # Luke 1:31 — ישע (yesha, "salvation") + יושיע (yoshia', Hiphil "to save")
            ('It is derived from the Hebrew word ���, salvation',
             'It is derived from the Hebrew word ישע, salvation'),
            ('salvation, from which comes �����, which signifies to save',
             'salvation, from which comes יושיע, which signifies to save'),
            # Luke 1:31 — יהושוע (Yehoshua, "Joshua")
            ('that it differs from the Hebrew name ������, (Jehoshua or Joshua.)',
             'that it differs from the Hebrew name יהושוע, (Jehoshua or Joshua.)'),
            # Luke 1:79 — שלום (shalom, "peace")
            ('But as the Hebrew word ����, *peace,* denotes every kind of prosperity',
             'But as the Hebrew word שלום, *peace,* denotes every kind of prosperity'),
            # Matthew 1:21 — יהוה (YHWH, "Jehovah")
            ('the two words ᾿Ιησοῦς and ����*, Jesus* and *Jehovah,*',
             'the two words ᾿Ιησοῦς and יהוה*, Jesus* and *Jehovah,*'),
            # Matthew 1:21 — יושיע (yoshia', Hiphil verb)
            ('in the Hiphil conjugation, �����, which signifies *to save*',
             'in the Hiphil conjugation, יושיע, which signifies *to save*'),
            # Matthew 1:21 — יהושוע (Yehoshua)
            ('the Hebrew word ������, *Jehoshua,* or *Joshua,*',
             'the Hebrew word יהושוע, *Jehoshua,* or *Joshua,*'),
            # Matthew 1:23 — עלמה (almah, "virgin") + בעלמה (b'almah, "with a maid")
            ('the Hebrew word ����*, virgin*',
             'the Hebrew word עלמה*, virgin*'),
            ('“the way of a man with a maids,” �����,',
             '“the way of a man with a maids,” בעלמה,'),
            # Luke 2:14 — רצון (ratzon, "good-will" = Greek εὐδοκία)
            ('in Scripture in the sense of the Hebrew word ����, the old translator',
             'in Scripture in the sense of the Hebrew word רצון, the old translator'),
            # Matthew 2:23 — נזיר (nazir, "Nazirite") + נזר (nazar, "to separate") + נצר (netzer, "branch/flower")
            ('The word ����, or *Nazarite,* signifies *holy and devoted to God,*',
             'The word נזיר, or *Nazarite,* signifies *holy and devoted to God,*'),
            ('and is derived from ���, *to separate.*',
             'and is derived from נזר, *to separate.*'),
            ('The noun ���, indeed, signifies a *flower:*',
             'The noun נצר, indeed, signifies a *flower:*'),
            # Matthew 4:18 — כנרת (Kinneret, "Chinnereth")
            ('lake among the ancient Hebrews was ����, (*Chinnereth*;)',
             'lake among the ancient Hebrews was כנרת, (*Chinnereth*;)'),
            # Mark 3:17 — בני רגש (b'nei regesh, "sons of thunder" = Boanerges)
            ('the full pronunciation would be ��� ���, *(Benae-regesh;)*',
             'the full pronunciation would be בני רגש, *(Benae-regesh;)*'),
            # Matthew 5:20 — פרושים (Perushim, "Pharisees" / "Expounders")
            ('They were called ������, that is, *Expound-* *ers,*',
             'They were called פרושים, that is, *Expound-* *ers,*'),
            # Matthew 5:22 — גיא (gei, "valley" → Gehenna/Ge-Hinnom)
            ('foreign word. ���(*Ge*) is the Hebrew word for a valley',
             'foreign word. גיא (*Ge*) is the Hebrew word for a valley'),
            # Matthew 10:10 — שבט (shebet, "rod/staff")
            ('ambiguity in the use of the Hebrew word ���, *(shebet;)*',
             'ambiguity in the use of the Hebrew word שבט, *(shebet;)*'),
            # Matthew 10:12 — שלום (shalom, again)
            ('As the Hebrew word ����, *(shalom,) peace,*',
             'As the Hebrew word שלום, *(shalom,) peace,*'),
        ],
    },
    'harmony3': {
        'format': 'ccel_harmony',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_matai_make3.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/harmony3/harmony3_raw.txt'),
        'skip_pages': 8,
        'header_y_max': 62,
        'footnote_size_max': 9.5,
        'page_num_x_min': 450,
        'page_w': 612.0,
        'body_left': 108.0,
        'body_right': 504.0,
        # `centering` 同时门控 1) 居中检测 2) 多列经文检测
        # （split_block_by_columns 调用都在 if cfg.get('centering') 内）
        # harmony3 章首也是 3 栏共观经文，需要 multi-col 表，开
        'centering': True,
    },
    'matthew': {
        'format': 'ccel_parallel',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_matai_make2.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/harmony2/harmony2_raw.txt'),
        'skip_pages': 7,
        'header_y_max': 55,
        'footnote_size_max': 7.5,
        'extract_footnotes': True,
    },
    'acts1': {
        'format': 'ccel_acts',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_acts1.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/acts1/acts1_raw.txt'),
        'skip_pages': 6,
        'header_y_max': 55,
        'footer_y_min': 705,
        'footnote_size_max': 7.5,
    },
    'acts2': {
        'format': 'ccel_acts',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_acts2.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/acts2/acts2_raw.txt'),
        'skip_pages': 6,
        'header_y_max': 55,
        'footer_y_min': 705,
        'footnote_size_max': 7.5,
    },
    'heb': {
        'format': 'ages_heb',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_xibolaishu.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/heb/heb_raw.txt'),
        'skip_pages': 8,
        'header_y_max': 55,
        'latin_x_min': 200,
    },
    '1cor-vol1': {
        'format': 'ages_corinth',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_gelinduo1.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/1cor-vol1/calvin_1cor-vol1.md'),
        'table_split_x': 305,
        'skip_pages': set(range(6)) | {6, 19},
        'stop_page': 301,
        'greek': False,
        'verse_period': True,   # verse nums as "1." (with period)
    },
    '1cor-vol2': {
        'format': 'ages_corinth',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_gelinduo2.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/1cor-vol2/calvin_corinth-vol2.md'),
        'table_split_x': 305,
        'skip_pages': set(range(6)),
        'stop_page': None,
        'greek': True,
        'verse_period': False,  # verse nums "1" or "1." (normalized)
    },
    'phil': {
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin_filibi.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/phil/calvin_filibi_structured.txt'),
    },
    'john': {
        # Ages Digital Library single-column English (Pringle translation, 1998 typeset).
        # Diagnosed 2026-06: 410×626 page; single x0 peak ≈ 30; 878 <NNNNNN> Ages
        # scripture-ref markers; 21 chapters; "THE ARGUMENT" → "CHAPTER 1" structure.
        # Reusing ages_phil format as closest match (single-col Ages with <NNNNNN>).
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_JOHN.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/john/calvin_john_structured.txt'),
    },
    'acts': {
        # Ages Digital Library single-column English (Beveridge/Fetherstone tr).
        # Diagnosed 2026-06-08: 410×626 page, 886 pages, x0 peak 30 (body);
        # F#-prefixed sup footnote refs; Ages <NNNNNN> scripture markers;
        # 28 chapters across the whole book (acts1+acts2 merged in one PDF).
        # Same format family as john/eph/colossians → ages_phil extractor.
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_ACTS.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/acts/calvin_acts_structured.txt'),
    },
    'romans': {
        # Ages Digital Library single-column English. Diagnosed 2026-06:
        # 410×626 page; x0 双峰 (30/200) — 30 是 body, 200 是居中标题/题献。
        # 6 种颜色齐全 (#800000/#000080/#0000d4/#006411/#008080);
        # 21/50 sample 页有 <NNNNNN> Ages cross-ref. Same format as john.
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_ROMM.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/romans/calvin_romans_structured.txt'),
    },
    'galatians': {
        # Ages bilingual (same as romans). 410×626; x0 单峰 30 + bilingual
        # peak 220; 6 colors; 36/50 sample pages have Ages markers; 197 pages
        # (Galatians + Ephesians per Pringle ed. — check chapter range).
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_GALA.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/galatians/calvin_galatians_structured.txt'),
    },
    'ephesians': {
        # Ages bilingual. 410×626; 175 pages; x0 双峰 (30/220);
        # 5 colors (#800000/#000080/#0000d4/#008080); 37/50 sample Ages markers.
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_EPHS.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/ephesians/calvin_ephesians_structured.txt'),
    },
    'colossians': {
        # Ages bilingual. 410×626; 108 pages; x0 双峰 (30/220); 4 colors; 37/50 Ages markers.
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_COLO.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/colossians/calvin_colossians_structured.txt'),
    },
    'philemon': {
        # Ages bilingual. 410×626; 18 pages (single-chapter book); 4 colors.
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_PHLM.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/philemon/calvin_philemon_structured.txt'),
    },
    'zephaniah': {
        # Ages Digital Library single-col English. Diagnosed 2026-06-02:
        # 410×626 page; 145 pages; x0 单峰 30 + 缩进 220; 5 colors
        # (#800000/#000080/#0000d4/#006411/#008080); 25/50 sample pages have
        # Ages <NNNNNN> markers; 3 chapters (OT minor prophet).
        'format': 'ages_phil',
        'pdf':  '/Users/yanpeifa/Documents/论文/calvin/CAL_ZEPH.pdf',
        'out':  os.path.join(BASE, 'calvin_raw/zephaniah/calvin_zephaniah_structured.txt'),
    },
    # ── Batch 2026-06-02: Ages PDFs from sabda.org. Same format as Zephaniah. ──
    '1thessalonians':  { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_1THS.pdf', 'out': os.path.join(BASE, 'calvin_raw/1thessalonians/calvin_1thessalonians_structured.txt') },
    '2thessalonians':  { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_2THS.pdf', 'out': os.path.join(BASE, 'calvin_raw/2thessalonians/calvin_2thessalonians_structured.txt') },
    '1timothy':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_1TIM.pdf', 'out': os.path.join(BASE, 'calvin_raw/1timothy/calvin_1timothy_structured.txt') },
    '2timothy':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_2TIM.pdf', 'out': os.path.join(BASE, 'calvin_raw/2timothy/calvin_2timothy_structured.txt') },
    'titus':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_TITU.pdf', 'out': os.path.join(BASE, 'calvin_raw/titus/calvin_titus_structured.txt') },
    'james':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JAME.pdf', 'out': os.path.join(BASE, 'calvin_raw/james/calvin_james_structured.txt') },
    '1peter':          { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_1PET.pdf', 'out': os.path.join(BASE, 'calvin_raw/1peter/calvin_1peter_structured.txt') },
    '2peter':          { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_2PET.pdf', 'out': os.path.join(BASE, 'calvin_raw/2peter/calvin_2peter_structured.txt') },
    '1john':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_1JOH.pdf', 'out': os.path.join(BASE, 'calvin_raw/1john/calvin_1john_structured.txt') },
    'jude':            { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JUDE.pdf', 'out': os.path.join(BASE, 'calvin_raw/jude/calvin_jude_structured.txt') },
    'genesis':         { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_GENE.pdf', 'out': os.path.join(BASE, 'calvin_raw/genesis/calvin_genesis_structured.txt') },
    'joshua':          { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JOSH.pdf', 'out': os.path.join(BASE, 'calvin_raw/joshua/calvin_joshua_structured.txt') },
    'lamentations':    { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_LAMN.pdf', 'out': os.path.join(BASE, 'calvin_raw/lamentations/calvin_lamentations_structured.txt') },
    'ezekiel':         { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_EZEK.pdf', 'out': os.path.join(BASE, 'calvin_raw/ezekiel/calvin_ezekiel_structured.txt') },
    'daniel':          { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_DANL.pdf', 'out': os.path.join(BASE, 'calvin_raw/daniel/calvin_daniel_structured.txt') },
    'hosea':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HOSE.pdf', 'out': os.path.join(BASE, 'calvin_raw/hosea/calvin_hosea_structured.txt') },
    'joel':            { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JOEL.pdf', 'out': os.path.join(BASE, 'calvin_raw/joel/calvin_joel_structured.txt') },
    'amos':            { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_AMOS.pdf', 'out': os.path.join(BASE, 'calvin_raw/amos/calvin_amos_structured.txt') },
    'obadiah':         { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_OBDH.pdf', 'out': os.path.join(BASE, 'calvin_raw/obadiah/calvin_obadiah_structured.txt') },
    'jonah':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JONH.pdf', 'out': os.path.join(BASE, 'calvin_raw/jonah/calvin_jonah_structured.txt') },
    'micah':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_MICA.pdf', 'out': os.path.join(BASE, 'calvin_raw/micah/calvin_micah_structured.txt') },
    'nahum':           { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_NAHM.pdf', 'out': os.path.join(BASE, 'calvin_raw/nahum/calvin_nahum_structured.txt') },
    'habakkuk':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HABK.pdf', 'out': os.path.join(BASE, 'calvin_raw/habakkuk/calvin_habakkuk_structured.txt') },
    'haggai':          { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HAGG.pdf', 'out': os.path.join(BASE, 'calvin_raw/haggai/calvin_haggai_structured.txt') },
    'zechariah':       { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_ZECH.pdf', 'out': os.path.join(BASE, 'calvin_raw/zechariah/calvin_zechariah_structured.txt') },
    'malachi':         { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_MALC.pdf', 'out': os.path.join(BASE, 'calvin_raw/malachi/calvin_malachi_structured.txt') },
    'isaiah-1':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_ISA1.pdf', 'out': os.path.join(BASE, 'calvin_raw/isaiah-1/calvin_isaiah-1_structured.txt') },
    'isaiah-2':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_ISA2.pdf', 'out': os.path.join(BASE, 'calvin_raw/isaiah-2/calvin_isaiah-2_structured.txt') },
    'jeremiah-1':      { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JER1.pdf', 'out': os.path.join(BASE, 'calvin_raw/jeremiah-1/calvin_jeremiah-1_structured.txt') },
    'jeremiah-2':      { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_JER2.pdf', 'out': os.path.join(BASE, 'calvin_raw/jeremiah-2/calvin_jeremiah-2_structured.txt') },
    'psalms-1':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_PSA1.pdf', 'out': os.path.join(BASE, 'calvin_raw/psalms-1/calvin_psalms-1_structured.txt') },
    'psalms-2':        { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_PSA2.pdf', 'out': os.path.join(BASE, 'calvin_raw/psalms-2/calvin_psalms-2_structured.txt') },
    # Calvin's Harmony of the Law (4 vols) — covers Exodus + Leviticus +
    # Numbers + Deuteronomy in topical / parallel-passage arrangement.
    # Calvin never wrote a sequential Exodus commentary; this Harmony is
    # his treatment of those 4 books. Same Ages 410×626 format.
    'harmony-law-1':   { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HAL1.pdf', 'out': os.path.join(BASE, 'calvin_raw/harmony-law-1/calvin_harmony-law-1_structured.txt') },
    'harmony-law-2':   { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HAL2.pdf', 'out': os.path.join(BASE, 'calvin_raw/harmony-law-2/calvin_harmony-law-2_structured.txt') },
    'harmony-law-3':   { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HAL3.pdf', 'out': os.path.join(BASE, 'calvin_raw/harmony-law-3/calvin_harmony-law-3_structured.txt') },
    'harmony-law-4':   { 'format': 'ages_phil', 'pdf': '/Users/yanpeifa/Documents/论文/calvin/CAL_HAL4.pdf', 'out': os.path.join(BASE, 'calvin_raw/harmony-law-4/calvin_harmony-law-4_structured.txt') },
}


# ══════════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def get_first_span(block):
    lines = block.get('lines', [])
    if not lines:
        return None
    spans = lines[0].get('spans', [])
    return spans[0] if spans else None


def get_block_text(block):
    return '\n'.join(
        ''.join(s['text'] for s in line.get('spans', []))
        for line in block.get('lines', [])
    )


def _make_sub_block(orig, lines):
    if not lines:
        return orig
    y0 = lines[0]['bbox'][1]
    y1 = lines[-1]['bbox'][3]
    return {'type': 0, 'bbox': [orig['bbox'][0], y0, orig['bbox'][2], y1], 'lines': lines}


def write_txt_output(blocks, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for block in blocks:
            f.write(block + '\n\n')
    print(f'Written: {out_path}')
    print(f'Total blocks: {len(blocks)}')


# ══════════════════════════════════════════════════════════════════════════════
# CCEL HARMONY FORMAT  (matthew1, harmony3)
# Single-column CCEL PDF; gospel book name headers; optional centering detection
# ══════════════════════════════════════════════════════════════════════════════

_LINE_BREAK = {'__line_break__': True}


_QUOTE_ANY   = r'["“”\'‘’]'
_QUOTE_DOUBLE = r'["“”]'
_RE_SPLIT_IT_QUOTE_A = re.compile(
    rf'\*({_QUOTE_ANY})\*([^*]+?)\*([,.;:!?]*{_QUOTE_ANY})\*'
)
_RE_SPLIT_IT_QUOTE_B = re.compile(
    rf'\*({_QUOTE_ANY})\*([^*]+?{_QUOTE_DOUBLE})'
)


def _fix_split_italic_quotes(text):
    """PDF 中引文起讫的双引号常被单独提取为 italic span，markdown 产出
    `*“*X*,”*`（两侧都 italic）或 `*“*X”`（只 open italic），kramdown 渲染时
    两侧 `*` 无法配对 → 显示成字面星号。解决：扩 italic 范围到包整段引文。

    Pattern A：两侧均有 `*` 包引号 → 移除内部 `*`，italic 包整句
    Pattern B：仅 open 有 `*` 包引号 → 补 close `*` 包整句

    apostrophe `'`/`'` 故意从 Pattern B 的 close 集合中排除，避免被
    `king'*s` 这种英文 possessive 误截断。"""
    text = _RE_SPLIT_IT_QUOTE_A.sub(r'*\1\2\3*', text)
    text = _RE_SPLIT_IT_QUOTE_B.sub(r'*\1\2*', text)
    return text


def ccel_spans_to_md(lines, fn_size_max=None):
    """Convert block lines to Markdown, normalising bold verse numbers → **N.**

    When `fn_size_max` is provided, superscript digit spans below that font size
    are rewritten as Kramdown footnote references (`[^N]`)."""
    all_spans = []
    for li, line in enumerate(lines):
        all_spans.extend(line.get('spans', []))
        if li < len(lines) - 1:
            all_spans.append(_LINE_BREAK)

    parts = []
    i = 0
    while i < len(all_spans):
        span = all_spans[i]
        if span is _LINE_BREAK:
            if parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        t = span['text']
        flags = span.get('flags', 0)
        is_bold   = bool(flags & 16)
        is_italic = bool(flags & 2)
        is_sup    = bool(flags & 1)

        # Inline footnote reference: small-font digit span (CCEL inconsistently
        # sets the superscript flag — detect by font size instead).
        if (fn_size_max is not None and t.strip().isdigit()
                and span.get('size', 99) < fn_size_max + 1):
            # Strip any trailing space on previous part — Markdown ref glues to word
            if parts and parts[-1].endswith(' '):
                parts[-1] = parts[-1].rstrip()
            parts.append(f'[^{t.strip()}]')
            i += 1
            continue

        # Normalise verse number: bold digit(s) → **N.**
        if is_bold and re.match(r'^\d+$', t.strip()):
            num = t.strip()
            j = i + 1
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            # consume optional non-bold period
            if (j < len(all_spans) and all_spans[j] is not _LINE_BREAK
                    and all_spans[j]['text'].strip() in ('.', '.\xa0', '')
                    and not (all_spans[j]['flags'] & 16)):
                j += 1
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            # consume optional bold NBSP
            while (j < len(all_spans) and all_spans[j] is not _LINE_BREAK
                   and not all_spans[j]['text'].strip()
                   and (all_spans[j]['flags'] & 16)):
                j += 1
            parts.append(f'**{num}.**')
            i = j
            continue

        stripped = t.strip()
        if not stripped:
            if t and parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        if is_bold and is_italic:
            parts.append(f'{lead}***{stripped}***{tail}')
        elif is_bold:
            parts.append(f'{lead}**{stripped}**{tail}')
        elif is_italic:
            parts.append(f'{lead}*{stripped}*{tail}')
        else:
            parts.append(t)
        i += 1

    result = ''.join(parts)
    # 合并同 style 紧邻 span：PDF 中 `Matthew 5:42.` 的 bold 有时被切成
    # `Matthew 5:42` + `.` 两段，产出 `**Matthew 5:42****.**` 让 kramdown
    # 渲染成两个 <strong>，破坏 verse-nav 的 `Book Ch:N\.` 整体匹配
    result = result.replace('****', '')
    # 修正引文 italic 只包到引号字符（PDF 中引号常被单独切成 italic span）
    # `*“*X*,”*` → `*“X,”*` ；`*“*X”` → `*“X”*`
    result = _fix_split_italic_quotes(result)
    return re.sub(r' {2,}', ' ', result).strip()


def ccel_fix_hyphenation(text):
    return re.sub(r'-\s+([a-z])', r'\1', text)


def ccel_harmony_is_running_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    span = get_first_span(block)
    return span is not None and bool(span.get('flags', 0) & 2)


def ccel_harmony_is_page_number(block, cfg):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    return block['bbox'][0] > cfg['page_num_x_min']


def ccel_harmony_is_footnote(block, cfg):
    span = get_first_span(block)
    return span is not None and span.get('size', 0) < cfg['footnote_size_max']


def parse_ccel_footnote_block(block):
    """Parse a CCEL footnote block into a list of (num, text) tuples.

    A footnote block at the bottom of a page contains 1+ footnotes laid out as:
        <num>
        text line 1
        text line 2
        <next num>
        text…
    The leading `<num>` is a separate line whose stripped text is just digits.

    The printed page number (a stray digit line at the very end of the block)
    is dropped; entries without any body text are also dropped (avoids spurious
    "[^N]: " entries when a continuation block ends with the page number)."""
    raw_lines = []
    for line in block.get('lines', []):
        spans = [s for s in line.get('spans', []) if s['text'].strip()]
        if not spans:
            continue
        raw_lines.append(''.join(s['text'] for s in spans).strip())

    # Trailing standalone digit = printed page number, not a footnote start
    while raw_lines and raw_lines[-1].isdigit():
        raw_lines.pop()

    entries = []
    cur_num = None
    cur_lines = []
    for line_text in raw_lines:
        if line_text.isdigit() and (cur_num is None or cur_lines):
            if cur_num is not None and cur_lines:
                entries.append((cur_num, ' '.join(cur_lines).strip()))
            cur_num = line_text
            cur_lines = []
        else:
            cur_lines.append(line_text)
    if cur_num is not None and cur_lines:
        entries.append((cur_num, ' '.join(cur_lines).strip()))
    return entries


def ccel_harmony_is_index_start(block):
    return bool(re.match(
        r'^(Indexes?$|Index of (Scripture|Greek|Hebrew|Latin|French))',
        get_block_text(block).strip(), re.I))


def ccel_harmony_is_section_header(block):
    span = get_first_span(block)
    if not span or span.get('color', 0) != 0 or span.get('size', 0) < 10.0:
        return False
    first = span['text'].strip()
    return bool(first) and first == first.upper() and bool(
        re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', first))


def ccel_harmony_is_blue_label(block):
    span = get_first_span(block)
    if not span:
        return False
    return span.get('color', 0) == 255 and not (span.get('flags', 0) & 16)


def ccel_harmony_norm(text):
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    return re.sub(r':\s+(\d)', r':\1', text)


def split_block_by_columns(block, page_mid, col_gap_min=50, expected_slot_x0s=None):
    """If `block` is laid out in N parallel columns (e.g. CCEL synoptic
    genealogy or 3-gospel parallel passages), return list of N line-lists
    ordered left-to-right. Otherwise None.

    Detection: cluster line x0 values; if 2+ clusters separated by gaps
    > col_gap_min, treat as multi-column. Each line is assigned to its
    nearest cluster center.

    Without `expected_slot_x0s`: every column needs ≥ 3 lines + 20%+ y-axis
    column alternation (filters正文带几行居中的假阳性).

    With `expected_slot_x0s`（section header 已锁定列布局）：放宽到每列
    ≥ 1 行 + 跳过交替检查（信任 header 标的布局；处理极短并列段，如
    Luke 16:17 仅 1 行对应 Matt 5:17 多行）。
    """
    lines = block.get('lines', [])
    min_lines = 3 if expected_slot_x0s is None else 2
    if len(lines) < min_lines:
        return None

    line_x0s = []
    for line in lines:
        spans = [s for s in line.get('spans', []) if s['text'].strip()]
        if not spans:
            continue
        line_x0s.append((spans[0]['bbox'][0], line))

    # section_col_layout 锁定时降到 2 行（处理 Luke 16:17 仅 1 行 + Matt 5:17 2 行）
    nonempty_min = 2 if expected_slot_x0s is not None else 6
    if len(line_x0s) < nonempty_min:
        return None

    # 列中心：若 section 已锁定 layout，直接用 expected_slot_x0s（跳过聚类
    # 避免 outlier 把主簇串成一团 + 处理极短并列段）；否则按 1D 聚类。
    if expected_slot_x0s is not None:
        centers = list(expected_slot_x0s)
    else:
        from collections import Counter
        x0_freq = Counter(round(x) for x, _ in line_x0s)
        main_x0s = sorted(x for x, c in x0_freq.items() if c >= 3)
        if not main_x0s:
            return None
        clusters = [[main_x0s[0]]]
        for x in main_x0s[1:]:
            if x - clusters[-1][-1] < col_gap_min:
                clusters[-1].append(x)
            else:
                clusters.append([x])

        if len(clusters) < 2:
            return None

        centers = [sum(c) / len(c) for c in clusters]

    # 把每行分到最近的列；outlier 行（x0 在簇外）也归到距离最近的列
    # 把每行分到最近的列；outlier 行也归到距离最近的列。
    # 对宽到跨列的整行（line bbox 宽度超过单列槽宽 1.4x），按 span 级 x 中心
    # 拆分到各列——处理 PDF 偶有的一行物理跨越两列的边角情况。
    col_slot_w = ((max(centers) - min(centers)) / max(len(centers) - 1, 1)
                   if len(centers) >= 2 else 200)
    cross_thresh = max(col_slot_w * 1.4, 200)
    column_lines = [[] for _ in centers]
    for x0, line in line_x0s:
        bbox = line.get('bbox')
        line_w = (bbox[2] - bbox[0]) if bbox else 0
        spans = [s for s in line.get('spans', []) if s['text'].strip()]
        # 跨列检测：line 宽度超阈值 AND 相邻 span 之间有显著空白（> 25px，
        # 即真有列间隔），才视为物理跨列。普通全宽叙述行（含上标脚注 ref
        # 这种紧贴的多 span）虽然宽度大但 span 间无空白，按整行 x0 归列。
        is_cross = False
        if line_w > cross_thresh and len(spans) >= 2:
            spans_sorted = sorted(spans, key=lambda s: s['bbox'][0])
            for i in range(1, len(spans_sorted)):
                gap = spans_sorted[i]['bbox'][0] - spans_sorted[i-1]['bbox'][2]
                sp = spans_sorted[i]
                # bold 数字 span = 新节号开始 → 必属下一列（如 Mark 2:22 末 +
                # Luke 5:39 起在同一物理行的情形）；区分于 sup 脚注 ref。
                is_verse_marker = (
                    (sp.get('flags', 0) & 16)
                    and sp['text'].strip().rstrip('.').isdigit()
                )
                if gap > 25 or is_verse_marker:
                    is_cross = True
                    break
        if is_cross:
            per_col_sps = [[] for _ in centers]
            for s in spans:
                sc = (s['bbox'][0] + s['bbox'][2]) / 2
                best = min(range(len(centers)), key=lambda i: abs(centers[i] - sc))
                per_col_sps[best].append(s)
            for col_idx, col_sps in enumerate(per_col_sps):
                if col_sps:
                    column_lines[col_idx].append({'spans': col_sps, 'bbox': line['bbox']})
        else:
            best = min(range(len(centers)), key=lambda i: abs(centers[i] - x0))
            column_lines[best].append(line)

    # 把行数 < 3 的「小簇」并入最近的主列（处理尾续接、宽行 wrap 的 outlier x0）
    # section_col_layout 锁定时降到 ≥ 1 行，处理极短并列段
    main_threshold = 1 if expected_slot_x0s is not None else 3
    main = [i for i in range(len(centers)) if len(column_lines[i]) >= main_threshold]
    if len(main) < 2:
        return None
    if len(main) != len(centers):
        new_col_lines = [[] for _ in main]
        new_centers   = [centers[i] for i in main]
        for i, lines in enumerate(column_lines):
            target = i if i in main else min(
                range(len(main)), key=lambda k: abs(new_centers[k] - centers[i]))
            target_idx = main.index(i) if i in main else target
            new_col_lines[target_idx].extend(lines)
        column_lines = new_col_lines
        centers      = new_centers

    # 每列至少 N 行：默认 3 行避免误判；当 section header 已锁定布局
    # （expected_slot_x0s 非 None）时降为 1 行
    per_col_min = 1 if expected_slot_x0s is not None else 3
    sizes = [len(c) for c in column_lines]
    if min(sizes) < per_col_min:
        return None
    # section_col_layout 锁定时跳过 y-轴交替检查（极短并列段无须验证）
    if expected_slot_x0s is not None:
        for col in column_lines:
            col.sort(key=lambda l: l['bbox'][1])
        return column_lines
    # 列与列必须在 y 方向上反复交替（真多列），而非「一大段单列 + 少量居中行」。
    # 按 y 排序所有候选行，给出原属列序号；转换次数 / 总行数 < 0.2 视为误判。
    by_y = sorted(line_x0s, key=lambda p: p[1]['bbox'][1])
    col_seq = []
    for x0, line in by_y:
        col_seq.append(min(range(len(centers)), key=lambda i: abs(centers[i] - x0)))
    transitions = sum(1 for i in range(1, len(col_seq)) if col_seq[i] != col_seq[i-1])
    if transitions / max(len(col_seq), 1) < 0.20:
        return None
    for col in column_lines:
        col.sort(key=lambda l: l['bbox'][1])
    return column_lines


def split_lines_by_paragraph_indent(lines, body_left,
                                    indent_min=10, indent_max=60):
    """Split a sequence of lines into paragraph groups where a non-first line
    that starts ~18px right of `body_left` marks a new paragraph (PDF first-
    line indent). Centered/blockquote lines should already be removed before
    calling this."""
    groups, cur, first_seen = [], [], False
    for line in lines:
        spans = [s for s in line.get('spans', []) if s['text'].strip()]
        if not spans:
            cur.append(line)
            continue
        x0 = spans[0]['bbox'][0]
        indent = x0 - body_left
        is_para_start = first_seen and indent_min <= indent <= indent_max
        if is_para_start and cur:
            groups.append(cur)
            cur = []
        cur.append(line)
        first_seen = True
    if cur:
        groups.append(cur)
    return groups


def classify_lines_by_centering(lines, cfg):
    """Split lines into groups of [is_centered, [line, ...]].
    Promotes preceding closing-quote line into the same centered group."""
    body_w  = cfg['body_right'] - cfg['body_left']
    page_cx = cfg['page_w'] / 2

    classified = []
    line_lms   = []
    for line in lines:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            continue
        lx0  = spans[0]['bbox'][0]
        lx1  = spans[-1]['bbox'][2]
        w    = lx1 - lx0
        cx   = (lx0 + lx1) / 2
        text = ''.join(s['text'] for s in spans).strip()
        left_margin  = lx0 - cfg['body_left']
        right_margin = cfg['body_right'] - lx1
        is_c = (
            abs(cx - page_cx) < 3
            and left_margin  > 2
            and right_margin > 2
        )
        classified.append([is_c, line, text])
        line_lms.append(left_margin)

    # Reject uniform-margin runs: a justified block quote (e.g. CCEL chapter
    # scripture heading rendered in a narrower column) gives every line the
    # same lm/rm and would otherwise look centered. A genuine centered block
    # has at least one line with substantial left margin (>10px) — usually a
    # short last line or citation. Without such an anchor, drop the run.
    n = len(classified)
    i = 0
    while i < n:
        if classified[i][0]:
            j = i
            while j < n and classified[j][0]:
                j += 1
            if not any(line_lms[k] > 10 for k in range(i, j)):
                for k in range(i, j):
                    classified[k][0] = False
            i = j
        else:
            i += 1

    for i in range(1, len(classified)):
        if classified[i][0] and not classified[i - 1][0]:
            if classified[i - 1][2].endswith(('"', ',"', ';"', '."', '"', ',"')):
                classified[i - 1][0] = True

    # Promote wide scripture-quote heads. When a multi-line centered quotation
    # has its top lines wide enough to span the full body width, the per-line
    # margin signal vanishes (lm=0/rm=0, indistinguishable from justified body
    # text). Detect by content: a line that begins with an opening curly quote
    # AND has cx pinned to page center AND can reach an already-centered line
    # (citation anchor) within a few cx-aligned steps forward → promote the
    # opening-quote line and every line up to that anchor.
    def _cx_aligned(idx):
        spans = [s for s in classified[idx][1].get('spans', []) if s['text'].strip()]
        if not spans:
            return False
        cx = (spans[0]['bbox'][0] + spans[-1]['bbox'][2]) / 2
        return abs(cx - page_cx) < 3

    for i in range(len(classified) - 1):
        if classified[i][0]:
            continue
        text = classified[i][2]
        if not text or text[0] not in ('"', '“', '‘'):
            continue
        if not _cx_aligned(i):
            continue
        for j in range(i + 1, min(len(classified), i + 5)):
            if not _cx_aligned(j):
                break
            if classified[j][0]:
                for k in range(i, j):
                    classified[k][0] = True
                break

    groups = []
    for is_c, line, _ in classified:
        if groups and groups[-1][0] == is_c:
            groups[-1][1].append(line)
        else:
            groups.append([is_c, [line]])
    return groups


def extract_ccel_harmony(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Total pages: {total}, processing {cfg['skip_pages'] + 1}–{total}")

    output_blocks    = []
    pending_fns      = []   # footnote defs buffered until next section header / EOF
    last_section_upper = None
    last_col_centers   = None   # 最近多列块的列中心 x，用于识别尾续接短块
    # 本节首次多列识别确立的列布局 (n_cols, col_x0s)。后续多列块按 x0 重映射到
    # 此布局，避免「3 列 + 2 列 + 2 列」混搭时 col 索引错位（如 Luke 续接段
    # 被错配到 Mark 列）
    section_col_layout = None

    def flush_section_header(label):
        # Emit any pending footnote defs from the just-finished section BEFORE
        # the new header — keeps defs out of the body paragraph flow so blank
        # lines around them don't fragment the paragraph that surrounds them.
        if pending_fns:
            output_blocks.extend(pending_fns)
            pending_fns.clear()
        output_blocks.append(f'\n## {label}\n')

    def cols_look_like_commentary(cols):
        """检查 cols 是否含注释信号——避免把窄列注释（如分栏 commentary）
        错认作多列经文。任何一列出现 *italic*（去 **bold** 后）或
        **Book Ch:N.** 起首，即视为注释。"""
        for col_lines in cols:
            text = ''.join(s['text'] for ln in col_lines
                           for s in (ln.get('spans') or []) if s['text'].strip())
            if re.match(r'^\*?\*?[A-Z][a-z]+ \d+:\d+', text.strip()):
                return True
            # ccel_spans_to_md 会把 italic span 包成 *...*，但 PDF 原 text 没标记，
            # 用 italic flag 判断
            for ln in col_lines:
                for s in ln.get('spans', []):
                    if s.get('flags', 0) & 2 and s['text'].strip():
                        # 含斜体 span，且斜体不是脚注上标——是注释
                        if not (s.get('flags', 0) & 1 and s['text'].strip().isdigit()):
                            return True
        return False

    def emit_multi_col(cols):
        """Emit detected multi-col cols, update last_col_centers / x0s.

        若本 section 已经确立列布局（section_col_layout 非 None），按 x0
        把本次 cols 重映射到该布局，使后续多列块共用同一索引空间。

        Returns:
            True  → 成功 emit
            False → cols 被识别为注释，已拒绝；调用方应 fall through 到单
                    列处理
        """
        nonlocal last_col_centers, section_col_layout
        # 注释过滤——所有进入 emit 的 cols 都必须通过该闸门，避免重构/新增
        # 调用路径时漏检（曾因调用方各自判断而错过 cross-block merge 路径）
        if cols_look_like_commentary(cols):
            return False
        n_cols = len(cols)
        centers = []
        col_x0s  = []
        per_col_x0_local = []   # 本次 emit 各列的 x0 中位数，按 cols 顺序
        for col_lines in cols:
            xs0 = sorted(s['bbox'][0] for ln in col_lines
                         for s in (ln.get('spans') or [])
                         if s['text'].strip())
            xs1 = sorted(s['bbox'][2] for ln in col_lines
                         for s in (ln.get('spans') or [])
                         if s['text'].strip())
            if xs0 and xs1:
                per_col_x0_local.append(xs0[len(xs0)//2])
                centers.append((xs0[len(xs0)//2] + xs1[len(xs1)//2]) / 2)
            else:
                per_col_x0_local.append(None)
                centers.append(None)

        # 决定输出用的 (out_n_cols, mapping[local_col_idx] -> out_col_idx)
        if section_col_layout is not None:
            out_n_cols, layout_x0s = section_col_layout
            mapping = []
            for x in per_col_x0_local:
                if x is None:
                    mapping.append(0)
                else:
                    best = min(range(len(layout_x0s)),
                               key=lambda i: abs((layout_x0s[i] or 1e9) - x))
                    mapping.append(best)
        else:
            out_n_cols = n_cols
            mapping = list(range(n_cols))
            section_col_layout = (n_cols, list(per_col_x0_local))

        # 发射 sentinel + 内容
        for local_idx, col_lines in enumerate(cols):
            md = ccel_fix_hyphenation(ccel_spans_to_md(col_lines, cfg.get('footnote_size_max')))
            if md:
                output_blocks.append(
                    f'<!--SCRIPTURE col={mapping[local_idx]} of={out_n_cols}-->\n{md}'
                )
            col_x0s.append(per_col_x0_local[local_idx])
        last_col_centers = (out_n_cols, centers, col_x0s)
        return True

    def block_looks_like_scripture_fragment(blk):
        """块小且像经文片段（含「数字.字母」节号样式 N.X 或 **N.**）。
        用来判断能否与下一块合并做跨 block 多列检测。"""
        if len(blk.get('lines', [])) > 12:
            return False
        text = get_block_text(blk)
        # 匹配 "5. And" / "5.And" / "5.\xa0And"（PDF 原文节号常以数字.接字母）
        return bool(re.search(r'\b\d+\.\s*[A-Za-z]', text[:200]))

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        # 索引推进而非 for-loop，便于跨 block 合并多列检测
        bi = 0
        while bi < len(blocks):
            block = blocks[bi]
            if block['type'] != 0:
                bi += 1; continue
            if ccel_harmony_is_running_header(block, cfg):
                bi += 1; continue
            if ccel_harmony_is_page_number(block, cfg):
                bi += 1; continue
            if ccel_harmony_is_footnote(block, cfg):
                if cfg.get('extract_footnotes'):
                    for num, fn_text in parse_ccel_footnote_block(block):
                        pending_fns.append(f'[^{num}]: {fn_text}')
                bi += 1; continue
            text = get_block_text(block).strip()
            if not text:
                bi += 1; continue

            if ccel_harmony_is_index_start(block):
                print(f'Stopping at index on page {page_idx + 1}')
                doc.close()
                if pending_fns:
                    output_blocks.extend(pending_fns)
                    pending_fns.clear()
                if cfg.get('mojibake_fixes'):
                    output_blocks = [apply_mojibake_fixes(b, cfg['mojibake_fixes']) for b in output_blocks]
                write_txt_output(output_blocks, cfg['out'])
                print(f"Sections: {sum(1 for b in output_blocks if b.startswith(chr(10) + '## '))}")
                return

            if ccel_harmony_is_section_header(block):
                norm = ccel_harmony_norm(text).upper()
                flush_section_header(norm)
                last_section_upper = norm
                last_col_centers = None
                # 按 section header 中**不同卷名**预先确立列布局（不是简单数
                # `;`——如「MARK 9:49-50; 4:21; LUKE 14:34-35; 8:16」一段
                # 里 4:21、8:16 等不带卷名前缀的部分是同卷续引）：
                parts = [p.strip() for p in norm.split(';')]
                books = []
                for p in parts:
                    bm = re.match(r'^([A-Z]+)\b', p)
                    if bm and bm.group(1) not in books:
                        books.append(bm.group(1))
                n_books = len(books)
                if n_books >= 2:
                    bl = cfg['body_left']; br = cfg['body_right']
                    slot_w = (br - bl) / n_books
                    slot_x0s = [bl + i * slot_w + 5 for i in range(n_books)]
                    section_col_layout = (n_books, slot_x0s)
                else:
                    section_col_layout = None
                bi += 1; continue

            if ccel_harmony_is_blue_label(block):
                label = ccel_harmony_norm(text).upper()
                if not re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', label):
                    bi += 1; continue
                x0 = block['bbox'][0]
                if x0 > 118:
                    if label != last_section_upper:
                        flush_section_header(label)
                        last_section_upper = label
                else:
                    if last_section_upper is None:
                        flush_section_header(label)
                        last_section_upper = label
                bi += 1; continue

            # Body block
            if cfg.get('centering'):
                # 1) 跨 block 前瞻合并多列检测：当前是经文小片段（≤12 行），
                #    尝试与紧邻的下一块合并 line 集再做多列检测。命中则一并消费，
                #    解决 PyMuPDF 把章首多列经文拆成「小 intro 块 + 主体大块」
                #    导致 intro 片段被孤立 emit 的问题。
                if (block_looks_like_scripture_fragment(block)
                        and bi + 1 < len(blocks)):
                    nb = blocks[bi + 1]
                    can_merge = (nb['type'] == 0
                                 and not ccel_harmony_is_running_header(nb, cfg)
                                 and not ccel_harmony_is_page_number(nb, cfg)
                                 and not ccel_harmony_is_footnote(nb, cfg)
                                 and not ccel_harmony_is_section_header(nb))
                    if can_merge:
                        fake_blk = {'lines': list(block['lines']) + list(nb['lines'])}
                        expected = section_col_layout[1] if section_col_layout else None
                        cols = split_block_by_columns(fake_blk, cfg['page_w'] / 2,
                                                      expected_slot_x0s=expected)
                        if cols and emit_multi_col(cols):
                            bi += 2
                            continue

                # 2) 直接对当前块跑多列检测
                expected = section_col_layout[1] if section_col_layout else None
                cols = split_block_by_columns(block, cfg['page_w'] / 2,
                                              expected_slot_x0s=expected)
                if cols and emit_multi_col(cols):
                    bi += 1; continue

                # 2.5) 跨页单列续接块：前面 emit 过多列，当前块所有行宽度
                #      明显窄于全宽正文（< 200px = 单列宽度），按 x0 或 cx
                #      匹配最近的列即作为该列延续 emit
                if last_col_centers is not None:
                    n_cols, centers, col_x0s = last_col_centers
                    nonempty = [l for l in block.get('lines', [])
                                if any(s['text'].strip() for s in l.get('spans', []))]
                    if nonempty:
                        line_x0s = [next(s['bbox'][0] for s in ln['spans']
                                          if s['text'].strip()) for ln in nonempty]
                        line_x1s = [max(s['bbox'][2] for s in ln['spans']
                                          if s['text'].strip()) for ln in nonempty]
                        widths = [x1 - x0 for x0, x1 in zip(line_x0s, line_x1s)]
                        if max(widths) < 200:
                            line_x0_med = sorted(line_x0s)[len(line_x0s)//2]
                            line_xc_med = (line_x0_med + sorted(line_x1s)[len(line_x1s)//2]) / 2
                            best_i = None
                            # 优先按 x0 精确匹配（同列直接续接）
                            valid_x0 = [(i, x) for i, x in enumerate(col_x0s) if x is not None]
                            if valid_x0:
                                ci, cx = min(valid_x0, key=lambda p: abs(p[1] - line_x0_med))
                                if abs(cx - line_x0_med) < 30:
                                    best_i = ci
                            # 兜底：按 cx 与列中心匹配（前页多列检测漏列时使用）
                            if best_i is None:
                                valid_c = [(i, c) for i, c in enumerate(centers) if c is not None]
                                if valid_c:
                                    ci, c = min(valid_c, key=lambda p: abs(p[1] - line_xc_med))
                                    if abs(c - line_xc_med) < 80:
                                        best_i = ci
                            if best_i is not None:
                                md = ccel_fix_hyphenation(ccel_spans_to_md(
                                    nonempty, cfg.get('footnote_size_max')))
                                if md:
                                    output_blocks.append(
                                        f'<!--SCRIPTURE col={best_i} of={n_cols}-->\n{md}'
                                    )
                                    bi += 1; continue

                # 3) 尾续接短块（PDF 跨页常见）：紧接多列块、1-2 行、x 匹配某列
                if last_col_centers is not None:
                    n_cols, centers, _x0s = last_col_centers
                    nonempty_lines = [l for l in block.get('lines', [])
                                      if any(s['text'].strip() for s in l.get('spans', []))]
                    if 1 <= len(nonempty_lines) <= 2:
                        sps = [s for s in nonempty_lines[0]['spans'] if s['text'].strip()]
                        if sps:
                            xc = (sps[0]['bbox'][0] + sps[-1]['bbox'][2]) / 2
                            valid = [(i, c) for i, c in enumerate(centers) if c is not None]
                            if valid:
                                best_i, best_c = min(valid, key=lambda p: abs(p[1] - xc))
                                if abs(best_c - xc) < 60:
                                    md = ccel_fix_hyphenation(ccel_spans_to_md(
                                        nonempty_lines, cfg.get('footnote_size_max')))
                                    if md:
                                        output_blocks.append(
                                            f'<!--SCRIPTURE col={best_i} of={n_cols}-->\n{md}'
                                        )
                                        bi += 1; continue
                last_col_centers = None   # 非尾续接则重置

                # 4) 单列处理：按 centering 分组 + 按段首缩进拆段
                for is_c, grp_lines in classify_lines_by_centering(block.get('lines', []), cfg):
                    if is_c:
                        md = ccel_fix_hyphenation(ccel_spans_to_md(grp_lines, cfg.get('footnote_size_max')))
                        if md:
                            output_blocks.append(f'<p style="text-align:center">{md}</p>')
                    else:
                        for para_lines in split_lines_by_paragraph_indent(grp_lines, cfg['body_left']):
                            md = ccel_fix_hyphenation(ccel_spans_to_md(para_lines, cfg.get('footnote_size_max')))
                            if md:
                                output_blocks.append(md)
            else:
                md = ccel_fix_hyphenation(ccel_spans_to_md(block.get('lines', []), cfg.get('footnote_size_max')))
                if md:
                    output_blocks.append(md)
            bi += 1

    doc.close()
    if pending_fns:
        output_blocks.extend(pending_fns)
        pending_fns.clear()
    if cfg.get('mojibake_fixes'):
        output_blocks = [apply_mojibake_fixes(b, cfg['mojibake_fixes']) for b in output_blocks]
    write_txt_output(output_blocks, cfg['out'])
    print(f"Sections: {sum(1 for b in output_blocks if b.startswith(chr(10) + '## '))}")


def apply_mojibake_fixes(text, fixes):
    """Replace each context-anchored mojibake span with its correct Unicode.

    Embedded Hebrew/Greek fonts in some CCEL PDFs have no ToUnicode map, so
    PyMuPDF returns U+FFFD for every glyph. We restore them by matching the
    surrounding English context, identified by OCR + linguistic knowledge.
    """
    for needle, replacement in fixes:
        text = text.replace(needle, replacement)
    return text


# ══════════════════════════════════════════════════════════════════════════════
# CCEL PARALLEL GOSPEL FORMAT  (matthew)
# Multi-column parallel gospel verses; dynamic column detection
# ══════════════════════════════════════════════════════════════════════════════

def ccel_pg_spans_to_md(block, fn_size_max):
    all_spans = []
    lines = block.get('lines', [])
    for li, line in enumerate(lines):
        all_spans.extend(line.get('spans', []))
        if li < len(lines) - 1:
            all_spans.append(_LINE_BREAK)

    parts = []
    i = 0
    while i < len(all_spans):
        span = all_spans[i]
        if span is _LINE_BREAK:
            if parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue
        t     = span['text']
        flags = span.get('flags', 0)
        is_sup    = bool(flags & 1)
        is_bold   = bool(flags & 16)
        is_italic = bool(flags & 2)
        stripped = t.strip()
        if not stripped:
            if t and parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue
        # 脚注上标识别：两种情况
        # 1. is_sup flag + 数字 + 小字号（PyMuPDF 正常标记的 sup）
        # 2. 数字 + 字号显著小于正文（如 6.6/7.5 vs 正文 12）—— Calvin
        #    PDF 偶尔不标 sup flag，但视觉上仍是 sup（如 vol 2 fn ref "399"
        #    flags=0 size=6.6）
        span_sz = span.get('size', 99)
        is_small_digit_ref = (
            stripped.isdigit()
            and span_sz < fn_size_max + 2  # < 9.5 for vol2
            and span_sz < 9  # 排除 page number 等 size=10
        )
        if (is_sup or is_small_digit_ref) and stripped.isdigit():
            # 用 kramdown footnote 引用 [^N] —— 配合 [^N]: 定义 kramdown
            # 自动渲染成 <sup id=fnref:N><a href=#fn:N>N</a></sup> +
            # 文末 ol 列表。与 harmony-3-en 同款。
            parts.append(f'[^{stripped}]')
            i += 1
            continue
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        if is_bold and is_italic:
            parts.append(f'{lead}***{stripped}***{tail}')
        elif is_bold:
            parts.append(f'{lead}**{stripped}**{tail}')
        elif is_italic:
            parts.append(f'{lead}*{stripped}*{tail}')
        else:
            parts.append(t)
        i += 1
    return re.sub(r' {2,}', ' ', ''.join(parts)).strip()


def ccel_pg_is_page_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    text = get_block_text(block).strip()
    return 'John Calvin' in text or bool(re.match(r'^\d+$', text))


def ccel_pg_is_page_number(block):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    span = get_first_span(block)
    return span is not None and span.get('size', 0) <= 10


def ccel_pg_is_footnote(block, cfg):
    """⚠️ 不要只看 first span size——CCEL parallel 中 verse 续接块的首 span
    常是上一节的 6.6pt footnote ref（如 `699 4. Now all this was done...`），
    其余正文 spans 是 12pt。只看首 span 会把整页跨页续接块误判为 fn，导致
    scripture-table 跨页内容全丢（harmony-2-en/21.md Matt 21:1-9 即此 bug）。

    判定两条路径：
    A. 首 span 小字 (< footnote_size_max) + 第二 span 小字 (< 10)
       —— 标准 fn 头：fn 编号 + 正文小字。
    B. 全部 span 字号 < 10 —— fn 续接段（fn 跨多个 PyMuPDF block 时，
       续接 block 的 first span 已不是数字编号，但 ALL 字号仍 < 10）。

    Vol 2 PDF 中：
      - 真脚注头块：first=6.3 + second=9.0  → IS fn (路径 A)
      - 真脚注续接块：first=9.0 + all=9.0 → IS fn (路径 B)
      - 经文续接块：first=6.6 + second=12.0 → NOT fn（first 小但 second 是正文）
    """
    spans = []
    for line in block.get('lines', []):
        for span in line.get('spans', []):
            if span.get('text', '').strip():
                spans.append(span)
    if not spans:
        return False
    # 路径 B：所有 spans 字号 < 10 → fn 续接块
    if all(sp.get('size', 12) < 10 for sp in spans):
        return True
    first_size = spans[0].get('size', 0)
    if first_size >= cfg['footnote_size_max']:
        return False
    # 路径 A：首 span 小，第二 span 也小 → fn 头
    if len(spans) >= 2:
        second_size = spans[1].get('size', 0)
        if second_size >= 10:
            return False
    return True


def ccel_pg_is_section_header(block):
    span = get_first_span(block)
    # x0 ≥ 80：section header 居中 ~99，col label 也可能 x0 ≥ 90
    # 不能用 x0 ≥ 100（实测有 section header x0=99.8 被误漏）。
    # size ≥ 18 + uppercase 已足够区分（col label size 16.8 < 18）。
    if not span or span.get('size', 0) < 18 or block['bbox'][0] < 80:
        return False
    return bool(re.search(r'(MATTHEW|MARK|LUKE|JOHN|HARMONY)',
                           get_block_text(block).strip().upper()))


def ccel_pg_is_col_label(block):
    span = get_first_span(block)
    if not span:
        return False
    size  = span.get('size', 0)
    flags = span.get('flags', 0)
    return (14 <= size <= 17 and bool(flags & 16) and block['bbox'][0] >= 50
            and bool(re.search(r'(Matthew|Mark|Luke|John)\s+\d+:\d+',
                               get_block_text(block).strip())))


def ccel_pg_extract_col_info(block):
    """返回 [(text, x0, x1), ...] — 含 label bbox 两端，build_verse_table
    据此估算 col 间 gutter 中点作为分桶 split。
    单 x0 不够：col label 是 left-aligned，x0 反映 label 起点而非 cell 起点。
    用 (cur.x1 + next.x0)/2 才是真正的 gutter 中点。

    Col label 可能跨多行（如 "Luke 18:28-30, / 22:28-31" 占同一 col 两行），
    需把 x 重叠的多行合并成一个 col label。
    """
    raw = []
    for line in block.get('lines', []):
        text = ''.join(s['text'] for s in line.get('spans', [])).strip()
        if text:
            raw.append((text, line['bbox'][0], line['bbox'][2]))
    raw.sort(key=lambda c: c[1])
    # 合并 x 范围重叠的相邻 cols（多行 col label）
    merged = []
    for entry in raw:
        if merged and entry[1] < merged[-1][2]:
            prev_text, prev_x0, prev_x1 = merged[-1]
            merged[-1] = (prev_text + ' ' + entry[0],
                          min(prev_x0, entry[1]),
                          max(prev_x1, entry[2]))
        else:
            merged.append(entry)
    return merged


def ccel_pg_is_verse_block(block):
    span = get_first_span(block)
    if not span or not (span.get('flags', 0) & 16):
        return False
    size = span.get('size', 0)
    if size < 10 or size > 14:
        return False
    if not re.match(r'^\d+([.\xa0]|$)', span['text'].strip()):
        return False
    # 排除 Calvin commentary verse-header block：
    # 「**44.** *Again, the kingdom of heaven is like a treasure*. ...」
    # 这种块 sp0 是粗体数字（满足上述判定），但 sp1 是斜体的 verse 引文
    # （flags & 2），sp2 才是 roman 注释正文。
    # Scripture verse block：sp0 粗体数字，sp1 是 ". And it happened..."
    # 等正常 roman 经文文本（无 italic flag）。
    all_spans = []
    for line in block.get('lines', []):
        for sp in line.get('spans', []):
            if sp.get('text', '').strip():
                all_spans.append(sp)
                if len(all_spans) >= 3:
                    break
        if len(all_spans) >= 3:
            break
    if len(all_spans) >= 2:
        sp1 = all_spans[1]
        sp1_text = sp1.get('text', '').strip()
        sp1_italic = bool(sp1.get('flags', 0) & 2)
        # 斜体 sp1 且不以「.」起头 = commentary verse-header
        if sp1_italic and not sp1_text.startswith('.'):
            return False
    return True


def ccel_pg_block_is_multi_col(block, n_cols=3):
    """检查 block 内是否含 multi-col scripture 布局——lines 起始 x 在
    ≥ (n_cols - 1) 个 col 期望位置上（vol 2 narrow parallel：74/230/386）。

    用途：区分多 col scripture 大块 vs 单 col commentary 大块（含 indented
    quote 等）。单 col commentary 可能有 line.x0=[72, 90, 148, 264]，
    cluster 数 >=2 但位置不在 col 边界 → 不算 multi-col。

    要求至少 (n_cols - 1) 个 cluster 位置落在 [60, 90] ∪ [220, 240] ∪
    [376, 396] 等 col 期望 ± 12px 区间。
    """
    line_x0s = sorted({round(line['bbox'][0])
                       for line in block.get('lines', [])
                       if line.get('spans')})
    if not line_x0s:
        return False
    BODY_LEFT, BODY_RIGHT = 74, 538
    cw = (BODY_RIGHT - BODY_LEFT) / max(n_cols, 1)
    expected = [BODY_LEFT + cw * i for i in range(n_cols)]
    hits = 0
    for ex in expected:
        if any(abs(x - ex) <= 12 for x in line_x0s):
            hits += 1
    return hits >= max(2, n_cols - 1)


def ccel_pg_is_index_start(block):
    text = get_block_text(block).strip()
    return (bool(re.match(r'^Indexes?$', text, re.I))
            or bool(re.match(r'^Index of ', text, re.I))
            or text.startswith('•'))


def ccel_pg_is_decoration(block):
    return get_block_text(block).strip().lstrip('\xa0').strip() in (
        'COMMENTARY', 'ON A', 'VOLUME SECOND')


def ccel_pg_build_verse_table(section_header, verse_blocks, col_info):
    """⚠️ verse_blocks 现在是 [(block_dict, words_list), ...]
    words_list 是 page.get_text("words") 过滤到 block.bbox 内的 word 列表。

    span-level 分桶遇到 PyMuPDF 把多列同 y 的不同 spans **合并为一个 span**
    时无解（Matt v10 末 + Matt v11 起首 + Luke v27 末 全在一个 span 内）。
    word-level 给每个 word 独立的 x0 → 可靠分桶。

    Splits 选择策略（按可靠性顺序）：
    1. **section-level word x0 histogram**：扫整节所有 word x0，
       2px bin，找 (n_cols-1) 个最大的"空 bin 段"作为 gutter
       —— 这是最可靠：直接从内容自身决定 cell 边界
    2. 回退 label gutter：col_info 中 (x1, next.x0) 的中点
    3. 最终回退 page 几何等分"""
    n_cols = max(1, len(col_info))
    splits = []

    if n_cols >= 2:
        # 收集本节所有 word x0
        all_x0s = []
        for entry in verse_blocks:
            words_list = entry[1] if len(entry) >= 2 else []
            all_x0s.extend(int(w[0]) for w in words_list)

        # page 几何等分 splits（最稳定）
        # vol 2 narrow parallel：body 74-538，等分 n_cols（3-col → 228/386）
        # K-means 在内容分布不均时（如 Luke 6:11 仅 1 节经文，词量远少
        # 于 Matt/Mark）会把中心拉向词密集区，导致 Luke 中心 ≈362 而非
        # 真实位置 460 → splits 偏左，Mark 内容落入 Luke。
        # page 几何是 fixed signal，不受内容分布影响。
        if n_cols >= 2 and all_x0s:
            BODY_LEFT, BODY_RIGHT = 74, 538
            cw = (BODY_RIGHT - BODY_LEFT) / n_cols
            splits = [BODY_LEFT + cw * (i + 1) for i in range(n_cols - 1)]

    # 回退：label gutter midpoint
    if not splits and n_cols == 2:
        splits = [305]
    elif not splits and n_cols >= 3 and len(col_info[0]) >= 3:
        splits = [(col_info[i][2] + col_info[i + 1][1]) / 2
                  for i in range(n_cols - 1)]
    elif not splits and n_cols >= 3:
        BODY_LEFT, BODY_RIGHT = 74, 504
        cw = (BODY_RIGHT - BODY_LEFT) / n_cols
        splits = [BODY_LEFT + cw * (i + 1) for i in range(n_cols - 1)]
    col_lines = [[] for _ in range(n_cols)]

    # ── word-level 分桶 ──
    # 1. 把所有 verse_blocks 的 words 合并并按 (y0, x0) 排序
    # 2. 按 y0 聚成 visual lines（同 y 内多个 word 属同视觉行）
    # 3. 每个 word 按 x0 vs splits 分桶到对应 col
    # 4. 同 col 同行 words 拼成 line text，按 verse-start (^\d+\.) 分段
    #
    # sup 上标识别：用与每个 word 关联的字号信息（从 span_size_map）。
    # 该 map 在 verse_buf 收集时构建，把 (round(y), round(x0)) → size
    all_word_recs = []   # (page_idx, y0, x0, x1, text, size, is_sup)
    seen_words = set()   # 去重 key (pn, round(y0), round(x0), text)
    # 跨 block 去重：PyMuPDF 偶尔生成两个 bbox 重叠的 block（如 block A
    # bbox=(230,88,382,114) 完全位于 block B bbox=(74,88,382,373) 内），
    # block_to_verse_buf_entry 用 y range 过滤会导致 A∩B 区域的 word
    # 被收集两次 → 输出 "87 87 that that they they should should"
    # 双词字串。dedupe 用 (page, round(y), round(x), text) 强 key。
    for entry in verse_blocks:
        # 兼容 (block_dict, words_list, span_size_map) 老格式（无 page_idx）
        if len(entry) == 4:
            block_dict, words_list, span_size_map, pn = entry
        else:
            block_dict, words_list, span_size_map = entry
            pn = 0
        for w in words_list:
            wx0, wy0, wx1, wy1, wtext = w[:5]
            dkey = (pn, round(wy0), round(wx0), wtext)
            if dkey in seen_words:
                continue
            seen_words.add(dkey)
            key = (round(wy0), round(wx0))
            size, is_sup = span_size_map.get(key, (12.0, False))
            all_word_recs.append((pn, wy0, wx0, wx1, wtext, size, is_sup))

    # 按 (page_idx, y, x) 排序 — 跨页时必须先按 page 排序
    all_word_recs.sort(key=lambda r: (r[0], round(r[1]), r[2]))

    # 聚成行：y 接近的 word 同一行
    Y_TOL = 2
    line_groups = []
    cur_group = []
    cur_y = None
    cur_pn = None
    for rec in all_word_recs:
        pn, y = rec[0], rec[1]
        # 同页 + y 接近才同行；跨页强制断行
        if (cur_pn == pn and cur_y is not None and abs(y - cur_y) <= Y_TOL):
            cur_group.append(rec)
        else:
            if cur_group:
                line_groups.append(cur_group)
            cur_group = [rec]
            cur_pn = pn
            cur_y = y
    if cur_group:
        line_groups.append(cur_group)

    # 每行按 x0 分桶到 col（用 section-level 全局 splits）
    for grp in line_groups:
        bucks = [[] for _ in range(n_cols)]
        for pn, y0, x0, x1, text, size, is_sup in grp:
            ci = sum(1 for s in splits if x0 >= s)
            stripped = text.strip()
            if is_sup and stripped.isdigit() and size < 9.5:
                # scripture-table cell 是 HTML（<td><p>）—— kramdown 不会
                # 在 raw HTML 内处理 markdown 除非 markdown="1"。直接输出
                # 显式链接 HTML，跳过 markdown 处理同样能跳到 fn def。
                bucks[ci].append(
                    f'<sup id="fnref:{stripped}">'
                    f'<a href="#fn:{stripped}" class="footnote">{stripped}</a>'
                    f'</sup>'
                )
            else:
                bucks[ci].append(text)
        for ci in range(n_cols):
            line_text = re.sub(r'\s+', ' ',
                ' '.join(bucks[ci]).replace('\xa0', ' ')).strip()
            if line_text:
                col_lines[ci].append(
                    (bool(re.match(r'^\d+\.?\s', line_text)), line_text)
                )

    def lines_to_rows(lines):
        rows, cur = [], []
        for is_start, text in lines:
            if cur and is_start:
                rows.append(' '.join(cur))
                cur = [text]
            else:
                cur.append(text)
        if cur:
            rows.append(' '.join(cur))
        return rows

    col_rows = [lines_to_rows(lines) for lines in col_lines]
    if not any(col_rows):
        return ''
    max_rows = max(len(r) for r in col_rows)
    for r in col_rows:
        r += [''] * (max_rows - len(r))

    col_labels = [c[0] for c in col_info] if col_info else [''] * n_cols
    html = [
        '<table class="calvin-scripture">',
        f'<thead><tr><th colspan="{n_cols}" style="text-align:center">{section_header}</th></tr></thead>',
    ]
    if any(col_labels):
        html.append('<thead><tr>' + ''.join(f'<th>{l}</th>' for l in col_labels) + '</tr></thead>')
    html.append('<tbody>')
    for ri in range(max_rows):
        cells    = [col_rows[ci][ri] for ci in range(n_cols)]
        non_empty = sum(1 for c in cells if c)
        if not non_empty:
            continue
        # 一律按 col 渲染，不用 colspan——publish 透传 td 到对应 col。
        # 之前 non_empty==1 时合 colspan 会让 publish.py 把内容路由错
        # （Mark v11-12 单 col 续接被推到 Matt col，因为 colspan 默认
        # 给第一栏）。
        html.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    html.append('</tbody></table>')
    return '\n'.join(html)


def extract_ccel_parallel(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Total pages: {total}, skipping first {cfg['skip_pages']}")

    output_blocks       = []
    pending_continuation = None
    in_verse_section    = False
    current_header      = None
    current_col_info    = []
    verse_buf           = []
    fn_size_max         = cfg['footnote_size_max']
    # 累计 fn defs，下一 section header 时 flush。让 fn defs 紧贴所属
    # commentary，不要全部塞到文件末尾（章末效果差）。
    pending_fns         = []
    # 上一个 commentary block 的 (page_idx, y_end) — 用于检测连续 block
    # 是否属于同一段（视觉 y 间距小则合并）。Calvin vol 2 PDF 偶尔把同
    # 一段拆成两个相邻 block（如 fn ref 起头的延续行单独成块）。
    last_commentary_pos = None

    def get_first_nonempty_span(block):
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                if span.get('text', '').strip():
                    return span
        return None

    def flush():
        nonlocal verse_buf, last_commentary_pos
        if verse_buf and current_header:
            tbl = ccel_pg_build_verse_table(current_header, verse_buf, current_col_info)
            if tbl:
                output_blocks.append(tbl)
        verse_buf = []
        last_commentary_pos = None  # section 切换重置 commentary 合并位置

    def handle_commentary(block):
        nonlocal pending_continuation, last_commentary_pos
        rich = ccel_pg_spans_to_md(block, fn_size_max)
        rich = re.sub(r'-\s+([a-z])', r'\1', rich)
        if not rich:
            return
        if rich.endswith('-'):
            pending_continuation = (pending_continuation or '') + rich[:-1]
            last_commentary_pos = None
            return
        if pending_continuation:
            rich = pending_continuation + rich
            pending_continuation = None
        # 同段续接合并：同页 + 前块结束 y 与本块起始 y 间距 ≤ 5px → 视为
        # 同一段（PyMuPDF 把段内换行点拆成两个 block，如 fn ref "399"
        # 起头的延续行）。合并到上一 output_blocks 末尾，不新开段。
        cur_pos = (page_idx, block['bbox'][1], block['bbox'][3])
        merged = False
        if (last_commentary_pos is not None and output_blocks
                and last_commentary_pos[0] == page_idx
                and 0 <= cur_pos[1] - last_commentary_pos[2] <= 5):
            output_blocks[-1] = output_blocks[-1].rstrip() + ' ' + rich
            merged = True
        if not merged:
            output_blocks.append(rich)
        last_commentary_pos = cur_pos

    def block_to_verse_buf_entry(block, page, page_idx):
        """build_verse_table 现在要 (block_dict, words_list, span_size_map, page_idx)。
        page_idx 必须随 word 进 sort key——否则跨页块词混排序错乱。"""
        x0, y0, x1, y1 = block['bbox']
        page_words = page.get_text('words')
        wlist = [w for w in page_words
                 if y0 - 1 <= w[1] and w[3] <= y1 + 1]
        sm = {}
        for line in block.get('lines', []):
            for sp in line.get('spans', []):
                if not sp.get('text', '').strip():
                    continue
                sx0, sy0 = sp['bbox'][0], sp['bbox'][1]
                sz = sp.get('size', 12.0)
                is_sup = bool(sp.get('flags', 0) & 1)
                sm[(round(sy0), round(sx0))] = (sz, is_sup)
        return (block, wlist, sm, page_idx)

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if ccel_pg_is_page_header(block, cfg):
                continue
            if ccel_pg_is_page_number(block):
                continue
            if ccel_pg_is_footnote(block, cfg):
                # 提取 fn defs 而非丢弃 —— inline body 有 <sup>N</sup>
                # 引用，对应的 [^N]: 定义就在 page-bottom 这种 block 里。
                if cfg.get('extract_footnotes'):
                    for num, fn_text in parse_ccel_footnote_block(block):
                        pending_fns.append(f'[^{num}]: {fn_text}')
                continue
            if ccel_pg_is_decoration(block):
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if ccel_pg_is_index_start(block):
                print(f'Stopping at index on page {page_idx + 1}')
                flush()
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                if pending_fns:
                    output_blocks.extend(pending_fns)
                    pending_fns.clear()
                doc.close()
                write_txt_output(output_blocks, cfg['out'])
                tbl_marker = '<table class="calvin-scripture">'
                print(f"Tables: {sum(1 for b in output_blocks if tbl_marker in b)}")
                return

            if ccel_pg_is_section_header(block):
                flush()
                # 在新 section header 前 flush pending fn defs，让 fn defs
                # 紧贴所属 section 的 commentary（kramdown 全局 fn 也接受
                # 散落 [^N]: 定义，不一定都到文末）。
                if pending_fns:
                    output_blocks.extend(pending_fns)
                    pending_fns.clear()
                current_header   = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
                current_col_info = []
                output_blocks.append(f'\n## {current_header}\n')
                in_verse_section = True
            elif ccel_pg_is_col_label(block):
                current_col_info = ccel_pg_extract_col_info(block)
            elif in_verse_section and ccel_pg_is_verse_block(block):
                # ccel_pg_is_verse_block 已经检查 sp1 italic 排除了
                # commentary 段头「**4.** *Bear forth fruit*」型。
                # 这里直接加入 verse_buf——不要再用 ccel_pg_block_is_multi_col
                # 否决（短 verse block 整行跨 3 col，line.x0=74 不被 multi-col
                # 检测命中，会被误杀）。
                verse_buf.append(block_to_verse_buf_entry(block, page, page_idx))
            elif in_verse_section:
                first_span = get_first_nonempty_span(block)
                if verse_buf and first_span and not bool(first_span.get('flags', 0) & 16):
                    # 真 scripture continuation = 跨页续接（前页 verse 行
                    # 中断，本页 top block 继续）。判定：本 block 必须在
                    # 新页 TOP（y < 200）。同页中部出现的非粗体续接段
                    # 几乎都是 commentary，不应加入 verse_buf。
                    first_italic = bool(first_span.get('flags', 0) & 2)
                    n_cols = len(current_col_info)
                    bw = block['bbox'][2] - block['bbox'][0]
                    not_mc = (
                        n_cols >= 2 and bw >= 260
                        and not ccel_pg_block_is_multi_col(block, n_cols=n_cols)
                    )
                    # 跨页续接判定：block 必须在新页 TOP (y < 200)。同一
                    # section 跨页续接可能有多个 block（Mark-only 小块 +
                    # 多 col 大块），都在 page top，都应接受——所以不能
                    # 用「page_idx > last_buf_page」这种严比较（一旦加了
                    # 一个 block，page_idx 就等于 last_buf_page）。
                    # 只要 block_y0 < 200 + verse_buf 中有更早 page 的 block，
                    # 就是合法的 cross-page top 续接。
                    # multi-col section 中，cross-page-top block 可能只是
                    # 某一 col 的延续（如 Matt v4 末尾仅 Matt col 有续接，
                    # 没 Mark/Luke 续接）。此时块宽度 / col 数 / multi-col
                    # layout 都不应作为否决条件。
                    # 单 col section 跨页续接判别：高度阈值不稳（scripture
                    # 续接可达 170px，commentary 可短到 127px）。
                    # 改用结构信号：scripture verse marker = 粗体小数字 +
                    # 紧跟 non-italic span（". And the master..."）。
                    # commentary verse-intro = 粗体数字 + 紧跟 italic span
                    # （*Again, the kingdom...*）。统计前者 ≥ 2 → scripture。
                    earliest_buf_page = min(
                        (e[3] for e in verse_buf if len(e) >= 4),
                        default=page_idx,
                    )
                    block_y0 = block['bbox'][1]
                    scripture_markers = 0
                    if n_cols <= 1:
                        flat_spans = []
                        for line in block.get('lines', []):
                            for sp in line.get('spans', []):
                                if sp.get('text', '').strip():
                                    flat_spans.append(sp)
                        for i, sp in enumerate(flat_spans):
                            txt = sp.get('text', '').strip()
                            flags = sp.get('flags', 0)
                            spsz = sp.get('size', 0)
                            if not (bool(flags & 16) and spsz >= 10
                                    and re.match(r'^\d+\.?$', txt)):
                                continue
                            try:
                                n = int(txt.rstrip('.'))
                            except ValueError:
                                continue
                            if n >= 100:
                                continue
                            if i + 1 < len(flat_spans):
                                nxt = flat_spans[i + 1]
                                if not bool(nxt.get('flags', 0) & 2):
                                    scripture_markers += 1
                    # 极短块（h < 60px ≈ 1-3 行）即使 markers 只有 1 个也
                    # 是 scripture 续接（v30 末尾 "repent." 跨页接 v31，
                    # 仅 1 markers）。commentary block 续接极少 < 60px。
                    block_h = block['bbox'][3] - block['bbox'][1]
                    is_cross_page_top = (
                        page_idx > earliest_buf_page and block_y0 < 200
                        and (n_cols >= 2 or scripture_markers >= 2
                             or block_h < 60)
                    )
                    # 同页续接判定：multi-col section（n_cols >= 2）才允许同
                    # 页续接（PyMuPDF 经常把 multi-col 表中间断成几个 block，
                    # 包括跨页后续表上有重叠 / 紧邻的多个 block）。
                    # 范围：current page_idx 必须在 verse_buf 已收 page 集合
                    # 内（之前 page 或当前 cross-page-top 已加的 page）。
                    # 单 col section（n_cols=1）禁止同页续接——commentary 也
                    # 是单 col 全宽，无法可靠区分。除非 first span text 是
                    # 纯数字（footnote ref 紧贴前个 verse_block 续接）。
                    first_text = first_span.get('text', '').strip()
                    is_pure_digit = bool(re.match(r'^\d+\.?$', first_text))
                    buf_pages = {e[3] for e in verse_buf if len(e) >= 4}
                    is_same_page_continuation = (
                        n_cols >= 2 and page_idx in buf_pages
                    )
                    is_legit_continuation = (
                        is_cross_page_top or is_same_page_continuation
                        or (n_cols == 1 and is_pure_digit)
                    )
                    # multi-col section 中，块可能只是某一 col 的续接（如
                    # Matt v4 末尾仅 Matt col 续接 → not_mc=True 但仍是
                    # scripture）。豁免：not_mc + 块 h < 100px 是 scripture
                    # 单 col 续接（commentary 续接基本 ≥ 100px），不论 cross-
                    # page 还是 same-page。
                    single_col_short = (
                        not_mc and block_h < 100
                        and (is_cross_page_top or is_same_page_continuation)
                    )
                    if first_italic:
                        flush()
                        in_verse_section = False
                        handle_commentary(block)
                    elif single_col_short:
                        verse_buf.append(block_to_verse_buf_entry(block, page, page_idx))
                    elif not_mc or not is_legit_continuation:
                        flush()
                        in_verse_section = False
                        handle_commentary(block)
                    else:
                        verse_buf.append(block_to_verse_buf_entry(block, page, page_idx))
                else:
                    flush()
                    in_verse_section = False
                    handle_commentary(block)
            else:
                handle_commentary(block)

    flush()
    if pending_continuation:
        output_blocks.append(pending_continuation)
    if pending_fns:
        output_blocks.extend(pending_fns)
        pending_fns.clear()
    doc.close()
    write_txt_output(output_blocks, cfg['out'])
    tbl_marker = '<table class="calvin-scripture">'
    print(f"Tables: {sum(1 for b in output_blocks if tbl_marker in b)}")


# ══════════════════════════════════════════════════════════════════════════════
# CCEL ACTS FORMAT  (acts1, acts2)
# "Acts N:M" bold-italic headers; verse blocks identified by x-position
# ══════════════════════════════════════════════════════════════════════════════

def ccel_acts_is_scripture_header(block):
    span = get_first_span(block)
    if not span:
        return False
    x = block['bbox'][0]
    # Allow optional whitespace after `:` — some headers in calvin_acts*.pdf
    # render as "Acts 2: 5-12" with a space after the colon.
    return (span.get('size', 0) >= 14 and bool(span.get('flags', 0) & 20)
            and 180 < x < 360
            and bool(re.match(r'^Acts\s+\d+:\s*\d+', get_block_text(block).strip())))


def ccel_acts_is_page_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    text = get_block_text(block).strip()
    return ('John Calvin' in text or 'Comm on Acts' in text
            or 'Commentary on Acts' in text or bool(re.match(r'^\d+$', text)))


def ccel_acts_is_page_number(block):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    span = get_first_span(block)
    return span is not None and span.get('size', 0) <= 10


def ccel_acts_is_footnote(block, cfg):
    if block['bbox'][1] < cfg['footer_y_min']:
        return False
    span = get_first_span(block)
    if span and span.get('size', 0) < 8:
        return True
    return not get_block_text(block).strip()


def ccel_acts_is_verse_block(block):
    x0 = block['bbox'][0]
    if x0 < 65 or x0 > 85:
        return False
    lines = block.get('lines', [])
    if not lines:
        return False
    first_spans = lines[0].get('spans', [])
    if not first_spans:
        return False
    fs = first_spans[0]
    return bool(fs.get('flags', 0) & 4) and bool(re.match(r'^\d+\.$', fs['text'].strip()))


def ccel_acts_extract_block_rich(block, fn_size_max=7.5):
    """Extract block as markdown, preserving:
    - **N.** bold-italic verse-number markers (font flag bit 4 = bold-italic
      in this PDF; matches `^\\d+\\.$`)
    - *text* italic markup (flag bit 2 = italic). Calvin's commentary cites
      scripture phrases in italic; missing this caused commentary blocks to
      be misclassified as scripture in the publish pipeline.
    - [^N] footnote refs (small-font sup digits inline in body text). Without
      this, refs appeared as bare digits like " 39 " mid-sentence.
    """
    parts = []
    block_seen_content = False  # have we emitted any non-digit content yet?
    for line in block.get('lines', []):
        spans = line.get('spans', [])
        lp = []
        italic_open = False
        for span in spans:
            text = span['text']
            t = text.strip()
            flags = span.get('flags', 0)
            size = span.get('size', 99)
            # Verse marker (bold-italic, e.g. "**9.**")
            if bool(flags & 4) and re.match(r'^\d+\.$', t):
                if italic_open:
                    lp.append('*'); italic_open = False
                lp.append(f'**{t}**')
                block_seen_content = True
                continue
            # Inline footnote ref: small-font digit-only span → [^N]
            # ONLY when block has already seen non-digit content; a digit at
            # the very start of a block could be a merged page number (PyMuPDF
            # sometimes glues the page-number into the next body block) and
            # gets disambiguated in publish_acts.py.
            if t.isdigit() and size < fn_size_max + 1:
                if block_seen_content:
                    if italic_open:
                        lp.append('*'); italic_open = False
                    lp.append(f'[^{t}]')
                else:
                    # Preserve leading digit verbatim; publish layer decides.
                    lp.append(text)
                continue
            # Italic toggle (flag bit 2)
            is_italic = bool(flags & 2) and not bool(flags & 4) and t != ''
            if is_italic and not italic_open:
                lp.append('*')
                italic_open = True
            elif not is_italic and italic_open:
                lp.append('*')
                italic_open = False
            lp.append(text)
            if t:
                block_seen_content = True
        if italic_open:
            lp.append('*')
            italic_open = False
        parts.append(''.join(lp))
    return ' '.join(parts).strip()


def ccel_acts_split_rich_by_verse(rich):
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]


def extract_ccel_acts(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Total pages: {total}, skipping first {cfg['skip_pages']}")

    output_blocks        = []
    pending_continuation = None
    pending_fns          = []   # accumulated [^N]: defs since last scripture header

    fn_size_max = cfg.get('footnote_size_max', 7.5)

    def flush_pending_fns_before_header():
        # Emit accumulated footnote defs as kramdown ref lines BEFORE the next
        # scripture header — keeps the defs scoped to the previous section so
        # the publish step can group them per chapter at the right boundary.
        nonlocal pending_fns
        if pending_fns:
            output_blocks.append('\n'.join(pending_fns))
            pending_fns = []

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if ccel_acts_is_page_header(block, cfg):
                continue
            if ccel_acts_is_page_number(block):
                continue
            if ccel_acts_is_footnote(block, cfg):
                # Footer footnote block — parse and capture as `[^N]: text`
                for num, fn_text in parse_ccel_footnote_block(block):
                    pending_fns.append(f'[^{num}]: {fn_text}')
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if text.strip().upper() in ('INDEX', 'INDEX OF SCRIPTURE REFERENCES',
                                         'SUBJECT INDEX', 'INDEX OF SUBJECTS'):
                print(f'Stopping at index page {page_idx + 1}')
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                flush_pending_fns_before_header()
                doc.close()
                write_txt_output(output_blocks, cfg['out'])
                return

            if ccel_acts_is_scripture_header(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                flush_pending_fns_before_header()
                normalized = re.sub(r':\s+(\d)', r':\1',
                                    text.replace(chr(10), ' ').strip())
                output_blocks.append(f'\n## {normalized}\n')
            elif ccel_acts_is_verse_block(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                output_blocks.append(ccel_acts_extract_block_rich(block, fn_size_max))
            else:
                rich = ccel_acts_extract_block_rich(block, fn_size_max)
                if rich.endswith('-'):
                    pending_continuation = (pending_continuation or '') + rich[:-1]
                else:
                    if pending_continuation:
                        rich = pending_continuation + rich
                        pending_continuation = None
                    for sub in ccel_acts_split_rich_by_verse(rich):
                        output_blocks.append(sub)

    if pending_continuation:
        output_blocks.append(pending_continuation)
    flush_pending_fns_before_header()
    doc.close()
    write_txt_output(output_blocks, cfg['out'])


# ══════════════════════════════════════════════════════════════════════════════
# AGES DIGITAL LIBRARY — HEBREWS FORMAT  (heb)
# Bilingual English/Latin; simpler line-level extraction; outputs raw .txt
# ══════════════════════════════════════════════════════════════════════════════

def heb_is_page_header(block, cfg):
    if block['bbox'][1] > cfg['header_y_max']:
        return False
    text = get_block_text(block).strip()
    return ('John Calvin' in text or 'Comm on Hebrews' in text
            or 'Commentary on Hebrews' in text or bool(re.match(r'^\d+$', text)))


def heb_is_page_number(block):
    if not re.match(r'^\d+$', get_block_text(block).strip()):
        return False
    span = get_first_span(block)
    return span is not None and span.get('size', 0) <= 10


def heb_is_footnote(block):
    span = get_first_span(block)
    if span and span.get('size', 0) < 10:
        return True
    return not get_block_text(block).strip()


def heb_is_decorative_header(block):
    span = get_first_span(block)
    if not span or span.get('size', 0) < 14:
        return False
    text = get_block_text(block).strip().upper()
    return any(re.match(p, text) for p in [
        r'^COMMENTAR', r'^CHAPTER\s+\d', r'^THE\s+ARGUMENT',
        r'^TRANSLATOR', r'^DEDICATOR', r'^TO\s+THE\s+', r'^EPISTLE\s+', r'^PREFACE'])


def heb_is_scripture_header(block, cfg):
    span = get_first_span(block)
    if not span:
        return False
    x0 = block['bbox'][0]
    return (span.get('size', 0) >= 14 and bool(span.get('flags', 0) & 20)
            and 80 < x0 < 300
            and bool(re.match(r'^Hebrews\s+(Chapter\s+)?\d+:\d+',
                               get_block_text(block).strip())))


def heb_extract_line_rich(line):
    spans = [s for s in line.get('spans', []) if s.get('text', '')]
    if not spans:
        return ''
    parts     = []
    skip_dot  = False
    for span in spans:
        text  = span['text']
        flags = span.get('flags', 0)
        size  = span.get('size', 0)
        t     = text.strip()
        if skip_dot:
            skip_dot = False
            if text.startswith('.'):
                text = text[1:]
            parts.append(text)
            continue
        if bool(flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            num = t.rstrip('.')
            parts.append(f'**{num}.**')
            if not t.endswith('.'):
                skip_dot = True
        else:
            parts.append(text)
    return ''.join(parts).strip()


def heb_extract_english_lines(block, latin_x_min):
    parts = []
    for line in block.get('lines', []):
        if line['bbox'][0] >= latin_x_min:
            continue
        text = heb_extract_line_rich(line)
        if text:
            parts.append(text)
    return ' '.join(parts).strip()


def heb_build_verse_table(section_header, verse_blocks, latin_x_min):
    verses = {}
    for block in verse_blocks:
        cur_en = cur_la = None
        for line in block.get('lines', []):
            spans = [s for s in line.get('spans', []) if s.get('text', '').strip()]
            if not spans:
                continue
            lx        = line['bbox'][0]
            line_text = heb_extract_line_rich(line)
            if not line_text:
                continue
            vn_m = re.match(r'\*\*(\d+)\.\*\*', line_text)
            if lx >= latin_x_min:
                if vn_m:
                    cur_la = int(vn_m.group(1))
                if cur_la is not None:
                    verses.setdefault(cur_la, {'en': [], 'la': []})['la'].append(line_text)
            else:
                if vn_m:
                    cur_en = int(vn_m.group(1))
                if cur_en is not None:
                    verses.setdefault(cur_en, {'en': [], 'la': []})['en'].append(line_text)

    if not verses:
        return ''

    def md_to_html(text):
        text = text.replace('|', '&#124;')
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*',   r'<em>\1</em>', text)
        return text

    html = [
        '<table class="calvin-scripture">',
        f'<thead><tr><th colspan="2" style="text-align:center">{section_header}</th></tr></thead>',
        '<tbody>',
    ]
    for vn in sorted(verses.keys()):
        en = md_to_html(' '.join(verses[vn].get('en', [])))
        la = md_to_html(' '.join(verses[vn].get('la', [])))
        html.append(f'<tr><td>{en}</td><td>{la}</td></tr>')
    html += ['</tbody>', '</table>']
    return '\n'.join(html)


def heb_split_rich_by_verse(rich):
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]


def extract_ages_heb(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    latin_x_min = cfg['latin_x_min']
    print(f"Total pages: {total}, skipping first {cfg['skip_pages']}")

    output_blocks        = []
    pending_continuation = None
    in_verse_section     = False
    current_header       = None
    verse_buf            = []

    def flush():
        nonlocal verse_buf
        if verse_buf and current_header:
            tbl = heb_build_verse_table(current_header, verse_buf, latin_x_min)
            if tbl:
                output_blocks.append(tbl)
        verse_buf = []

    def handle_commentary(rich):
        nonlocal pending_continuation
        if rich.endswith('-'):
            pending_continuation = (pending_continuation or '') + rich[:-1]
        else:
            if pending_continuation:
                rich = pending_continuation + rich
                pending_continuation = None
            for sub in heb_split_rich_by_verse(rich):
                output_blocks.append(sub)

    for page_idx in range(cfg['skip_pages'], total):
        page   = doc[page_idx]
        blocks = sorted(
            page.get_text('dict', flags=fitz.TEXT_PRESERVE_WHITESPACE)['blocks'],
            key=lambda b: b['bbox'][1])

        for block in blocks:
            if block['type'] != 0:
                continue
            if heb_is_page_header(block, cfg):
                continue
            if heb_is_page_number(block):
                continue
            if heb_is_footnote(block):
                continue
            if heb_is_decorative_header(block):
                continue
            text = get_block_text(block).strip()
            if not text:
                continue

            if re.match(r'^(APPENDIX|INDEX)', text.upper()):
                print(f'Stopping at appendix/index on page {page_idx + 1}')
                flush()
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                doc.close()
                write_txt_output(output_blocks, cfg['out'])
                return

            if heb_is_scripture_header(block, cfg):
                flush()
                current_header = re.sub(r'^(Hebrews)\s+Chapter\s+', r'\1 ',
                                         text.replace('\n', ' ').strip())
                output_blocks.append(f'\n## {current_header}\n')
                in_verse_section = True
            elif in_verse_section and (block['bbox'][0] >= latin_x_min
                                       or any(line['bbox'][0] < latin_x_min
                                              and line.get('spans', [{}])[0].get('flags', 0) & 4
                                              for line in block.get('lines', []))):
                # verse block (English or Latin column)
                verse_buf.append(block)
            elif in_verse_section:
                flush()
                in_verse_section = False
                rich = heb_extract_english_lines(block, latin_x_min)
                if not rich:
                    rich = get_block_text(block).replace('\n', ' ').strip()
                if rich:
                    handle_commentary(rich)
            else:
                if block['bbox'][0] >= latin_x_min:
                    continue
                rich = heb_extract_english_lines(block, latin_x_min)
                if not rich:
                    rich = get_block_text(block).replace('\n', ' ').strip()
                if rich:
                    handle_commentary(rich)

    flush()
    if pending_continuation:
        output_blocks.append(pending_continuation)
    doc.close()
    write_txt_output(output_blocks, cfg['out'])


# ══════════════════════════════════════════════════════════════════════════════
# AGES DIGITAL LIBRARY — CORINTHIANS FORMAT  (1cor-vol1, 1cor-vol2)
# Full bilingual pipeline: footnotes, Stage 1.5/1.6, direct .md output
# ══════════════════════════════════════════════════════════════════════════════

def convert_ages_greek(text):
    VMAP = {'a':'α','e':'ε','h':'η','i':'ι','o':'ο','u':'υ','w':'ω',
            'A':'Α','E':'Ε','H':'Η','I':'Ι','O':'Ο','U':'Υ','W':'Ω'}
    CONSMAP = {'b':'β','g':'γ','d':'δ','z':'ζ','q':'θ','k':'κ','l':'λ','m':'μ',
               'n':'ν','x':'ξ','p':'π','r':'ρ','s':'σ','v':'ς','t':'τ','f':'φ',
               'c':'χ','y':'ψ','B':'Β','G':'Γ','D':'Δ','Z':'Ζ','Q':'Θ','K':'Κ',
               'L':'Λ','M':'Μ','N':'Ν','X':'Ξ','P':'Π','R':'Ρ','S':'Σ','T':'Τ',
               'F':'Φ','C':'Χ','Y':'Ψ'}

    def convert_token(token):
        if not re.search(r'[><~|j]', token):
            return token
        result, i, chars = [], 0, list(token)
        while i < len(chars):
            c = chars[i]
            if c == 'j':
                i += 1
                continue
            if c in VMAP:
                base, j = VMAP[c], i + 1
                diacritics = []
                while j < len(chars) and chars[j] in '><~|j':
                    diacritics.append(chars[j])
                    j += 1
                i = j
                combined = base
                for d in diacritics:
                    combined += {'>':'́','<':'̀','~':'͂','|':'ͅ'}.get(d,'')
                result.append(unicodedata.normalize('NFC', combined))
            elif c in CONSMAP:
                result.append(CONSMAP[c])
                i += 1
            elif c in '><~|':
                i += 1
            else:
                result.append(c)
                i += 1
        return ''.join(result)

    parts = re.split(r'(<[a-zA-Z/!][^>]*>)', text)
    out = []
    for part in parts:
        if part.startswith('<'):
            out.append(part)
        else:
            out.append(re.sub(
                r'[a-zA-Z][a-zA-Z><~|j]*(?:[><~|j][a-zA-Z]*)*',
                lambda m: convert_token(m.group()) if re.search(r'[><~|j]', m.group()) else m.group(),
                part))
    return ''.join(out)


def cor_is_bold(span):       return bool(span['flags'] & 16)
def cor_is_italic(span):     return bool(span['flags'] & 2)
def cor_is_superscript(span):return bool(span['flags'] & 1)

def cor_is_footnote_ref(span):
    t = span['text'].strip()
    if not t.isdigit():
        return False
    return (cor_is_superscript(span) and span['size'] < 8) or (6.4 <= span['size'] <= 7.5)

def cor_is_footnote_def_block(block):
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans or not all(s['size'] <= 9.5 for s in spans):
        return False
    return any(s['size'] < 7 and s['text'].strip().isdigit() and not cor_is_superscript(s)
               for s in spans)

def cor_is_running_header(block): return block['bbox'][1] < 58

def cor_is_page_number(block):
    if block['bbox'][1] < 725:
        return False
    return bool(re.match(r'^\d+$',
        ''.join(s['text'] for l in block['lines'] for s in l['spans']).strip()))

def cor_block_has_right_col(block, tsx):
    for line in block['lines']:
        fs = [s for s in line['spans'] if s['text'].strip()]
        if fs and fs[0]['bbox'][0] >= tsx:
            return True
    return False

def cor_block_is_full_width(block, tsx):
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    return bool(spans) and not cor_block_has_right_col(block, tsx) and block['bbox'][2] > 400

def cor_split_by_size(block):
    lws = [(l, next((s for s in l['spans'] if s['text'].strip()), None))
           for l in block['lines']]
    sizes = [fs['size'] for _, fs in lws if fs]
    if sizes and sizes[0] < 14 and max(sizes) >= 24:
        h1 = [l for l, fs in lws if fs and fs['size'] >= 24]
        if h1:
            return [_make_sub_block(block, h1)]
    groups, cur_lines, cur_sz = [], [], None
    for line in block['lines']:
        fs = next((s for s in line['spans'] if s['text'].strip()), None)
        if fs is None:
            cur_lines.append(line)
            continue
        sz = fs['size']
        if cur_sz is not None and abs(sz - cur_sz) > 2:
            if cur_lines:
                groups.append(_make_sub_block(block, cur_lines))
            cur_lines = [line]
        else:
            cur_lines.append(line)
        cur_sz = sz
    if cur_lines:
        groups.append(_make_sub_block(block, cur_lines))
    return groups if groups else [block]

def cor_split_by_verse_number(block, tsx):
    if cor_block_has_right_col(block, tsx) or not cor_block_is_full_width(block, tsx):
        return [block]
    groups, cur = [], []
    for i, line in enumerate(block['lines']):
        fs = [s for s in line['spans'] if s['text'].strip()]
        if i > 0 and fs:
            s = fs[0]
            if (bool(s['flags'] & 16) and not bool(s['flags'] & 2)
                    and re.match(r'^\d+\.$', s['text'].strip())):
                if cur:
                    groups.append(_make_sub_block(block, cur))
                cur = [line]
                continue
        cur.append(line)
    if cur:
        groups.append(_make_sub_block(block, cur))
    return groups if len(groups) > 1 else [block]

def cor_split_by_paragraph_indent(block, tsx):
    if cor_block_has_right_col(block, tsx) or not cor_block_is_full_width(block, tsx):
        return [block]
    bx0 = block['bbox'][0]
    INDENT_LOW, INDENT_HIGH, SIZE_MIN = 10, 60, 11.0
    groups, cur, first_seen, prev_deep = [], [], False, False
    for line in block['lines']:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            cur.append(line)
            continue
        x0    = spans[0]['bbox'][0]
        size  = spans[0]['size']
        indent = x0 - bx0
        is_deep = indent > INDENT_HIGH and size >= SIZE_MIN
        fc      = spans[0]['text'].lstrip()[:1]
        is_para = (first_seen and size >= SIZE_MIN and (
            (INDENT_LOW <= indent <= INDENT_HIGH)
            or (is_deep and not prev_deep and not fc.islower())))
        if is_para and cur:
            groups.append(_make_sub_block(block, cur))
            cur = []
        cur.append(line)
        first_seen = True
        prev_deep  = is_deep
    if cur:
        groups.append(_make_sub_block(block, cur))
    return groups if len(groups) > 1 else [block]

def cor_is_table_header(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    return abs(block['lines'][0]['spans'][0]['size'] - 16.8) < 0.6

def cor_is_h1(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    return block['lines'][0]['spans'][0]['size'] >= 24

def cor_is_h2(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    s = block['lines'][0]['spans'][0]['size']
    return 14 <= s < 24

def cor_collect_footnote_defs(blocks):
    defs = {}
    for b in blocks:
        if not cor_is_footnote_def_block(b):
            continue
        cur_num, cur_parts = None, []
        for line in b['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                if not t:
                    continue
                if t.isdigit() and span['size'] < 7 and not cor_is_superscript(span):
                    if cur_num is not None:
                        defs[cur_num] = ' '.join(cur_parts).strip()
                    cur_num, cur_parts = t, []
                else:
                    cur_parts.append(t)
        if cur_num is not None:
            defs[cur_num] = ' '.join(cur_parts).strip()
    return defs

def cor_format_span(span):
    t = span['text']
    if not t.strip():
        return t
    if cor_is_footnote_ref(span):
        return f'[^{t.strip()}]'
    lead = t[:len(t) - len(t.lstrip())]
    tail = t[len(t.rstrip()):]
    inner = t.strip()
    if cor_is_bold(span) and cor_is_italic(span):
        return f'{lead}***{inner}***{tail}'
    if cor_is_bold(span):
        return f'{lead}**{inner}**{tail}'
    if cor_is_italic(span):
        return f'{lead}*{inner}*{tail}'
    return t

def cor_spans_to_text(spans):
    parts = []
    for span in spans:
        part = cor_format_span(span)
        if not part:
            continue
        if parts:
            prev = parts[-1]
            if (prev and not prev[-1].isspace()
                    and not part[0].isspace()
                    and part[0] not in '.,;:!?)\'"_-'):
                parts.append(' ')
        parts.append(part)
    return re.sub(r' {2,}', ' ', ''.join(parts)).strip()

def cor_fnref_to_html(text):
    text = re.sub(r'\[\^(\d+)\]',
        lambda m: f'<sup><a href="#fn:{m.group(1)}" id="fnref:{m.group(1)}">{m.group(1)}</a></sup>',
        text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<em><strong>\1</strong></em>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',   r'<em>\1</em>', text)
    return text

def cor_build_table(header_text, rows):
    hdr = header_text.strip().upper()
    lines = ['', '<table class="calvin-scripture">',
             f'<thead><tr><th colspan="2" style="text-align:center">{hdr}</th></tr></thead>',
             '<tbody>']
    for en, la in rows:
        en_e = cor_fnref_to_html(en.replace('|', '&#124;'))
        la_e = cor_fnref_to_html(la.replace('|', '&#124;'))
        lines.append(f'<tr><td>{en_e}</td><td>{la_e}</td></tr>')
    lines += ['</tbody>', '</table>', '']
    return '\n'.join(lines)

def cor_extract_scripture(header_block, verse_blocks, cfg):
    tsx  = cfg['table_split_x']
    header_text = ' '.join(s['text'] for l in header_block['lines'] for s in l['spans']).strip()

    all_spans = sorted(
        [s for b in verse_blocks for l in b['lines'] for s in l['spans'] if s['text'].strip()],
        key=lambda s: (s['bbox'][1], s['bbox'][0]))

    left  = [s for s in all_spans if s['bbox'][0] <  tsx]
    right = [s for s in all_spans if s['bbox'][0] >= tsx]

    if cfg.get('verse_period', True):
        # vol1: verse nums "1." (with period); row format: "1. text"
        def parse(spans):
            verses, cur_num, cur_parts = [], None, []
            for span in spans:
                t = span['text'].strip()
                if cor_is_bold(span) and re.match(r'^\d+\.$', t):
                    if cur_num is not None:
                        verses.append((cur_num, cor_spans_to_text(cur_parts)))
                    cur_num, cur_parts = t, []
                else:
                    cur_parts.append(span)
            if cur_num is not None:
                verses.append((cur_num, cor_spans_to_text(cur_parts)))
            return verses

        en_d = {v[0]: v[1] for v in parse(left)}
        la_d = {v[0]: v[1] for v in parse(right)}
        nums = sorted(set(list(en_d) + list(la_d)), key=lambda x: int(x.rstrip('.')))
        rows = [(f'{n} {en_d.get(n,"")}'.strip(), f'{n} {la_d.get(n,"")}'.strip())
                for n in nums]
    else:
        # vol2: verse nums "1" or "1." (normalised); strip leading ". " from text
        def parse(spans):
            verses, cur_num, cur_parts = [], None, []
            for span in spans:
                t = span['text'].strip()
                if cor_is_bold(span) and re.match(r'^\d+\.?$', t):
                    if cur_num is not None:
                        verses.append((cur_num, cor_spans_to_text(cur_parts)))
                    cur_num, cur_parts = t.rstrip('.'), []
                else:
                    cur_parts.append(span)
            if cur_num is not None:
                verses.append((cur_num, cor_spans_to_text(cur_parts)))
            return verses

        en_d = {v[0]: v[1] for v in parse(left)}
        la_d = {v[0]: v[1] for v in parse(right)}
        nums = sorted(set(list(en_d) + list(la_d)), key=lambda x: int(x))
        rows = []
        for n in nums:
            er = en_d.get(n, '')
            lr = la_d.get(n, '')
            if er.startswith('. '): er = er[2:]
            if lr.startswith('. '): lr = lr[2:]
            rows.append((f'{n}. {er}'.strip() if er else f'{n}.',
                         f'{n}. {lr}'.strip() if lr else f'{n}.'))

    return cor_build_table(header_text, rows)

def cor_process_page(page, pending_header, cfg):
    tsx    = cfg['table_split_x']
    blocks = page.get_text('dict')['blocks']

    body_blocks, fn_def_blocks = [], []
    for b in blocks:
        if b['type'] != 0:
            continue
        if cor_is_running_header(b):
            continue
        if cor_is_page_number(b):
            continue
        if cor_is_footnote_def_block(b):
            fn_def_blocks.append(b)
        else:
            for s in cor_split_by_size(b):
                for s2 in cor_split_by_verse_number(s, tsx):
                    body_blocks.extend(cor_split_by_paragraph_indent(s2, tsx))

    footnote_defs = cor_collect_footnote_defs(fn_def_blocks)
    body_blocks.sort(key=lambda b: b['bbox'][1])

    pending_out  = None
    carried_table = None
    if pending_header is not None:
        if isinstance(pending_header, dict) and 'header' in pending_header:
            carry_hdr, prev_verses = pending_header['header'], pending_header['verses']
        else:
            carry_hdr, prev_verses = pending_header, []

        new_verses = []
        for b in body_blocks:
            if cor_is_table_header(b) or cor_is_h1(b) or cor_is_h2(b):
                break
            if cor_block_is_full_width(b, tsx):
                break
            new_verses.append(b)

        all_verses = prev_verses + new_verses
        carried_table = {'type': 'TABLE', 'html': cor_extract_scripture(carry_hdr, all_verses, cfg)}
        body_blocks   = body_blocks[len(new_verses):]

    items = []
    if carried_table:
        items.append(carried_table)

    page_h1_count = 0
    i = 0
    while i < len(body_blocks):
        b = body_blocks[i]
        if cor_is_h1(b):
            if page_h1_count > 0:
                i += 1
                continue
            items.append({'type': 'H1', 'text': ' '.join(
                s['text'] for l in b['lines'] for s in l['spans']).strip()})
            page_h1_count += 1
            i += 1
        elif cor_is_table_header(b):
            hdr_block  = b
            verse_blks = []
            j          = i + 1
            hit_comm   = False
            while j < len(body_blocks):
                nb = body_blocks[j]
                if cor_is_table_header(nb) or cor_is_h1(nb) or cor_is_h2(nb):
                    hit_comm = True
                    break
                if cor_block_has_right_col(nb, tsx):
                    verse_blks.append(nb)
                    j += 1
                elif cor_block_is_full_width(nb, tsx):
                    hit_comm = True
                    break
                else:
                    verse_blks.append(nb)
                    j += 1
            if not hit_comm and verse_blks:
                pending_out = {'header': hdr_block, 'verses': verse_blks}
            elif not hit_comm and not verse_blks:
                pending_out = hdr_block
            else:
                if verse_blks:
                    items.append({'type': 'TABLE',
                                  'html': cor_extract_scripture(hdr_block, verse_blks, cfg)})
            i = j
        elif cor_is_h2(b):
            h2_lines  = [l for l in b['lines']
                          if next((s for s in l['spans'] if s['text'].strip()), None)
                          and next((s for s in l['spans'] if s['text'].strip()), {}).get('size', 0) >= 14]
            body_lines = [l for l in b['lines'] if l not in h2_lines]
            h2_text    = ' '.join(s['text'] for l in h2_lines for s in l['spans']).strip()
            if h2_text:
                items.append({'type': 'H2', 'text': h2_text})
            if body_lines:
                body_text = cor_spans_to_text([s for l in body_lines for s in l['spans']])
                if body_text:
                    fi = 0
                    for line in body_lines:
                        ls = [s for s in line['spans'] if s['text'].strip()]
                        if ls:
                            fi = round(ls[0]['bbox'][0] - b['bbox'][0])
                            break
                    items.append({'type': 'BODY', 'text': body_text, 'indent': fi})
            i += 1
        else:
            text = cor_spans_to_text([s for l in b['lines'] for s in l['spans']])
            if text:
                fi = 0
                for line in b['lines']:
                    ls = [s for s in line['spans'] if s['text'].strip()]
                    if ls:
                        fi = round(ls[0]['bbox'][0] - b['bbox'][0])
                        break
                items.append({'type': 'BODY', 'text': text, 'indent': fi})
            i += 1

    return items, footnote_defs, pending_out


def cor_is_sentence_end(text):
    s = text.rstrip().rstrip('"\'')
    return not s or s[-1] in '.!?…'


def extract_ages_corinth(cfg):
    doc        = fitz.open(cfg['pdf'])
    skip_pages = cfg['skip_pages']
    stop_page  = cfg.get('stop_page')
    use_greek  = cfg.get('greek', False)

    all_items    = []
    all_fn_defs  = {}
    pending_hdr  = None

    for page_num in range(len(doc)):
        if page_num in skip_pages:
            continue
        if stop_page is not None and page_num >= stop_page:
            break
        page = doc[page_num]
        items, fn_defs, pending_hdr = cor_process_page(page, pending_hdr, cfg)
        all_items.append({'type': 'PAGE', 'num': page_num + 1})
        all_items.extend(items)
        all_fn_defs.update(fn_defs)

    doc.close()

    # Stage 1.5: merge paragraph fragments across page/block boundaries
    PARA_INDENT_LOW = 10
    idx = 0
    while idx < len(all_items):
        if all_items[idx]['type'] == 'BODY':
            j = idx + 1
            while j < len(all_items) and all_items[j]['type'] == 'PAGE':
                j += 1
            if j < len(all_items) and all_items[j]['type'] == 'BODY':
                cur = all_items[idx]['text']
                nxt = all_items[j]['text']
                nxt_indent = all_items[j].get('indent', 0)
                open_paren = bool(re.search(r'\([^)]*$', cur.rstrip()))
                if (nxt_indent < PARA_INDENT_LOW and not cor_is_sentence_end(cur)) \
                        or (open_paren and not cor_is_sentence_end(cur)):
                    all_items[idx]['text'] = cur.rstrip() + ' ' + nxt.lstrip()
                    all_items[idx]['indent'] = min(
                        all_items[idx].get('indent', 0), all_items[j].get('indent', 0))
                    del all_items[j]
                    continue
        idx += 1

    # Stage 1.6: relocate leading footnote refs to previous paragraph end
    idx = 0
    while idx < len(all_items):
        if all_items[idx]['type'] == 'BODY':
            text    = all_items[idx]['text']
            m_pre   = re.match(r'^(\[\^\d+\])\s+', text)
            m_solo  = re.match(r'^(\[\^\d+\])$', text.strip())
            if m_pre or m_solo:
                fn_ref = (m_pre or m_solo).group(1)
                rest   = text[m_pre.end():] if m_pre else ''
                pi     = idx - 1
                while pi >= 0 and all_items[pi]['type'] == 'PAGE':
                    pi -= 1
                if pi >= 0 and all_items[pi]['type'] == 'BODY':
                    all_items[pi]['text'] = all_items[pi]['text'].rstrip() + fn_ref
                    if rest:
                        all_items[idx]['text'] = rest
                    else:
                        del all_items[idx]
                        continue
        idx += 1

    # Render to Markdown
    md_lines = []
    for item in all_items:
        t = item['type']
        if t == 'PAGE':
            md_lines.append(f'\n<!-- PAGE {item["num"]} -->\n')
        elif t == 'H1':
            md_lines.append(f'\n# {item["text"]}\n')
        elif t == 'H2':
            md_lines.append(f'\n## {item["text"]}\n')
        elif t == 'TABLE':
            md_lines.append(item['html'])
        elif t == 'BODY':
            text = item['text']
            if use_greek:
                text = convert_ages_greek(text)
            text = re.sub(r'^(\d+)\. ', lambda m: f'{m.group(1)}\\. ', text)
            if '<table' not in text and '<tr' not in text:
                text = text.replace('|', '\\|')
            md_lines.append(f'\n{text}\n')
            if item.get('indent', 0) > 20:
                md_lines.append('{: style="text-align: center"}\n')

    if all_fn_defs:
        md_lines.append('\n---\n')
        for num in sorted(all_fn_defs.keys(), key=lambda x: int(x)):
            fn_text = all_fn_defs[num]
            if use_greek:
                fn_text = convert_ages_greek(fn_text)
            fn_text = fn_text.replace('|', '\\|')
            md_lines.append(f'\n[^{num}]: {fn_text}\n')

    out_path = cfg['out']
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(''.join(md_lines))
    print(f'Done. Written to {out_path}')
    print(f"Pages: {sum(1 for i in all_items if i['type']=='PAGE')}  "
          f"Tables: {sum(1 for i in all_items if i['type']=='TABLE')}  "
          f"Body: {sum(1 for i in all_items if i['type']=='BODY')}  "
          f"Footnotes: {len(all_fn_defs)}")


# ══════════════════════════════════════════════════════════════════════════════
# AGES DIGITAL LIBRARY — PHILIPPIANS FORMAT  (phil)
# Intermediate tagged output: [H1] / [H2] / [BODY] / [FOOTNOTE] lines
# ══════════════════════════════════════════════════════════════════════════════

def phil_dominant_class(line_spans):
    sizes = [s['size'] for s in line_spans if s['text'].strip()]
    if not sizes:
        return 'BODY', 12.0
    ms = max(sizes)
    if ms >= 22:   return 'H1', ms
    if ms >= 16:   return 'H2', ms
    if ms == 11:   return 'VERSE', ms
    return 'BODY', ms


def _render_spans_with_italic(spans):
    """Render a line of spans, wrapping styled runs with `<sty c="..." i="0|1">…</sty>`.

    Captures BOTH italic flag (PyMuPDF flags & 2) AND span color (`s['color']`
    as int). Default (black + non-italic) spans emit as plain text without wrap.
    Consecutive same-style spans coalesce. The converter decides how to render
    each (color, italic) combination — e.g. #800000 italic → red verse-phrase
    span, #008080 → Hebrew teal, #0000d4 → title blue, etc.
    """
    parts = []
    open_style = None  # tuple (color_int, is_italic), or None
    for s in spans:
        text = s['text']
        if not text:
            continue
        is_italic = bool(s['flags'] & 2)
        color = s.get('color', 0)
        # Plain black non-italic → no style wrap needed
        style = (color, is_italic) if (color != 0 or is_italic) else None
        if style != open_style:
            if open_style is not None:
                parts.append('</sty>')
            if style is not None:
                color_hex = f'{style[0]:06x}'
                parts.append(f'<sty c="{color_hex}" i="{1 if style[1] else 0}">')
            open_style = style
        parts.append(text)
    if open_style is not None:
        parts.append('</sty>')
    return ''.join(parts)


def phil_reconstruct_page(page, page_num=None):
    page_w = page.rect.width
    page_cx = page_w / 2
    blocks      = [b for b in page.get_text('dict')['blocks'] if b['type'] == 0]
    blocks.sort(key=lambda b: b['bbox'][1])

    output_lines  = []
    prev_block_y1 = None
    page_label   = str(page_num + 1) if page_num is not None else None  # PDF "page 17" = doc[16]

    # Bilingual scripture-mode state machine (Romans / 1Cor 等双语 PDF).
    # State transitions:
    #   - Enter scripture-mode on H2 with `<NNNNNN>BOOK Ch:V-V'` marker.
    #   - In scripture-mode: blocks emit as [TABLE_LEFT]/[TABLE_RIGHT] by
    #     line x0 (split at LATIN_X_MIN). Both narrow-half-page blocks and
    #     bilingual mixed blocks handled.
    #   - Exit scripture-mode on first full-width block (commentary starts).
    # For single-column books (John): no H2 marker emits NNNNNN OR no x≥200
    # lines means mode quietly stays off; emits identical to old behavior.
    LATIN_X_MIN = 200
    SCRIPTURE_BLOCK_WIDTH_MAX = 290  # narrow-half-page blocks ≤ this
    in_scripture_mode = False
    scripture_table_header = None
    scripture_buffer = []  # accumulate English lines across scripture-mode blocks

    def flush_scripture_buffer():
        nonlocal scripture_buffer
        if scripture_buffer:
            joined = ' '.join(scripture_buffer)
            output_lines.append(f'[BODY] {joined}')
            scripture_buffer = []

    for block_idx, block in enumerate(blocks):
        if prev_block_y1 is not None and block['bbox'][1] - prev_block_y1 > 8:
            output_lines.append('')
        prev_block_y1 = block['bbox'][3]

        bx0, _, bx1, _ = block['bbox']
        block_w = bx1 - bx0

        # Section-header detection per LINE: the H2 `<NNNNNN>BOOK Ch:V-V'`
        # is one line; verse lines follow. Per-block regex was too greedy
        # (matched "1:1-71" instead of "1:1-7" when next line started "1.").
        sec_match = None
        sec_line_idx = None
        for li_idx, line in enumerate(block['lines'][:3]):
            line_text = ''.join(s['text'] for s in line['spans']).strip()
            m = re.match(
                r'^<(\d{6,7})>\s*([A-Z][A-Za-z]*(?:\s\d)?[A-Z\s]*?\d+:\d+(?:[-,]\d{1,3})?)\s*$',
                line_text,
            )
            if m:
                sec_match = m
                sec_line_idx = li_idx
                break

        # Check if any line in block has x ≥ LATIN_X_MIN → bilingual block
        line_lefts = []
        line_rights = []
        for line in block['lines']:
            ne = [s for s in line['spans'] if s['text'].strip()]
            if not ne:
                continue
            lx0 = ne[0]['bbox'][0]
            if lx0 >= LATIN_X_MIN:
                line_rights.append(line)
            else:
                line_lefts.append(line)
        is_bilingual_block = bool(line_lefts and line_rights)
        is_narrow_block = block_w < SCRIPTURE_BLOCK_WIDTH_MAX

        # Decide whether to treat as scripture content
        treat_as_scripture = False
        if sec_match:
            # New section header → flush prior scripture buffer (if any) then enter mode
            flush_scripture_buffer()
            in_scripture_mode = True
            treat_as_scripture = True
        elif in_scripture_mode:
            if is_bilingual_block or is_narrow_block:
                treat_as_scripture = True
            else:
                # Full-width block → commentary starts → flush & exit scripture-mode
                flush_scripture_buffer()
                in_scripture_mode = False

        if treat_as_scripture:
            if sec_match:
                # Emit H2 first
                output_lines.append(f'[H2] <sty c="800000" i="0"><{sec_match.group(1)}></sty>{sec_match.group(2)}')
                # Re-split lines, skipping the section header line itself
                line_lefts = []
                line_rights = []
                for li_idx, line in enumerate(block['lines']):
                    if li_idx == sec_line_idx:
                        continue  # skip header line
                    ne = [s for s in line['spans'] if s['text'].strip()]
                    if not ne:
                        continue
                    lx0 = ne[0]['bbox'][0]
                    if lx0 >= LATIN_X_MIN:
                        line_rights.append(line)
                    else:
                        line_lefts.append(line)
            # Accumulate ENGLISH lines into scripture_buffer; emit as a single
            # [BODY] when scripture-mode exits (so ≥2 verse anchors in one
            # paragraph triggers structured_to_md's scripture-box).
            for ln in line_lefts:
                txt = _render_spans_with_italic(ln['spans']).rstrip()
                if not txt.strip():
                    continue
                if scripture_buffer and scripture_buffer[-1].endswith('-'):
                    scripture_buffer[-1] = scripture_buffer[-1][:-1] + txt.lstrip()
                else:
                    scripture_buffer.append(txt)
            continue  # skip the rest of normal block processing

        # Centered block detection: symmetric left/right margins.
        # - Long blocks (≥ 80 chars): need lm/rm both ≥ 30 (avoid hitting body
        #   paragraphs that happen to be centered cx but have tiny margins ≈ 25).
        # - Short blocks (< 80 chars): only need lm/rm both ≥ 22 AND strong
        #   symmetry |lm-rm| < 4 (covers title-page short lines like
        #   "TO THE READER" lm≈26 that the strict threshold rejected).
        bx0, _, bx1, _ = block['bbox']
        lm = bx0
        rm = page_w - bx1
        block_text_preview = ''
        for line in block['lines']:
            for s in line['spans']:
                if s['text'].strip():
                    block_text_preview += s['text']
        block_text_preview = block_text_preview.strip()
        is_short = len(block_text_preview) < 80
        if is_short:
            is_centered_block_geom = (
                abs(lm - rm) < 4
                and lm >= 22
                and rm >= 22
            )
        else:
            is_centered_block_geom = (
                abs(lm - rm) < 8
                and lm > 30
                and rm > 30
            )
        # Reject only when block ends with `(` — that's a justified-body last
        # line whose bible-ref continues on the next block (e.g. "(<NNNNNN>" split).
        # Do NOT reject on trailing `,` — title-page dedication lines like
        # "BARON OF DENBIGH, MAISTER OF THE HORSE..." end in comma and ARE centered.
        ends_with_continuation = bool(re.search(r'\(\s*$', block_text_preview))
        # Also reject when block starts with a numbered list item `N.` — those
        # are PDF outline subitems (indented from body), not centered titles.
        # PDF outline can have lm/rm symmetric (e.g. lm=44 rm=45) but is
        # semantically a left-indented list, not centered.
        starts_with_list_item = bool(re.match(r'^\s*[IVX]+\.\s|^\s*\d+\.\s', block_text_preview))
        # Check if ALL spans in this block are italic (flags & 2). If so AND
        # lm > 30, this is a citation/quote paragraph, not a centered title.
        is_all_italic = False
        if not is_centered_block_geom or len(block_text_preview) > 100:
            total_chars = 0
            italic_chars = 0
            for line in block['lines']:
                for s in line['spans']:
                    t = s['text'].strip()
                    if not t:
                        continue
                    total_chars += len(t)
                    if s['flags'] & 2:
                        italic_chars += len(t)
            if total_chars > 50 and italic_chars / total_chars > 0.9:
                is_all_italic = True
        is_centered_block = (
            is_centered_block_geom
            and not ends_with_continuation
            and not starts_with_list_item
            and not is_all_italic
        )

        # First block of a page often combines page-number header + continuation text.
        # Detect: y0 < 30 AND first non-empty span = digits matching page label.
        is_top_block = block['bbox'][1] < 30 and block_idx <= 1
        strip_page_num = False
        if is_top_block and page_label:
            for line in block['lines']:
                for s in line['spans']:
                    if s['text'].strip():
                        if s['text'].strip() == page_label:
                            strip_page_num = True
                        break
                break

        block_lines_output = []
        for line_idx, line in enumerate(block['lines']):
            non_empty = [s for s in line['spans'] if s['text'].strip()]
            if not non_empty:
                continue
            line_class, ms = phil_dominant_class(non_empty)
            # Strip page-number prefix from the first line of a top-of-page block.
            spans = list(line['spans'])
            if strip_page_num and line_idx == 0:
                # Drop the first non-empty span if it's the page label,
                # plus any trailing whitespace span immediately following.
                new_spans = []
                dropped = False
                for s in spans:
                    if not dropped and s['text'].strip() == page_label:
                        dropped = True
                        continue
                    if dropped and not s['text'].strip() and len(new_spans) == 0:
                        continue  # skip the space span right after page number
                    new_spans.append(s)
                spans = new_spans
                # Re-evaluate non_empty for class detection
                non_empty = [s for s in spans if s['text'].strip()]
                if not non_empty:
                    continue
                line_class, ms = phil_dominant_class(non_empty)
            full_text = _render_spans_with_italic(spans)
            if not full_text.strip():
                continue
            if non_empty[0]['size'] <= 8:
                if re.match(r'^[Ff]t?\d+$|^<\d+>$', non_empty[0]['text'].strip()):
                    line_class = 'FOOTNOTE'
            stripped = full_text.strip()
            if ms >= 16 and any(kw in stripped for kw in ('PHILIPPIANS','COLOSSIANS','THESSALONIANS')):
                if re.search(r'\d+:\d+', stripped):
                    line_class = 'VERSE'
            # Indented body: block lm >= 35 (significantly indented from body
            # x≈26) AND not centered AND no Latin column → outline subitem
            # OR short signature (e.g. "J. O." / "W.P. AUCHTERARDER")
            # OR italic citation paragraph (PDF indented italic quote)
            # OR right-aligned narrow byline (lm >> rm, e.g. "by John Calvin"
            # on PDF title page at x=278-350 page_w=410).
            block_lm = block['bbox'][0]
            block_w_local = block['bbox'][2] - block['bbox'][0]
            is_outline_item = bool(re.match(r'^\s*[IVX]+\.\s|^\s*\d+\.\s|^\s*[liI]\.\s', block_text_preview))
            is_narrow_indented = block_w_local < page_w * 0.55
            # Right-aligned: lm >> rm (lm > 2*rm) AND narrow + indented
            is_right_aligned = (
                block_lm > 100  # significantly past page center
                and lm > rm * 1.5
                and block_w_local < page_w * 0.5
                and not is_centered_block
                and line_class == 'BODY'
            )
            if is_right_aligned:
                line_class = 'RIGHT'
                continue_processing = False
            else:
                continue_processing = True
            is_indented_subitem = (
                continue_processing
                and block_lm >= 35
                and not is_centered_block
                and line_class == 'BODY'
                and rm > 20
                and (is_outline_item or is_narrow_indented or is_all_italic)
            )
            if is_indented_subitem:
                line_class = 'INDENT'
            # Centered block: override BODY → CENTERED (do not override FOOTNOTE/VERSE).
            # Also demote H1/H2 → CENTERED_H1/CENTERED_H2 when centered AND NOT
            # a chapter heading ("CHAPTER N"). Chapter headings keep H1 so the
            # publish script's `^# CHAPTER (\d+)` regex still splits correctly.
            # Strip any <sty>...</sty> wrap before testing the content.
            stripped_text = re.sub(r'</?sty(?:\s[^>]*)?>', '', full_text).strip()
            # Allow trailing fn marker ` f432` etc — PDF sometimes attaches a
            # footnote ref to chapter heading.
            stripped_text_no_fn = re.sub(r'\s+f\d+[A-Za-z]?\s*$', '', stripped_text).strip()
            is_chapter_h1 = bool(re.match(r'^CHAPTER\s+\d+\s*$', stripped_text_no_fn))
            if is_centered_block:
                if line_class == 'BODY':
                    line_class = 'CENTERED'
                elif line_class == 'H1' and not is_chapter_h1:
                    line_class = 'CENTERED_H1'
                elif line_class == 'H2':
                    line_class = 'CENTERED_H2'
            block_lines_output.append((line_class, full_text))

        if not block_lines_output:
            continue

        cur_cls, cur_texts = block_lines_output[0]
        for cls, txt in block_lines_output[1:]:
            if cls == cur_cls:
                prev = cur_texts[-1] if isinstance(cur_texts, list) else cur_texts
                if (prev if isinstance(prev, str) else '').rstrip().endswith('-'):
                    cur_texts = (cur_texts[:-1] if isinstance(cur_texts, list) else []) + \
                                [(prev if isinstance(prev, str) else '').rstrip()[:-1] + txt.lstrip()]
                else:
                    if isinstance(cur_texts, str):
                        cur_texts = [cur_texts]
                    cur_texts.append(txt)
            else:
                texts = cur_texts if isinstance(cur_texts, list) else [cur_texts]
                merged = ' '.join(t.strip() for t in texts if t.strip())
                if merged.strip():
                    output_lines.append(f'[{cur_cls}] {merged}')
                cur_cls, cur_texts = cls, txt

        texts  = cur_texts if isinstance(cur_texts, list) else [cur_texts]
        merged = ' '.join(t.strip() for t in texts if t.strip())
        if merged.strip():
            output_lines.append(f'[{cur_cls}] {merged}')

    # End of page — flush any pending scripture buffer
    flush_scripture_buffer()
    return output_lines


def extract_ages_phil(cfg):
    doc   = fitz.open(cfg['pdf'])
    total = len(doc)
    print(f"Processing {total} pages...")

    all_output = []
    for page_num in range(total):
        all_output.append(f'\n--- PAGE {page_num + 1} ---\n')
        all_output.extend(phil_reconstruct_page(doc[page_num], page_num=page_num))

    doc.close()
    out_path = cfg['out']
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_output) + '\n')
    print(f'Done! Written to: {out_path}')
    print(f'Total lines: {len(all_output)}')


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

DISPATCH = {
    'ccel_harmony':  extract_ccel_harmony,
    'ccel_parallel': extract_ccel_parallel,
    'ccel_acts':     extract_ccel_acts,
    'ages_heb':      extract_ages_heb,
    'ages_corinth':  extract_ages_corinth,
    'ages_phil':     extract_ages_phil,
}


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/calvin_extract.py <volume>')
        print('Volumes:', ', '.join(sorted(VOLUMES)))
        sys.exit(1)
    vol = sys.argv[1]
    if vol not in VOLUMES:
        print(f'Unknown volume: {vol!r}')
        print('Volumes:', ', '.join(sorted(VOLUMES)))
        sys.exit(1)
    cfg = VOLUMES[vol]
    print(f'Extracting {vol} [{cfg["format"]}]...')
    DISPATCH[cfg['format']](cfg)


if __name__ == '__main__':
    main()
