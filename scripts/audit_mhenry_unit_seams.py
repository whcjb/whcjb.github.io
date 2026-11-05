#!/usr/bin/env python3
"""马太亨利中文版：经文框 ↔ 注释体「接缝」体检（只读，零模型额度）。

把每个 mh-unit 的经文框末尾、注释体开头放回中文 PDF 定位，报两类错：

  [A] 注释开头被吞：PDF 里经文末尾与注释开头之间夹着一段 md 没有的仿宋正文
      （马太3章 1-6 节：引言 + 「I.他出现的时间……前章说的是」整段丢失）
  [B] 注释漏进经文框：经文框末尾那段在 PDF 里是仿宋（注释字体），不是楷体经文
      （马太3章 7-12 节：「约翰所传的是悔改的道……」挂在经文框尾）

PDF 字体：经文=整行 KaiTi，注释=FangSong（注释里的引文也用 KaiTi，所以 [B]
只看经文框最末一段、按字计 FangSong 占比）。只比汉字流，md 与 PDF 的标点/引号
差异不影响定位。

用法：
  python3 scripts/audit_mhenry_unit_seams.py              # 全部有中文 PDF 的卷
  python3 scripts/audit_mhenry_unit_seams.py matthew mark
"""
import glob, os, re, sys
import fitz, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.expanduser('~/Documents/论文/matthew_henry/')
TOP_MARGIN = 40
ANCHOR = 12          # 汉字锚点长度
GAP_MIN = 8          # [A] 接缝处多出的汉字数阈值（小标题一般 ≤ 8 字）
HAN = re.compile(r'[一-鿿]')
# 约翰 385 页版的页眉落在 y>40，按文字丢
RUNHEAD = re.compile(r'^马太亨利(完整)?圣经注释\s*[-–—：:]\s*\S{2,6}$')

# 书名 → PDF 文件（约翰用 385 页清洁版，见 mhenry skill §4.9）
OVERRIDE = {'john': ['马太亨利圣经注释-约翰福音.pdf']}


def pdf_files(book, zh):
    if book in OVERRIDE:
        return OVERRIDE[book]
    fs = sorted(os.path.basename(p) for p in glob.glob(PDF_DIR + '*.pdf')
                if zh in os.path.basename(p) and os.path.getsize(p) > 50000)
    return fs


_PROFILE = {}


def pdf_profile(files):
    """(正文最小字号, 繁转简函数或 None)。多数卷正文 12 号、脚注 10 号；罗马书 PDF 为繁体
    新细明体、正文 10.6 号、脚注 9 号——门槛取「正文众数字号 - 0.8」，繁体逐字转简（一对一，下标不变）。"""
    k = tuple(files)
    if k in _PROFILE:
        return _PROFILE[k]
    import collections
    sizes, trad = collections.Counter(), 0
    for fn in files:
        doc = fitz.open(PDF_DIR + fn)
        for page in list(doc)[2:12]:
            for blk in page.get_text('dict')['blocks']:
                for ln in blk.get('lines', []):
                    for sp in ln['spans']:
                        n = len(HAN.findall(sp['text']))
                        sizes[round(sp['size'], 1)] += n
                        if 'MingLiU' in sp['font']:
                            trad += n
    body = sizes.most_common(1)[0][0] if sizes else 12.0
    conv = None
    if trad > sum(sizes.values()) * 0.5:
        import opencc
        cc = opencc.OpenCC('t2s')
        cache = {}
        def conv(t):
            out = []
            for c in t:
                if c not in cache:
                    r = cc.convert(c)
                    cache[c] = r if len(r) == 1 else c
                out.append(cache[c])
            return ''.join(out)
    _PROFILE[k] = (min(11.0, body - 0.8), conv)
    return _PROFILE[k]


def pdf_stream(files):
    """汉字流 + 每字字体代码（各书经文字体不同，按书自适应）。丢页眉、丢脚注（<11 号）。"""
    chars, fonts, codes = [], [], {}
    min_size, conv = pdf_profile(files)
    for fn in files:
        doc = fitz.open(PDF_DIR + fn)
        for page in doc:
            for blk in page.get_text('dict')['blocks']:
                for ln in blk.get('lines', []):
                    for sp in ln['spans']:
                        if sp['size'] < min_size or sp['bbox'][1] < TOP_MARGIN:
                            continue
                        if RUNHEAD.match(sp['text'].strip()):
                            continue
                        k = codes.setdefault(sp['font'], chr(65 + len(codes)))
                        for c in HAN.findall(conv(sp['text']) if conv else sp['text']):
                            chars.append(c); fonts.append(k)
    return ''.join(chars), ''.join(fonts)


def han(s):
    s = re.sub(r'<[^>]+>', '', s)
    return ''.join(HAN.findall(s))


def _head(P, t, lo, hi):
    """t 的开头在 P[lo:hi] 里的位置；先试 12 字锚点，不行就往里挪、缩到 8 字。返回 (pos, exact)。"""
    for size in (ANCHOR, 8):
        for off in range(0, min(60, len(t) - size + 1), 3):
            j = P.find(t[off:off + size], lo, hi)
            if j >= 0:
                return j - off, off == 0 and size == ANCHOR
    return -1, False


def _tail(P, t, lo, hi):
    """t 的结尾在 P[lo:hi] 里的位置（从后往前找）。返回 (end, exact)。"""
    n = len(t)
    for size in (ANCHOR, 8):
        for off in range(0, min(60, n - size + 1), 3):
            j = P.rfind(t[n - off - size:n - off], lo, hi)
            if j >= 0:
                return j + size + off, off == 0 and size == ANCHOR
    return -1, False


VAR = str.maketrans('著麼么甚祢牠', '着吗吗什你它')
_NORM = {}


def locate(P, v, b, cur):
    """经文框开头 vs、经文框结尾 ve、注释开头 bs。先定开头与注释头，再在两者之间倒找框尾，
    避免框尾句子在前文重复出现（利2:3=2:10、家谱名单）时锚错。全程做和合本用字归一
    （著/着、么/吗…一对一替换，下标不变），框头在多处出现时挑后续吻合度最高的候选。"""
    if _NORM.get('id') != (len(P), P[:300]):   # 不能用 id(P)：前一卷对象回收后 id 会被复用
        _NORM['id'], _NORM['P'] = (len(P), P[:300]), P.translate(VAR)
    P = _NORM['P']
    v, b = v.translate(VAR), b.translate(VAR)
    vs, ex1 = _best(P, v, cur)
    if vs < 0 or not ex1:
        g, gx = _best(P, v, 0, len(P))           # 前面某单元锚得太靠后时，起点会被带跑
        if g >= 0 and gx:
            vs, ex1 = g, gx
    if vs < 0:
        return None
    hi = min(len(P), vs + len(v) + 3000)
    bs, ex2 = _head(P, b, vs + 1, hi)
    if bs < 0:
        return ('nobody', vs)
    ve, ex3 = _tail(P, v, vs, bs + ANCHOR)
    if ve < 0 or ve > bs + ANCHOR:
        return ('notail', vs)
    return vs, min(ve, bs), bs, (ex1, ex2, ex3)


def _best(P, v, cur, window=150000):
    import difflib
    key = v[:8]
    a = v[:200]
    best, score = -1, 0.0
    j = P.find(key, cur, cur + window)
    while j >= 0:
        def hit(x, y):
            sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
            return sum(k.size for k in sm.get_matching_blocks()) / max(1, len(x))
        r = 0.5 * hit(a[:60], P[j:j + 90]) + 0.5 * hit(a, P[j:j + int(len(a) * 1.5) + 20])
        if r > score:
            best, score = j, r
        j = P.find(key, j + 1, cur + window)
    if score >= 0.7:
        return best, True
    j, ex = _head(P, v, cur, len(P))
    return j, ex

UNIT_RE = re.compile(r'<div class="mh-verse">(.*?)</div>\s*<div class="mh-unit-body">(.*?)(?=<div class="mh-unit">|<aside|\Z)', re.S)


def chapter_files(book):
    fs = glob.glob(f'{ROOT}/mhenry/{book}/[0-9]*.md')
    return sorted(fs, key=lambda p: int(re.match(r'(\d+)', os.path.basename(p)).group(1)))


def audit(book, zh):
    files = pdf_files(book, zh)
    if not files:
        return None
    P, F = pdf_stream(files)
    out = []
    cur = 0
    for md in chapter_files(book):
        ch = os.path.basename(md)[:-3]
        s = open(md, encoding='utf-8').read()
        for ui, m in enumerate(UNIT_RE.finditer(s), 1):
            v, b = han(m.group(1)), han(m.group(2))
            if len(v) < ANCHOR or len(b) < ANCHOR:
                continue
            loc = locate(P, v, b, cur)
            if loc is None:
                out.append((ch, ui, '?', 'verse-head-not-found', v[:ANCHOR])); continue
            if len(loc) == 2:
                out.append((ch, ui, '?', loc[0], v[:ANCHOR])); cur = loc[1]; continue
            vs, ve, bs, exact = loc
            cur = bs
            vf = F[vs:vs + ANCHOR]
            vfont = max(set(vf), key=vf.count)
            gap = P[ve:bs]
            if len(gap) >= GAP_MIN:
                nv = sum(1 for c in F[ve:bs] if c != vfont)
                kind = '注释开头缺' if nv >= len(gap) / 2 else '经文框缺经文'
                out.append((ch, ui, 'A', f'{kind} {len(gap)} 字', gap[:60]))
            # [B]：经文框最后一个句子单元的字体
            tail = re.split(r'[。！？”」]', re.sub(r'<[^>]+>', '', m.group(1)).strip().rstrip('。！？”」 \n'))[-1]
            th = han(tail)
            if len(th) >= 6:
                tf = F[ve - len(th):ve]
                if sum(1 for c in tf if c != vfont) / len(tf) > 0.6:
                    out.append((ch, ui, 'B', f'经文框尾 {len(th)} 字为注释字体', th[:60]))
    return out


def main():
    books = yaml.safe_load(open(f'{ROOT}/_data/mhenry_books.yml', encoding='utf-8'))
    names = {}
    for grp in books.values():
        for bk in grp:
            names[bk['id']] = bk['name']
    want = sys.argv[1:] or list(names)
    total = 0
    for book in want:
        if book.endswith('-en') or book not in names:
            continue
        res = audit(book, names[book])
        if res is None and '纪' in names[book]:
            res = audit(book, names[book].replace('纪', '记'))
        if res is None and '记' in names[book]:
            res = audit(book, names[book].replace('记', '纪'))
        if res is None:
            print(f'-- {book}: 无中文 PDF，跳过'); continue
        print(f'== {book}: {len(res)}')
        for r in res:
            print('  ', *r)
        total += sum(1 for r in res if r[2] in 'AB')
    print('TOTAL A/B:', total)


if __name__ == '__main__':
    main()
