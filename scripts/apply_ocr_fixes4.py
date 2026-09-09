#!/usr/bin/env python3
"""第四轮：**先把 raw 页对齐到正文，再在页内落点**——收 held3 的尾巴。

为什么还要换一次机制
--------------------
第三轮（apply_ocr_fixes3.py）用「上下文贴合度」定位，比第二轮的「章内唯一命中」
稳得多，但候选池仍然是**整章**。约翰福音一章两三万字，`情`/`说` 这种一两字的
目标串一章里出现七八次，贴合度分不开，于是 136 条被守卫拦下：

    贴合度不足 41 · 章内无此串 13 · 疑似改写 70 · PDF文本层否证 9 · 其它 3

而判读报告每条都带**页号**，raw 页文件就在 `calvin_raw/john-scan/ocr/page_NNNN.md`。
一页 600–900 字，把它对齐到章的 CJK 流上，能得到一个 ±5 字精度的区间
（实测 p74 覆盖率 0.98，跨度 4199–4846）。候选池从「一章」缩到「一页」，
`说` 这种字在一页里通常只剩 1–2 处，落点就唯一了。

两类活
------
A. **短串替换**（原 held 里的 贴合度不足 / 章内无此串 / 上下文太短）
   页内找 tcj → 仍多处则用上下文贴合度分辨（判据与第三轮相同）。
   页内找不到 tcj、却找得到 icj → 正文本来就是对的，跳过。

B. **整段类**（原 held 里 53 条 `文本=「（整段缺失）」`）
   这些不是「缺段」——commit a71de0062 已核过内容都在，是判读侧 clean_raw
   删标题行造成的假阳。但模型抄下来的**整段影像文本**是逐字的，把它对齐到
   页区间上，逐个 diff 出来的短差异反而是**位置最确凿**的一批修正：
   两侧各有 ≥12 字严格相等的锚，中间差 ≤3 字。
   实测 p74 的「这是因为(他)出示的证据」就是这么捞出来的。

安全闸：沿用第三轮的圈号/他祂假阳性过滤与 PDF 文本层否证（两次独立 OCR
一致 → 否掉判读那一票）；B 类另加「两侧锚 ≥12 字」与「差异 ≤3 字」。

用法：
    python3 scripts/apply_ocr_fixes4.py --book john --dry-run
    python3 scripts/apply_ocr_fixes4.py --book john --apply
"""
import argparse
import difflib
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from apply_ocr_fixes3 import (  # noqa: E402
    BOOKS, PdfWitness, cj, cjk_index, is_false_positive, locate, map_pages,
    parse_report, splice)

CJK = re.compile(r'[一-鿿]')

# 底本**自己**印错的字：判读没读错，但也不能照抄。
# 「貌视」——p314 / p345 两处，900 dpi 渲染出来确实是「貌」（豸+皃，无艹头），
# 而同书 p34 / p80 / p101 的「藐视」渲染出来艹头清清楚楚。也就是说这两处是
# 底本自身的错字，不是我们的 OCR 错。正文保留正字「藐视」，不回填。
# （第三轮把这两条归到「PDF文本层否证」，理由记反了——PDF 文本层其实也读作
#  「貌」，两次 OCR 都没错，错的是底本。结论一样，理由更正在此。）
SOURCE_TYPOS = {('藐视', '貌视'), ('藐', '貌')}

PAD = 40             # 页区间两侧的余量（对齐块边缘会差几个字）
MIN_ANCHOR = 12      # B 类：差异两侧各要有多少字严格相等
MAX_DELTA = 3        # B 类：一处差异最多几个字
MIN_FIT = 0.70
MIN_MARGIN = 0.06


def page_span(rawdir, pg, stream):
    """raw 第 pg 页在章 CJK 流里的区间 → (lo, hi, 覆盖率) 或 None"""
    f = rawdir / f'page_{pg:04d}.md'
    if not f.exists():
        return None
    rs = cj(re.sub(r'<[^>]+>', '', f.read_text(encoding='utf-8')))
    if len(rs) < 60:
        return None
    sm = difflib.SequenceMatcher(None, stream, rs, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 8]
    if not blocks:
        return None
    lo = max(0, min(b.a for b in blocks) - PAD)
    hi = min(len(stream), max(b.a + b.size for b in blocks) + PAD)
    cover = sum(b.size for b in blocks) / len(rs)
    return lo, hi, cover


def micro_diffs(imgcj, spancj):
    """整段影像文本 vs 正文页区间 → [(相对落点, 原串, 新串)]

    只取「两侧各 ≥MIN_ANCHOR 字严格相等、中间 ≤MAX_DELTA 字」的差异；
    别的（大段增删、连续多处小差）一律不碰——那多半是模型自己抄漏或改写。
    """
    sm = difflib.SequenceMatcher(None, spancj, imgcj, autojunk=False)
    ops = sm.get_opcodes()
    out = []
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == 'equal':
            continue
        if (i2 - i1) > MAX_DELTA or (j2 - j1) > MAX_DELTA:
            continue
        prev = ops[k - 1] if k else None
        nxt = ops[k + 1] if k + 1 < len(ops) else None
        if not prev or prev[0] != 'equal' or prev[2] - prev[1] < MIN_ANCHOR:
            continue
        if not nxt or nxt[0] != 'equal' or nxt[2] - nxt[1] < MIN_ANCHOR:
            continue
        out.append((i1, spancj[i1:i2], imgcj[j1:j2]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True, choices=sorted(BOOKS))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--held', help='只处理这个 tsv 里列出的条目（默认 logs/held3_<book>.tsv）')
    ap.add_argument('--all', action='store_true',
                    help='处理判读报告里的全部条目（罗马书那种「前几轮机制不可信、'
                         '整卷回滚重做」的场合用）')
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        sys.exit('要 --apply 或 --dry-run')
    cfg = BOOKS[a.book]

    pubtexts = {f: f.read_text(encoding='utf-8')
                for f in sorted((ROOT / cfg['pub']).glob('*.md'))}
    recs = parse_report(ROOT / cfg['report'])
    if a.all:
        heldfile = Path('(全部条目)')
    else:
        heldfile = Path(a.held) if a.held else ROOT / f'logs/held3_{a.book}.tsv'
        keys = set()
        for ln in heldfile.read_text(encoding='utf-8').splitlines():
            c = ln.split('\t')
            if len(c) >= 4:
                keys.add((int(c[0]), c[2], c[3]))
        recs = [r for r in recs if (r[0], r[2], r[1]) in keys]
    pagemap = map_pages(cfg, pubtexts)
    rawdir = ROOT / cfg['raw']
    witness = PdfWitness(cfg['verify_pdf']) if cfg.get('verify_pdf') else None
    print(f'待收尾条目 {len(recs)}（{heldfile.name}）；页→章映射 {len(pagemap)} 页\n')

    if a.apply:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = ROOT / f'logs/bak4_{a.book}_{stamp}'
        bak.mkdir(parents=True, exist_ok=True)
        for f in pubtexts:
            shutil.copy(f, bak / f.name)
        print(f'已备份 → {bak}\n')

    stat, applied, held = Counter(), [], []
    spans = {}

    for pg, img, txt, ctx in recs:
        f = pagemap.get(pg)
        if not f:
            stat['跳过·该页无章映射'] += 1
            held.append((pg, '?', txt, img, '该页无章映射')); continue
        fp, why = is_false_positive(img, txt)
        if fp:
            stat[why] += 1; continue
        if (cj(txt), cj(img)) in SOURCE_TYPOS:
            stat['跳过·底本自身错字'] += 1; continue
        if cj(txt) == cj(img):
            # 汉字部分完全一样，差的是圈号/标点——发布时已经归一成
            # `**约翰福音 N:V。**` 前缀了，回填等于空转
            stat['跳过·汉字无差异'] += 1; continue

        body = pubtexts[f]
        stream, idxmap = cjk_index(body)
        sp = spans.get((pg, f))
        if sp is None:
            sp = page_span(rawdir, pg, stream)
            spans[(pg, f)] = sp
        if not sp:
            stat['跳过·页对不齐'] += 1
            held.append((pg, f.name, txt, img, '页对不齐')); continue
        lo, hi, cover = sp
        if cover < 0.5:
            stat['跳过·页对齐覆盖率低'] += 1
            held.append((pg, f.name, txt, img, f'覆盖率{cover:.2f}')); continue

        icj, tcj, ctxcj = cj(img), cj(txt), cj(ctx)
        span = stream[lo:hi]

        # ── B 类：整段影像文本，逐差回填 ───────────────────────────────
        if len(icj) >= 25 and len(tcj) <= 4:
            hits = micro_diffs(icj, span)
            if not hits:
                stat['整段·无可靠短差'] += 1
                held.append((pg, f.name, txt, img[:24] + '…', '整段·无短差')); continue
            for rel, old, new in hits:
                if witness and witness.refutes(pg, old, new):
                    stat['整段·PDF文本层否证'] += 1
                    held.append((pg, f.name, old, new, '整段·PDF否证')); continue
                pos = lo + rel
                nb = splice(body, idxmap, pos, old, new) if old else None
                if old and not new:
                    nb = None                      # 只删字不做
                if nb is None:
                    stat['整段·无法回写'] += 1
                    held.append((pg, f.name, old, new, '整段·无法回写')); continue
                body = nb
                pubtexts[f] = body
                stream, idxmap = cjk_index(body)
                stat['整段·已应用'] += 1
                applied.append((pg, f.name, old, new,
                                f'整段对齐 …{span[max(0, rel-8):rel]}[{old}→{new}]'
                                f'{span[rel+len(old):rel+len(old)+8]}…'))
            continue

        # ── A 类：短串替换，页内落点 ──────────────────────────────────
        if not tcj:
            stat['跳过·错误串无汉字'] += 1; continue
        if witness and witness.refutes(pg, tcj, icj):
            stat['跳过·PDF文本层否证'] += 1
            held.append((pg, f.name, txt, img, 'PDF文本层否证')); continue
        if tcj not in span:
            if icj and icj in span:
                stat['跳过·正文已正确'] += 1; continue
            stat['退回·页内无此串'] += 1
            held.append((pg, f.name, txt, img, '页内无此串')); continue

        n_in_span = span.count(tcj)
        if len(ctxcj) >= 8:
            rel, score, after, before, margin = locate(span, tcj, icj, ctxcj)
            tag = f'页内{n_in_span}处 贴合={score:.2f} 方向={after-before:+.2f} 领先={margin:.2f}'
            if before >= 0.95 and after <= before:
                stat['跳过·正文已正确'] += 1; continue
            if n_in_span > 1 and (score < MIN_FIT or margin < MIN_MARGIN):
                stat['退回·页内落点仍不唯一'] += 1
                held.append((pg, f.name, txt, img, tag)); continue
            if n_in_span == 1 and score < 0.55:
                stat['退回·上下文与页内唯一处对不上'] += 1
                held.append((pg, f.name, txt, img, tag)); continue
        else:
            if n_in_span > 1:
                stat['退回·上下文太短且页内多处'] += 1
                held.append((pg, f.name, txt, img, f'页内{n_in_span}处·无上下文')); continue
            rel = span.index(tcj)
            tag = f'页内唯一·无上下文'

        # 缺字类：正文可能早就是完整写法（第三轮的坑）
        if len(icj) > len(tcj) and tcj in icj:
            if any(o <= rel < o + len(icj) or rel <= o < rel + len(tcj)
                   for o in (m.start() for m in re.finditer(re.escape(icj), span))):
                stat['跳过·正文已是完整写法'] += 1; continue

        pos = lo + rel
        nb = splice(body, idxmap, pos, tcj, icj)
        if nb is None:
            stat['退回·落点跨标点无法回写'] += 1
            held.append((pg, f.name, txt, img, '落点跨标点')); continue
        pubtexts[f] = nb
        stat['已应用'] += 1
        applied.append((pg, f.name, txt, img,
                        f'{tag} …{span[max(0, rel-8):rel]}[{tcj}→{icj}]'
                        f'{span[rel+len(tcj):rel+len(tcj)+8]}…'))

    for k, v in stat.most_common():
        print(f'  {k}: {v}')

    if a.apply:
        for f, t in pubtexts.items():
            f.write_text(t, encoding='utf-8')
        print(f'\n✓ 写回 {len(pubtexts)} 个文件')
    else:
        print('\n（dry-run，未写回）')

    (ROOT / f'logs/applied4_{a.book}.tsv').write_text(
        '\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{how}' for p, fn, t, i, how in applied)
        + '\n', encoding='utf-8')
    (ROOT / f'logs/held4_{a.book}.tsv').write_text(
        '\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{r}' for p, fn, t, i, r in held)
        + '\n', encoding='utf-8')
    print(f'明细 → logs/applied4_{a.book}.tsv / held4_{a.book}.tsv')


if __name__ == '__main__':
    main()
