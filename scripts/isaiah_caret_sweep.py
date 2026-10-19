#!/usr/bin/env python3
"""以赛亚书发布页的 `^` 一个不留（用户 2026-10-19：「把全书所有的 ^ 都解决了」）。

原书不印 `^`，它全是 ABBYY 把希伯来/希腊活字读崩时吐的残渣。前面几步
（闭集选词、证人比对、[Heb.]/[Gk.] 标记、拉丁字母去 ^）已经按位置处理了大头，
这一步是链条**最后**的兜底，作用在发布页上——放在最后，是因为人工判读表里有的
规则前文正好含 `^`，早删了它们就对不上：

  1. 粘在希伯来/希腊字母上的 `^`（`^צלצל`、`מחים^`、`^βάρβαροι`）→ 删，字是对的
  2. 前后都不挨拉丁字母数字的单独 `^`（`^`、`*^*`、`(^`）→ 删；删完若剩空斜体 `**` 一并删
  3. 剩下夹在拉丁乱码里的 → 删 `^` 本身，逐条记日志（这些前面证人比对救不回、
     也判不出文字种类，至少不再露出 `^`）

幂等：跑完全书 0 个 `^`，再跑无变化。
    python3 scripts/isaiah_caret_sweep.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'alexander/isaiah'
LOG = ROOT / 'logs/alexander_isaiah_caret_sweep.tsv'
FOREIGN = r'֐-׿Ͱ-Ͽἀ-῿'


def sweep(body, name, log):
    def note(kind):
        def f(m):
            log.append((name, kind, body[max(0, m.start() - 30):m.end() + 30].replace('\n', ' ')))
            return ''
        return f
    body = re.sub(rf'\^+(?=[*"“”‘’\'(]*[{FOREIGN}])|(?<=[{FOREIGN}])([*"“”‘’\')]*)\^+',
                  lambda m: (m.group(1) or '') if m.group(0) else '', body)
    body = re.sub(r'(?<![A-Za-z0-9\\])\^+(?![A-Za-z0-9])', note('单独'), body)
    body = re.sub(r'\^+', note('乱码中'), body)
    body = re.sub(r'(?<![*\\])\*\*(?![*])', '', body)          # 删 ^ 后留下的空斜体 `**`
    body = re.sub(r'\\\*\s*\\\*', '', body)
    body = re.sub(r'[ \t]{2,}', ' ', body)
    return body


def main():
    log, changed = [], 0
    for p in sorted(PUB.glob('*.md')):
        t = p.read_text(encoding='utf-8')
        head, sep, body = t.partition('\n---\n') if t.startswith('---') else ('', '', t)
        if '^' not in body:
            continue
        new = sweep(body, p.stem, log)
        p.write_text(head + sep + new, encoding='utf-8')
        changed += 1
    left = sum(p.read_text(encoding='utf-8').count('^') for p in PUB.glob('*.md'))
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('chapter\tkind\tcontext\n')
        for r in log:
            f.write('\t'.join(r) + '\n')
    print(f'^ 清扫：改 {changed} 篇，记录 {len(log)} 处 → {LOG}；剩余 ^ = {left}')


if __name__ == '__main__':
    main()
