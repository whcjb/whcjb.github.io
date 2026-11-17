#!/usr/bin/env python3
"""合成 1859 初版脚注表 notes_1859.tsv。

底稿 = notes_map.tsv 指定的 hOCR 行（bonar_notes_ocr.clean 规整）；
再套 notes_fixes.tsv（号\t原样\t改作，原样须在该条里恰好出现一次；
原样写成「开头⋯结尾」时替换整段，供整首引诗重排用）；
notes_typed.tsv 里已逐字对图录入的条目整条覆盖；
最后套 manual_fixes.tsv 里单元为 note-N 的编者改正（初版本身的错，首页逐条列出）。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bonar_notes_ocr import clean  # noqa: E402

B = Path(__file__).resolve().parent.parent / 'bonar_raw' / 'psalms'


def tsv(name):
    f = B / name
    if not f.exists():
        return []
    return [l.rstrip('\n').split('\t') for l in open(f) if l.strip() and not l.startswith('#')]


def main():
    pages = {pg['p']: pg['lines'] for pg in json.load(open(B / 'work' / 'hocr_lines.json'))}
    typed = {int(r[0]): r[1:] for r in tsv('notes_typed.tsv')}
    fixes = {}
    for r in tsv('notes_fixes.tsv'):
        fixes.setdefault(int(r[0]), []).append((r[1].replace('\\t', '\t'), r[2] if len(r) > 2 else ''))
    editor = {}
    for r in tsv('manual_fixes.tsv'):
        if r[0].startswith('note-'):
            editor.setdefault(int(r[0][5:]), []).append((r[1], r[2]))
    out, bad = [], []
    for n, spec in ((int(a), b) for a, b in tsv('notes_map.tsv')):
        if n in typed:
            out.append([n, typed[n][0], typed[n][1] if len(typed[n]) > 1 else '对图逐字录入'])
            continue
        if spec.startswith('DUP'):
            out.append([n, '', f'录入本多出的记号，脚注见第 {spec[3:]} 条'])
            continue
        lines, pp = [], []
        for part in spec.split(';'):
            p, ys = part.split(':')
            y0, y1 = map(int, ys.split('-'))
            lines += [l for l in pages[int(p)] if y0 <= l['y0'] <= y1 and len(l['t'].strip()) > 2]
            pp.append(p)
        t = clean(lines)
        t = re.sub(r'^\s*(\*|†|‡|§|[tfJX^•■]|\'\'?|")\s+', '', t, count=1) if not fixes.get(n, [('', '')])[0][0].startswith('^') else t
        for old, new in fixes.get(n, []):
            if '⋯' in old:  # 区段写法「开头⋯结尾」：替换从开头到其后第一个结尾的整段
                a, b = old.split('⋯')
                k = t.count(a)
                if k == 1 and b in t[t.index(a) + len(a):]:
                    i = t.index(a)
                    j = t.index(b, i + len(a)) + len(b)
                    t = t[:i] + new + t[j:]
                    continue
                bad.append(f'{n}: 区段「{old}」未唯一命中')
                continue
            k = t.count(old)
            if k != 1:
                bad.append(f'{n}: 「{old}」出现 {k} 次')
                continue
            t = t.replace(old, new)
        for old, new in editor.get(n, []):
            if t.count(old) != 1:
                bad.append(f'{n}: 编者改正「{old}」出现 {t.count(old)} 次')
                continue
            t = t.replace(old, new)
        out.append([n, t, 'OCR+改' + (' 跨 p' + '–'.join(dict.fromkeys(pp)) if len(set(pp)) > 1 else '')])
    if bad:
        print('\n'.join(bad))
        sys.exit(1)
    with open(B / 'notes_1859.tsv', 'w') as f:
        f.write('# 1859 初版脚注（scripts/bonar_notes_build.py 生成，勿手改）：号\t正文（*斜体*）\t来源\n')
        for r in out:
            f.write('\t'.join(map(str, r)) + '\n')
    print(len(out), 'typed', len(typed), 'fixed', sum(len(v) for v in fixes.values()))


if __name__ == '__main__':
    main()
