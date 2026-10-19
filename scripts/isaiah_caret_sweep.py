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


# 原书不印的残渣符号（§ 是格塞纽斯语法书的节号，真的，不在此列）
JUNK = '•«»£~|±°®¬¦¤¢¥©'
JUNK_RE = '[' + re.escape(JUNK) + ']'


def sweep_junk(body, name, log):
    """同 ^ 的办法清其余残渣符号（2026-10-19 续：「•'מלאכי」字回来了，前面还粘着 •'）"""
    def note(kind):
        def f(m):
            log.append((name, kind, body[max(0, m.start() - 30):m.end() + 30].replace('\n', ' ')))
            return ''
        return f
    body = body.replace('‹heb›', '[Heb.]')
    body = re.sub(r'(?<=[A-Za-z])~ ?(?=[a-z])', '', body)              # Swe~ den → Sweden（行末断词）
    # 粘在外文/标记上的（含夹在中间的单个撇号：•'מלאכי）
    body = re.sub(rf'{JUNK_RE}+[\'’]?(?=[*"“”‘(]*(?:[{FOREIGN}]|\[(?:Heb|Gk)\.\]))', note('粘外文前'), body)
    body = re.sub(rf'(?<=[{FOREIGN}\]]){JUNK_RE}+', note('粘外文后'), body)
    body = re.sub(rf'(?<![A-Za-z0-9]){JUNK_RE}+(?![A-Za-z0-9])', note('单独'), body)
    body = re.sub(rf'{JUNK_RE}+', note('乱码中'), body)
    # 外文词前落单的引号：乱码开头那个 `"`（`"psxba`）在乱码换成希伯来文后留了下来（「with "מלאכי was」）；
    # 词后 25 字符内没有对应收引号的才删，真引文不动
    def lone_quote(m):
        close = {'"': '"', '“': '”', "'": "'", '‘': '’'}[m.group(1)]
        word = re.match(r'\S+', body[m.end():]).group(0)
        if close in body[m.end():m.end() + len(word) + 25]:
            return m.group(0)
        log.append((name, '落单引号', body[max(0, m.start() - 30):m.end() + 30].replace('\n', ' ')))
        return ''
    body = re.sub(rf'(?<![A-Za-z])(["“\'‘])(?=[{FOREIGN}])', lone_quote, body)
    body = re.sub(r'\((?:[ \t]+)(?=\S)', '(', body)                 # 删符号后留下的「( 」
    return re.sub(r'[ \t]{2,}', ' ', body)


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
        new = sweep_junk(sweep(body, p.stem, log) if '^' in body else body, p.stem, log)
        if new == body:
            continue
        p.write_text(head + sep + new, encoding='utf-8')
        changed += 1
    left = sum(p.read_text(encoding='utf-8').split('\n---\n', 1)[-1].count('^') for p in PUB.glob('*.md'))
    junk_left = sum(len(re.findall(JUNK_RE, p.read_text(encoding='utf-8').split('\n---\n', 1)[-1])) for p in PUB.glob('*.md'))
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('chapter\tkind\tcontext\n')
        for r in log:
            f.write('\t'.join(r) + '\n')
    print(f'^ 与残渣符号清扫：改 {changed} 篇，记录 {len(log)} 处 → {LOG}；剩余 ^ = {left}，残渣符号 = {junk_left}')


if __name__ == '__main__':
    main()
