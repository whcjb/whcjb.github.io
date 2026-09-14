#!/usr/bin/env python3
"""逐词回退判据（old-book-ocr skill §3.1）。

> 旧串每个词都是真词、新串出现非词 = 越改越坏 → 报出来

改错的字是**静默**的：它成了一个合法英文词，判词典不认它有问题，读者也看
不出来。留在账上的残字反而是可见的。所以每一轮改动都要拿上一个**已知良好
的提交**逐词比一遍——不是比 HEAD，HEAD 可能已经被别的会话改过。

用法:
    python3 scripts/qa_davenant_regress.py [基准提交]
"""
import collections
import difflib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import davenant_witness as W                        # noqa: E402

FILES = ([f'davenant/colossians/{i}.md' for i in (1, 2, 3, 4)]
         + sorted(str(p.relative_to(ROOT)) for p in
                  (ROOT / 'davenant/colossians/dissertation').glob('*.md'))
         + ['davenant/colossians/gallican.md']
         + sorted(str(p.relative_to(ROOT)) for p in
                  (ROOT / 'davenant/colossians/indexes').glob('*.md')))


def strip(t):
    t = re.sub(r'^---\n.*?\n---\n', '', t, flags=re.S)
    return re.sub(r'<[^>]+>|\[\^\w+\]', ' ', t)


def real(w):
    """这个词是不是「真词」。

    ⚠️ 用 `_wordish` 太宽：它认屈折形表，而 `louded`（loaded 被读花）恰好
    是 `loud`+`ed`，于是这条回退被判成「新词也是真词」放了过去（实测）。
    改用 `attested`——它多问一句「词干在本书里站不站得住」。
    """
    n = W._norm(w)
    return len(n) < 2 or W.attested(w) or bool(re.fullmatch(r'[ivxlcdm]+', n))


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else 'HEAD'
    bad = 0
    for f in FILES:
        old = subprocess.run(['git', 'show', f'{base}:{f}'],
                             capture_output=True, text=True).stdout
        if not old:
            continue
        new = (ROOT / f).read_text(encoding='utf-8')
        a, b = strip(old).split(), strip(new).split()
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, a, b, autojunk=False).get_opcodes():
            if tag != 'replace':
                continue
            was, now = a[i1:i2], b[j1:j2]
            if len(was) > 3 or len(now) > 3:
                continue                  # 大段重排不在这条判据的射程
            if all(real(x) for x in was) and not all(real(x) for x in now):
                bad += 1
                print(f'  {Path(f).name:18} {" ".join(was)!r} → {" ".join(now)!r}')
    print(f'逐词回退：{bad} 处（基准 {base}）')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
