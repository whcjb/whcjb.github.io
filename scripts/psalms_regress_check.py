#!/usr/bin/env python3
"""逐词回退判据：这一轮改动有没有把本来对的改坏。

判据（skill old-book-ocr §4.1）：
    旧串每个词都是真词、新串冒出非词  →  越改越坏，退回去

为什么要自动化：改错是**静默**的。留在账上的残字可见可再查；改错的字成了
另一个合法英文词，判词典不认它有问题，读者也看不出来。这条能自动抓出绝大
多数「改坏了」。

**比对要对着上一个已知良好的提交**，不是 HEAD——HEAD 可能已经被别的会话改过。

用法：
    python3 scripts/psalms_regress_check.py            # 对着 HEAD
    python3 scripts/psalms_regress_check.py b10deb7b7  # 对着指定提交
"""
import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = 'alexander/psalms'
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
TAG = re.compile(r'<[^<>]+>')


def at_rev(rev, path):
    r = subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=ROOT,
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def body(t):
    return t.split('---', 2)[2] if t.startswith('---') else t


def main(rev='HEAD'):
    lex = L.build()
    files = sorted((ROOT / SRC).glob('*.md'))
    total = suspect = 0
    for f in files:
        old = at_rev(rev, f'{SRC}/{f.name}')
        if old is None:
            continue
        a, b = body(old), body(f.read_text(encoding='utf-8'))
        if a == b:
            continue
        A, B = re.split(r'(\s+)', a), re.split(r'(\s+)', b)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, A, B, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            o, n = ''.join(A[i1:i2]), ''.join(B[j1:j2])
            ow = WORD.findall(TAG.sub(' ', o))
            nw = WORD.findall(TAG.sub(' ', n))
            total += 1
            if not ow or not nw:
                continue
            if all(L.is_word(w, lex) for w in ow) and \
               not all(L.is_word(w, lex) for w in nw):
                suspect += 1
                bad = [w for w in nw if not L.is_word(w, lex)]
                print(f'  !! [{f.stem}] {o[:46]!r} → {n[:46]!r}   新出现的非词 {bad[:3]}')
    print(f'对着 {rev} 比：改动 {total} 块；'
          + ('疑似改坏 %d 块' % suspect if suspect else '没有「真词改成非词」的 ✓'))
    return 1 if suspect else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'HEAD'))
