#!/usr/bin/env python3
"""附卷与索引的检查闸。正文那几道（Gate W/S）不适用，另立六道。

正文有 92 个节组的经文可以拿 KJV 逐节比（Gate S），附卷与索引没有经文块，
之前只验了脚注与标签配对——那只证明产物自洽，不证明它忠于底本。这里补上：

    Gate A  零丢失     产物词多重集 == OCR 原文（该块页范围）扣掉页眉页脚，
                       与正文 Gate W 同一套判据
    Gate B  编号连续   OBJECTION / REPLY / ARGUMENT 的序号必须 1..N 不断不重，
                       断号＝那一条被吞或被并进了上一段
    Gate C  页序单调   同一块内的页码标记必须不降；倒序＝段落被排错位
    Gate D  字母分区   索引的 A–Z 分隔必须按序出现，且该段条目首字母相符
    Gate E  条目带页码 索引条目必须含页码数字；不含的多半是回行被误判成新条目
    Gate F  目录对章   `contents-dissertation` 列的章题必须在附卷里找得到

用法: python3 scripts/qa_davenant_appx.py
"""
import collections
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
sys.path.insert(0, str(ROOT / 'scripts'))
import extract_davenant as E                        # noqa: E402
import extract_davenant_appx as A                   # noqa: E402
import extract_davenant_index as X                  # noqa: E402

PAGE_RE = re.compile(r'<!--v?\d*p?(\d+)(?:-(\d+))?-->')
TAGGED = re.compile(r'^\[([A-Z_]+)\] (.*)$')


def words(t):
    return collections.Counter(re.findall(r'[A-Za-z]+', t))


def parse(path):
    for ln in path.read_text(encoding='utf-8').splitlines():
        m = TAGGED.match(ln)
        if m:
            yield m.group(1), m.group(2)


def strip_pg(t):
    m = PAGE_RE.match(t)
    return (t[m.end():], int(m.group(1)),
            int(m.group(2) or m.group(1))) if m else (t, None, None)


def ocr_words(vol, lo, hi):
    """按提取器同一套规则，从 OCR 原文重建该页范围「应有」的词多重集。"""
    c = collections.Counter()
    joined = ''
    t = (RAW / f'vol{vol}_ocr.txt').read_text(encoding='utf-8')
    for n, body in re.findall(r'<!-- PAGE (\d+) -->\n(.*?)(?=\n<!-- PAGE |\Z)',
                              t, re.S):
        if not (lo <= int(n) <= hi):
            continue
        lines = [l for l in body.split('\n') if l.strip()]
        for _ in range(3):                    # 剥页眉
            if lines and (any(r.search(lines[0]) for r in A.HEAD_RES)
                          or E.JUNK_RE.match(lines[0])
                          or E.SPECK_RE.match(lines[0])):
                lines.pop(0)
                continue
            break
        for _ in range(2):                    # 剥页脚签名
            if lines and E.is_foot(lines[-1]):
                lines.pop()
                continue
            break
        for l in lines:
            joined = E.dehyph(joined, l) if joined else l
    c.update(re.findall(r'[A-Za-z]+', joined))
    return c


def gate_a(name, got, vol, lo, hi):
    exp = ocr_words(vol, lo, hi)
    miss, extra = exp - got, got - exp
    print(f'  Gate A 零丢失 {name}：产物 {sum(got.values()):,} 词 / '
          f'应有 {sum(exp.values()):,} 词')
    print(f'    应有而缺 {sum(miss.values()):,} · 多出 {sum(extra.values()):,}')
    if miss:
        print(f'    缺得最多: {dict(miss.most_common(8))}')
    if extra:
        print(f'    多得最多: {dict(extra.most_common(8))}')


def gate_b(items):
    seq = collections.defaultdict(list)
    for tag, txt in items:
        body = strip_pg(txt)[0]
        m = re.match(r'(OBJECTION|REPLY|ARGUMENT|ANSWER)\s+(\d{1,3})\b', body)
        if m:
            seq[m.group(1)].append(int(m.group(2)))
    print('  Gate B 编号连续：')
    for k, v in sorted(seq.items()):
        runs, cur = [], [v[0]]
        for a, b in zip(v, v[1:]):
            (cur.append(b) if b == a + 1 else (runs.append(cur), cur.clear(),
                                               cur.append(b)))
        runs.append(cur)
        gaps = [f'{r[0]}–{r[-1]}' for r in runs if r]
        flag = '' if len(runs) == 1 else f'   <<< 断成 {len(runs)} 段：{gaps}'
        print(f'    {k:10} 共 {len(v):3} 条  1–{max(v)}{flag}')


def gate_c(items):
    bad = 0
    last, cur = 0, None
    for tag, txt in items:
        if tag == 'SEC':
            last, cur = 0, txt.split('|')[0]
            continue
        _, a, b = strip_pg(txt)
        if a is None:
            continue
        if a < last:
            bad += 1
            if bad <= 5:
                print(f'    页码倒退 {cur}: {last} → {a}')
        last = max(last, b or a)
    print(f'  Gate C 页序单调：倒退 {bad} 处')


def gate_d_e(items):
    letter, bad_first, no_page, n = None, [], 0, 0
    for tag, txt in items:
        body = strip_pg(txt)[0].strip()
        if tag == 'LETTER':
            letter = body.strip('. ')[:1].upper()
            continue
        if tag != 'E':
            continue
        n += 1
        if not re.search(r'\d', body):
            no_page += 1
        if letter and body[:1].isupper() and body[:1] != letter \
                and not body[:1].isdigit():
            bad_first.append((letter, body[:38]))
    print(f'  Gate D 字母分区：条目 {n}，首字母与分区不符 {len(bad_first)}')
    for l, b in bad_first[:6]:
        print(f'    [{l}] {b}')
    print(f'  Gate E 条目带页码：不含数字的条目 {no_page} / {n}')


def gate_f(items):
    titles = [strip_pg(t)[0] for g, t in items if g == 'E']
    appx = (RAW / 'davenant_colossians_appendix.txt').read_text(encoding='utf-8')
    heads = re.findall(r'^\[SEC\] [^|]*\|([^|]*)', appx, re.M)
    heads += re.findall(r'^\[BODY\] (?:<!--[^>]*-->)?(CHAP[^.]*\..{0,60})',
                        appx, re.M)
    miss = []
    for t in titles:
        key = re.sub(r'[^a-z ]', ' ', t.lower())
        key = ' '.join(key.split()[:6])
        if not key:
            continue
        if not any(difflib.SequenceMatcher(None, key, h.lower()).ratio() > 0.5
                   for h in heads):
            miss.append(t[:60])
    print(f'  Gate F 目录对章：{len(titles)} 条，附卷里找不到对应章题 {len(miss)}')
    for m in miss[:8]:
        print(f'    {m}')


def main():
    appx = list(parse(RAW / 'davenant_colossians_appendix.txt'))
    idx = list(parse(RAW / 'davenant_colossians_index.txt'))

    print('《论基督之死》+ 法国之争')
    got = words(' '.join(strip_pg(t)[0] for g, t in appx if g != 'SEC'))
    for pc in A.PIECES:
        pass
    gate_a('附卷全体', got, A.VOL, min(p['lo'] for p in A.PIECES),
           max(p['hi'] for p in A.PIECES))
    gate_b(appx)
    gate_c(appx)

    print('\n六种索引 + ERRATA')
    gotx = words(' '.join(strip_pg(t)[0] for g, t in idx if g == 'E'))
    gate_a('索引全体', gotx, 2, min(p['lo'] for p in X.PIECES),
           max(p['hi'] for p in X.PIECES))
    gate_c(idx)
    gate_d_e(idx)
    cont = []
    keep = False
    for g, t in idx:
        if g == 'SEC':
            keep = t.split('|')[0] == 'contents-dissertation'
            continue
        if keep:
            cont.append((g, t))
    gate_f(cont)
    return 0


if __name__ == '__main__':
    sys.exit(main())
