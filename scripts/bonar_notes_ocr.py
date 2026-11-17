#!/usr/bin/env python3
"""1859 初版脚注：从 hOCR 切出每页页底脚注块，按记号切段，作为录入底稿。

输出 work/notes_ocr_segs.json：[{i, p, mark, text, cont_pages}]，按书序。
记号行：行首为 * † ‡ § 或其 OCR 变体（t f • ^ ■ 等）。跨页续文：上一段未以
句末标点结束时，把下一页页底小字区开头无记号的连续行接上。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / 'bonar_raw' / 'psalms' / 'work'
MARK = re.compile(r"^\s*([*†‡§•■^]|[tfJ+]\s|'\"|''|\"\s*\*)")
END = re.compile(r'[.?!"”\')\]]\s*$')


def small_tail(lines):
    # 去掉旁注（页边窄条小字）与页码/折标
    L = [l for l in lines if len(l['t'].strip()) > 2 and l['x1'] - l['x0'] > 600]
    i = len(L)
    while i > 0 and L[i - 1]['fs'] <= 7:
        i -= 1
    return L[i:]


def clean(lines):
    s = ''
    for l in lines:
        t = re.sub(r'\s+', ' ', l['t']).strip()
        if s.endswith('-') and t[:1].islower():
            s = s[:-1] + t
        else:
            s = (s + ' ' + t).strip()
    s = re.sub(r'\s+([;:?!,.])', r'\1', s)
    s = re.sub(r'(^|[\s(—-])"\s+', r'\1"', s)
    s = re.sub(r'\s+—\s*|\s*—\s+', '—', s)
    return s


def main():
    pages = json.load(open(W / 'hocr_lines.json'))
    owner = {id(l): pg['p'] for pg in pages for l in pg['lines']}
    pg_of = lambda l: owner[id(l)]  # noqa: E731
    segs = []
    for pg in pages:
        T = small_tail(pg['lines'])
        if not T:
            continue
        k = next((j for j, l in enumerate(T) if MARK.match(l['t'])), None)
        prev = segs[-1] if segs else None
        open_prev = prev and not END.search(prev['text']) and pg['p'] - prev['last_p'] <= 2
        if k is None:
            if open_prev:
                prev['lines'] += T
                prev['text'] = clean(prev['lines'])
                prev['last_p'] = pg['p']
                prev['cont'].append(pg['p'])
            continue
        if open_prev and k > 0:
            j = k
            while j > 0 and T[j]['y0'] - T[j - 1]['y1'] < 40:
                j -= 1
            if T[j:k]:
                prev['lines'] += T[j:k]
                prev['text'] = clean(prev['lines'])
                prev['cont'].append(pg['p'])
        cur = None
        for l in T[k:]:
            m = MARK.match(l['t'])
            if m:
                cur = {'p': pg['p'], 'last_p': pg['p'], 'mark': m.group(1).strip(), 'lines': [], 'cont': []}
                segs.append(cur)
            cur['lines'].append(l)
        for s in segs:
            if s['p'] == pg['p']:
                s['text'] = clean(s['lines'])
    out = [{'i': i + 1, 'p': s['p'], 'mark': s['mark'], 'cont': s['cont'], 'text': s['text'],
            'at': [[pg_of(l), l['y0']] for l in s['lines']]} for i, s in enumerate(segs)]
    json.dump(out, open(W / 'notes_ocr_segs.json', 'w'), ensure_ascii=False, indent=0)
    print(len(out))


if __name__ == '__main__':
    main()
