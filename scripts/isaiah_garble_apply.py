#!/usr/bin/env python3
"""把看图读定的乱码落盘：按拼图编号找回那一处的前后词，按位置替换（不按串全局替换）。

读定表（TSV，看一张拼图记一张）：
    编号 \t 读法            —— 把可疑串的核心部分换成读法，前后标点保留
    编号 \t =原串 \t 新串    —— 不能只换一个词时（乱码跨两个词、要并词），给出整段原串与新串

替换走 applyfix 同一套：章内必须唯一，记入 foreign_image.tsv（外文）。
用法：python3 scripts/isaiah_garble_apply.py $S/verify/sheets/index.tsv readings.tsv "标签"
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = re.compile(r"^([(\[*'\"‘“—–-]*)(.*?)([)\].,;:*'\"’”?!—–-]*)$")


def main(index_path, readings_path, tag):
    idx = {}
    for line in open(index_path, encoding='utf-8'):
        f = line.rstrip('\n').split('\t')
        idx[f[0]] = dict(verdict=f[1], ch=f[2], page=f[3], tok=f[4], ctx=f[6] if len(f) > 6 else '')
    book = {p: p.read_text(encoding='utf-8') for p in (ROOT / 'alexander/isaiah').glob('[0-9]*.md')}
    by_ch, bad = {}, 0
    for line in open(readings_path, encoding='utf-8'):
        if not line.strip() or line.startswith('#'):
            continue
        f = line.rstrip('\n').split('\t')
        no = f[0]
        e = idx[no]
        p = ROOT / f"alexander/isaiah/{e['ch']}.md"
        if f[1].startswith('='):
            old, new = f[1][1:], f[2]
        else:
            toks = e['ctx'].split(' ')
            ks = [k for k, t in enumerate(toks) if t == e['tok']]
            if not ks:
                print('上下文里找不到', no, e['tok']); bad += 1; continue
            k = min(ks, key=lambda k: abs(k - 7))
            prev = toks[k - 1] if k else ''
            nxt = toks[k + 1] if k + 1 < len(toks) else ''
            pre, core, post = CORE.match(e['tok']).groups()
            if re.search(r'[\u0590-\u05FF\u0370-\u03FF\u1F00-\u1FFF]', f[1]):
                # 乱码两侧的 " ? : 是 OCR 吃进来的残渣，换成外文时一并去掉（2026-11-17 首批 22 处 יד? / "חסד）
                pre, post = pre.replace('"', ''), re.sub(r'[?:"]', '', post)
            rep = pre + f[1] + post
            old = ' '.join(x for x in (prev, e['tok'], nxt) if x)
            new = ' '.join(x for x in (prev, rep, nxt) if x)
        n = book[p].count(old)
        if n != 1:
            print('章内计数', n, no, repr(old)); bad += 1; continue
        by_ch.setdefault(e['ch'], []).append((old, new))
        book[p] = book[p].replace(old, new)
    if bad:
        sys.exit('有问题，未落盘')
    rows = []
    for ch, fx in by_ch.items():
        p = ROOT / f'alexander/isaiah/{ch}.md'
        p.write_text(book[p], encoding='utf-8')
        rows += [f'{ch}\t\t{o}\t{n}\timg\t\t' for o, n in fx]
    with open(ROOT / 'alexander_raw/isaiah/foreign_image.tsv', 'a', encoding='utf-8') as fh:
        fh.write(f'# —— {tag} ——\n' + '\n'.join(rows) + '\n')
    print('落盘', len(rows), '处，涉及', len(by_ch), '章')


if __name__ == '__main__':
    main(*sys.argv[1:4])
