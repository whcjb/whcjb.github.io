#!/usr/bin/env python3
"""TCP 缺字母记号 → 语料自证判读（old-book-ocr 第 ① 层）→ manual_fixes.tsv

    python3 scripts/leighton_gapfill.py            # 试跑：分档统计 + 抽样
    python3 scripts/leighton_gapfill.py --apply    # 写 gap_decisions.tsv / manual_fixes.tsv

逻辑与 hutcheson_gapfill.py 完全相同（守卫、两档证据 lex / ctx、大小写还原），只换书目路径；
判据说明见那份脚本的文档。第 ②③ 层（1864 重印本按位判读 + 1693/1694 同版影像复核）的
结论在 gap_review_witness.tsv，导出时一并并入。
"""
import argparse
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leighton_common as hc  # noqa: E402

RAW = hc.RAW
DEC = RAW / 'gap_decisions.tsv'
WEB2 = Path('/usr/share/dict/web2')

RE_WORD = re.compile(r"[A-Za-z]+")
PUNCT = '.,;:()?!\'"[]’‘'


def plain(md):
    return re.sub(r'<[^>]+>', ' ', md).replace('*', ' ')


def build_corpus():
    """本书词频（不分大小写）+ 每个词的大小写形态 + 三元搭配。
    缺字所在的词不进语料（`•` 把它切碎了，碎片也不收）。"""
    freq = collections.Counter()
    forms = collections.defaultdict(collections.Counter)
    tri = collections.Counter()
    for f in sorted(hc.SRC.glob('*.md')):
        toks = plain(f.read_text(encoding='utf-8')).split()
        clean = []
        for t in toks:
            core = t.strip(PUNCT)
            if hc.TOK.search(t) or not re.fullmatch(r'[A-Za-z]+', core):
                clean.append(None)
                continue
            freq[core.lower()] += 1
            forms[core.lower()][core] += 1
            clean.append(core.lower())
        for a, b, c in zip(clean, clean[1:], clean[2:]):
            if a and b and c:
                tri[(a, b, c)] += 1
    return freq, forms, tri


def neighbours(md, a, b):
    """缺字词前后各一个纯字母词（小写），跨了标点就不算邻词。"""
    left = plain(md[:a]).split()
    right = plain(md[b:b + 200]).split()
    lw = left[-1] if left else ''
    rw = right[0] if right else ''
    lw = lw.lower() if re.fullmatch(r'[A-Za-z]+', lw) else None
    rw = rw.lower() if re.fullmatch(r'[A-Za-z]+', rw) else None
    return lw, rw


def judge(word, md, a, b, freq, forms, tri, lex):
    """→ (fixed 或 None, 证据)"""
    if re.search(r'〈|▪', word):
        return None, 'skip:非字母缺口'
    lead = len(word) - len(word.lstrip(PUNCT))
    trail = len(word) - len(word.rstrip(PUNCT))
    core = word[lead:len(word) - trail] if trail else word[lead:]
    if re.search(r'\d', core):
        return None, 'skip:含数字'
    if not re.fullmatch(r'[A-Za-z•]+', core):
        return None, 'skip:非纯字母'
    if len(re.sub('•', '', core)) < 3:
        return None, 'skip:已知字母<3'
    rx = re.compile('^' + ''.join('.' if c == '•' else re.escape(c.lower()) for c in core) + '$')
    cands = sorted({w for w in freq if rx.match(w)} | {w for w in lex.get(len(core), ()) if rx.match(w)})
    if not cands:
        return None, 'none:无候选'
    pick, ev = None, None
    if len(cands) == 1 and freq[cands[0]] >= 3:
        pick, ev = cands[0], f'lex:{cands[0]}×{freq[cands[0]]}'
    elif len(cands) == 1:
        return None, f'rare:{cands[0]}×{freq[cands[0]]}'
    else:
        lw, rw = neighbours(md, a, b)
        if lw and rw:
            hits = [(c, tri[(lw, c, rw)]) for c in cands if tri[(lw, c, rw)]]
            if len(hits) == 1 and hits[0][1] >= 2:
                pick, ev = hits[0][0], f'ctx:{lw} {hits[0][0]} {rw}×{hits[0][1]}'
        if not pick:
            return None, 'ambig:' + '/'.join(f'{c}×{freq[c]}' for c in
                                             sorted(cands, key=lambda c: -freq[c])[:4])
    # 还原大小写
    if core.isupper() or (core.replace('•', '').isupper() and len(core) > 1):
        fixed = pick.upper()
    else:
        out = []
        for i, c in enumerate(core):
            if c != '•':
                out.append(c)
                continue
            ch = pick[i]
            if i == 0:
                best = forms[pick].most_common(1)
                ch = best[0][0][0] if best else ch
            out.append(ch)
        fixed = ''.join(out)
    return word[:lead] + fixed + (word[len(word) - trail:] if trail else ''), ev


def load_lex():
    by_len = collections.defaultdict(set)
    if WEB2.exists():
        for w in WEB2.read_text(encoding='utf-8').split():
            if w.islower():
                by_len[len(w)].add(w)
    return by_len


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    freq, forms, tri = build_corpus()
    lex = load_lex()
    rows = []
    tally = collections.Counter()
    for f in sorted(hc.SRC.glob('*.md'), key=lambda p: (not p.stem.isdigit(), int(p.stem) if p.stem.isdigit() else 0, p.stem)):
        slug = f.stem
        md = f.read_text(encoding='utf-8')
        seen = set()
        for i, m in enumerate(hc.TOK.finditer(md)):
            s, e = hc.gap_word(md, m)
            if (s, e) in seen:          # 同一个词里的第二处记号：随第一处一起判
                continue
            seen.add((s, e))
            word = md[s:e]
            fixed, ev = judge(word, md, s, e, freq, forms, tri, lex)
            tally[ev.split(':')[0]] += 1
            rows.append((slug, i, word, fixed or '?', ev))

    print('分档：' + '  '.join(f'{k} {v}' for k, v in tally.most_common()), file=sys.stderr)
    # 2026-10-16 用户规定：「不能猜，推断必须经过同意」。语料自证（lex / ctx）属推断，
    # 只留在 gap_decisions.tsv 当候选，**不直接导出到 manual_fixes.tsv**；
    # 修正表只从看图复核过的证人表、以及经用户同意的推断表（gap_review_approved.tsv）导出。
    cand = [r for r in rows if r[3] != '?']
    done = []
    print(f'语料候选 {len(cand)} / {len(rows)}（不直接落盘，待证人核对或用户同意）', file=sys.stderr)
    for r in cand[::max(1, len(cand) // 25)]:
        print(f'  {r[0]}#{r[1]}  {r[2]!r} → {r[3]!r}  [{r[4]}]', file=sys.stderr)
    # 证人（1864 重印本定位 + 1693/1694 同版影像复核）：语料判不了的那些，裁出页图**人工逐条看过**
    # 的结论（gap_review_witness.tsv，leighton_review.py 录入）一并导出。judge 的自动判读
    # 只是预填值，不直接落盘。语料档已判的不被覆盖。
    for wit in (RAW / 'gap_review_witness.tsv', RAW / 'gap_review_approved.tsv'):
        if not wit.exists():
            continue
        have = {(r[0], int(r[1])) for r in done}
        for ln in wit.read_text(encoding='utf-8').splitlines():
            if not ln or ln.startswith('#'):
                continue
            f = ln.split('\t')
            if f[3] != '?' and (f[0], int(f[1])) not in have:
                done.append((f[0], int(f[1]), f[2], f[3], f[4]))
    print(f'  并入复核表后共 {len(done)} 条', file=sys.stderr)
    if a.apply:
        DEC.write_text('# slug\tord\ttcp_word\t判读(?=不判)\t证据\n'
                       + '\n'.join('\t'.join(map(str, r)) for r in rows) + '\n', encoding='utf-8')
        hc.FIXES.write_text(
            '# 由 leighton_gapfill.py 从 gap_decisions.tsv 导出，勿手改；手工判读另加在文件末尾 MANUAL 段之后\n'
            + '\n'.join(f'{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t{r[4]}' for r in done) + '\n', encoding='utf-8')
        print(f'写入 {DEC.name} {len(rows)} 行，{hc.FIXES.name} {len(done)} 条', file=sys.stderr)


if __name__ == '__main__':
    main()
