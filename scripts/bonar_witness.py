#!/usr/bin/env python3
"""博纳尔诗篇：1859 年 Nisbet 初版（IA christhischurchi00bona，普林斯顿神学院藏本）的 ABBYY hOCR → 证人索引。

用途：
  - para_start(text)：Monergism 跨页接缝后的文字，在初版里是否是缩进的段首；
  - footnotes()：初版每页底的脚注（小字号、以 * † ‡ § 起头的行）。
hOCR 解析结果缓存在 work/hocr_lines.json。
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'bonar_raw' / 'psalms'
HOCR = RAW / 'src' / 'ia1859' / 'hocr.html'
CACHE = RAW / 'work' / 'hocr_lines.json'


def pages():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding='utf-8'))
    src = HOCR.read_text(encoding='utf-8')
    out = []
    for pg in re.split(r'<div class="ocr_page"', src)[1:]:
        pno = int(re.search(r'ppageno (\d+)', pg).group(1))
        lines = []
        for m in re.finditer(r'<span class="ocr_line"[^>]*title="bbox (\d+) (\d+) (\d+) (\d+); x_size ([\d.]+); '
                             r'x_fsize (\d+)[^"]*"[^>]*>(.*?)</span>\s*(?=<span class="ocr_line"|</p>)', pg, re.S):
            x0, y0, x1, y1, xs, fs, inner = m.groups()
            words = re.findall(r'<span class="ocrx_word"[^>]*>(.*?)</span>', inner, re.S)
            t = html.unescape(' '.join(re.sub('<[^>]+>', '', w) for w in words))
            lines.append(dict(x0=int(x0), y0=int(y0), x1=int(x1), y1=int(y1), xs=float(xs), fs=int(fs), t=t))
        out.append(dict(p=pno, lines=lines))
    CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out


def norm_words(s):
    return re.findall(r'[a-z]+', s.lower())


_IDX = None


def _index():
    """正文行（fs ≥ 7）：(页, 行号, 是否缩进, 规范化词)。缩进 = x0 比该页正文行 x0 的众数大 25px 以上。"""
    global _IDX
    if _IDX is None:
        _IDX = []
        for pg in pages():
            body = [l for l in pg['lines'] if l['fs'] >= 7]
            if len(body) < 5:
                continue
            xs = sorted(l['x0'] for l in body)
            margin = xs[len(xs) // 4]
            for i, l in enumerate(body):
                _IDX.append((pg['p'], i, l['x0'] - margin > 25, norm_words(l['t'])))
    return _IDX


def para_start(text, k=5):
    """→ True（初版此处是缩进行首）/ False（行首但不缩进，或不在行首）/ None（找不到）。"""
    w = norm_words(text)[:k]
    if len(w) < 3:
        return None
    hits = [ind for _, _, ind, lw in _index() if lw[:len(w)] == w]
    if not hits:
        w3 = w[:3]
        hits = [ind for _, _, ind, lw in _index() if lw[:3] == w3]
    if not hits:
        return None
    return any(hits)
