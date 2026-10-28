#!/usr/bin/env python3
"""费尔贝恩《教牧书信》(1874)：StudyLight 录入本 → fairbairn_raw/pastoral/units.json

底本是人工录入本（StudyLight「Fairbairn's Commentary on Ezekiel, Jonah and Pastoral
Epistles」，即 BibleSupport 的 e-Sword 模块，出自 2008 年 Libronix 本），网页经互联网
档案馆快照取得，地址见 PROVENANCE.md。正文字句一律照录入本。

录入本按经节挂条目，挂错了几处（1 章第 8 节条目放的是 2:8 的注释、1 章第 15 节放的是
5:15、提后 2 章多出一条提前 2:9–10），附录又「为方便起见」整篇嵌进了相关经节。扫描本
（IA pastoralepistle00fair 的 OCR 文本）在这里**只当顺序证人**：把录入本每一段按 6 词
串定位到原书里的位置，

  - 条目按原书位置重排；夹在别章条目之间的，改挂到前后条目所在的那一章；
  - 原书位置落在附录区的段落，是嵌进经节注释的附录副本，删去（附录另有单页）；
  - 录入本整节缺文的（原书有、录入本没有），记进 missing，页面上注明，不从 OCR 补。

用法：python3 scripts/extract_fairbairn.py      # 需要 src/（不入库，见 PROVENANCE.md）
"""
import collections
import html
import json
import re
import statistics
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'fairbairn_raw' / 'pastoral'
SRC = RAW / 'src' / 'studylight'
OCR = RAW / 'src' / 'scan' / 'pastoralepistle00fair_djvu.txt'

# 原书顺序：提前、提多、提后（「Expository Notes」三部分的先后）
BOOKS = [('1timothy', '1-timothy', 6), ('titus', 'titus', 3), ('2timothy', '2-timothy', 4)]
NV = {'1timothy': [20, 15, 16, 16, 25, 21], 'titus': [16, 15, 15], '2timothy': [18, 26, 17, 22]}

# 录入本整节缺文。原书页码据扫描本页眉；OCR 位置是 gaps 检测的结果，见 PROVENANCE.md。
MISSING = [
    ('1timothy', 1, 8, 'pp. 85–86'),
    ('1timothy', 1, 15, 'pp. 95–97'),
    ('1timothy', 5, 19, 'pp. 219–220'),
    ('titus', 3, 14, 'p. 305'),
    ('2timothy', 4, 3, 'pp. 383–384'),
]

K = 6


# ── 行内 HTML 清洗 ─────────────────────────────────────────────────────
KEEP = {'em', 'strong', 'sup', 'sub'}


def clean_inline(s: str) -> str:
    """录入本段落 HTML → 只留 em/strong/sup/sub 的干净 HTML；修好错层的 em/strong。"""
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<a\b[^>]*>', '', s).replace('</a>', '')
    out, stack = [], []
    for tok in re.split(r'(<[^>]+>)', s):
        if not tok:
            continue
        m = re.match(r'<(/?)([a-z0-9]+)', tok)
        if not tok.startswith('<') or not m:
            t = html.unescape(tok)
            t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            out.append(t)
            continue
        close, name = m.group(1) == '/', m.group(2)
        if name not in KEEP:
            continue
        if not close:
            stack.append(name)
            out.append(f'<{name}>')
        elif name in stack:
            # 关掉中间层再重开，保证嵌套正确
            reopen = []
            while stack and stack[-1] != name:
                n = stack.pop(); out.append(f'</{n}>'); reopen.append(n)
            stack.pop(); out.append(f'</{name}>')
            for n in reversed(reopen):
                stack.append(n); out.append(f'<{n}>')
        # 没开过的闭标签：丢掉
    while stack:
        out.append(f'</{stack.pop()}>')
    t = ''.join(out)
    t = re.sub(r'<(em|strong|sup|sub)>(\s*)</\1>', r'\2', t)          # 空标签
    t = re.sub(r'</(em|strong)>(\s*)<\1>', r'\2', t)                    # 相邻同类合并
    # 录入本的希腊文常把重音符拆成独立的组合字符并前后留空格：Κυ ́ ριου → Κύριου
    t = re.sub(r'\s*́\s*', '́', t)
    t = unicodedata.normalize('NFC', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def text_of(h: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()


# ── OCR 顺序证人 ──────────────────────────────────────────────────────
def ocr_index():
    ocr = OCR.read_text(encoding='utf-8', errors='ignore')
    ocr = re.sub(r'-\s*\n\s*', '', ocr)
    W = re.findall(r'[a-z]+', ocr.lower())
    idx = collections.defaultdict(list)
    for i in range(len(W) - K):
        idx[' '.join(W[i:i + K])].append(i)
    # 附录区起点：注释末尾之后第一个 APPENDIX
    appx = next(i for i in range(130000, len(W) - 1) if W[i] == 'appendix' and W[i + 1] == 'a')
    # 注释区起点：经文与译文之后的「THE FIRST EPISTLE TO TIMOTHY. CHAPTER I.」
    global NOTES_START
    NOTES_START = next(i for i in range(15000, len(W) - 6)
                       if W[i:i + 6] == ['the', 'first', 'epistle', 'to', 'timothy', 'chapter'])
    return idx, appx


NOTES_START = 0


def locate(h, idx):
    """段落在原书里的位置。只认注释区里的命中：注释段常整句引经文，经文在前面的
    「经文与译文」部分也出现过，不限范围会定位到那里（提多书 1:1 踩过）。"""
    T = re.findall(r'[a-z]+', text_of(h).lower())
    pos = []
    for i in range(max(1, len(T) - K + 1)):
        g = ' '.join(T[i:i + K])
        if g in idx and len(idx[g]) <= 3:
            pos += [q for q in idx[g] if q >= NOTES_START]
    return statistics.median(pos) if pos else None


# ── 章页：条目 ────────────────────────────────────────────────────────
HEADING_RE = re.compile(r'^(The (First|Second) Epistle (to|of Paul to) (Timothy|Titus)|The Epistle of Paul to Titus|'
                        r'Chapter [IVX\d]+|Appendix [ABC]\b.*)$')


def chapter_entries(book, page, ch, idx):
    t = (SRC / f'{page}-{ch}.html').read_text(encoding='utf-8', errors='ignore')
    i = t.find('<div class="commentaries-entry-div">')
    out = []
    for seg in re.split(r'(?=<div class="commentaries-entry-div">)', t[i:])[1:]:
        key = re.search(r'data-entry="([^"]+)"', seg).group(1)
        seg = seg.split('return-to-top-div')[0]
        paras = []
        for p in re.findall(r'<p>(.*?)</p>', seg, re.S):
            c = clean_inline(p)
            if not c:
                continue
            paras.append(dict(html=c, pos=locate(c, idx)))
        out.append(dict(book=book, ch=ch, key=key, src=f'{page}-{ch}#{key}', paras=paras))
    return out


VER_RE = re.compile(r'^(?:<[^>]+>)*\s*(Vers?)\s*[.,]\s*([\d][\d\s,\-–]*\d|\d+)\s*\.')


def parse_verses(e):
    """条目首段的「Ver. 5.」「Vers. 9, 10.」「Vers. 18-20.」→ [5] / [9,10] / [18,19,20]。"""
    for p in e['paras']:
        m = VER_RE.match(p['html'])
        if m:
            nums = [int(x) for x in re.findall(r'\d+', m.group(2))]
            if re.search(r'[-–]', m.group(2)) and len(nums) == 2:
                return list(range(nums[0], nums[1] + 1)), m.group(0)
            return nums, m.group(0)
        break
    nums = [int(x) for x in re.findall(r'\d+', e['key'])]
    return (list(range(nums[0], nums[-1] + 1)) if nums else []), None


def build_notes(idx, appx):
    entries = []
    for book, page, nch in BOOKS:
        for ch in range(1, nch + 1):
            entries += chapter_entries(book, page, ch, idx)
    log = dict(appendix_paras=0, heading_paras=0, moved=[])
    for e in entries:
        keep = []
        for p in e['paras']:
            tx = text_of(p['html'])
            if p['pos'] is not None and p['pos'] >= appx:
                log['appendix_paras'] += 1          # 嵌进经节的附录副本
                continue
            if HEADING_RE.match(tx) or (p['pos'] is None and len(tx.split()) <= 6 and not VER_RE.match(p['html'])
                                        and not re.match(r'(Sic fiunt|Quinque per)', tx)):
                log['heading_paras'] += 1
                continue
            keep.append(p)
        e['paras'] = keep
    entries = [e for e in entries if e['paras']]
    # 条目中途以「Ver. N.」起段的，从那里拆成子条目（录入本把相邻几节并在一个条目里）
    split = []
    for e in entries:
        cur = None
        for p in e['paras']:
            if cur is None or VER_RE.match(p['html']) and cur['paras'] and \
                    any(VER_RE.match(q['html']) for q in cur['paras']):
                cur = dict(e, paras=[], key=e['key'] if cur is None else e['key'] + '+')
                split.append(cur)
            cur['paras'].append(p)
    entries = split
    for e in entries:
        # 位置：带「Ver. N.」那一段的位置最可靠（其他段里的引文可能匹配到导论里的同句）
        lab = [p['pos'] for p in e['paras'] if VER_RE.match(p['html']) and p['pos'] is not None]
        ps = [p['pos'] for p in e['paras'] if p['pos'] is not None]
        e['pos'] = lab[0] if lab else (statistics.median(ps) if ps else None)
    # 没定位到的（短段）跟随录入本里的前一条
    last = 0
    for e in entries:
        if e['pos'] is None:
            e['pos'] = last + 0.01
        last = e['pos']
    # 按原书位置重排；前后各 3 条邻居里多数属于别的章的，改挂过去
    entries.sort(key=lambda e: e['pos'])
    home = [(e['book'], e['ch']) for e in entries]
    for k, e in enumerate(entries):
        nb = home[max(0, k - 3):k] + home[k + 1:k + 4]
        (best, cnt), = collections.Counter(nb).most_common(1)
        if best != home[k] and cnt >= 4:
            log['moved'].append(f"{e['src']} → {best[0]} {best[1]}")
            e['book'], e['ch'] = best
    for e in entries:
        e['vv'], e['label'] = parse_verses(e)
    # 缺文占位
    for book, ch, v, pages in MISSING:
        anchor = max((e for e in entries if e['book'] == book and e['ch'] == ch and e['vv'] and e['vv'][0] < v),
                     key=lambda e: e['pos'])
        k = entries.index(anchor) + 1
        entries.insert(k, dict(book=book, ch=ch, key=f'verse-{v}', src='(missing)', vv=[v], label=None,
                               pos=anchor['pos'] + 0.5, missing=pages, paras=[]))
    return entries, log


# ── 书卷首页：序言、导论、经文与译文、附录 ──────────────────────────────
def book_page():
    t = (SRC / '1-timothy.html').read_text(encoding='utf-8', errors='ignore')
    i = t.find('<div class="plr5">')
    j = t.find('StudyLight.org ©', i)
    return [clean_inline(p) for p in re.findall(r'<p>(.*?)</p>', t[i:j], re.S)]


def split_front(ps):
    tx = [text_of(p) for p in ps]

    def at(pred, start=0):
        return next(k for k in range(start, len(tx)) if pred(tx[k]))
    k_pref = at(lambda x: x == 'Preface')
    k_intro = at(lambda x: x == 'Introduction', k_pref)
    k_sec = [at(lambda x, n=n: x.startswith(f'Section {n}'), k_intro) for n in (1, 2, 3, 4)]
    k_text = at(lambda x: x.startswith('The Greek Text of the Epistles'))
    k_g = [at(lambda x: x.startswith('ΠΡΟΣ ΤΙΜΟΘΕΟΝ Α')), at(lambda x: x.startswith('ΠΡΟΣ ΤΙΤΟΝ')),
           at(lambda x: x.startswith('ΠΡΟΣ ΤΙΜΟΘΕΟΝ Β'))]
    k_app = at(lambda x: x == 'Appendix', k_text)
    k_a = [at(lambda x, L=L: x.startswith(f'Appendix {L}'), k_app) for L in 'ABC']
    k_note = at(lambda x: x.startswith('NOTE to p.'), k_a[2])
    sec_title = lambda k: re.sub(r'^Section \d\s*', '', tx[k]).strip()
    front = dict(
        title=[tx[k] for k in range(0, k_pref) if tx[k] and not tx[k].startswith('[') and 'Prepared for' not in tx[k]],
        preface=ps[k_pref + 1:k_intro],
        introduction=[dict(n=n + 1, title=sec_title(k_sec[n]),
                           paras=ps[k_sec[n] + 1:(k_sec[n + 1] if n < 3 else k_text)]) for n in range(4)],
        appendices=[dict(letter=L, head=tx[k_a[n]], paras=ps[k_a[n] + 1:(k_a[n + 1] if n < 2 else len(ps))])
                    for n, L in enumerate('ABC')],
        note_head=tx[k_note],
    )
    text = {}
    for n, book in enumerate(['1timothy', 'titus', '2timothy']):
        seg = ps[k_g[n]:(k_g[n + 1] if n < 2 else k_app)]
        gr, en = [], []
        for p in seg:
            x = text_of(p)
            g = len(re.findall(r'[Ͱ-Ͽἀ-῿]', x))
            L = len(re.findall(r'[A-Za-z]', x))
            if re.match(r'^(ΠΡΟΣ|The (First|Second) Epistle|The Epistle)', x):
                continue
            (gr if g > L else en).append(p)
        text[book] = dict(greek=split_chapters(gr), english=split_chapters(en))
    return front, text


CH_RE = re.compile(r'(?:(?<=\s)|^)((?:[IVΙ]{1,3}|IV|VI|V))\s?\.\s*(?=1\b)')


def split_chapters(paras):
    """连续经文流按章号（I. / II. …，希腊文里是希腊字母 Ι）切开。"""
    s = ' '.join(paras)
    s = re.sub(r'\s+', ' ', s)
    parts = CH_RE.split(s)
    chs = [parts[0].strip()]
    for k in range(1, len(parts), 2):
        chs.append(parts[k + 1].strip())
    if not chs[0]:
        chs = chs[1:]
    return chs


def main():
    idx, appx = ocr_index()
    entries, log = build_notes(idx, appx)
    front, text = split_front(book_page())
    for b, d in text.items():
        print(b, 'greek ch', len(d['greek']), 'english ch', len(d['english']))
    # 各章经节覆盖
    uncovered = []
    for book, _, nch in BOOKS:
        for ch in range(1, nch + 1):
            got = {v for e in entries if e['book'] == book and e['ch'] == ch for v in e['vv']}
            miss = [v for v in range(1, NV[book][ch - 1] + 1) if v not in got]
            if miss:
                uncovered.append(f'{book} {ch}: {miss}')
    units = dict(notes=[dict(book=e['book'], ch=e['ch'], vv=e['vv'], label=e['label'], src=e['src'],
                             missing=e.get('missing'), paras=[p['html'] for p in e['paras']]) for e in entries],
                 front=front, text=text, uncovered=uncovered,
                 log=dict(appendix_paras=log['appendix_paras'], heading_paras=log['heading_paras'],
                          moved=log['moved']))
    (RAW / 'units.json').write_text(json.dumps(units, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('条目', len(entries), '| 删附录副本段', log['appendix_paras'], '| 删标题段', log['heading_paras'])
    print('改挂章:', *log['moved'], sep='\n  ')
    print('未单独出条的经节（并入相邻条目或缺文）:', *uncovered, sep='\n  ')


if __name__ == '__main__':
    main()
