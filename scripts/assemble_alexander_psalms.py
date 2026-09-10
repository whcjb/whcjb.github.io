#!/usr/bin/env python3
"""ABBYY XML → 每篇诗篇一份 raw markdown（含斜体、页码标记、节号）。

段落合并规则完全依赖 ABBYY 的 par 属性，不自己按几何猜：
    有 startIndent → 首行缩进 → 新段落
    无 startIndent → 上一段的续行（典型场景：段落跨页，被切成两个 par）
唯一的补充信号是节号——Alexander 每节解说都以 "N." 开头另起一段，OCR 偶尔
会漏掉 startIndent，用节号兜底。
"""
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_abbyy import IT_ON, IT_OFF, is_running_head

SRC = Path(__file__).resolve().parent.parent / 'alexander_raw/psalms/src'
VOLS = [('01', 1, 50), ('02', 51, 100), ('03', 101, 150)]

# 节号段：'1.' / '7 (5.)' —— 后者是 Alexander 标注希伯来文与英文节号不同时的写法
VERSE_START = re.compile(r'^\s*(\d{1,3})\s*(?:\(\d{1,3}\.?\)|\.)')


def strip_sentinels(t):
    return t.replace(IT_ON, '').replace(IT_OFF, '')


def collect(pages, heads, lo, hi):
    """→ {psalm_no: [ (page_index, par), ... ]}"""
    # 每篇的起点 (page, par_index)，终点是下一篇的起点
    marks = [(n, heads[n][0], heads[n][1]) for n in range(lo, hi + 1)]
    out = {}
    for k, (n, pg0, pi0) in enumerate(marks):
        pg1, pi1 = (marks[k + 1][1], marks[k + 1][2]) if k + 1 < len(marks) \
            else (pages[-1]['index'] + 1, 0)
        chunk = []
        for pg in pages:
            if pg['index'] < pg0 or pg['index'] > pg1:
                continue
            for i, par in enumerate(pg['pars']):
                if pg['index'] == pg0 and i <= pi0:
                    continue
                if pg['index'] == pg1 and i >= pi1:
                    continue
                if is_running_head(par, pg['pars']):
                    continue
                chunk.append((pg['index'], par))
        out[n] = chunk
    return out


def merge_paragraphs(chunk):
    """[(page, par)] → [(page_of_first_line, text)]，跨页续段已合并"""
    paras = []
    for page, par in chunk:
        t = par['text'].strip()
        if not t:
            continue
        new = ('startIndent' in par['attrs']) or bool(VERSE_START.match(strip_sentinels(t)))
        if new or not paras:
            paras.append([page, t])
        else:
            prev = paras[-1][1]
            # 跨页续段：前半截若以连字符结尾，同样按断词处理
            if prev.rstrip(IT_OFF).endswith('-') and strip_sentinels(t)[:1].islower():
                tail = prev.rstrip(IT_OFF)
                paras[-1][1] = tail[:-1] + (IT_OFF if prev.endswith(IT_OFF) else '') + t
            else:
                paras[-1][1] = prev + ' ' + t
    return [(p, t) for p, t in paras]


def main():
    outdir = SRC.parent / 'chapters_raw'
    outdir.mkdir(parents=True, exist_ok=True)
    total = 0
    for v, lo, hi in VOLS:
        pages = pickle.load(open(SRC / f'pages{v}.pkl', 'rb'))
        heads = pickle.load(open(SRC / f'heads{v}.pkl', 'rb'))
        chunks = collect(pages, heads, lo, hi)
        for n in range(lo, hi + 1):
            paras = merge_paragraphs(chunks[n])
            lines = [f'<!-- psalm {n} | vol {int(v)} | scan pages '
                     f'{paras[0][0]}-{paras[-1][0]} -->', '']
            cur = None
            for page, t in paras:
                if page != cur:
                    lines.append(f'<!-- PAGE {page} -->')
                    cur = page
                lines.append(t)
                lines.append('')
            (outdir / f'{n}.txt').write_text('\n'.join(lines), encoding='utf-8')
            total += len(paras)
        print(f'vol{v}: psalms {lo}-{hi} written')
    print('total paragraphs:', total)


if __name__ == '__main__':
    main()
