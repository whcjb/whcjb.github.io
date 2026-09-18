#!/usr/bin/env python3
"""缩进块（[OUTLINE] / <div class="dv-outline">）的体检。

原书在一句领起语之后，把各支／清单／引诗整体右移排成一块，行距仍是行距
（v2p232「The principal divisions of this Chapter are three:」下面三条是标本）。
抽取器按「缩进＝新段落」读，一条一段，发布出来是十几个孤零零的短段。
现在由 extract_davenant.outline_items 按几何认块，这里查三件事：

Gate O1  产物里的每个 [OUTLINE] 块，都是几何规则**现在**仍然认的那一块
         （规则改了而产物没重跑，或产物被手改过，都在这里露馅）
Gate O2  产物里的每一条，都能在该页 OCR 行里按原样找到（不多字不少字）
Gate O3  发布页的 <div class="dv-outline"> 开闭配对，条数 == 1 + <br /> 个数

用法: python3 scripts/qa_davenant_outline.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PUB = ROOT / 'davenant' / 'colossians'
sys.path.insert(0, str(ROOT / 'scripts'))
import extract_davenant as E                                    # noqa: E402

STRUCT = RAW / 'davenant_colossians_structured.txt'


def geo_blocks():
    """→ {(vol, page): [[行文本, …], …]}，按当前几何规则认出来的缩进块。"""
    out = {}
    for vol in (1, 2):
        lo, hi = E.RANGES[vol]
        pages = [r for r in E.load(vol) if lo <= r['page'] <= hi]
        fn_max, indent_min = E.calibrate(pages)
        for rec in pages:
            lines = sorted(rec['lines'], key=lambda r: r['y0'])
            for _ in range(3):
                if lines and any(r.search(lines[0]['text']) for r in E.HEAD_RES):
                    lines.pop(0)
                    continue
                if lines and (E.JUNK_RE.match(lines[0]['text'])
                              or E.SPECK_RE.match(lines[0]['text'])):
                    lines.pop(0)
                    continue
                break
            for _ in range(2):
                if lines and (E.is_foot(lines[-1]['text'])
                              or E.is_signature(lines[-1])):
                    lines.pop()
                    continue
                break
            for l in lines:
                t2, x2 = E.unspeck(l)
                if t2 != l['text']:
                    l['text'], l['x0'] = t2, x2
            body, _fn = E.split_page(lines, fn_max)
            if not body:
                continue
            ds = E.line_offsets(body, E.page_body_x0(body), indent_min)
            acc = E.outline_items(body, ds, indent_min)
            run = []
            for l, a in list(zip(body, acc)) + [(None, False)]:
                if a:
                    run.append(l['text'])
                elif run:
                    out.setdefault((vol, rec['page']), []).append(run)
                    run = []
    return out


def norm(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def main():
    txt = STRUCT.read_text(encoding='utf-8')
    if '[ITEM]' in txt:
        print('✗ 产物里还有 [ITEM]，merge_outline 没跑到')
        return 1
    blocks = []
    for m in re.finditer(r'^\[OUTLINE\] (?:<!--v(\d+)p(\d+)(?:-(\d+))?-->)?(.*)$',
                         txt, re.M):
        vol = int(m.group(1)) if m.group(1) else 0
        pg = int(m.group(2)) if m.group(2) else 0
        blocks.append((vol, pg, m.group(4).split('\\n')))
    print(f'Gate O1 规则与产物同步：产物 {len(blocks)} 块 / '
          f'{sum(len(b[2]) for b in blocks)} 条')

    geo = geo_blocks()
    pool = {}
    for (vol, pg), runs in geo.items():
        # 按页并起来：产物里一块可以横跨同页的两段右移行（v1p569 的四句诗，
        # 中间一句被读成续行，几何上就成了两段），判据只问「每一条都来自
        # 这一页的右移行」，不卡段界。
        pool.setdefault(vol, []).append((pg, norm(''.join(x for r in runs
                                                          for x in r))))
    n_geo = sum(len(v) for v in geo.values())
    print(f'        几何规则现在认 {n_geo} 块（其余被经文对齐那一步吃掉了）')

    # 已核过、判定为「留着」的不一致：v1p569 那首四行诗的第三句，OCR 把页边
    # 一个斑点连着读进行首（`2 Shall make eferna! servitude…`，x0 从 296 掉到
    # 34），于是这一句在几何上不算右移行、被并进了上一条。unspeck 只剥固定几个
    # 从不合法出现在行首的字符，数字不在其中（`2. ` 起首的段落全书几百处），
    # 为这一处放宽不值当。
    KNOWN = {(1, 569, 'Who sells his freedom in exchange for gold,')}

    bad1 = []
    for vol, pg, rows in blocks:
        # 抽取那边还会再校勘（拆词/换字/接断词），条数也可能被上游改过
        # （v1p553 有一条被经文块吃掉、v1p569 两句诗被并成一行），所以判据是
        # 「同卷、页码差 ≤1 的某个几何块里，本块每一条都能原样找到」。
        hit = any(abs(p - pg) <= 1 and all(norm(r)[:40] in got for r in rows)
                  for p, got in pool.get(vol, []))
        if not hit and (vol, pg, rows[0]) not in KNOWN:
            bad1.append((vol, pg, rows[0][:48]))
    print(f'        对不上几何规则的块：{len(bad1)}（另有 {len(KNOWN)} 处已核定留着）')
    for v, p, t in bad1[:12]:
        print(f'          v{v}p{p}  {t}')

    bad3 = []
    for f in sorted(PUB.rglob('*.md')):
        t = f.read_text(encoding='utf-8')
        if t.count('<div class="dv-outline"') == 0:
            continue
        for m in re.finditer(r'<div class="dv-outline" markdown="1">\n(.*?)\n</div>',
                             t, re.S):
            body = m.group(1)
            if '\n\n' in body:
                bad3.append((f.name, '块内有空行'))
            rows = body.count('<br />') + 1
            if rows != len([x for x in body.split('<br />')]):
                bad3.append((f.name, '条数对不上'))
    n_div = sum(f.read_text(encoding='utf-8').count('<div class="dv-outline"')
                for f in PUB.rglob('*.md'))
    print(f'Gate O3 发布页：{n_div} 个 dv-outline 块，结构有问题 {len(bad3)}')
    for n, why in bad3[:12]:
        print(f'          {n}  {why}')
    return 1 if (bad1 or bad3) else 0


if __name__ == '__main__':
    sys.exit(main())
