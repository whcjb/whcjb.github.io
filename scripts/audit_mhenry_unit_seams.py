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


def pdf_stream(files):
    """汉字流 + 每字字体代码（各书经文字体不同，按书自适应）。丢页眉、丢脚注（<11 号）。"""
    chars, fonts, codes = [], [], {}
    for fn in files:
        doc = fitz.open(PDF_DIR + fn)
        for page in doc:
            for blk in page.get_text('dict')['blocks']:
                for ln in blk.get('lines', []):
                    for sp in ln['spans']:
                        if sp['size'] < 11 or sp['bbox'][1] < TOP_MARGIN:
                            continue
                        if RUNHEAD.match(sp['text'].strip()):
                            continue
                        k = codes.setdefault(sp['font'], chr(65 + len(codes)))
                        for c in HAN.findall(sp['text']):
                            chars.append(c); fonts.append(k)
    return ''.join(chars), ''.join(fonts)


def han(s):
    s = re.sub(r'<[^>]+>', '', s)
    return ''.join(HAN.findall(s))


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
            ve = P.find(v[-ANCHOR:], cur)
            if ve < 0:
                ve = P.find(v[-ANCHOR:])
            if ve < 0:
                out.append((ch, ui, '?', 'verse-tail-not-found', v[-ANCHOR:]))
                continue
            ve += ANCHOR
            bs = P.find(b[:ANCHOR], ve - ANCHOR)
            if bs < 0 or bs - ve > 3000:
                out.append((ch, ui, '?', 'body-head-not-found', b[:ANCHOR]))
                cur = ve
                continue
            cur = bs
            # 经文字体 = 经文框开头那段在 PDF 里的主字体
            vs = P.find(v[:ANCHOR], max(0, ve - len(v) - 200), ve)
            vf = F[vs:vs + ANCHOR] if vs >= 0 else F[ve - ANCHOR:ve]
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
