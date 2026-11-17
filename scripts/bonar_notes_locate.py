#!/usr/bin/env python3
"""博纳尔诗篇：Monergism 本的脚注号（* † ‡，及标题「PSALM 6*」）→ 1859 初版页码，供看图录入脚注正文。

    python3 scripts/bonar_notes_locate.py      # → work/note_sites.json

定位：取记号前 6 个词，在初版各页正文行（规范化后拼成一串）里找；多页命中取离上一个记号最近的后续页。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bonar_witness as W  # noqa: E402

RAW = W.RAW
JOIN = '\n⁣'


def page_strings():
    out = []
    for pg in W.pages():
        body = ' '.join(l['t'] for l in pg['lines'])
        # 行尾连字符接回
        body = re.sub(r'(\w)-\s+(\w)', r'\1\2', body)
        out.append((pg['p'], ' '.join(W.norm_words(body))))
    return out


def main():
    units = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    ps = page_strings()
    sites, last = [], 0
    for u in units:
        uid = f"psalm-{u['num']}" if u['type'] == 'psalm' else u['title'].lower().replace(' ', '-')
        texts = []
        if u.get('mark'):
            texts.append(('head', f"PSALM {u['num']}{u['mark']}"))
        for i, p in enumerate(u['paras']):
            texts.append((i, p.replace(JOIN, '\n')))
        for where, t in texts:
            flat = re.sub(r'\s+', ' ', t)
            for m in re.finditer(r'[*†‡]', flat):
                before = flat[:m.start()]
                k = len(sites) + 1
                if where == 'head':
                    key = None
                    # 标题的脚注：落在该篇第一页
                    first = ' '.join(W.norm_words(u['paras'][0]))[:40]
                    cand = [p for p, s in ps if p >= last and ' '.join(first.split()[2:7]) in s]
                else:
                    words = W.norm_words(re.sub(r'⟪\d+⟫', ' ', before))
                    cand = []
                    for n in (6, 5, 4):
                        key = ' '.join(words[-n:])
                        cand = [p for p, s in ps if key and key in s]
                        if cand:
                            break
                after = [p for p in cand if p >= last] or cand
                page = min(after, key=lambda p: p - last if p >= last else 999) if after else None
                if page is not None:
                    last = page
                sites.append(dict(n=k, unit=uid, para=where, mark=m.group(0),
                                  before=flat[max(0, m.start() - 80):m.start()],
                                  after=flat[m.end():m.end() + 40], page=page, ncand=len(cand)))
    (RAW / 'work' / 'note_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=1) + '\n',
                                                 encoding='utf-8')
    miss = [s for s in sites if s['page'] is None]
    multi = [s for s in sites if s['ncand'] > 1]
    print(f'记号 {len(sites)}；未定位 {len(miss)}；多页命中 {len(multi)}', file=sys.stderr)
    for s in miss:
        print('  未定位', s['n'], s['unit'], s['before'][-50:], file=sys.stderr)


if __name__ == '__main__':
    main()
