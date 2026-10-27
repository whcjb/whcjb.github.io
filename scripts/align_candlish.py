#!/usr/bin/env python3
"""坎德利什约翰一书：Monergism（底本）↔ ccbiblestudy e-Sword 本（同一份 Anderson 录入本的另一导出）逐讲词对齐。

    python3 scripts/align_candlish.py            # 分类统计 + 写 work/diffs.tsv

两份是同一份录入本，正常应逐词一致。不一致只来自导出时各自的损坏：
  Monergism：行尾截字（`ordin|manner` ← ordinary）；脚注正文整条丢失，只剩 `*`。
  e-Sword：Son→「Song of Solomon」、is→「Isaiah ,」、Re-→「Revelation -」等经卷名误展开；
           经文引用包了 HYPERLINK 域；数字粘连（`of1John`）；脚注以括注嵌在正文里。
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'candlish_raw' / '1john'
WORK = RAW / 'work'

RE_TOK = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?")


def cc_text():
    """两卷 e-Sword 本 → 段落列表（一行一段），去掉 HYPERLINK 域与 e-Sword 自加的章节标签。"""
    import subprocess
    paras = []
    for v in (1, 2):
        t = WORK / f'cc{v}.txt'
        if not t.exists():
            subprocess.run(['textutil', '-convert', 'txt', '-output', str(t),
                            str(RAW / 'src' / 'ccbiblestudy' / f'vol{v}.doc')], check=True)
        s = t.read_text(encoding='utf-8')
        s = re.sub(r'\s*HYPERLINK "[^"]*"(?: \\t "[^"]*")?\s*', ' ', s)
        for line in s.split('\n'):
            line = line.strip()
            if not line or re.fullmatch(r'\d\d Chapter \d+|Verses? [\d\-, ]+|Verse \d+', line):
                continue
            paras.append(line)
    return paras


# e-Sword 经卷名误展开：只用于对齐时把它折回，不进产物
ESWORD = [(r'\bSong of Solomon ?,?', 'Son'), (r'\bIsaiah ,', 'is'), (r'\bRevelation -', 'Re-'),
          (r'\bAmos ,', 'Am'), (r'\bActs ,', 'Acts')]


def toks(s):
    return [(m.group(0), m.start(), m.end()) for m in RE_TOK.finditer(s)]


def norm(w):
    return w.lower().replace('’', "'")


def main():
    units = json.loads((RAW / 'units.json').read_text())
    cc = cc_text()
    cc_full = '\n'.join(cc)
    cc_fold = cc_full
    for a, b in ESWORD:
        cc_fold = re.sub(a, b, cc_fold)
    ct = toks(cc_fold)
    cw = [norm(w) for w, _, _ in ct]

    # 底本：逐段逐行记 token，标出是否落在行尾（段末那行不算）
    mt = []  # (word, unit_idx, para_idx, line_end?)
    for ui, u in enumerate(units):
        for pi, p in enumerate(u.get('epi', []) + u.get('paras', [])):
            lines = p.split('\n')
            for li, line in enumerate(lines):
                tt = toks(line)
                for k, (w, s, e) in enumerate(tt):
                    end = (k == len(tt) - 1) and li < len(lines) - 1 and e >= len(line.rstrip(' *"\'”’)'))
                    mt.append((w, ui, pi, end))
    mw = [norm(w) for w, *_ in mt]
    print('tokens  monergism', len(mw), ' cc', len(cw), file=sys.stderr)

    sm = difflib.SequenceMatcher(None, mw, cw, autojunk=False)
    rows = []
    stats = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        a = ' '.join(w for w, *_ in mt[i1:i2])
        b = ' '.join(w for w, _, _ in ct[j1:j2])
        endflag = any(x[3] for x in mt[i1:i2]) or (i1 > 0 and mt[i1 - 1][3])
        cat = 'other'
        if op == 'replace' and i2 - i1 == 1 and mt[i1][3] and j2 - j1 >= 1 and \
                (cw[j1].startswith(mw[i1]) and cw[j1] != mw[i1]):
            cat = 'trunc'
        elif op == 'insert' and i1 > 0 and mt[i1 - 1][3]:
            cat = 'trunc_word'
        elif op == 'replace' and mt[i1][3] and cw[j1].startswith(mw[i1]):
            cat = 'trunc'
        stats[cat] = stats.get(cat, 0) + 1
        ctx_b = cc_fold[ct[max(j1 - 6, 0)][1]:ct[min(j2 + 5, len(ct) - 1)][2]]
        rows.append((cat, op, str(units[mt[min(i1, len(mt) - 1)][1]].get('num', units[mt[min(i1, len(mt) - 1)][1]]['title'][:20])),
                     a, b, ctx_b.replace('\n', ' ⏎ '), 'E' if endflag else ''))
    with open(WORK / 'diffs.tsv', 'w', encoding='utf-8') as f:
        for r in rows:
            f.write('\t'.join(r) + '\n')
    print(stats)


if __name__ == '__main__':
    main()
