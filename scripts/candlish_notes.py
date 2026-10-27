#!/usr/bin/env python3
"""坎德利什约翰一书：Monergism 本丢了全部脚注正文（只剩 `*`/`†`），从 ccbiblestudy e-Sword 本取回。

    python3 scripts/candlish_notes.py          # → candlish_raw/1john/work/notes_auto.json（供人工复核）

e-Sword 本把脚注排成正文里的括注 `(…)`，或在经文题记后另起一段 `1] …`；第 XV 讲那条是讲末的
「NOTE REFERRED TO AT PAGE 186」。定位：取 `*` 前的 6 个词，在 e-Sword 本里按词序（忽略标点）找，
其后 400 字符内取第一个括注或 `1]` 段。

取回的文字只做机械清理（e-Sword 的经卷名误展开、HYPERLINK 域、数字粘连），清理后的定稿写在
candlish_raw/1john/notes.json，由人逐条看过；发布只读定稿，不读本脚本的输出。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import align_candlish as A  # noqa: E402

RAW = A.RAW


def balanced(s, i):
    """s[i] == '('：返回配平的右括号位置。"""
    d = 0
    for k in range(i, len(s)):
        if s[k] == '(':
            d += 1
        elif s[k] == ')':
            d -= 1
            if d == 0:
                return k
    return -1


def main():
    units = json.loads((RAW / 'units.json').read_text())
    full = '\n'.join(A.cc_text())
    out = []
    n = 0
    for u in units:
        for p in u.get('epi', []) + u.get('paras', []):
            for m in re.finditer(r'[*†]', p):
                n += 1
                before = re.findall(r"[A-Za-z0-9]+", p[:m.start()])[-6:]
                pat = r'[^A-Za-z0-9]+'.join(re.escape(w) for w in before)
                hits = [h for h in re.finditer(pat, full)]
                rec = dict(n=n, unit=u.get('num') or u['title'], sym=m.group(0),
                           anchor=p[max(0, m.start() - 70):m.start() + 1].replace('\n', ' '), hits=len(hits))
                if len(hits) >= 1:
                    j = hits[0].end()
                    seg = full[j:j + 400]
                    pi = seg.find('(')
                    bi = seg.find('1]')
                    if bi >= 0 and (pi < 0 or bi < pi):
                        k = full.find('\n1]', j)
                        e = full.find('\n', k + 1)
                        rec['cc'] = full[k + 1:e].strip()
                        rec['form'] = '1]'
                    elif pi >= 0:
                        k = j + pi
                        e = balanced(full, k)
                        rec['cc'] = full[k + 1:e].strip()
                        rec['form'] = '()'
                out.append(rec)
    (RAW / 'work' / 'notes_auto.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for r in out:
        print(f"#{r['n']} {r['unit']} hits={r['hits']} {r.get('form')}  …{r['anchor'][-50:]}\n    {r.get('cc', '')[:150]!r}")


if __name__ == '__main__':
    main()
