#!/usr/bin/env python3
"""Realign mhenry/romans/*.md structure from the PDF.

Background (skill mhenry §4.9 — same class of bug as the John gospel):
  The Romans chapters were extracted with the OT/John pipeline whose
  is_scripture() only fires on KaiTi font or 约N:M+hint. The Romans PDF
  ("45马太亨利圣经注释：罗马书.pdf", 古旧福音 edition) prints scripture in
  the SAME PMingLiU font as commentary and uses thematic section headings
  (保罗为犹太人担忧 / 神的主权 / 外邦人归信 …) rather than 约N:M markers, so no
  scripture was ever detected. Result: scripture got dumped inline into the
  mh-overview and the tails of mh-unit-body paragraphs, and only stray single
  verses ended up in mh-verse boxes.

Fix strategy (this script):
  1. Extract each chapter's paragraphs from the PDF (reuse get_page_paras).
  2. Locate scripture blocks by matching against 和合本 (assets/cuv.json book 45),
     searching verse-by-verse MONOTONICALLY forward (v.30 "这样我们可说什么呢"
     collides with v.14 — forward search disambiguates, cf. realign_john).
  3. Group verses into blocks by position gap (adjacent verses within a block
     are ~30-80 chars apart; commentary between blocks is thousands of chars).
  4. Each block => one mh-unit: mh-verse = the block's scripture text taken
     verbatim from the PDF (preserves edition wording e.g. 服事/陶匠), commentary
     = text between this block's end and the next block's heading. Thematic
     headings are dropped (they are an artifact of this edition; matthew et al.
     have none). Overview = text before the first block, minus chapter heading.
  5. Commentary paragraphs are wrapped with render_body_para (I./II. => mh-l1).

Usage:
  python3 scripts/realign_romans.py --dry-run 9     # report ch9 segmentation
  python3 scripts/realign_romans.py 9               # rewrite ch9
  python3 scripts/realign_romans.py                 # rewrite all 16
"""
import sys, re, json, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF  = Path.home() / "Documents/论文/matthew_henry/45马太亨利圣经注释：罗马书.pdf"
CUV  = json.load(open(ROOT / "assets/cuv.json", encoding="utf-8"))["45"]

# reuse helpers from the main pipeline
_spec = importlib.util.spec_from_file_location("mh", ROOT / "scripts/mhenry_pdf_to_md.py")
mh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mh)

import fitz

# Chapter start pages (0-indexed) — found via large-font 罗马书第X章 heading.
CH_START = {1:4, 2:19, 3:32, 4:47, 5:60, 6:75, 7:84, 8:95, 9:122,
            10:138, 11:148, 12:164, 13:191, 14:201, 15:225, 16:248}
DOC = fitz.open(str(PDF))
LAST_PAGE = len(DOC)  # 266

CN = ['', '一','二','三','四','五','六','七','八','九','十',
      '十一','十二','十三','十四','十五','十六']

def norm(s):
    # keep only CJK characters — strips every space / half- & full-width punctuation
    # (incl. ． U+FF0E used as verse-number separator "8．第一…") and digits, so the
    # fuzzy head/tail comparison aligns on scripture characters only.
    return re.sub(r'[^一-鿿]', '', s)

def dedup_repeated(text, minlen=140):
    """Remove verbatim duplicated blocks. The 古旧福音 Romans PDF duplicates the
    Rom 8:31-39 triumph passage (pages 114 & 116 repeat scripture + identical
    commentary). Detect a long block that reappears later and drop the 2nd copy.
    Conservative: only exact repeats >= minlen chars are removed (lossless)."""
    def norm_idx(s):
        return s
    changed = True
    while changed:
        changed = False
        n = len(text)
        # shingle -> first position
        W = 70
        seen = {}
        for i in range(0, n - W):
            sh = text[i:i + W]
            if sh in seen:
                j = seen[sh]                       # earlier occurrence at j, dup at i
                # extend the match forward
                a, b = j, i
                L = 0
                while b + L < n and text[a + L] == text[b + L]:
                    L += 1
                if L >= minlen and b >= a + L:     # non-overlapping, long enough
                    text = text[:b] + text[b + L:]
                    changed = True
                    break
            else:
                seen[sh] = i
        # loop again if we removed something
    return text

def chapter_text(ch):
    """Join all paragraphs of a chapter into one string (paras separated by \\n)."""
    start = CH_START[ch]
    end = CH_START[ch + 1] if ch + 1 in CH_START else LAST_PAGE
    paras = []
    for pg in range(start, end):
        paras.extend(mh.get_page_paras(DOC[pg]))
    return dedup_repeated("\n".join(p["text"] for p in paras))

# between two consecutive scripture chars the PDF may insert any run of spaces or
# punctuation — fullwidth 。／半角 . ／commas／quotes／brackets. Match any short run of
# non-Chinese, non-digit chars (stops at the next Chinese char or a verse number).
SEP = r'[^一-鿿\d]{0,4}'

def find_verse(orig, frm, vnum, cuv_text, head_n=6, max_bad=1):
    """Find position in `orig` (from frm) where verse `vnum` + its CUV text starts.
    Tolerant: the 古旧福音 edition uses variant characters vs 和合本 (做/作, 侍/事,
    窑/陶, 预/豫 …), so compare the first head_n Chinese chars allowing max_bad diffs.
    The verse number must be a standalone token (not part of a longer number)."""
    head = norm(cuv_text)[:head_n]
    if not head:
        return None
    vnum = str(vnum)
    for m in re.finditer(r'(?<!\d)' + re.escape(vnum) + r'(?!\d)', orig[frm:]):
        start = frm + m.start()
        window = orig[start + len(vnum): start + len(vnum) + head_n + 10]
        wnorm = norm(window)[:head_n]
        if len(wnorm) < head_n:
            continue
        bad = sum(1 for a, b in zip(head, wnorm) if a != b)
        if bad <= max_bad:
            return start
    return None

def verse_end(orig, frm, cuv_text, tail_n=6, max_bad=1):
    """Find the end index (in orig) of the verse whose CUV text tail is given, from frm.
    Tolerant of edition variant characters (see find_verse)."""
    tail = norm(cuv_text)[-tail_n:]
    if not tail:
        return None
    best = None
    for m in re.finditer(re.escape(tail[0]) + SEP + SEP.join(re.escape(c) for c in tail[1:tail_n]),
                         orig[frm:]):
        return frm + m.end()
    # fuzzy fallback: slide a window comparing normalized tail with <=max_bad diffs
    on = orig[frm:]
    onn = norm(on)
    # map normalized index back is complex; do a simple exact-first, else search last char cluster
    m = re.search(re.escape(tail[-1]), on)
    return frm + m.end() if m else None

def collapse(s):
    """Collapse whitespace inside scripture / commentary to single spaces, keep it one line."""
    s = re.sub(r'[\s　]+', ' ', s).strip()
    return s

HEADING_TAIL_RE = re.compile(r'[。.」』！？!?]\s*([^\s。.」』！？!?，、：]{2,12})\s*$')

def strip_trailing_heading(text):
    """Remove a short thematic heading glued to the end of a commentary chunk."""
    text = text.rstrip()
    m = HEADING_TAIL_RE.search(text)
    if m:
        return text[:m.start(1)].rstrip(), m.group(1)
    return text, None

def segment_chapter(ch):
    """Return (overview, [ (lo, hi, scripture_text, commentary_text) ... ])."""
    orig = chapter_text(ch)
    # drop leading chapter heading "罗马书第X章"
    hm = re.search(rf'罗马书第{CN[ch]}章', orig)
    if hm:
        orig = orig[hm.end():]
    verses = sorted(CUV[str(ch)].keys(), key=int)
    # locate each verse monotonically
    pos = {}
    cur = 0
    for v in verses:
        p = find_verse(orig, cur, v, CUV[str(ch)][v])
        if p is not None:
            pos[v] = p
            cur = p + 1
        # unmatched verses (edition spelling diff) are interpolated later
    matched = [v for v in verses if v in pos]
    # group into blocks by gap
    blocks = []
    curblk = [matched[0]]
    for v in matched[1:]:
        gap = pos[v] - pos[curblk[-1]]
        if gap > 400:            # commentary between => new block
            blocks.append(curblk); curblk = [v]
        else:
            curblk.append(v)
    blocks.append(curblk)

    units = []
    # overview = text before first block's heading
    first_pos = pos[blocks[0][0]]
    ov_raw = orig[:first_pos]
    overview, _ = strip_trailing_heading(ov_raw)

    for bi, blk in enumerate(blocks):
        lo, hi = blk[0], blk[-1]
        lo_pos = pos[lo]
        # scripture end = end of verse hi
        e = verse_end(orig, pos[hi], CUV[str(ch)][hi])
        if e is None:
            e = pos[hi] + 60
        scripture = collapse(orig[lo_pos:e])
        # commentary = from e to next block heading start
        if bi + 1 < len(blocks):
            nxt = pos[blocks[bi + 1][0]]
            comm_raw = orig[e:nxt]
        else:
            comm_raw = orig[e:]
        commentary, _ = strip_trailing_heading(comm_raw)
        # verse_end may cut mid-punctuation, leaving a stray leading 。/?/. — strip it
        commentary = re.sub(r'^[\s　。.，,：:；;？?！!」』]+', '', commentary.strip())
        units.append({
            "lo": int(lo), "hi": int(hi),
            "scripture": scripture,
            "commentary": commentary,
        })
    return overview.strip(), units

def split_commentary_paras(text):
    """Split commentary into paragraphs at outline markers (I. II. / 1. 2. / (1) / [1.])."""
    # normalize hard newlines to spaces first (PDF wrapping already joined by get_page_paras
    # per-block, but our slice may span multiple original paragraphs joined by \n)
    text = re.sub(r'\n+', '', text)
    # insert split points before outline markers
    marker = re.compile(r'(?=(?:^|)(?:I{1,3}|IV|VI{0,3}|VII|VIII|IX|X)\.'
                        r'|(?<=[。.」』])\d{1,2}\.'
                        r'|(?<=[。.」』])[（(]\d{1,2}[.）)]'
                        r'|(?<=[。.」』])\[\d{1,2}\.\])')
    # simpler: split before roman numerals at sentence starts and numbered points
    parts = re.split(r'(?<=[。.」』])(?=(?:I{1,3}|IV|VI{0,3}|VII|VIII|IX|X)\.\D)', text)
    out = []
    for part in parts:
        part = part.strip()
        if part:
            out.append(part)
    return out

TERMINAL_RE = re.compile(r'[。．.！!？?」』）)]$')
# an outline marker always begins a new logical paragraph even when the previous
# line ends mid-sentence (Matthew Henry's "为了…, I.他用庄严…" enumeration lead-in
# ends with a comma but I./II./III. must still become separate mh-l1 points).
OUTLINE_RE = re.compile(r'^(?:(?:I{1,3}|IV|VI{0,3}|VII|VIII|IX|X)\.'
                        r'|\d{1,2}\.'
                        r'|[（(]\d{1,2}[.）)]'
                        r'|\[\d{1,2}\.\])')

def merge_paras(text):
    """Split commentary on paragraph newlines, then squash page-break hard-wraps:
    join a chunk onto the previous one when the previous does not end with a
    sentence terminator (cut mid-sentence by a page/column break) UNLESS the
    chunk starts with an outline marker (then it is a real new point)."""
    chunks = [c.strip() for c in text.split('\n') if c.strip()]
    out = []
    for c in chunks:
        if out and not TERMINAL_RE.search(out[-1]) and not OUTLINE_RE.match(c):
            out[-1] = out[-1] + c
        else:
            out.append(c)
    return out

def read_frontmatter(ch):
    """Preserve existing header-img and date (skill §1.6: never change dates)."""
    p = ROOT / f"mhenry/romans/{ch}.md"
    hdr, date = "nt-bg-100.jpg", "2026-04-29 10:57"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("header-img:"): hdr = line.split(":",1)[1].strip()
            elif line.startswith("date:"): date = line.split(":",1)[1].strip()
            elif line.startswith("<div"): break
    return hdr, date

def render_chapter(ch):
    overview, units = segment_chapter(ch)
    hdr, date = read_frontmatter(ch)
    parts = [f"""---
layout: mhenry-chapter
book_id: romans
book_name: 罗马书
chapter: {ch}
total_chapters: 16
header-img: {hdr}
date: {date}
---

"""]
    if overview:
        parts.append(f'<div class="mh-overview">\n{mh.html_escape(overview)}\n</div>\n\n')
    for u in units:
        unit = {
            "label": "",
            "verse_range": u["scripture"],       # actual PDF scripture text goes in mh-verse
            "body": merge_paras(u["commentary"]),
        }
        parts.append(mh.render_unit(unit))
        parts.append("\n")
    return "".join(parts)

def write_chapter(ch):
    out = render_chapter(ch)
    p = ROOT / f"mhenry/romans/{ch}.md"
    p.write_text(out, encoding="utf-8")
    ov, units = segment_chapter(ch)
    ranges = ", ".join("%d-%d" % (u["lo"], u["hi"]) for u in units)
    print(f"✓ ch{ch}: {len(units)} 单元 [{ranges}]  ({len(out)}字节)")

def dry_run(ch):
    overview, units = segment_chapter(ch)
    print(f"\n===== 罗马书 ch{ch}: {len(units)} 个经文单元 =====")
    print(f"[overview] ({len(overview)}字) {overview[:80]}…")
    for u in units:
        print(f"\n  ── v.{u['lo']}-{u['hi']} ──")
        print(f"    经文({len(u['scripture'])}字): {u['scripture'][:100]}")
        print(f"    注释({len(u['commentary'])}字): {u['commentary'][:90]}…")

def main(argv):
    dry = "--dry-run" in argv
    argv = [a for a in argv if not a.startswith("-")]
    chs = [int(a) for a in argv] if argv else list(range(1, 17))
    for ch in chs:
        if dry:
            dry_run(ch)
        else:
            write_chapter(ch)

if __name__ == "__main__":
    main(sys.argv[1:])
