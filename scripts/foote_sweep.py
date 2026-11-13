#!/usr/bin/env python3
"""福特《路加福音讲义》实读抽查后的全书成类清理（2026-11-13 用户令「把上表这几类全书清掉」）。

第 5、60、95 讲逐页对图实读，错多为标点空格一类；以下几类按页面形态全书扫，规则逐条列表过目后定：

  dash   破折号两侧的空格：`Christ— written` `short —that`。印本破折号一律不留空格（全书无空格的 710 处，
         带空格的 200 余处是 OCR 加的）。只动紧挨字母的；`—" These` 照全书开引号后留空格的写法不动
  open   开引号挤到逗号后：`he said," Yea` → `he said, " Yea`。按段内引号奇偶定：此处之前偶数个引号＝开引号；
         第 45 讲 `prayer," Rom.` 前面奇偶乱了、实为收引号，除外
  I      数字 1 当 I：`verily 1 say` → `I say`（后接 say/am/have/will/was/do/know）
  born   `bom` → born（全书 4 处均是）
  stop   句末引号前多空格：`incense ."*` → `incense."*`
  fn     `."t This` → 注号读成 t

    python3 scripts/foote_sweep.py --rules    # 链条：foote_hand_pending --apply --late3 之后 → sweep_fixes.tsv
    python3 scripts/foote_sweep.py --apply
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402

RULES = A.RAW / 'sweep_fixes.tsv'
OPEN_SKIP = {('045', 'prayer," Rom.')}
PATS = [
    ('dash', re.compile(r'(?<=[A-Za-z"*,;:.!?)])— (?=[A-Za-z])'), '—'),
    ('dash', re.compile(r'(?<=[A-Za-z]) —(?=[A-Za-z])'), '—'),
    ('I', re.compile(r'(?<=[a-z,;:?!"*] )1(?= (?:say|am|have|will|was|do|know)\b)'), 'I'),
    ('born', re.compile(r'\bbom\b'), 'born'),
    ('stop', re.compile(r'(?<=[a-z]) \.(?=")'), '.'),
    ('fn', re.compile(r'(?<=[.,;]")t(?= [A-Z])'), A.FN_MARK),
]


def edits(lec, t):
    """[(起, 止, 新)]，起止为全文位置。"""
    out = []
    for kind, rx, rep in PATS:
        out += [(m.start(), m.end(), rep, kind) for m in rx.finditer(t)]
    pos = 0
    for para in t.split('\n\n'):
        for m in re.finditer(r'(?<=[a-z]),"( ?)(?=\*?[A-Z])', para):
            k = m.start() + 1
            if para[:k].count('"') % 2 == 0 and (lec, para[k - 7:k + 6]) not in OPEN_SKIP:
                out.append((pos + m.start(), pos + m.end(), ', "' + ' ', 'open'))
        pos += len(para) + 2
    return sorted(out)


def rules():
    """同一段内的几处合成一条（整段换），避免相邻规则上下文互相重叠。"""
    rows, stat = [], Counter()
    for f in sorted(A.SRC.glob('*.md')):
        lec, t = f.stem, f.read_text(encoding='utf-8')
        ed = edits(lec, t)
        pos = 0
        for para in t.split('\n\n'):
            mine = [x for x in ed if pos <= x[0] and x[1] <= pos + len(para)]
            if mine:
                new, last = [], pos
                for s, e, rep, kind in mine:
                    new.append(t[last:s] + rep)
                    last = e
                    stat[kind] += 1
                new = ''.join(new) + t[last:pos + len(para)]
                if t.count(para) != 1:
                    raise SystemExit(f'{lec}: 段不唯一 {para[:60]!r}')
                rows.append((lec, para, new))
            pos += len(para) + 2
    RULES.write_text('# lecture\t原串\t改作 —— foote_sweep.py 生成（实读抽查后成类清理，整段换）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in rows), encoding='utf-8')
    print(dict(stat), f'规则 {len(rows)} → {RULES}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.rules:
        rules()
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
