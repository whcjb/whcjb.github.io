#!/usr/bin/env python3
"""拿整页转录当第三证人，与我们的正文逐页比对。**全部在本地跑，不花钱。**

转录只送过一次图（johnstone_transcribe.py）。从此所有判据都在这里加：
文字、斜体范围、边码、脚注标记、标点、段落……想到一类就加一个 check，
重跑一遍几秒钟。

⚠️ 它是**证人不是正文**：这里只报「哪里不一致」，一致与否不等于谁对。
分歧要么回影像定夺，要么看另外两家（ABBYY / tesseract）怎么读。

    python3 scripts/johnstone_vlm_diff.py                 # 全部检查
    python3 scripts/johnstone_vlm_diff.py --check italic  # 只看斜体
    python3 scripts/johnstone_vlm_diff.py --leaves 119,367
"""
import argparse
import difflib
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import extract_johnstone as E
import johnstone_page_proofread as P

ROOT = os.path.dirname(HERE)
VLM = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'vlm')
WORD = re.compile(r"[A-Za-zÆæ][A-Za-zÆæ0-9'’-]*")
QUOTE = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"', '—': '-', '–': '-'})


RE_REF_SPAN = re.compile(r'<span class="jh-ref">.*?</span>', re.S)


def clean_vlm(t):
    """去掉版面标记，留纯正文（含斜体星号）。"""
    t = re.sub(r'^\[HEAD\].*$', '', t, flags=re.M)
    t = re.sub(r'^\[FN:[^\]]*\].*$', '', t, flags=re.M)
    t = re.sub(r'\[SIG:[^\]]*\]', '', t)
    t = re.sub(r'\[FN:[^\]]*\]', '', t)
    t = re.sub(r'\[M:([^\]]*)\]', r'\1 ', t)
    return re.sub(r'\n{3,}', '\n\n', t).strip()


def norm(t, keep_italic=False):
    t = t.translate(QUOTE)
    if not keep_italic:
        t = t.replace('*', '')
    t = t.replace('\\', '')
    return re.sub(r'\s+', ' ', t).strip()


def ital_runs(t):
    """`*…*` 区间 → 用首尾各两个词表示，便于两边对位。"""
    out = []
    for m in re.finditer(r'\*([^*]{1,200})\*', t):
        w = WORD.findall(m.group(1))
        if w:
            out.append(' '.join(w))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', default='all',
                    choices=['all', 'text', 'italic', 'margin'])
    ap.add_argument('--leaves', default='')
    ap.add_argument('--show', type=int, default=40)
    ap.add_argument('--emit', default='',
                    help='把 text 差异写成 manual_fixes 格式的表')
    a = ap.parse_args()

    ab = A.parse_pages(E.load_xml())
    ocr = E.ocr_pages()
    for lf in E.drop_duplicate_leaves(ocr):
        del ocr[lf]
    first, shapes = E.learn_heads(ocr)
    whole = P.published()
    w_words, w_pos = [], []
    for m in P.WORD.finditer(whole):
        w_words.append(m.group(0)); w_pos.append((m.start(), m.end()))

    have = sorted(int(f[:-4]) for f in os.listdir(VLM) if f.endswith('.txt')) \
        if os.path.isdir(VLM) else []
    if a.leaves:
        have = [int(x) for x in a.leaves.split(',')]

    stat = Counter()
    rows = []
    for leaf in have:
        vt = clean_vlm(open(os.path.join(VLM, f'{leaf:04d}.txt'),
                            encoding='utf-8').read())
        raw = E.page_text([p['text'] for p in ab[leaf]['pars']], ocr[leaf],
                          first.get(leaf, ''), shapes)
        ours = P.slice_for(raw, whole, w_words, w_pos)
        if ours:
            # 发布层自己生成的经文出处（`Philippians i. 1, 2`）印面上没有，
            # 要连内容一起去掉，只去标签不够。
            ours = P.strip_markup(RE_REF_SPAN.sub('', ours))
        if not ours:
            stat['锚不上'] += 1; continue
        stat['比对页'] += 1

        if a.check in ('all', 'text'):
            # **比对用纯词，输出取原文区间**。
            # 只拿纯词比：标点前后的空格（1875 年排 `Rome ;`，转录按现代排法
            # 并掉）、引号后的空格、数字间距、脚注上标 —— 这些全是排版样式，
            # 不并掉的话假阳性能把真差异淹掉（实测 2262 vs 真的几百处）。
            # 但输出必须带标点，否则回不到正文里定位。
            def toks(t):
                n = norm(t)
                ws = [(m.group(0).strip("'’‘").lower(), m.start(), m.end())
                      for m in WORD.finditer(n)]
                return n, [w[0] for w in ws], [(w[1], w[2]) for w in ws]

            on, ow, osp = toks(ours)
            vn, vw, vsp = toks(vt)
            sm = difflib.SequenceMatcher(None, ow, vw, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    continue
                if i2 - i1 > 6 or j2 - j1 > 6:
                    continue
                if i1 < 5 or i2 > len(ow) - 5:    # 切片两头是邻页，不算
                    continue
                stat['text'] += 1
                lo = osp[max(0, i1 - 4)][0]; hi = osp[min(len(osp) - 1, i2 + 3)][1]
                vlo = vsp[max(0, j1 - 4)][0] if vsp else 0
                vhi = vsp[min(len(vsp) - 1, j2 + 3)][1] if vsp else 0
                rows.append(('text', leaf, on[lo:hi], vn[vlo:vhi]))

        if a.check in ('all', 'italic'):
            oi, vi = ital_runs(ours), ital_runs(vt)
            sm = difflib.SequenceMatcher(None, oi, vi, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    continue
                stat['italic'] += 1
                rows.append(('italic', leaf, ' | '.join(oi[i1:i2]) or '(无)',
                             ' | '.join(vi[j1:j2]) or '(无)'))

    if a.emit:
        # 第三证人的差异 → 与印面比对同格式的修正表，交给 repair 阶段消费。
        # 两条滤网：
        #   · 我们自己生成的经文出处（`Philippians i. 1, 2` vs 印面 `PHIL.`）
        #     印面上本来就没有，34 处全是假阳性
        #   · 上下文不足 12 个字的不要，定位不住
        import collections
        seen, out = set(), []
        for kind, leaf, x, y in rows:
            if kind != 'text':
                continue
            if 'Philippians' in x and 'PHIL' in y:
                continue
            if len(x) < 12 or (x, y) in seen:
                continue
            seen.add((x, y))
            out.append((leaf, x, y))
        with open(a.emit, 'w', encoding='utf-8') as fh:
            for leaf, x, y in out:
                fh.write(f'{leaf}\t{x}\t{y}\n')
        print(f'→ {a.emit}（{len(out)} 条）')

    print('  '.join(f'{k} {v}' for k, v in stat.most_common()))
    for kind, leaf, x, y in rows[:a.show]:
        print(f'  [{kind}] leaf {leaf}')
        print(f'      我们 {x[:96]}')
        print(f'      转录 {y[:96]}')


if __name__ == '__main__':
    main()
