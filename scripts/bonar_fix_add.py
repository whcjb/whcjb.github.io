#!/usr/bin/env python3
"""往 notes_fixes.tsv 追加改正：从 stdin 读「号 ⟂ 原样 ⟂ 改作」每行一条（⟂ 作分隔，免得 heredoc 里打 tab）。"""
import sys
from pathlib import Path

F = Path(__file__).resolve().parent.parent / 'bonar_raw' / 'psalms' / 'notes_fixes.tsv'
with open(F, 'a') as f:
    k = 0
    for line in sys.stdin:
        line = line.rstrip('\n')
        if not line.strip():
            continue
        n, old, new = line.split(' ⟂ ')
        f.write(f'{n}\t{old}\t{new}\n')
        k += 1
print('added', k)
