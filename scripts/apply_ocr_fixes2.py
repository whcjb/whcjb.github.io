#!/usr/bin/env python3
"""第二轮：用 raw 页上下文定位，收尾 apply_ocr_fixes.py 跳过的条目。

第一轮的瓶颈是**错误串太短**（中位 3–4 字），一章内多处重复就无法确定改哪个，
罗马书因此跳过 149 条。

本轮做法
--------
错误串在 **raw 页**里是唯一可定位的（页很短）。所以：
  1. 在 raw 页文本里找到错误串，向两侧各取 N 字，得到一个长上下文窗口
  2. 把该窗口在**所属章的 CJK 流**里查——窗口够长时通常唯一
  3. 命中后把 CJK 流下标映射回原文件字节偏移，在那个位置改

关键是第 3 步：正文里混着 HTML、markdown、标点、空白，不能拿 CJK 下标
直接当文件下标。构建 cjk→原文件位置 的索引数组即可。

窗口从宽到窄逐级尝试（24→18→12→8），先严后松，一旦唯一命中就停。

安全闸沿用第一轮：影像含「?」跳过、长度变化 >6 退回、
较长串要求相似度 ≥0.5（两侧皆 ≤2 字的单字形近替换直接放行）。

用法：
    python3 scripts/apply_ocr_fixes2.py --book romans --dry-run
    python3 scripts/apply_ocr_fixes2.py --book romans --apply
"""
import argparse
import difflib
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


def cjk_index(text):
    """→ (cjk流, [每个cjk字在原串中的下标])"""
    chars, idx = [], []
    for i, c in enumerate(text):
        if CJK.match(c):
            chars.append(c)
            idx.append(i)
    return ''.join(chars), idx


def parse_report(path):
    t = Path(path).read_text(encoding='utf-8')
    blocks = re.split(r'^## page (\d+)\s*$', t, flags=re.M)[1:]
    out = []
    for i in range(0, len(blocks), 2):
        pg = int(blocks[i])
        for m in FIND_RE.finditer(blocks[i + 1]):
            out.append((pg, m.group(1), m.group(2)))
    return out


def map_pages(cfg, pubtexts):
    """raw 页 → 章文件。多探针：单一探针失败就换位置再试，提高映射率。"""
    pubcjk = {f: cjk_index(re.sub(r'<[^>]+>', '', t))[0] for f, t in pubtexts.items()}
    m = {}
    for rf in sorted((ROOT / cfg['raw']).glob('page_*.md')):
        n = int(re.search(r'page_(\d+)', rf.name).group(1))
        if cfg['max_page'] and n > cfg['max_page']:
            continue
        t = ''.join(CJK.findall(re.sub(r'<[^>]+>', '', rf.read_text(encoding='utf-8'))))
        if len(t) < 40:
            continue
        for off in (30, 80, 150, 250, 10):        # 多探针
            probe = t[off:off + 24]
            if len(probe) < 20:
                continue
            hit = [f for f, body in pubcjk.items() if probe in body]
            if len(hit) == 1:
                m[n] = hit[0]
                break
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

    pubtexts = {f: f.read_text(encoding='utf-8')
                for f in sorted((ROOT / cfg['pub']).glob('*.md'))}
    recs = parse_report(ROOT / cfg['report'])
    pagemap = map_pages(cfg, pubtexts)
    print(f'判读条目 {len(recs)}；页→章映射 {len(pagemap)} 页（多探针）\n')

    if a.apply:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = ROOT / f'logs/bak2_{a.book}_{stamp}'
        bak.mkdir(parents=True, exist_ok=True)
        for f in pubtexts:
            shutil.copy(f, bak / f.name)
        print(f'已备份 → {bak}\n')

    rawcache = {}
    stat = Counter()
    applied, held = [], []

    for pg, img, txt in recs:
        if '?' in img or not img.strip() or not txt.strip():
            stat['跳过·存疑/无锚点'] += 1; continue
        f = pagemap.get(pg)
        if not f:
            stat['跳过·该页无章映射'] += 1; continue

        short = len(txt) <= 2 and len(img) <= 2
        ratio = difflib.SequenceMatcher(None, txt, img).ratio()
        if abs(len(img) - len(txt)) > 6 or (not short and ratio < 0.5):
            stat['退回人工·疑似改写'] += 1
            held.append((pg, f.name, txt, img, round(ratio, 2))); continue

        body = pubtexts[f]
        n_direct = body.count(txt)
        if n_direct == 1:                      # 第一轮已处理过的那类
            pubtexts[f] = body.replace(txt, img, 1)
            stat['已应用·唯一命中'] += 1
            applied.append((pg, f.name, txt, img, 'direct')); continue
        if n_direct == 0:
            stat['跳过·章内找不到'] += 1; continue

        # 多处命中 → 用 raw 页上下文收窄
        if pg not in rawcache:
            rp = ROOT / cfg['raw'] / f'page_{pg:04d}.md'
            rawcache[pg] = ''.join(CJK.findall(
                re.sub(r'<[^>]+>', '', rp.read_text(encoding='utf-8')))) if rp.exists() else ''
        raw = rawcache[pg]
        tcj = ''.join(CJK.findall(txt))
        rpos = raw.find(tcj)
        if rpos < 0 or not tcj:
            stat['跳过·raw中定位不到'] += 1; continue

        stream, idxmap = cjk_index(body)
        placed = False
        for w in (24, 18, 12, 8):              # 窗口由宽到窄
            lo = max(0, rpos - w)
            win = raw[lo:rpos + len(tcj) + w]
            if len(win) < len(tcj) + 4:
                continue
            hits = [m.start() for m in re.finditer(re.escape(win), stream)]
            if len(hits) != 1:
                continue
            # 命中窗口 → 定位其中错误串的 cjk 下标 → 映射回文件偏移
            off_in_win = win.find(tcj)
            s_cjk = hits[0] + off_in_win
            s_file = idxmap[s_cjk]
            e_file = idxmap[s_cjk + len(tcj) - 1] + 1
            seg = body[s_file:e_file]
            if ''.join(CJK.findall(seg)) != tcj:
                continue
            pubtexts[f] = body[:s_file] + img + body[e_file:]
            stat['已应用·上下文定位'] += 1
            applied.append((pg, f.name, txt, img, f'ctx{w}'))
            placed = True
            break
        if not placed:
            stat['跳过·上下文仍不唯一'] += 1

    for k, v in stat.most_common():
        print(f'  {k}: {v}')

    if a.apply:
        for f, t in pubtexts.items():
            f.write_text(t, encoding='utf-8')
        print(f'\n✓ 写回 {len(pubtexts)} 个文件')
    else:
        print('\n（dry-run，未写回）')

    (ROOT / f'logs/applied2_{a.book}.tsv').write_text(
        '\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{how}' for p, fn, t, i, how in applied),
        encoding='utf-8')
    (ROOT / f'logs/held2_{a.book}.tsv').write_text(
        '\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{r}' for p, fn, t, i, r in held),
        encoding='utf-8')
    print(f'明细 → logs/applied2_{a.book}.tsv / held2_{a.book}.tsv')


if __name__ == '__main__':
    main()
