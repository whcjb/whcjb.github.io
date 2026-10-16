"""雷登《彼得前书实用注释》共用：读抽取产物并落缺字判读表。

发布（英文）与翻译都从这里取正文，判读结果因此只有一个落盘口
（old-book-ocr §3.1 硬约束 1：产物层的修正必须能一条命令全量恢复）。

manual_fixes.tsv（制表符分隔，# 起头为注释）：

    slug  ord  tcp_word  fixed  evidence

- ord：该篇里第几处缺字记号（0 起，次序 = gap_sites.json 里同篇的次序）
- tcp_word：缺字所在的整个词（记号连同贴着它的残字，如 `Ab••ham`），
  用来**核对位置**——对不上就报错、不落（§4.3 规则自检）
- fixed：判读结果，替换整个 tcp_word；判不出的不进表，记号留在页面上。
  以 `+` 收尾 = 与后一个词拼合（TCP 在行末断词处录了一个认不清的标点
  `iudg▪ ment`，影像上是断词，不是标点）；以 `+` 起头 = 与前一个词拼合
  （`bru •ish,` → `brutish,`）
- evidence：判读依据（leaf 号、他版、语料），给人看的
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'leighton_raw' / '1peter'
SRC = RAW / 'en_chapters'
FIXES = RAW / 'manual_fixes.tsv'

TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
# 缺字记号贴着的残字：不含空白、不含 HTML/markdown 标记
RE_LEFT = re.compile(r'[^\s<>*]*$')
RE_RIGHT = re.compile(r'^[^\s<>*]*')


def load_fixes():
    fixes = {}
    if not FIXES.exists():
        return fixes
    for n, ln in enumerate(FIXES.read_text(encoding='utf-8').splitlines(), 1):
        if not ln.strip() or ln.startswith('#'):
            continue
        f = ln.split('\t')
        if len(f) < 4:
            raise ValueError(f'manual_fixes.tsv:{n} 列数不足：{ln!r}')
        fixes[(f[0], int(f[1]))] = (f[2], f[3], n)
    return fixes


def gap_word(md, m):
    """缺字记号 m 所在的整个词的 (起, 止)。"""
    a = m.start() - len(RE_LEFT.search(md[:m.start()]).group(0))
    b = m.end() + len(RE_RIGHT.match(md[m.end():]).group(0))
    return a, b


def apply_fixes(slug, md, fixes=None, report=None):
    fixes = load_fixes() if fixes is None else fixes
    ms = list(TOK.finditer(md))
    # 同一个词里可能有两处记号（`Ab•ah•m`）：按词去重，表里登记的是词里头一处的 ord
    edits = []
    seen = set()
    for i, m in enumerate(ms):
        key = (slug, i)
        if key not in fixes:
            continue
        tcp, fixed, line = fixes[key]
        a, b = gap_word(md, m)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if md[a:b] != tcp:
            msg = (f'manual_fixes.tsv:{line} {slug}#{i} 位置对不上：'
                   f'表里 {tcp!r}，产物里 {md[a:b]!r}')
            if report is not None:
                report.append(msg)
                continue
            raise ValueError(msg)
        if fixed.startswith('+'):
            fixed = fixed[1:]
            while a > 0 and md[a - 1] == ' ':
                a -= 1
        if fixed.endswith('+'):
            fixed = fixed[:-1]
            while b < len(md) and md[b] == ' ':
                b += 1
        edits.append((a, b, fixed))
    for a, b, fixed in sorted(edits, reverse=True):
        md = md[:a] + fixed + md[b:]
    return md, len(edits)


ERRATA = RAW / 'manual_errata.tsv'


def load_errata():
    """TCP 录入错（非缺字）修正表：slug \t 原串（含足够上下文，须在该篇唯一）\t 改后 \t 依据。"""
    rows = []
    if not ERRATA.exists():
        return rows
    for n, ln in enumerate(ERRATA.read_text(encoding='utf-8').splitlines(), 1):
        if not ln.strip() or ln.startswith('#'):
            continue
        f = ln.split('\t')
        rows.append((f[0], f[1], f[2], n))
    return rows


def apply_errata(slug, md, rows, report=None):
    n = 0
    for sl, old, new, line in rows:
        if sl != slug:
            continue
        c = md.count(old)
        if c != 1:
            if md.count(new) == 1 and c == 0:
                continue          # 已是改后形态（幂等）
            msg = f'manual_errata.tsv:{line} {slug} 原串出现 {c} 次（须唯一）：{old!r}'
            if report is not None:
                report.append(msg)
                continue
            raise ValueError(msg)
        md = md.replace(old, new)
        n += 1
    return md, n


def load(slug, fixes=None):
    md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    md = apply_fixes(slug, md, fixes)[0]
    return apply_errata(slug, md, load_errata())[0]


if __name__ == '__main__':
    # 自检：表里每一条都要落得下
    fx = load_fixes()
    errs = []
    total = 0
    for slug in sorted({k[0] for k in fx}):
        md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        _, n = apply_fixes(slug, md, fx, errs)
        total += n
    er = load_errata()
    m = 0
    for slug in sorted({r[0] for r in er}):
        md = apply_fixes(slug, (SRC / f'{slug}.md').read_text(encoding='utf-8'), fx)[0]
        m += apply_errata(slug, md, er, errs)[1]
    for e in errs:
        print(e, file=sys.stderr)
    print(f'manual_fixes.tsv：{len(fx)} 条，落下 {total}；manual_errata.tsv：{len(er)} 条，落下 {m}；'
          f'对不上 {len(errs)}', file=sys.stderr)
    sys.exit(1 if errs else 0)
