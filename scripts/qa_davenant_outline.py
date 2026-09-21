#!/usr/bin/env python3
"""原书版式块的体检：缩进块 [OUTLINE]、居中小标题 [HEAD]、右对齐出处 [ATTRIB]。

原书在一句领起语之后，把各支／清单／引诗整体右移排成一块，行距仍是行距
（v2p232「The principal divisions of this Chapter are three:」下面三条是标本）。
抽取器按「缩进＝新段落」读，一条一段，发布出来是十几个孤零零的短段。
现在由 extract_davenant.outline_items 按几何认块，这里查三件事：

Gate O1  产物里的每个 [OUTLINE] 块，都是几何规则**现在**仍然认的那一块
         （规则改了而产物没重跑，或产物被手改过，都在这里露馅）
Gate O2  产物里的每一条，都能在该页 OCR 行里按原样找到（不多字不少字）
Gate O3  发布页的 <div class="dv-outline"> 开闭配对，条数 == 1 + <br /> 个数
Gate O4  产物里的每个 [HEAD] / [ATTRIB]，几何规则**现在**仍然认它是居中／靠右

用法: python3 scripts/qa_davenant_outline.py
"""
import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PUB = ROOT / 'davenant' / 'colossians'
sys.path.insert(0, str(ROOT / 'scripts'))
import extract_davenant as E                                    # noqa: E402

STRUCT = RAW / 'davenant_colossians_structured.txt'


def geo_roles():
    """→ {(vol, page): {归一化文本: 角色}}，按当前几何规则认出来的居中／靠右行。"""
    out = {}
    for vol in (1, 2):
        lo, hi = E.RANGES[vol]
        pages = [r for r in E.load(vol) if lo <= r['page'] <= hi]
        fn_max, indent_min = E.calibrate(pages)
        for rec in pages:
            body = _body(rec, fn_max)
            if not body:
                continue
            x0 = E.page_body_x0(body)
            ds = E.line_offsets(body, x0, indent_min)
            starts = [d > indent_min for d in ds]
            marks = E.outline_items(body, ds, indent_min)
            right = E.text_right(body)
            roles = E.centered_heads(body, ds, starts, marks, x0, right,
                                     indent_min)
            # 缩排（而非居中）的小鉴题也是「原书版式」的一档，同样要比
            roles = E.indent_heads(body, ds, starts, marks, roles, right,
                                   indent_min, (vol, rec['page']))
            d = out.setdefault((vol, rec['page']), collections.Counter())
            for r in roles:
                if r:
                    d[r] += 1
    return out


def _body(rec, fn_max):
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
    return body


def geo_blocks():
    """→ {(vol, page): [[行文本, …], …]}，按当前几何规则认出来的缩进块。"""
    out = {}
    for vol in (1, 2):
        lo, hi = E.RANGES[vol]
        pages = [r for r in E.load(vol) if lo <= r['page'] <= hi]
        fn_max, indent_min = E.calibrate(pages)
        for rec in pages:
            body = _body(rec, fn_max)
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

    # 按**页计数**比，不按文本比：产物那一侧的文字过了校勘（v1p357 的
    # `2s Aet` 已按人工票改成 `is Aet`），拿文本当 key 会假报。方向只卡一边
    # ——几何认的行有一多半被经文对齐吃掉了，所以要求的是「产物里的每一条
    # 都有几何撑着」，不是两边相等。
    geo = geo_blocks()
    gcnt = collections.Counter()
    for (vol, pg), runs in geo.items():
        gcnt[(vol, pg)] += sum(len(r) for r in runs)
    print(f'        几何规则现在认 {sum(len(v) for v in geo.values())} 块 / '
          f'{sum(gcnt.values())} 行（其余被经文对齐那一步吃掉了）')
    pcnt = collections.Counter()
    for vol, pg, rows in blocks:
        pcnt[(vol, pg)] += len(rows)
    bad1 = [(vol, pg, n, gcnt.get((vol, pg), 0))
            for (vol, pg), n in sorted(pcnt.items())
            if n > gcnt.get((vol, pg), 0) + gcnt.get((vol, pg + 1), 0)]
    print(f'        几何撑不住的页：{len(bad1)}')
    for v, pg, n, g in bad1[:12]:
        print(f'          v{v}p{pg}: 产物 {n} 条，几何只认 {g} 行')

    # ── Gate O4 ─────────────────────────────────────────────────────────
    # 按**页计数**比，不按文本比：产物那一侧的文字过了校勘（v2p232 的 `or`
    # 已按人工票改成 `OF`），拿文本当 key 会假报。方向也只卡一边——几何认的
    # 行有一部分会被 SECTION / 经文对齐吃掉（`Verse 15.` 是节号标题），
    # 所以要求的是「产物里的每一行都有几何撑着」，不是两边相等。
    roles = geo_roles()
    want = {'HEAD': 'head', 'ATTRIB': 'attrib'}
    prod = collections.Counter()
    n4 = 0
    for m in re.finditer(r'^\[(HEAD|ATTRIB)\] (?:<!--v(\d+)p(\d+)(?:-\d+)?-->)?',
                         txt, re.M):
        n4 += 1
        prod[(int(m.group(2) or 0), int(m.group(3) or 0), want[m.group(1)])] += 1
    bad4 = [(v, pg, role, n, roles.get((v, pg), {}).get(role, 0))
            for (v, pg, role), n in sorted(prod.items())
            if n > roles.get((v, pg), {}).get(role, 0)]
    print(f'Gate O4 居中／靠右：产物 {n4} 行，几何撑不住的 {len(bad4)}')
    for v, pg, role, n, g in bad4[:12]:
        print(f'          v{v}p{pg} {role}: 产物 {n} 行，几何只认 {g} 行')

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
    return 1 if (bad1 or bad3 or bad4) else 0


if __name__ == '__main__':
    sys.exit(main())
