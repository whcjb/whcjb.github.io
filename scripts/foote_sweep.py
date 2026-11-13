#!/usr/bin/env python3
"""福特《路加福音讲义》实读抽查后的全书成类清理（2026-11-13 用户令「把上表这几类全书清掉」）。

第 5、60、95 讲逐页对图实读，错多为标点空格一类；以下几类按页面形态全书扫，规则逐条列表过目后定：

  dash   破折号两侧的空格：`Christ— written` `short —that`。印本破折号一律不留空格（全书无空格的 710 处，
         带空格的 200 余处是 OCR 加的）。只动紧挨字母的；`—" These` 照全书开引号后留空格的写法不动
  open   开引号挤到逗号后：`he said," Yea` → `he said, " Yea`。按段内引号奇偶定：此处之前偶数个引号＝开引号；
         第 45 讲 `prayer," Rom.` 前面奇偶乱了、实为收引号，除外
  I      数字 1 当 I：`verily 1 say` → `I say`（后接小写词，书卷名缩写除外；第 46 讲实读后放宽，2026-11-13）
  bis    `bis` → his（第 46 讲实读带出，全书 8 处）
  born   `bom` → born（全书 4 处均是）
  stop   句末引号前多空格：`incense ."*` → `incense."*`
  fn     `."t This` → 注号读成 t
  so     `80 that` → so that（此版字体 s 形近 8）
  O      呼格 `0 Lord` `" 0 send` → O

    python3 scripts/foote_sweep.py --rules    # 链条：foote_hand_pending --apply --late3 之后 → sweep_fixes.tsv
    python3 scripts/foote_sweep.py --apply

第 48 讲实读（2026-11-13）带出的几类，放在 foote_vlm_recheck 之后另跑一轮（--late：现场生成即落，表 sweep2_fixes.tsv）：
  qstar  `*"*` 在开引号位：引号两侧多读出的星号（140 处左右）→ `"`；收引号位的不动（可能真是斜体收尾）
  qopen  `*" X` 星号与开引号倒序 → `" *X`
  qmark  `you*?"` 问号落在斜体外 → `you?"*`
  vnum   经文段节号中夹 `\*`：`4\*2.` → `42.`
  ord    序数被拆：`the 2 2d verse` → `22d`
  slash  `" / *beseech` 的 `/` 是 I
  god    `of god` → `of God`
  qclose 收引号位 `*"*` 前文无开斜体 → `"`（4）
  qnext  斜体收尾星号挪到引号后一词：`temptation." We*` → `temptation."* We`
  fnspur 多出的注号哨兵：本段跨及的各页注区都无注、整页转录这几页也都无 [FN:]（第 48 讲 p.106 一例带出）→ 删哨兵

    python3 scripts/foote_sweep.py --late --rules && python3 scripts/foote_sweep.py --late --apply
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
RULES2 = A.RAW / 'sweep2_fixes.tsv'
OPEN_SKIP = {('045', 'prayer," Rom.')}
PATS = [
    ('dash', re.compile(r'(?<=[A-Za-z"*,;:.!?)])— (?=[A-Za-z])'), '—'),
    ('dash', re.compile(r'(?<=[A-Za-z]) —(?=[A-Za-z])'), '—'),
    ('I', re.compile(r'(?<=[a-zA-Z,;:?!"*] )1(?= (?!(?:Cor|Kings|Sam|Chron|John|Pet|Thess|Tim|st)\b)[a-z]+\b(?!\*))'), 'I'),
    ('bis', re.compile(r'(?<=[a-z] )bis(?= [a-z])'), 'his'),        # 全书 8 处均英文语境（Latin bis 不在其列）
    ('st', re.compile(r'(?<=\b1) st(?= chapter)'), 'st'),
    ('born', re.compile(r'\bbom\b'), 'born'),
    ('stop', re.compile(r'(?<=[a-z]) \.(?=")'), '.'),
    ('fn', re.compile(r'(?<=[.,;]")t(?= [A-Z])'), A.FN_MARK),
    ('so', re.compile(r'\b80(?= [a-z])'), 'so'),                       # 此版 s 形近 8（全书 16 处均是）
    ('O', re.compile(r'(?:^|(?<=[ "(*—]))0(?= [A-Za-z])', re.M), 'O'),  # 呼格 O 读成 0（看图 v2 p.105）
]

PATS2 = [
    ('qstar', re.compile(r'(?<=[ —(\n])\*"\*(?!\*)'), '"'),
    ('qopen', re.compile(r'(?<=[ (—:;,\n])\*" ?(?=[A-Za-z])'), '" *'),
    ('qmark', re.compile(r'(?<=[a-z])\*([?!])"'), None),
    ('vnum', re.compile(r'(?<=[.?!;:] )(\d)\\\*(\d)(?=\. [A-Z])'), None),
    ('ord', re.compile(r'\b(\d) (\d(?:d|th|st|nd))(?= verse)'), None),
    ('slash', re.compile(r'(?<=" )/ \*(?=[a-z])'), '*I '),
    ('god', re.compile(r'\b(?<=of )god\b'), 'God'),
    ('qclose', re.compile(r'(?<=[a-z.,;:!?])\*"\*(?!\*)'), '"'),
    ('qnext', re.compile(r'(?<=[.,;:!?])"(\s+[A-Za-z]+)\*(?=\s)'), None),
]
QNEXT_SKIP = {'102'}           # `our "day," and*` 是斜体小标题本身的收尾


def fnspur(lec, body, notes):
    """注号哨兵所在段跨及的页：注区无该页注、转录各页都在且无 [FN:] → 多出的哨兵位置。"""
    import foote_vlm_adjudicate as V
    n = int(lec)
    vol = 1 if n <= 40 else (2 if n <= 90 else 3)
    if vol not in _INV:
        _INV[vol] = {pg: leaf for leaf, pg in sorted(V.leaf_pages(vol).items(), reverse=True) if pg}
    inv = _INV[vol]
    npages = set(re.findall(r'<!-- NOTE p\.(\S+?) -->', notes))
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'<!-- PAGE (\S*) -->', body)]
    out = []
    for m in re.finditer(A.FN_MARK, body):
        prev = [pg for k, pg in marks if k < m.start()]
        nxt = [pg for k, pg in marks if k > m.start()]
        if not prev or not prev[-1].isdigit():
            continue
        a = int(prev[-1])
        b = int(nxt[0]) if nxt and nxt[0].isdigit() and int(nxt[0]) >= a else a + 1
        pages = [str(x) for x in range(a, max(a, b) + 1)]
        if any(pg in npages for pg in pages):
            continue
        ok = True
        for pg in pages:
            leaf = inv.get(pg)
            f = V.VLM / f'v{vol}' / f'{leaf:04d}.txt' if leaf is not None else None
            if f is None or not f.exists() or '[FN:' in f.read_text(encoding='utf-8'):
                ok = False
                break
        if ok:
            out.append((m.start(), m.end(), '', 'fnspur'))
    return out


_INV = {}
SUB2 = {'qnext': lambda m: '"*' + m.group(1), 'qmark': lambda m: m.group(1) + '"*', 'vnum': lambda m: m.group(1) + m.group(2), 'ord': lambda m: m.group(1) + m.group(2)}


def edits2(lec, t):
    body, _, notes = t.partition('\n---\n')
    out = []
    for kind, rx, rep in PATS2:
        if kind == 'qnext' and lec in QNEXT_SKIP:
            continue
        for m in rx.finditer(body):
            out.append((m.start(), m.end(), SUB2[kind](m) if rep is None else rep, kind))
    out += fnspur(lec, body, notes)
    return sorted(out)


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


def rules(late=False):
    """同一段内的几处合成一条（整段换），避免相邻规则上下文互相重叠。"""
    rows, stat = [], Counter()
    for f in sorted(A.SRC.glob('*.md')):
        lec, t = f.stem, f.read_text(encoding='utf-8')
        ed = edits2(lec, t) if late else edits(lec, t)
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
    out = RULES2 if late else RULES
    out.write_text('# lecture\t原串\t改作 —— foote_sweep.py 生成（实读抽查后成类清理，整段换）；\\n 表换行\n'
                   + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in rows), encoding='utf-8')
    print(dict(stat), f'规则 {len(rows)} → {out}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--late', action='store_true')
    a = ap.parse_args()
    R = RULES2 if a.late else RULES
    if a.rules:
        rules(a.late)
    elif a.apply and R.exists():
        I.apply_multiline(R)


if __name__ == '__main__':
    main()
