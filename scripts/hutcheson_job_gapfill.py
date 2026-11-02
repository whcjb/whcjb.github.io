#!/usr/bin/env python3
"""约伯记 TCP 缺字 → 语料自证候选（old-book-ocr 第 ① 层）→ gap_pending_approval.tsv

    python3 scripts/hutcheson_job_gapfill.py            # 试跑：分档统计 + 抽样
    python3 scripts/hutcheson_job_gapfill.py --write    # 写 gap_decisions.tsv + gap_pending_approval.tsv

判据整套复用 hutcheson_gapfill.judge（约翰福音那份：lex 全书语料∪web2 唯一候选且本书 ≥3 次；
ctx 同搭配唯一候选 ≥2 次；缺整词/一截/标点/含数字/已知字母<3 一律不碰）。

和约翰福音的区别：**只出待批清单，不写 manual_fixes.tsv**。约翰福音当时语料档是直接落的；
2026-10-16 起的规矩是「补缺字只有证人同位读出且看图核过的可直接落，语料自证/上下文/推补
一律列清单待用户同意」。本书 1669 年版公开渠道没有影像（2026-11-02 查：IA bim 胶片集
无此书、Google Books 1669 本与一种年份不明重印本都不开放页面），没有可看图的证人，
所以这里判出的全部是待批。用户同意后，把同意的行抄进 manual_fixes.tsv 再发布。
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hutcheson_common as hc  # noqa: E402

hc.use('job')
import hutcheson_gapfill as g  # noqa: E402

DEC = hc.RAW / 'gap_decisions.tsv'
PENDING = hc.RAW / 'gap_pending_approval.tsv'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    freq, forms, tri = g.build_corpus()
    lex = g.load_lex()
    rows = []
    tally = collections.Counter()
    for f in sorted(hc.SRC.glob('*.md'), key=lambda p: (not p.stem.isdigit(), int(p.stem) if p.stem.isdigit() else 0, p.stem)):
        slug = f.stem
        md = f.read_text(encoding='utf-8')
        seen = set()
        for i, m in enumerate(hc.TOK.finditer(md)):
            s, e = hc.gap_word(md, m)
            if (s, e) in seen:
                continue
            seen.add((s, e))
            word = md[s:e]
            fixed, ev = g.judge(word, md, s, e, freq, forms, tri, lex)
            tally[ev.split(':')[0]] += 1
            rows.append((slug, i, word, fixed or '?', ev))

    print('分档：' + '  '.join(f'{k} {v}' for k, v in tally.most_common()), file=sys.stderr)
    done = [r for r in rows if r[3] != '?']
    print(f'语料可判 {len(done)} / {len(rows)}（全部待批，不落盘）', file=sys.stderr)
    for r in done[::max(1, len(done) // 25)]:
        print(f'  {r[0]}#{r[1]}  {r[2]!r} → {r[3]!r}  [{r[4]}]', file=sys.stderr)
    if a.write:
        DEC.write_text('# slug\tord\ttcp_word\t判读(?=不判)\t证据\n'
                       + '\n'.join('\t'.join(map(str, r)) for r in rows) + '\n', encoding='utf-8')
        PENDING.write_text('# 语料自证候选，**未经同意不落**。同意的行原样抄进 manual_fixes.tsv。\n'
                           '# slug\tord\ttcp_word\t候选\t证据\n'
                           + '\n'.join('\t'.join(map(str, r)) for r in done) + '\n', encoding='utf-8')
        print(f'写入 {DEC.name} {len(rows)} 行，{PENDING.name} {len(done)} 条', file=sys.stderr)


if __name__ == '__main__':
    main()
