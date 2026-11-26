#!/usr/bin/env python3
"""卡里尔缺部 OCR：人工对图改正表落盘（old-book-ocr §4.5 抽章实读的产物）。

    /usr/bin/python3 scripts/caryl_ocr_manual.py            # 试跑：每条命中情况
    /usr/bin/python3 scripts/caryl_ocr_manual.py --apply    # 落到各部 fixed/（排在 caryl_ocr_ctx.py 之后、caryl_ocr_sweep.py 之前）

表：caryl_raw/job_ocr/manual_fixes.tsv，列 = 部目录（p4/p6/p82/p9）、段（31-7）、原串、改成、依据（看图所见，如「p.212 影像」）。
改成写作 `@正文` 时：原串是一整条旁注的文字，拆掉旁注标签放回正文（切栏失败的页）。
原串、改成里的 `\\n` 代表换行（用来并回被页缝劈开的段落）。`#` 起头且无制表符的是注释行（「#### 小节标题」这类原串不会被吞，old-book-ocr §4.5）。
匹配在去掉标签的纯文本上做（与抽读时打印的文字一致），原串在该段须唯一；改正区若跨页码锚点、旁注、经文框等标签就拒绝
（缩短原串再落）；只与存疑标记 cy-ocr 重叠的，连标记一并去掉（人工看图确认过了）。
幂等：原串已找不到、改成的已在 → 视为已落盘。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
TABLE = BASE / 'manual_fixes.tsv'
RE_TAG = re.compile(r'<[^>]+>')
RE_OCR_OPEN = re.compile(r'<span class="cy-ocr"[^>]*>')


def plain_map(md):
    """→ (纯文本, 纯文本每个字符在 md 里的位置)。"""
    out, idx, k = [], [], 0
    for m in RE_TAG.finditer(md):
        for i in range(k, m.start()):
            out.append(md[i])
            idx.append(i)
        k = m.end()
    for i in range(k, len(md)):
        out.append(md[i])
        idx.append(i)
    return ''.join(out), idx


def apply_one(md, old, new):
    """→ (新 md, 状态)。状态：ok / done / missing / multi / blocked"""
    if new == '@正文':                          # 切栏失败、被划进旁注的正文行末词：拆掉旁注标签放回正文（第 12 轮，p4 印本 p.550）
        pre = ''
        if '⟦' in old:                          # 「that which ⟦is」：旁注文字太短、段内不唯一时，⟦ 前写紧挨着的正文作定位（第 16 轮，p82「is」）
            pre, old = old.split('⟦', 1)
        tag = f'<span class="cy-margin">{old}</span>'
        hits = [m.start() for m in re.finditer(re.escape(tag), md)
                if not pre or RE_TAG.sub('', md[max(0, m.start() - 400):m.start()]).rstrip().endswith(pre.rstrip())]
        if len(hits) == 1:
            return md[:hits[0]] + old + md[hits[0] + len(tag):], 'ok'
        return md, ('multi' if len(hits) > 1 else 'done' if (pre + old) in plain_map(md)[0] or old in plain_map(md)[0] else 'missing')
    pt, idx = plain_map(md)
    n = pt.count(old)
    if new and new in pt and (n == 0 or old in new):
        return md, 'done'                   # 改成的串已在（上游已修好，或此前已落盘）：原串是改成串的一部分时不这样判就会叠字（A A good man）；
                                            # 反过来改成串是原串的前缀（删页底签名「base and H h h」→「base and 」）时原串还在，要照改
    if n == 0:
        return md, ('done' if new and new in pt else 'missing')
    if n > 1:
        return md, 'multi'
    p = pt.index(old)
    s, e = idx[p], idx[p + len(old) - 1] + 1
    # 把与改正区重叠的 cy-ocr 标记整个包进来（连标记去掉）
    for m in RE_OCR_OPEN.finditer(md):
        close = md.find('</span>', m.end())
        if m.start() < e and close + 7 > s:
            s, e = min(s, m.start()), max(e, close + 7)
    seg = md[s:e]
    rest = RE_OCR_OPEN.sub('', seg).replace('</span>', '') if RE_OCR_OPEN.search(seg) else seg
    if RE_TAG.search(rest):
        return md, 'blocked'
    seg_plain = RE_TAG.sub('', seg)
    if old not in seg_plain:
        return md, 'blocked'
    return md[:s] + seg_plain.replace(old, new, 1) + md[e:], 'ok'


def load_table():
    rows = []
    if not TABLE.exists():
        return rows
    for ln in TABLE.read_text(encoding='utf-8').splitlines():
        if not ln.strip() or (ln.startswith('#') and '\t' not in ln):
            continue
        f = ln.split('\t')
        if len(f) < 4:
            raise SystemExit(f'改正表行不足 4 列：{ln!r}')
        f[2], f[3] = f[2].replace('\\n', '\n'), f[3].replace('\\n', '\n')   # 「\n」写法：跨段的改正（页底签名、接字把一句话劈成两段）
        rows.append(f[:5] + [''] * (5 - len(f[:5])))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    rows = load_table()
    cache, stat = {}, {}
    bad = []
    for part, slug, old, new, note in rows:
        f = BASE / part / 'fixed' / f'{slug}.md'
        if f not in cache:
            cache[f] = f.read_text(encoding='utf-8')
        cache[f], st = apply_one(cache[f], old, new)
        stat[st] = stat.get(st, 0) + 1
        if st in ('missing', 'multi', 'blocked'):
            bad.append((st, part, slug, old, new))
    print(f'改正表 {len(rows)} 条：' + '，'.join(f'{k} {v}' for k, v in sorted(stat.items())), file=sys.stderr)
    for b in bad:
        print('  ⚠', *b, sep=' | ', file=sys.stderr)
    if a.apply:
        for f, md in cache.items():
            f.write_text(md, encoding='utf-8')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
