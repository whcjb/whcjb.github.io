#!/usr/bin/env python3
"""福特《路加福音讲义》游离符号逐个取证（skill old-book-ocr §3.2b）。

白名单列允许出现的字符，其余（`^` `«` `»` `♦` `•` `£` `%` `€` `$` `■` `{` `}` `¥` `▼` `©` `~` `®` …）
一律报出，**逐个**拿前后各四个词去 tesseract 重扫（foote_tesseract.py，第二条非生成式字流）
里按位置定位，看证人在两锚之间印的是什么：

  我们的缝（两锚之间）去掉怪符号 == 证人的缝          → 删（证人那里没有这个墨点）
  我们的缝里怪符号换成证人那一个正常标点 == 证人的缝  → 换（`not^ however` → `not, however`）
  其余（定位不到、证人也是怪符号、对不上）              → 留着，等看图

形态一样意思不同的不按形态清：`^` 有时是逗号、有时是开引号、有时是撇号，全看证人。
希腊引文里的字符不碰（两侧有希腊字母的跳过；第 ④ 层的事）。

判决落成 foote_raw/luke/symbol_fixes.tsv（讲次、左锚、原缝、新缝），`--apply` 按表落：
左锚＋原缝必须在本讲恰好出现一次。publish 之前、adjudicate 之后跑。

    python3 scripts/foote_symbols.py            # 取证 → 规则表 + logs/foote_symbols.tsv
    python3 scripts/foote_symbols.py --apply
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_foote as F  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
SRC = RAW / 'en_chapters'
TESS = RAW / 'tess'
RULES = RAW / 'symbol_fixes.tsv'
LOG = ROOT / 'logs' / 'foote_symbols.tsv'

ALLOW = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:!?'\"()-—–’‘“”*\\\n<>/=_[]&"
            "\ue010æœÆŒéèêëàâîïôûüçÉ#")
GOOD_PUNCT = set(",;:.!?'\"“”‘’()—-")
WORD = re.compile(r"[A-Za-z]+")
GREEK = re.compile(r'[\u0370-\u03ff\u1f00-\u1fff]')
K = 4


def norm_quotes(s):
    """tesseract 的引号方向不可靠（开双引号读成 ‘‘ / “‘ / ‘“）；本书正文用直引号，统一归成直引号。"""
    s = re.sub(r"[‘’“”'\"]{2,}", '"', s)
    return s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")


def norm_words(s):
    return [w.lower() for w in WORD.findall(s)]


def tess_text(vol):
    pages = sorted((TESS / f'v{vol}').glob('*.txt'))
    t = '\n'.join(p.read_text(encoding='utf-8') for p in pages)
    t = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', t)
    return re.sub(r'\s+', ' ', t)


def word_spans(s):
    return [(m.start(), m.end(), m.group(0).lower()) for m in WORD.finditer(s)]


def index(spans):
    idx = {}
    for i in range(len(spans) - K + 1):
        idx.setdefault(tuple(w for _, _, w in spans[i:i + K]), []).append(i)
    return idx


def judge():
    texts = {v: tess_text(v) for v in (1, 2, 3)}
    spans = {v: word_spans(texts[v]) for v in texts}
    idxs = {v: index(spans[v]) for v in spans}
    rules, log, stat = [], [], Counter()
    for n in range(1, 138):
        vol = next(v for v in (1, 2, 3) if F.FIRST_LECT[v] <= n <= F.LAST_LECT[v])
        path = SRC / f'{n:03d}.md'
        text = path.read_text(encoding='utf-8')
        ours = word_spans(text)
        tw, ts, ti = texts[vol], spans[vol], idxs[vol]
        seen_gaps = set()
        # 转义星号 `\*`（OCR 自带的星号，多为开引号读错，skill §4.4）也逐个取证
        for m in re.finditer(r'\\\*|[^\s]', text):
            ch = m.group(0)
            if ch != '\\*' and (ch in ALLOW or GREEK.match(ch)):
                continue
            pos = m.start()
            if text.rfind('<!--', 0, pos) > text.rfind('-->', 0, pos):
                continue
            # 本处所在的两词之缝
            left = [k for k, (a, b, w) in enumerate(ours) if b <= pos]
            if len(left) < K:
                stat['edge'] += 1
                continue
            li = left[-1]
            ri = li + 1
            if ri + K > len(ours):
                stat['edge'] += 1
                continue
            gap_a, gap_b = ours[li][1], ours[ri][0]
            if (n, gap_a) in seen_gaps:
                continue
            seen_gaps.add((n, gap_a))
            gap = text[gap_a:gap_b]
            if GREEK.search(text[max(0, gap_a - 30):gap_b + 30]) or '\n' in gap:
                stat['skip'] += 1
                continue
            lkey = tuple(w for _, _, w in ours[li - K + 1:li + 1])
            rkey = tuple(w for _, _, w in ours[ri:ri + K])
            hits = []
            for i in ti.get(lkey, []):
                j = i + K
                if tuple(w for _, _, w in ts[j:j + K]) == rkey:
                    hits.append(j)
            if len(hits) != 1:
                stat['nolocate'] += 1
                log.append((f'{n:03d}', gap, '', 'nolocate'))
                continue
            j = hits[0]
            wgap = norm_quotes(tw[ts[j - 1][1]:ts[j][0]])
            core = re.sub(r'\s', '', gap)
            wcore = re.sub(r'\s', '', wgap)
            stripped = ''.join(c for c in core.replace('\\*', '') if c in ALLOW and c not in '\\')
            new = None
            if stripped == wcore.replace('\\', ''):
                new = 'delete'
            elif len(wcore) and all(c in GOOD_PUNCT for c in wcore):
                # 把我们缝里的怪符号（及紧挨的星号残形）换成证人的标点，其余字符须与证人一致
                ours_clean = ''.join(c for c in core if c in GOOD_PUNCT)
                if ours_clean == '' or wcore.startswith(ours_clean) or wcore.endswith(ours_clean):
                    new = 'replace'
            if not new:
                stat['mismatch'] += 1
                log.append((f'{n:03d}', gap, wgap, 'mismatch'))
                continue
            # 新缝：保留我们这侧的空白形态，标点取证人
            if new == 'delete':
                ng = re.sub(r'[^\sA-Za-z0-9.,;:!?\'"()\-—–’‘“”*\ue010]', '', gap.replace('\\*', ''))
                ng = re.sub(r'\\(?=\s|$)', '', ng)
            else:
                # 空白形态取证人的（逗号后有空格、开引号后无空格），首尾空白照我们原缝
                core_w = re.sub(r'\s+', ' ', wgap.strip())
                lead = gap[:len(gap) - len(gap.lstrip())]
                trail = gap[len(gap.rstrip()):]
                ng = lead + core_w + trail
            ng = re.sub(r' {2,}', ' ', ng)
            if not ng.strip() and not ng:
                ng = ' '
            if ng == gap:
                continue
            # 硬闸：斜体标记（未转义 `*`）一个不许少——证人没有格式，`^*` 里的 `*` 往往是斜体收尾，
            # 删了整段强调配对就乱（实测页面露出近 900 个字面星号，skill §4.4「修复表自己会制造错误」）
            if len(re.findall(r'(?<!\\)\*', gap)) != len(re.findall(r'(?<!\\)\*', ng)):
                stars = [m2.start() for m2 in re.finditer(r'(?<!\\)\*', gap)]
                if len(stars) == 1 and not re.findall(r'(?<!\\)\*', ng):
                    i = stars[0]
                    body = ng.strip()
                    if i > 0 and gap[i - 1].isspace():
                        # 前有空白＝下一个词的开斜体：放在空白之后、紧贴下一个词
                        ng = (' ' if ng[:1].isspace() else '') + body + ' *'
                    else:
                        # 紧贴前文＝上一个词的闭斜体：紧贴前一个词，放在新缝最前（him* "— → him* "—）
                        ng = '*' + ng
                    ng = re.sub(r'^ +(?=[,;:.!?])', '', ng)
                if len(re.findall(r'(?<!\\)\*', gap)) != len(re.findall(r'(?<!\\)\*', ng)):
                    stat['star'] += 1
                    continue
            # 证人在这道缝里有空白、我们的新缝没有（And^as → And as）：补一个空格
            if re.search(r'\s', wgap) and not re.search(r'\s', ng) and not ng.endswith('*'):
                ng = ng + ' '
            # 硬闸：只准动标点与空白，字母数字一个不许变（`8^"*` 里的 8 是真字）
            if re.sub(r'[^A-Za-z0-9]', '', gap) != re.sub(r'[^A-Za-z0-9]', '', ng):
                stat['letters'] += 1
                continue
            stat[new] += 1
            # 左取两词、右取一词：同一讲里「the Lord ^」可能出现两次
            lctx = text[ours[li - 2][0]:gap_a] if li >= 2 else text[ours[li][0]:gap_a]
            rctx = ours[ri][2] and text[ours[ri][0]:ours[ri][1]]
            rules.append((f'{n:03d}', lctx, gap, rctx, ng))
            log.append((f'{n:03d}', gap, wgap, new))
    with open(RULES, 'w', encoding='utf-8') as f:
        f.write('# lecture\tleft(前两词)\tgap\tright(后一词)\tnew —— foote_symbols.py 生成；每讲从后往前落\n')
        for r in rules:
            f.write('\t'.join(x.replace('\t', ' ').replace('\n', '\\n') for x in r) + '\n')
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('lecture\tgap\twitness\tkind\n')
        for r in log:
            f.write('\t'.join(x.replace('\t', ' ').replace('\n', '\\n') for x in r) + '\n')
    print('游离符号取证：', dict(stat), f'→ 规则 {len(rules)} 条', file=sys.stderr)


def _settled(ctx, rs):
    """锚里若夹着相邻那条规则的缝，换成它落盘后的样子（只用于「已落过」判断）。"""
    for _, g, _, nw in rs:
        if g.strip() and g in ctx:
            ctx = ctx.replace(g, nw)
    return ctx


def apply():
    """每讲**从后往前**落：相邻两缝都有怪符号时，前一条落了会改掉后一条的左锚。"""
    done = already = 0
    bad = []
    by = {}
    for ln in RULES.read_text(encoding='utf-8').splitlines():
        if ln.startswith('#') or not ln.strip():
            continue
        lec, lctx, gap, rctx, new = (x.replace('\\n', '\n') for x in ln.split('\t'))
        by.setdefault(lec, []).append((lctx, gap, rctx, new))
    for lec, rs in by.items():
        path = SRC / f'{lec}.md'
        text = path.read_text(encoding='utf-8')
        for lctx, gap, rctx, new in reversed(rs):
            c = text.count(lctx + gap + rctx)
            if c == 1:
                text = text.replace(lctx + gap + rctx, lctx + new + rctx)
                done += 1
            elif c == 0 and _settled(lctx, rs) + new + _settled(rctx, rs) in text:
                already += 1
            else:
                bad.append((lec, lctx, gap, c))
        path.write_text(text, encoding='utf-8')
    print(f'落盘 {done}；已落过 {already}；定位不唯一/失败 {len(bad)} {bad[:4]}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    apply() if a.apply else judge()


if __name__ == '__main__':
    main()
