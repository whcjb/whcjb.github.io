#!/usr/bin/env python3
"""卡里尔缺部 OCR 第 ② 层：对照本按位置判读（old-book-ocr §1 第 ② 层）。

    /usr/bin/python3 scripts/caryl_ocr_witness.py 4            # 试跑：各类判决计数、样例
    /usr/bin/python3 scripts/caryl_ocr_witness.py 4 --apply    # en/ → fixed/；判决记 witness.tsv

对照本（各部见 caryl_ocr.py 文首表）用 IA 自带 OCR 的 hOCR 检索文本（witness/w<部>_hocr_searchtext.txt.gz）。
IA 那层是 tesseract 产的，长 ſ 读成 f，比较时 f/ſ/s 一律折成 s、去大小写、去标点。

对齐：底本每段按约 400 词切块，骨架（折叠后前 4 字母）3 词组投票定偏移，再在偏移窗口内按骨架 difflib 逐词对齐
（对照本非词率 15.6%，按整词对齐时 replace 块两边长短不一、大半被跳过）。对照词比底本短 2 个字母以上的不取（fromit→from 丢了 it）。
判决只针对底本的**非词**（词表见 caryl_ocr_fix），1:1 的 replace 块里才取对照词（n:m 的跳过）：
  confirm  第 ① 层候选与对照词一致（或只差一个字母——对照本自己也有错）→ 用候选
  split    粘连词：对照本给出前半个词、余下是常见词 → 拆开（todesign → to design）
  agree    两份 OCR 读成同一个非词（这一支先于 confirm 判，否则 tobe 会被模糊「印证」成 robe） → 保留（多为当时拼法的真词）；agree-fix：第 ① 层有只改一处、≥ 50 次的常见词 → 改
  witness  第 ① 层无候选或不一致，对照词折回词表后与底本编辑距离 ≤ 2（8 字母以上 ≤ 3）→ 用对照词
  conflict 对照词在词表里但与底本差太远 → 不改，标存疑
  solo     对不上位置，但第 ① 层候选只改一处且本书常见（≥ 50 次）→ 改
  noalign  对不上位置 → 不改，标存疑（发布页 .cy-ocr 灰色虚下划线）
真词（词表里有的）：只在 realword 一种情形下改——对照词是只差一处形近字的另一个真词（trow/know、hin/him），
且前后两组搭配在 TCP 卡里尔语料里都出现过、支持对照词 ≥ 20 倍。
「Ishall」类：对照词 = 底本去掉首字母 I/a 后的词 → 拆开（原先会被 witness 一支改成 Shall，丢了 I）。
"""
import argparse
import collections
import difflib
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_fix as fx  # noqa: E402
import caryl_ocr_ctx as CTX  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
WIT = BASE / 'witness'
RE_TOK = re.compile(r"[A-Za-zſɇéèàæœ]+")


def norm(w):
    w = w.lower().replace('ſ', 's').replace('f', 's').replace('æ', 'ae').replace('œ', 'oe')
    return re.sub(r'[^a-z]', '', w)


@__import__('functools').lru_cache(maxsize=None)
def unfold(wn):
    """折叠后的对照词 → 词表里最常见的原形（fhould → should）。"""
    return FOLD.get(wn)


def build_fold():
    best = {}
    for w, c in fx.LEX.items():
        k = norm(w)
        if c > best.get(k, ('', 0))[1]:
            best[k] = (w, c)
    return {k: v[0] for k, v in best.items()}


FOLD = build_fold()


def edit(a, b):
    a, b = a.lower(), b.lower()
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def skel(t):
    return t[:4]


class Witness:
    """对照本词序列。定位用「骨架」（折叠后取前 4 字母）3 词组投票——对照本是 tesseract 读的胶片，非词率 15.6%，
    整词 4 词组完全相同的太少（第 4 部 73% 的块定位失败）；骨架容得下词尾错。"""
    def __init__(self, part):
        st = gzip.open(WIT / f'w{part}_hocr_searchtext.txt.gz').read().decode('utf-8', 'ignore')
        self.toks = [norm(m.group(0)) for m in RE_TOK.finditer(st)]
        self.toks = [t for t in self.toks if t]
        sk = [skel(t) for t in self.toks]
        self.idx = collections.defaultdict(list)
        for i in range(len(sk) - 2):
            self.idx[tuple(sk[i:i + 3])].append(i)
        self.ptr = 0

    def locate(self, seq):
        sk = [skel(t) for t in seq]
        votes = collections.Counter()
        for i in range(len(sk) - 2):
            hits = self.idx.get(tuple(sk[i:i + 3]))
            if hits and len(hits) <= 6:
                for h in hits:
                    votes[(h - i) // 25] += 1
        if not votes:
            return None
        # 偏好指针附近（两边都按原书顺序排），票数相近时取离指针近的
        b, n = max(votes.items(), key=lambda kv: (kv[1] - abs(kv[0] * 25 - self.ptr) / 4000, kv[1]))
        if n < 3:
            return None
        self.ptr = b * 25 + len(seq)
        return b * 25


def split_by(t, wn):
    """粘连词（todesign、whichusually、themfelves）：对照本给出前半个词 → 拆开。
    两半都须原样是常见词（各 ≥ 20 次），不借第 ① 层的猜测——否则 inordi → inor di、Augusrine → Augu shine。"""
    n = norm(t)
    if len(wn) >= 2 and n.startswith(wn) and len(n) > len(wn) + 1:
        k = len(wn)
        a, rest = t[:k], t[k:]
        if fx.freq(a.lower()) >= 20 and fx.freq(rest.lower()) >= 20 and len(rest) >= 2:
            return a + ' ' + rest
    return None


def tokens_of(md):
    """→ [(起, 止, 原词)]，避开受保护区（旁注、标签、出处行）。"""
    prot = [(m.start(), m.end()) for m in fx.RE_PROTECT.finditer(md)]
    out, k = [], 0
    for m in RE_TOK.finditer(md):
        while k < len(prot) and prot[k][1] <= m.start():
            k += 1
        if k < len(prot) and prot[k][0] <= m.start() < prot[k][1]:
            continue
        out.append((m.start(), m.end(), m.group(0)))
    return out


def judge(md, W, log, slug):
    toks = tokens_of(md)
    seq = [norm(t[2]) for t in toks]
    edits = {}
    for c0 in range(0, len(toks), 400):
        c1 = min(len(toks), c0 + 400)
        off = W.locate(seq[c0:c1])
        wins = None
        if off is not None:
            a = max(0, off - 60)
            b = min(len(W.toks), off + (c1 - c0) + 60)
            wins = (a, W.toks[a:b])
        align = {}
        if wins:
            a, wt = wins
            sm = difflib.SequenceMatcher(None, [skel(x) for x in seq[c0:c1]], [skel(x) for x in wt], autojunk=False)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
                    for k in range(i2 - i1):
                        align[c0 + i1 + k] = wt[j1 + k]
                elif op == 'replace' and i2 - i1 <= 8 and j2 - j1 <= 8:
                    # 长短不等的替换块（对照本错字多，拆词、粘词常见）：块内给每个底本词找编辑距离最近的对照词
                    for k in range(i1, i2):
                        b = seq[c0 + k]
                        d, wbest = min((edit(b, w), w) for w in wt[j1:j2])
                        if d <= max(1, len(b) // 3):
                            align[c0 + k] = wbest
        for i in range(c0, c1):
            s, e, t = toks[i]
            if len(t) >= 2 and (fx.freq(t) or fx.LEX.get(t.lower())):
                # 真词误读（trow/know、hin/him）：对照词是只差一处形近字的另一个真词，且前后搭配支持它 ≥ 20 倍才改
                wn = align.get(i)
                u = unfold(wn) if wn and wn != norm(t) else None
                vow = lambda x: re.sub(r'[aeiouy]', '', x.lower())          # noqa: E731
                if u and u.lower() != t.lower() and 0 < i < len(toks) - 1 and \
                        CTX.UNI.get(t.lower(), 0) < 200 and vow(u) != vow(t) and \
                        u.lower() in {v.lower() for v in fx.step({t.lower()})}:
                    # 常见真词（then、me、he…）不动；只差元音的是拼法变体（receave/receive，对照本可能是别的版次），不动
                    a, b = toks[i - 1][2].lower(), toks[i + 1][2].lower()
                    if CTX.BI.get((a, u.lower()), 0) and CTX.BI.get((u.lower(), b), 0) and \
                            CTX.p_bi(a, u.lower()) * CTX.p_bi(u.lower(), b) >= 20 * CTX.p_bi(a, t.lower()) * CTX.p_bi(t.lower(), b):
                        new = u.capitalize() if t[0].isupper() else u
                        log.append((slug, 'realword', t, new, wn))
                        edits[(s, e)] = new
                continue
            if len(t) <= 2:
                continue
            c = fx.best_fix(t)
            wn = align.get(i)
            if wn is None:
                # 对不上位置：第 ① 层候选只改一处且本书常见（≥ 50 次）才改（200 时 chariots 这类中频词够不上）（mhich→which）；其余留着（多为词表外的真词）
                if c and ' ' not in c and edit(t, c) == 1 and fx.freq(c) >= 50:
                    kind, new = 'solo', c
                else:
                    kind, new = 'noalign', None
            elif wn == norm(t):
                # 两份 OCR 读成同一个非词：多半是当时拼法的真词（frothing、tatling），保留；
                # 但斜体 h/b 之类两家会一起错（upou、beavy、Bebold），第 ① 层若有只改一处的常见词就改。
                # 这一支必须排在模糊印证之前：tobe 两边一致，模糊印证会把它「印证」成 robe。
                if c and edit(t, c) == 1 and fx.freq(c) >= 50:
                    kind, new = 'agree-fix', c
                else:
                    kind, new = 'agree', None
            elif c and (norm(c) == wn or (len(t) > 3 and edit(norm(c), wn) <= 1 and edit(t, c) <= 2)):
                kind, new = 'confirm', c          # 对照本自己也有错（foolish↔soolith），差一个字母仍算印证
            elif len(norm(t)) == len(wn) + 1 and norm(t).endswith(wn) and t[0] in 'IAa' and fx.freq(t[1:].lower()) >= 20:
                kind, new = 'split', t[0] + ' ' + t[1:]   # 「Ishall」：对照本只给 shall，首字母 I 不能丢
            elif split_by(t, wn):
                kind, new = 'split', split_by(t, wn)
            else:
                u = unfold(wn)
                lim = 3 if len(t) >= 8 else 2
                if u and len(u) >= 3 and len(t) - len(u) <= 1 and len(u) - len(t) <= 2 and edit(t, u) <= lim:
                    kind, new = 'witness', (u.capitalize() if t[0].isupper() else u)
                elif u:
                    kind, new = 'conflict', None
                else:
                    kind, new = 'noalign', None
            log.append((slug, kind, t, new or '', wn or ''))
            if new:
                edits[(s, e)] = new
            elif kind in ('noalign', 'conflict') and not fx.EXACT.get(t):
                # 判不了的：灰色虚下划线标出（不标红——其中大半是词表外的当时真词）
                edits[(s, e)] = f'<span class="cy-ocr" title="OCR 存疑：两份扫描都判不了">{t}</span>'
    out, last = [], 0
    for (s, e), new in sorted(edits.items()):
        out.append(md[last:s])
        out.append(new)
        last = e
    out.append(md[last:])
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', type=int)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d = BASE / f'p{a.part}'
    W = Witness(a.part)
    log, outs = [], {}
    for f in sorted((d / 'en').glob('*.md')):
        outs[f.name] = judge(f.read_text(encoding='utf-8'), W, log, f.stem)
    c = collections.Counter(k for _, k, *_ in log)
    nt = sum(len(tokens_of(f.read_text(encoding='utf-8'))) for f in (d / 'en').glob('*.md'))
    print(f'第 {a.part} 部：底本 {nt:,} 词，非词 {len(log):,}（{len(log) / nt:.2%}）：' +
          '，'.join(f'{k} {v:,}' for k, v in c.most_common()), file=sys.stderr)
    for kind in ('confirm', 'witness', 'conflict', 'noalign'):
        xs = [x for x in log if x[1] == kind][:: max(1, c[kind] // 12)][:12]
        print(f'  [{kind}] ' + '；'.join(f'{t}→{n or "·"}〔{w}〕' for _, _, t, n, w in xs), file=sys.stderr)
    if a.apply:
        out = d / 'fixed'
        out.mkdir(exist_ok=True)
        for name, md in outs.items():
            (out / name).write_text(md, encoding='utf-8')
        (d / 'witness.tsv').write_text(''.join('\t'.join(x) + '\n' for x in log), encoding='utf-8')


if __name__ == '__main__':
    main()
