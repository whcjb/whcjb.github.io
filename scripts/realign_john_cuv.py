#!/usr/bin/env python3
"""CUV-based structural rebuild for mhenry/john chapters that realign_john.py
left with verse-range LABEL boxes instead of scripture (ch 8,10,12,14-17).

Same robust approach as realign_romans.py: locate scripture blocks by matching
和合本 (assets/cuv.json book 43) verse-by-verse, segment by position gap, build
mh-unit (mh-verse = PDF scripture, mh-unit-body = commentary with mh-l1 outline).

Reuses the pure helpers from realign_romans (find_verse / verse_end / norm /
merge_paras / dedup_repeated) and mhenry_pdf_to_md.render_unit.

Only WRITES a chapter when the rebuild reaches high verse coverage and produces
zero label boxes; otherwise it reports and skips (so partially-divergent chapters
like the 梁弟兄-edition john 10 are never clobbered with a worse version).

Usage:
  python3 scripts/realign_john_cuv.py --dry-run 14 15 16 17
  python3 scripts/realign_john_cuv.py 12 14 15 16 17
"""
import sys, re, json, importlib.util
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF  = Path.home() / "Documents/论文/matthew_henry/马太亨利圣经注释-约翰福音.pdf"
CUV  = json.load(open(ROOT / "assets/cuv.json", encoding="utf-8"))["43"]

_m = importlib.util.spec_from_file_location("mh", ROOT / "scripts/mhenry_pdf_to_md.py")
mh = importlib.util.module_from_spec(_m); _m.loader.exec_module(mh)
_r = importlib.util.spec_from_file_location("rr", ROOT / "scripts/realign_romans.py")
rr = importlib.util.module_from_spec(_r); _r.loader.exec_module(rr)

norm = rr.norm
find_verse = rr.find_verse
verse_end = rr.verse_end
merge_paras = rr.merge_paras
dedup_repeated = rr.dedup_repeated
strip_trailing_heading = rr.strip_trailing_heading

DOC = fitz.open(str(PDF))
# realign_john.py's validated page ranges (1-indexed, inclusive)
CH_PAGES = {8:(130,157), 10:(176,190), 12:(214,234), 14:(253,268),
            15:(269,279), 16:(280,295), 17:(296,315)}

def chapter_text(ch):
    s, e = CH_PAGES[ch]
    txt = "\n".join(p["text"] for pg in range(s - 1, e) for p in mh.get_page_paras(DOC[pg]))
    txt = dedup_repeated(txt)
    # strip the chapter heading (arabic "第8 章" or chinese "第十章" or "约翰福音第X章")
    m = re.search(r'(?:约翰福音)?第\s*(?:\d{1,2}|[一二三四五六七八九十]+)\s*章', txt)
    if m and m.start() < 400:
        txt = txt[m.end():]
    return txt

def segment_chapter(ch):
    orig = chapter_text(ch)
    verses = sorted(CUV[str(ch)].keys(), key=int)
    cur, pos = 0, {}
    for v in verses:
        p = find_verse(orig, cur, v, CUV[str(ch)][v])
        if p is not None:
            pos[v] = p; cur = p + 1
    matched = [v for v in verses if v in pos]
    if not matched:
        return "", [], 0.0
    blocks = [[matched[0]]]
    for v in matched[1:]:
        if pos[v] - pos[blocks[-1][-1]] > 400:
            blocks.append([v])
        else:
            blocks[-1].append(v)
    first = pos[blocks[0][0]]
    overview, _ = strip_trailing_heading(orig[:first])
    units = []
    for bi, blk in enumerate(blocks):
        lo, hi = blk[0], blk[-1]
        e = verse_end(orig, pos[hi], CUV[str(ch)][hi]) or (pos[hi] + 60)
        scripture = re.sub(r'[\s　]+', ' ', orig[pos[lo]:e]).strip()
        # this edition prints a section marker "约14:1-3" / "1-3" right before the
        # scripture; find_verse anchors on the marker's number, so strip a leading
        # range marker (needs a dash between numbers → never matches real "1你们…").
        scripture = re.sub(r'^(?:约\s*\d+\s*[:：]\s*)?\d+\s*[-－]\s*\d+\s*', '', scripture)
        nxt = pos[blocks[bi + 1][0]] if bi + 1 < len(blocks) else len(orig)
        comm, _ = strip_trailing_heading(orig[e:nxt])
        comm = re.sub(r'^[\s　。.，,：:；;？?！!」』]+', '', comm.strip())
        units.append({"lo": int(lo), "hi": int(hi), "scripture": scripture, "commentary": comm})
    coverage = len(matched) / len(verses)
    return overview.strip(), units, coverage

def render_chapter(ch):
    overview, units, cov = segment_chapter(ch)
    p = ROOT / f"mhenry/john/{ch}.md"
    hdr, date = "nt-bg-100.jpg", "2026-04-29 10:57"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("header-img:"): hdr = line.split(":", 1)[1].strip()
        elif line.startswith("date:"): date = line.split(":", 1)[1].strip()
        elif line.startswith(("<div", "##")): break
    out = [f"""---
layout: mhenry-chapter
book_id: john
book_name: 约翰福音
chapter: {ch}
total_chapters: 21
header-img: {hdr}
date: {date}
---

"""]
    if overview:
        out.append(f'<div class="mh-overview">\n{mh.html_escape(overview)}\n</div>\n\n')
    for u in units:
        out.append(mh.render_unit({"label": "", "verse_range": u["scripture"],
                                    "body": merge_paras(u["commentary"])}))
        out.append("\n")
    return "".join(out), units, cov

def main(argv):
    dry = "--dry-run" in argv
    chs = [int(a) for a in argv if not a.startswith("-")] or sorted(CH_PAGES)
    for ch in chs:
        out, units, cov = render_chapter(ch)
        labels = sum(1 for u in units if re.match(r'^\s*约\s*\d+[:：]', u["scripture"]))
        ranges = ", ".join("%d-%d" % (u["lo"], u["hi"]) for u in units)
        ok = cov >= 0.85 and labels == 0
        status = "WRITE" if ok else "SKIP(覆盖率低/有标签)"
        if dry:
            print(f"[dry] john/{ch}: cov={cov:.2f} labels={labels} {len(units)}单元 [{ranges}] -> {status}")
        elif ok:
            (ROOT / f"mhenry/john/{ch}.md").write_text(out, encoding="utf-8")
            print(f"✓ john/{ch}: cov={cov:.2f} {len(units)}单元 [{ranges}] ({len(out)}字节)")
        else:
            print(f"⏭ john/{ch}: cov={cov:.2f} labels={labels} — 跳过(需单独处理)")

if __name__ == "__main__":
    main(sys.argv[1:])
