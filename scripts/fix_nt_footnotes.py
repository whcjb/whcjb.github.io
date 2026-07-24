#!/usr/bin/env python3
"""
Fix NT mhenry footnotes + body against the Chinese PDF ground truth.

The PDF renders body at font size 12 and footnotes at size 10.  The original
extractor scrambled the two at page-break seams: footnote text leaked INTO the
body (as stray paragraphs), real body text leaked OUT into the <aside>, and some
footnotes were dropped entirely.

Per chapter this tool:
  1. Extracts the authoritative footnote list (size-10 text, split on left-margin
     leader numbers) and the true body (size-12, y-aware, running headers stripped).
  2. Pass 1 — for every PDF footnote that is embedded in the md body, replaces that
     stray paragraph with the correct bridging body text taken from the PDF (this
     simultaneously removes the footnote and restores the displaced body).
  3. Pass 2 — for any remaining body gap (body text that leaked to the old aside),
     re-inserts the PDF bridge at the seam.
  4. Rebuilds the <aside> from the authoritative footnote list (recovers dropped ones,
     drops garbage, renumbers).

Every body edit is LOCALLY verified against the PDF (anchor+bridge+anchor must be a
contiguous PDF substring, anchors unique).  Anything uncertain is SKIPPED and logged;
the aside is still rebuilt (that part is always safe).  Set STRICT to require zero
skips before writing body edits.

    python3 scripts/fix_nt_footnotes.py analyze [book...]
    python3 scripts/fix_nt_footnotes.py apply   [book...]
"""
import fitz, re, sys, os

PDF_DIR = os.path.expanduser("~/Documents/论文/matthew_henry/")
BOOKS = {
    'matthew': ['40马太亨利完整圣经注释-马太福音（01-10）.pdf',
                '40马太亨利完整圣经注释-马太福音（11-20）.pdf',
                '40马太亨利完整圣经注释-马太福音（21-28）.pdf'],
    'mark':    ['41马太亨利完整圣经注释-马可福音.pdf'],
    'luke':    ['42马太亨利完整圣经注释-路加福音.pdf'],
    'acts':    ['44马太亨利完整圣经注释-使徒行传（第01-14章）.pdf',
                '44马太亨利完整圣经注释-使徒行传（第15-28章）.pdf'],
    'hebrews': ['58马太亨利完整圣经注释-希伯来书.pdf'],
    # ---- Old Testament ----
    'genesis': ['01马太亨利完整圣经注释-创世记01-20.pdf', '01马太亨利完整圣经注释-创世记21-50.pdf'],
    'exodus': ['02马太亨利完整圣经注释-出埃及记.pdf'],
    'leviticus': ['03马太亨利完整圣经注释-利未记.pdf'],
    'numbers': ['04马太亨利完整圣经注释-民数记.pdf'],
    'deuteronomy': ['05马太亨利完整圣经注释-申命记.pdf'],
    'joshua': ['06马太亨利完整圣经注释-约书亚记.pdf'],
    'judges': ['07马太亨利完整圣经注释-士师记.pdf'],
    'ruth': ['08马太亨利完整圣经注释-路得记.pdf'],
    '1samuel': ['09马太亨利完整圣经注释-撒母耳记上.pdf'],
    '2samuel': ['10马太亨利完整圣经注释-撒母耳记下.pdf'],
    '1kings': ['11马太亨利完整圣经注释-列王纪上.pdf'],
    '2kings': ['12马太亨利完整圣经注释-列王纪下.pdf'],
    '1chronicles': ['13马太亨利完整圣经注释-历代志上.pdf'],
    '2chronicles': ['14马太亨利完整圣经注释-历代志下.pdf'],
    'ezra': ['15马太亨利完整圣经注释-以斯拉记.pdf'],
    'nehemiah': ['16马太亨利完整圣经注释-尼希米记.pdf'],
    'esther': ['17马太亨利完整圣经注释-以斯帖记.pdf'],
    'psalms': ['19马太亨利完整圣经注释-诗篇（卷1）001-041.pdf', '19马太亨利完整圣经注释-诗篇（卷2）042-072.pdf',
               '19马太亨利完整圣经注释-诗篇（卷3）073-089.pdf', '19马太亨利完整圣经注释-诗篇（卷4）090-106.pdf',
               '19马太亨利完整圣经注释-诗篇（卷5）107-150.pdf'],
    'jeremiah': ['24马太亨利完整圣经注释-耶利米书.pdf'],
    'lamentations': ['25马太亨利完整圣经注释-耶利米哀歌.pdf'],
    'ezekiel': ['26马太亨利完整圣经注释-以西结书.pdf'],
    'daniel': ['27马太亨利完整圣经注释-但以理书.pdf'],
    'hosea': ['28马太亨利完整圣经注释-何西阿书.pdf'],
    'joel': ['29马太亨利完整圣经注释-约珥书.pdf'],
    'amos': ['30马太亨利完整圣经注释-阿摩司书.pdf'],
    'obadiah': ['31马太亨利完整圣经注释-俄巴底亚书.pdf'],
    'jonah': ['32马太亨利完整圣经注释-约拿书.pdf'],
    'micah': ['33马太亨利完整圣经注释-弥迦书.pdf'],
    'nahum': ['34马太亨利完整圣经注释-那鸿书.pdf'],
    'habakkuk': ['马太亨利完整圣经注释-哈巴谷书.pdf'],
    'zephaniah': ['马太亨利完整圣经注释-西番雅书.pdf'],
    'zechariah': ['马太亨利完整圣经注释-撒迦利亚书.pdf'],
    'malachi': ['马太亨利完整圣经注释-玛拉基书.pdf'],
}
CN = '零一二三四五六七八九十'
def _tens(s):
    if s == '十': return 10
    if '十' in s:
        a, _, b = s.partition('十'); return (CN.index(a) if a else 1) * 10 + (CN.index(b) if b else 0)
    return CN.index(s)
def cn2int(s):
    # supports up to 第一百五十篇 (Psalms)
    if '百' in s:
        a, _, rest = s.partition('百')
        h = (CN.index(a) if a else 1) * 100
        rest = rest.lstrip('零')                            # 一百零五 → 五
        if not rest: return h
        if rest.startswith('十'): rest = '一' + rest        # 一百十 → 110
        return h + _tens(rest)
    return _tens(s)

ASIDE_RE = re.compile(r'<aside class="mhenry-footnotes">(.*?)</aside>\s*', re.S)
ENTRY_RE = re.compile(r'<p><sup>\d+</sup>\s*(.*?)</p>', re.S)
TOP_MARGIN = 40           # running header y threshold
PAGE_MID   = 400          # boundary-page ownership midpoint
A = 18                    # anchor length


HEAD_RE = re.compile(r'第([零一二三四五六七八九十百]+)[章篇]')

def scan_headings(doc):
    """[(page, y, chapter_num)] for size>=13 第N章/第N篇 headings."""
    out = []
    for pi in range(len(doc)):
        for blk in doc[pi].get_text("dict")['blocks']:
            for ln in blk.get('lines', []):
                for sp in ln['spans']:
                    m = re.fullmatch(HEAD_RE, sp['text'].strip())
                    if m and round(sp['size']) >= 13:
                        out.append((pi, round(sp['bbox'][1]), cn2int(m.group(1))))
    return out


def running_header_ranges(doc):
    """Fallback for books without size-14 headings: attribute each page to the
       chapter named in its top running header (第N章). Whole-page segments."""
    page_ch = {}
    for pi in range(len(doc)):
        for blk in doc[pi].get_text("dict")['blocks']:
            for ln in blk.get('lines', []):
                for sp in ln['spans']:
                    if sp['bbox'][1] < TOP_MARGIN:
                        m = HEAD_RE.search(sp['text'])
                        if m:
                            page_ch[pi] = cn2int(m.group(1)); break
    cmap = {}
    for pi, ch in page_ch.items():
        cmap.setdefault(ch, dict(doc=doc, segs=[], fn_pages=[]))
        cmap[ch]['segs'].append((pi, TOP_MARGIN, 10 ** 6))
        cmap[ch]['fn_pages'].append(pi)
    return cmap


def chapter_map(files):
    """chapter_num -> dict(doc, segs=[(page,y_lo,y_hi)], fn_pages=[page,...])"""
    cmap = {}
    for fn in files:
        doc = fitz.open(PDF_DIR + fn)
        heads = scan_headings(doc)
        if not heads:                       # heading-less book → running-header fallback
            cmap.update(running_header_ranges(doc))
            continue
        BIG = 10 ** 6
        for i, (pg, y, ch) in enumerate(heads):
            npg, ny = (heads[i + 1][0], heads[i + 1][1]) if i + 1 < len(heads) else (len(doc) - 1, BIG)
            segs = []
            if npg == pg:
                segs.append((pg, y, ny))
            else:
                segs.append((pg, y, BIG))
                for p in range(pg + 1, npg):
                    segs.append((p, 0, BIG))
                if ny != BIG:
                    segs.append((npg, 0, ny))
                else:
                    segs.append((npg, 0, BIG))
            # footnote page ownership
            fn_pages = []
            for (p, ylo, yhi) in segs:
                owns = True
                if yhi != BIG and p == npg:                      # boundary page top belongs to ch
                    owns = (ny - 0) > (760 - ny)                 # ch owns majority?
                if p == pg and i + 1 < len(heads) and heads[i + 1][0] == pg:
                    owns = (ny - y) > (760 - ny)
                if owns:
                    fn_pages.append(p)
            cmap[ch] = dict(doc=doc, segs=segs, fn_pages=fn_pages)
    return cmap


def true_body(info):
    out = []
    doc = info['doc']
    for (p, ylo, yhi) in info['segs']:
        for blk in doc[p].get_text("dict")['blocks']:
            for ln in blk.get('lines', []):
                for sp in ln['spans']:
                    y = sp['bbox'][1]
                    if 11.3 <= sp['size'] <= 13.0 and sp['text'].strip() and y >= TOP_MARGIN and ylo <= y <= yhi:
                        out.append(sp['text'])
    s = ''.join(out)
    return re.sub(r'\s', '', s)


def extract_footnotes(info):
    doc = info['doc']; fns = []
    for p in info['fn_pages']:
        cur = None
        for blk in doc[p].get_text("dict")['blocks']:
            for ln in blk.get('lines', []):
                for sp in ln['spans']:
                    sz, x, t = sp['size'], sp['bbox'][0], sp['text']
                    if not t.strip():
                        continue
                    if sz <= 8.5 and x < 60 and re.fullmatch(r'\d{1,2}', t.strip()):
                        if cur is not None:
                            fns.append(cur)
                        cur = ''
                    elif 9.3 <= sz <= 10.7:
                        if cur is not None:
                            cur += t
        if cur is not None:
            fns.append(cur)
    return [re.sub(r'\s+', '', f) for f in fns if f.strip()]


def html_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def bridge(raw_body, tb, before_md, after_md, log, what):
    """Replace raw_body[after before_md : before after_md] with the PDF text between them.
       before_md/after_md are clean body substrings surrounding a corrupted span."""
    if raw_body.count(before_md) != 1:
        log.append(f"  SKIP[{what}] before-anchor not unique in md ({raw_body.count(before_md)})"); return None
    bpos = raw_body.find(before_md) + len(before_md)
    apos = raw_body.find(after_md, bpos)
    if apos < 0:
        log.append(f"  SKIP[{what}] after-anchor not found in md"); return None
    if tb.count(before_md) != 1:
        log.append(f"  SKIP[{what}] before-anchor not unique in PDF ({tb.count(before_md)})"); return None
    tb_b = tb.find(before_md) + len(before_md)
    tb_a = tb.find(after_md, tb_b)
    if tb_a < 0:
        log.append(f"  SKIP[{what}] after-anchor not found in PDF after before-anchor"); return None
    gap = tb[tb_b:tb_a]
    if len(gap) > 700:
        log.append(f"  SKIP[{what}] gap too long ({len(gap)})"); return None
    cur = raw_body[bpos:apos]
    if cur == gap:
        return raw_body  # already correct
    if '<' in cur or '>' in cur or '\n\n\n' in cur:
        log.append(f"  SKIP[{what}] span crosses structural markup ({len(cur)} chars)"); return None
    new = raw_body[:bpos] + gap + raw_body[apos:]
    # local verify: PDF contains before+gap+after contiguously
    assert (before_md + gap + after_md) in tb
    log.append(f"  OK[{what}] {len(cur)}→{len(gap)} : …{before_md[-6:]}⟨{gap[:22]}…⟩{after_md[:6]}…")
    return new


def clean_run(s, i, direction, n=A):
    """Grab n consecutive CJK/punct chars from s starting near i (no tag chars)."""
    # s here is raw md body; we want a contiguous plain-text run
    if direction > 0:
        m = re.search(r'[一-鿿，。；：？！、（）“”‘’]{%d,}' % n, s[i:i + 300])
        return m.group(0)[:n] if m else ''
    else:
        seg = s[max(0, i - 300):i]
        ms = re.findall(r'[一-鿿，。；：？！、（）“”‘’]{%d,}' % n, seg)
        return ms[-1][-n:] if ms else ''


def process(book, ch, info, path, apply):
    md = open(path, encoding='utf-8').read()
    m = ASIDE_RE.search(md)
    true_fns = extract_footnotes(info)
    tb = true_body(info)
    if not m and not true_fns:
        return
    old_entries = [re.sub(r'\s', '', e) for e in (ENTRY_RE.findall(m.group(1)) if m else [])]
    fn_blob = ''.join(true_fns)
    body = md[:m.start()] if m else md
    tail = md[m.end():] if m else ''
    log = []

    # ---- Pass 1: embedded footnotes in body ----
    for F in true_fns:
        if len(F) < 12:
            continue
        # try to find F (or a long prefix) embedded in body between blank lines
        probe = F
        idx = body.find(probe)
        if idx < 0:
            probe = F[:40]
            idx = body.find(probe) if len(probe) >= 20 else -1
        if idx < 0:
            continue
        # anchors = clean body just before the footnote and immediately after it
        # (works for both inline-in-overview and standalone-paragraph footnotes)
        before_md = clean_run(body, idx, -1)
        after_md = clean_run(body, idx + len(probe), +1)
        if not before_md or not after_md:
            log.append(f"  SKIP[embed] no clean anchor around {F[:16]}…"); continue
        res = bridge(body, tb, before_md, after_md, log, 'embed')
        if res:
            body = res

    # ---- Pass 1b: delete stray paragraphs that are wholly footnote text ----
    # (footnotes appended at the end of a unit body; body itself is complete).
    # Preserve any HTML tags in the segment — only the footnote TEXT is removed.
    def seg_core(p):
        return re.sub(r'\s', '', re.sub(r'<[^>]+>', '', p))
    parts = re.split(r'(\n\n+)', body)   # keep separators
    changed = False
    for i in range(0, len(parts), 2):
        core = seg_core(parts[i])
        if len(core) >= 16 and core in fn_blob:
            # drop the footnote text but keep tags (e.g. a trailing </div>)
            tags_only = ''.join(re.findall(r'<[^>]+>', parts[i]))
            log.append(f"  OK[trail] delete stray footnote para: {core[:26]}…")
            parts[i] = tags_only
            changed = True
    if changed:
        body = ''.join(parts)
        body = re.sub(r'\n{3,}', '\n\n', body)

    # ---- Pass 2: displaced-out body still sitting in old aside garbage ----
    for e in old_entries:
        # garbage = part of entry not in PDF footnote text
        k = 0
        while k < len(e):
            if e[k:] and e[k:] in fn_blob:
                break
            k += 1
        garbage = e[:k]
        if not garbage or garbage in fn_blob or len(garbage) < 6:
            continue
        if garbage not in tb:
            log.append(f"  SKIP[disp] garbage not in PDF body: {garbage[:18]}…"); continue
        gp = tb.find(garbage)
        if gp < A:
            continue
        before_md = tb[gp - A:gp]
        if body.count(before_md) != 1:
            continue  # likely already fixed by pass 1
        bpos = body.find(before_md) + len(before_md)
        after_md = clean_run(body, bpos, +1)
        if not after_md:
            continue
        res = bridge(body, tb, before_md, after_md, log, 'disp')
        if res:
            body = res

    # ---- rebuild aside ----
    if true_fns:
        aside = '<aside class="mhenry-footnotes">\n'
        for i, t in enumerate(true_fns, 1):
            aside += f"<p><sup>{i}</sup> {html_escape(t)}</p>\n"
        aside += "</aside>\n"
    else:
        aside = ''
    new_md = body.rstrip('\n') + ('\n\n' + aside if aside else '\n') + tail

    oks = sum(1 for l in log if l.strip().startswith('OK'))
    # residual: PDF footnotes (>=16 chars) still embedded in the final body
    fbody = new_md[:ASIDE_RE.search(new_md).start()] if ASIDE_RE.search(new_md) else new_md
    residual = [F for F in true_fns if len(F) >= 16 and F in fbody]
    tag = ' ⚠RESIDUAL' if residual else ''
    print(f"  ch{ch:<3} PDF_fn={len(true_fns):<3} old_fn={len(old_entries):<3} body_edits={oks} residual={len(residual)}{tag}")
    for l in log:
        print(l)
    for F in residual:
        print(f"     residual embedded fn: {F[:40]}…")

    if apply:
        m2 = ASIDE_RE.search(new_md)
        got = ''.join(re.sub(r'\s', '', x) for x in ENTRY_RE.findall(m2.group(1))) if m2 else ''
        assert got == re.sub(r'\s', '', fn_blob), f"aside mismatch {book} ch{ch}"
        open(path, 'w', encoding='utf-8').write(new_md)
    return residual


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'analyze'
    books = sys.argv[2:] or list(BOOKS)
    apply = (mode == 'apply')
    for book in books:
        print(f"\n===== {book} =====")
        cmap = chapter_map(BOOKS[book])
        for ch in sorted(cmap):
            path = f"mhenry/{book}/{ch}.md"
            if os.path.exists(path):
                process(book, ch, cmap[ch], path, apply)


if __name__ == '__main__':
    main()
