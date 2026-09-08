#!/usr/bin/env python3
"""把 adjudicate_ocr_page.py 判读出的差异，落回已发布的中译文件。

判读产出的格式是每行 `影像=「X」 文本=「Y」 上下文=「…」`——
影像是底本扫描件上的实际字样（**权威**），文本是 OCR 读出来的（可能错）。
所以修法是把 Y 改成 X。

为什么不能全局替换
------------------
错误串中位长度只有 3–4 字，在全书里必然多处重复。罗马书实测：
按错误串直接查，253 条唯一命中、**219 条多处命中**。多处命中若盲replace
会波及无辜段落。

模型给的「上下文」字段也不能用来定位——它带省略号且经过模型自己转述，
实测 519 条里 446 条在正文中匹配不上。

可行做法是**页→章映射**：raw 的 page_000N.md 取一段特征串去各已发布章里找，
命中唯一即确定该页属于哪一章（罗马书 290/323 页可映射）。
再把替换限制在那一章之内，唯一命中才动手。

安全闸
------
- 影像侧含「?」= 模型自陈看不清 → 跳过
- 文本侧为空 = 纯漏字、无锚点可定位 → 跳过
- 该页无章映射 → 跳过
- 在所属章内非唯一命中 → 跳过
- 动手前整目录备份

用法：
    python3 scripts/apply_ocr_fixes.py --book romans --dry-run
    python3 scripts/apply_ocr_fixes.py --book romans --apply
"""
import argparse
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CJK = re.compile(r'[一-鿿]')

BOOKS = {
    'romans':     {'pub': 'calvin/romans', 'raw': 'calvin_raw/romans-scan/ocr',
                   'report': 'logs/adjudicate_romans.md', 'max_page': 323},
    'colossians': {'pub': 'calvin/colossians', 'raw': 'calvin_raw/colossians-scan/ocr',
                   'report': 'logs/adjudicate_colossians.md', 'max_page': None},
}

FIND_RE = re.compile(r'影像=「(.*?)」\s*文本=「(.*?)」(?:\s*上下文=「(.*?)」)?')


def cj(s):
    return ''.join(CJK.findall(s))


def parse_report(path):
    t = Path(path).read_text(encoding='utf-8')
    blocks = re.split(r'^## page (\d+)\s*$', t, flags=re.M)[1:]
    out = []
    for i in range(0, len(blocks), 2):
        pg = int(blocks[i])
        for m in FIND_RE.finditer(blocks[i + 1]):
            out.append((pg, m.group(1), m.group(2)))
    return out


def map_pages(cfg):
    """raw 页 → 已发布章文件。取该页第 30–54 个汉字作特征串，唯一命中才算数。"""
    pub = {}
    for f in sorted((ROOT / cfg['pub']).glob('*.md')):
        pub[f] = cj(re.sub(r'<[^>]+>', '', f.read_text(encoding='utf-8')))
    m = {}
    for rf in sorted((ROOT / cfg['raw']).glob('page_*.md')):
        n = int(re.search(r'page_(\d+)', rf.name).group(1))
        if cfg['max_page'] and n > cfg['max_page']:
            continue
        t = cj(re.sub(r'<[^>]+>', '', rf.read_text(encoding='utf-8')))
        if len(t) < 40:
            continue
        hit = [f for f, body in pub.items() if t[30:54] in body]
        if len(hit) == 1:
            m[n] = hit[0]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True, choices=sorted(BOOKS))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        sys.exit('要 --apply 或 --dry-run')

    cfg = BOOKS[a.book]
    recs = parse_report(ROOT / cfg['report'])
    pagemap = map_pages(cfg)
    print(f'判读条目 {len(recs)}；页→章映射 {len(pagemap)} 页\n')

    if a.apply:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = ROOT / f'logs/bak_{a.book}_{stamp}'
        bak.mkdir(parents=True, exist_ok=True)
        for f in (ROOT / cfg['pub']).glob('*.md'):
            shutil.copy(f, bak / f.name)
        print(f'已备份 → {bak}\n')

    texts = {f: f.read_text(encoding='utf-8')
             for f in (ROOT / cfg['pub']).glob('*.md')}
    stat = Counter()
    applied = []
    held = []
    for pg, img, txt in recs:
        if '?' in img or not img.strip():
            stat['跳过·影像存疑'] += 1; continue
        if not txt.strip():
            stat['跳过·纯漏字无锚点'] += 1; continue
        f = pagemap.get(pg)
        if not f:
            stat['跳过·该页无章映射'] += 1; continue
        # 闸门：把「订正错字」与「改写措辞」分开。
        #
        # ⚠️ 不能只看相似度：**单字替换的相似度恒为 0**（无公共子串），
        # 而单字形近混淆正是最典型的 OCR 错（虑/忠、睛/瞎、安/妄）。
        # 只按 ratio<0.5 卡，会把最该修的一类全挡掉（踩过：66 条里大半是单字）。
        #
        # 分两档：
        #   两侧都 ≤2 字  → 形近字替换，放行
        #   较长的串      → 要求高相似（增删一两字），否则是改写，退回人工
        # 另外无论长短，长度变化 >6 字一律退回——那已经不是错字而是整句出入。
        import difflib
        ratio = difflib.SequenceMatcher(None, txt, img).ratio()
        short = len(txt) <= 2 and len(img) <= 2
        if abs(len(img) - len(txt)) > 6 or (not short and ratio < 0.5):
            stat['退回人工·疑似改写非订正'] += 1
            held.append((pg, f.name, txt, img, round(ratio, 2)))
            continue
        n = texts[f].count(txt)
        if n == 0:
            stat['跳过·章内找不到'] += 1; continue
        if n > 1:
            stat['跳过·章内多处命中'] += 1; continue
        texts[f] = texts[f].replace(txt, img, 1)
        stat['已应用'] += 1
        applied.append((pg, f.name, txt, img))

    for k, v in stat.most_common():
        print(f'  {k}: {v}')

    if a.apply:
        for f, t in texts.items():
            f.write_text(t, encoding='utf-8')
        print(f'\n✓ 写回 {len(texts)} 个文件')
    else:
        print('\n（dry-run，未写回）')

    log = ROOT / f'logs/applied_{a.book}.tsv'
    log.write_text('\n'.join(f'{p}\t{fn}\t{t}\t{i}' for p, fn, t, i in applied),
                   encoding='utf-8')
    hl = ROOT / f'logs/held_{a.book}.tsv'
    hl.write_text('\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{r}' for p, fn, t, i, r in held),
                  encoding='utf-8')
    print(f'已应用明细 → {log}')
    print(f'退回人工   → {hl}')


if __name__ == '__main__':
    main()
