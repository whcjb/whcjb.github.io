#!/usr/bin/env python3
"""在 1859 初版 hOCR 里找一段 Monergism 文字的位置：locate(before_text, after_text, start_line) → (行序号, 行)。

hOCR 全书各行的规范化词拼成一串，记下每个字符属于哪一行；用记号前 5/4/3 个词找，取 start_line 之后的第一处，
返回这几个词最后一个词所在的行。找不到再用记号后 4 个词找，返回其第一个词所在的行。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bonar_witness as W  # noqa: E402

_S = None


def _build():
    global _S
    if _S is None:
        lines, parts, owner = [], [], []
        for pg in W.pages():
            for i, l in enumerate(pg['lines']):
                k = len(lines)
                lines.append(dict(page=pg['p'], i=i, **l))
                t = ' '.join(W.norm_words(l['t']))
                if not t:
                    continue
                parts.append(t)
                owner.extend([k] * (len(t) + 1))
        _S = (' '.join(parts), owner, lines)
    return _S


def locate(before, after='', start=0):
    s, owner, lines = _build()
    bw, aw = W.norm_words(before), W.norm_words(after)
    for n in (5, 4, 3):
        if len(bw) < n:
            continue
        key = ' '.join(bw[-n:])
        hits = [m.end() - 1 for m in re.finditer(r'(?<![a-z])' + re.escape(key) + r'(?![a-z])', s)]
        hits = [h for h in hits if owner[h] >= start] or hits
        if hits:
            k = owner[hits[0]]
            return k, lines[k]
    if len(aw) >= 3:
        key = ' '.join(aw[:4])
        hits = [m.start() for m in re.finditer(r'(?<![a-z])' + re.escape(key) + r'(?![a-z])', s)]
        hits = [h for h in hits if owner[h] >= start] or hits
        if hits:
            k = owner[hits[0]]
            return k, lines[k]
    return None, None
